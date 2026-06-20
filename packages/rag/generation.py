from pathlib import Path

import structlog
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from packages.llm_serving import LLMClient, LLMMessage, LLMRequest
from packages.observability import get_tracer
from packages.observability.metrics import (
    generation_duration,
    generation_token_count,
    generation_total,
)
from packages.rag.search import SearchResult

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class GenerationConfig(BaseSettings):
    generation_model_name: str = Field(
        alias="GCP_GENERATION_MODEL", default="gemini-3.1-pro-preview"
    )
    prompt_version: str = Field(default="concise")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Citation(BaseModel):
    id: int
    source: str
    snippet: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    context_passages: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class GenerationService:
    def __init__(self, llm_client: LLMClient, config: GenerationConfig | None = None):
        self.config = config or GenerationConfig()
        self.llm_client = llm_client

        prompt_config_path = Path("configs/prompts.yaml")
        if prompt_config_path.exists():
            with open(prompt_config_path, encoding="utf-8") as f:
                prompts_data = yaml.safe_load(f)
            self.prompts = prompts_data.get("rag", {}).get("generation", {})
        else:
            self.prompts = {}
            logger.warning("generation.prompt_config_missing", path=str(prompt_config_path))

    async def generate_answer(
        self,
        query: str,
        search_results: list[SearchResult],
        chat_history: list[dict] | None = None,
        model_override: str | None = None,
    ) -> AnswerResponse:
        """Generates an answer from search context and formats the citations."""
        if not search_results:
            return AnswerResponse(
                answer=(
                    "I could not find any relevant information in the"
                    "knowledge base to answer your question."
                ),
                citations=[],
            )

        context_parts = []
        citations_meta = []
        for idx, result in enumerate(search_results, start=1):
            context_parts.append(f"[Source {idx}] File: {result.source}\nContent:\n{result.text}\n")

            snippet = (
                result.text[:200].strip() + "..." if len(result.text) > 200 else result.text.strip()
            )

            citations_meta.append(Citation(id=idx, source=result.source, snippet=snippet))

        context_str = "\n".join(context_parts)

        with tracer.start_as_current_span("generation.build_prompt") as span:
            prompt_def = self.prompts.get(self.config.prompt_version, {})

            # Fallback to defaults if missing
            system_instruction = prompt_def.get(
                "system_instruction", "You are a helpful assistant."
            )
            user_prompt_template = prompt_def.get(
                "user_prompt_template",
                "{history_str}Context:\n{context_str}\n\nQuestion:\n{query}\n\nAnswer:\n",
            )

            history_str = ""
            if chat_history:
                history_parts = ["Chat History:"]
                for msg in chat_history:
                    role = "User" if msg.get("role") == "user" else "AI"
                    history_parts.append(f"{role}: {msg.get('content')}")
                history_str = "\n".join(history_parts) + "\n\n"

            user_prompt = user_prompt_template.format(
                history_str=history_str,
                context_str=context_str,
                query=query,
            )
            span.set_attribute("generation.prompt_length", len(user_prompt))

        selected_model = model_override or self.config.generation_model_name
        logger.info("generation.started", model=selected_model, context_length=len(search_results))

        import time

        start_time = time.perf_counter()
        try:
            req = LLMRequest(
                messages=[LLMMessage(role="user", content=user_prompt)],
                model=selected_model,
                temperature=0.2,
                max_tokens=2048,
                system_instruction=system_instruction,
            )
            with tracer.start_as_current_span("generation.llm_call") as span:
                span.set_attribute("generation.model", selected_model)
                span.set_attribute("generation.context_passages", [r.text for r in search_results])
                response = await self.llm_client.generate(req)

        except Exception as e:
            duration = time.perf_counter() - start_time
            generation_duration.record(duration, {"model": selected_model})
            generation_total.add(1, {"model": selected_model, "status": "failed"})
            logger.error("generation.failed", model=selected_model, error=str(e), exc_info=True)
            raise RuntimeError(f"Generation failed: {e}") from e

        else:
            duration = time.perf_counter() - start_time
            generation_duration.record(duration, {"model": selected_model})
            generation_total.add(1, {"model": selected_model, "status": "completed"})
            if response.usage:
                generation_token_count.record(
                    response.usage.total_tokens, {"model": selected_model}
                )

            try:
                answer_text = (
                    response.text
                    or "I cannot answer this question due to safety policy restrictions."
                )
            except Exception:
                answer_text = "I cannot answer this question due to safety policy restrictions."

            logger.info("generation.completed", model=selected_model)
            return AnswerResponse(
                answer=answer_text,
                citations=citations_meta,
                context_passages=[r.text for r in search_results],
            )

    async def generate_answer_stream(
        self,
        query: str,
        search_results: list[SearchResult],
        model_override: str | None = None,
    ):
        """Generates an answer from search context and formats the citations as a stream.
        Yields dicts representing the events:
        - {"type": "chunk", "text": "..."}
        - {"type": "done", "citations": [...], "context_passages": [...]}
        - {"type": "error", "message": "..."}
        """
        if not search_results:
            yield {
                "type": "chunk",
                "text": (
                    "I could not find any relevant information in "
                    "the knowledge base to answer your question."
                ),
            }
            yield {"type": "done", "citations": [], "context_passages": []}
            return

        context_parts = []
        citations_meta = []
        for idx, result in enumerate(search_results, start=1):
            context_parts.append(f"[Source {idx}] File: {result.source}\nContent:\n{result.text}\n")

            snippet = (
                result.text[:200].strip() + "..." if len(result.text) > 200 else result.text.strip()
            )

            citations_meta.append(
                Citation(id=idx, source=result.source, snippet=snippet).model_dump()
            )

        context_str = "\n".join(context_parts)

        with tracer.start_as_current_span("generation.build_prompt") as span:
            prompt_def = self.prompts.get(self.config.prompt_version, {})

            system_instruction = prompt_def.get(
                "system_instruction", "You are a helpful assistant."
            )
            user_prompt_template = prompt_def.get(
                "user_prompt_template",
                "{history_str}Context:\n{context_str}\n\nQuestion:\n{query}\n\nAnswer:\n",
            )

            user_prompt = user_prompt_template.format(
                history_str="",
                context_str=context_str,
                query=query,
            )
            span.set_attribute("generation.prompt_length", len(user_prompt))

        selected_model = model_override or self.config.generation_model_name
        logger.info(
            "generation.started",
            model=selected_model,
            context_length=len(search_results),
            stream=True,
        )

        import time

        start_time = time.perf_counter()
        total_tokens = 0
        try:
            req = LLMRequest(
                messages=[LLMMessage(role="user", content=user_prompt)],
                model=selected_model,
                temperature=0.2,
                max_tokens=2048,
                system_instruction=system_instruction,
            )
            with tracer.start_as_current_span("generation.llm_call") as span:
                span.set_attribute("generation.model", selected_model)
                span.set_attribute("generation.context_passages", [r.text for r in search_results])
                response_stream = self.llm_client.generate_stream(req)
                async for chunk in response_stream:
                    if chunk.usage:
                        total_tokens += chunk.usage.total_tokens
                    if chunk.text:
                        yield {"type": "chunk", "text": chunk.text}

            duration = time.perf_counter() - start_time
            generation_duration.record(duration, {"model": selected_model})
            generation_total.add(1, {"model": selected_model, "status": "completed"})
            if total_tokens > 0:
                generation_token_count.record(total_tokens, {"model": selected_model})

            logger.info("generation.completed", model=selected_model, stream=True)
            yield {
                "type": "done",
                "citations": citations_meta,
                "context_passages": [r.text for r in search_results],
            }

        except Exception as e:
            duration = time.perf_counter() - start_time
            generation_duration.record(duration, {"model": selected_model})
            generation_total.add(1, {"model": selected_model, "status": "failed"})
            logger.error(
                "generation.failed", model=selected_model, error=str(e), stream=True, exc_info=True
            )
            yield {"type": "error", "message": f"Generation failed: {e}"}
