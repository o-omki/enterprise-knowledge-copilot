import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException
from nemoguardrails import LLMRails, RailsConfig
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from packages.observability import configure_logging, setup_tracing
from packages.safety import contains_jailbreak_local, contains_off_topic_local, redact_local_pii

configure_logging("guardrails", os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")

rails_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rails_app
    logger.info("guardrails.engine.initializing")
    try:
        gcp_project = os.getenv("GCP_PROJECT_ID")
        if gcp_project:
            os.environ["GOOGLE_CLOUD_PROJECT"] = gcp_project
            os.environ["GCP_PROJECT"] = gcp_project
            logger.info("guardrails.gcp_mapped", project=gcp_project)

        if not os.path.exists(CONFIG_DIR):
            logger.error("guardrails.config_dir_missing", path=CONFIG_DIR)
        else:
            config = RailsConfig.from_path(CONFIG_DIR)
            rails_app = LLMRails(config)
            logger.info("guardrails.engine.initialized")
    except Exception as e:
        logger.error("guardrails.engine.init_failed", error=str(e), exc_info=True)
    yield


app = FastAPI(title="Safety Guardrails Microservice", version="1.0.0", lifespan=lifespan)
setup_tracing(app, service_name="guardrails")
app.mount("/metrics", make_asgi_app())


class InputValidationRequest(BaseModel):
    query: str


class InputValidationResponse(BaseModel):
    is_safe: bool = Field(
        description="Flag indicating if the query is safe from jailbreaks and prompt injection."
    )
    is_off_topic: bool = Field(description="Flag indicating if the query is off-topic.")
    filtered_query: str = Field(
        description=("Masked or redacted query if PII was detected, otherwise original query.")
    )
    refusal_message: str | None = Field(
        default=None, description="The refusal message to return if query is blocked."
    )


class OutputValidationRequest(BaseModel):
    query: str
    response: str
    context: list[str] = Field(description="List of text chunks retrieved as grounding context.")


class OutputValidationResponse(BaseModel):
    is_grounded: bool = Field(
        description="Flag indicating if the generated answer is fully grounded in context."
    )
    refusal_message: str | None = Field(
        default=None,
        description="Fallback refusal message to return if hallucination is detected.",
    )


@app.get("/health")
@app.get("/health/live")
async def liveness():
    """Simple check if container is running."""
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    """Check if guardrails model and engine are fully initialized."""
    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")
    return {"status": "ready"}


@app.post("/validate/input", response_model=InputValidationResponse)
async def validate_input(request: InputValidationRequest):
    """Evaluates query against input rails: jailbreaks, off-topic, and PII masking."""
    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")

    try:
        logger.info("guardrails.input.checking", query=request.query)

        if contains_jailbreak_local(request.query):
            logger.warning("guardrails.blocked", check_type="local_jailbreak", query=request.query)
            return InputValidationResponse(
                is_safe=False,
                is_off_topic=False,
                filtered_query=request.query,
                refusal_message=(
                    "I cannot fulfill this request as it violates enterprise security policies."
                ),
            )

        if contains_off_topic_local(request.query):
            logger.warning("guardrails.blocked", check_type="local_off_topic", query=request.query)
            return InputValidationResponse(
                is_safe=True,
                is_off_topic=True,
                filtered_query=request.query,
                refusal_message=(
                    "I am only authorized to assist with internal enterprise documentation queries."
                ),
            )

        res_obj = await rails_app.generate_async(
            messages=[{"role": "user", "content": request.query}]
        )

        if res_obj and not isinstance(res_obj, str) and not isinstance(res_obj, dict):
            # Internal object response fallback
            try:
                res = res_obj[0].get("content")
            except Exception:
                res = str(res_obj)
        else:
            res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)

        filtered_query = redact_local_pii(request.query)

        is_safe = True
        is_off_topic = False
        refusal_message = None

        if "I cannot fulfill this request" in res or "violates enterprise security policies" in res:
            is_safe = False
            refusal_message = res
            logger.warning(
                "guardrails.blocked", check_type="rails_jailbreak", query=request.query, reason=res
            )
        elif (
            "only authorized to assist with internal enterprise" in res or "refuse off topic" in res
        ):
            is_off_topic = True
            refusal_message = res
            logger.warning(
                "guardrails.blocked", check_type="rails_off_topic", query=request.query, reason=res
            )

        logger.info(
            "guardrails.input.validated",
            is_safe=is_safe,
            is_off_topic=is_off_topic,
            filtered=filtered_query,
        )
        return InputValidationResponse(
            is_safe=is_safe,
            is_off_topic=is_off_topic,
            filtered_query=filtered_query,
            refusal_message=refusal_message,
        )
    except Exception as e:
        logger.error("guardrails.input.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate/output", response_model=OutputValidationResponse)
async def validate_output(request: OutputValidationRequest):
    """Evaluates generated answer against grounding/fact-checking rails."""
    if rails_app is None:
        raise HTTPException(status_code=503, detail="Guardrails engine not ready")

    try:
        logger.info("guardrails.output.checking", query=request.query)

        evidence_str = "\n".join(
            [f"Evidence {i + 1}: {chunk}" for i, chunk in enumerate(request.context)]
        )

        is_grounded = True
        refusal_message = None

        if hasattr(rails_app, "generate_async"):
            try:
                # Trigger the Colang 2 custom output validation flow defined in main.co
                # using generate_async and injecting $evidence and $response via context role
                res_obj = await rails_app.generate_async(
                    messages=[
                        {
                            "role": "context",
                            "content": {"evidence": evidence_str, "response": request.response},
                        },
                        {"role": "user", "content": "validate output please"},
                    ]
                )
                res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)

                # Check the refusal message returned by the custom flow
                if "cannot verify this information" in res:
                    is_grounded = False
                    refusal_message = res

            except Exception as ev_err:
                logger.warning(
                    "guardrails.output.flow_failed",
                    error=str(ev_err),
                    reason="falling back to default evaluation",
                )
                res_obj = await rails_app.generate_async(
                    prompt=(
                        f"Facts:\n{evidence_str}\n\nStatement:\n{request.response}\n\n"
                        "Is the statement fully grounded? (yes/no):"
                    )
                )
                res = res_obj.get("content", "") if isinstance(res_obj, dict) else str(res_obj)
                if "no" in res.lower():
                    is_grounded = False
                    refusal_message = (
                        "I'm sorry, but I cannot verify this information with internal "
                        "sources. Please try rephrasing your query."
                    )

        logger.info("guardrails.output.validated", is_grounded=is_grounded)
        return OutputValidationResponse(is_grounded=is_grounded, refusal_message=refusal_message)
    except Exception as e:
        logger.error("guardrails.output.error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
