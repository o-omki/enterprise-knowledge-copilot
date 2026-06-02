"""Golden QA dataset generator.

Reads source documents from the corpus and uses Gemini to generate
question-answer pairs with reference answers, expected citations,
and question type tags.  The output is a JSON file that serves as
the frozen evaluation dataset for answer quality assessment.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any

from google import genai
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class DatasetGenConfig(BaseSettings):
    project_id: str = Field(alias="GCP_PROJECT_ID")
    location: str = Field(alias="GCP_LOCATION", default="global")
    model: str = Field(
        alias="GCP_GENERATION_MODEL",
        default="gemini-3-flash-preview",
    )
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GeneratedQAPair(BaseModel):
    question: str = Field(
        ...,
        description="A realistic user question about the document content.",
    )
    reference_answer: str = Field(
        ...,
        description="The gold-standard answer derived strictly from the document.",
    )
    question_type: str = Field(
        ...,
        description=(
            "One of: 'factual_lookup', 'procedural', 'comparative', " "'multi_hop', 'ambiguous'."
        ),
    )
    key_citations: list[str] = Field(
        default_factory=list,
        description="2-3 key sentences from the document that support the answer.",
    )


class GeneratedQABatch(BaseModel):
    pairs: list[GeneratedQAPair] = Field(
        default_factory=list,
        description="List of generated QA pairs for this document.",
    )


SYSTEM_PROMPT = """\
You are an expert dataset creator for evaluating a Retrieval-Augmented Generation (RAG) system.

Given a source document, generate 2-3 high-quality question-answer pairs.

Rules:
1. Questions should be realistic — the kind an enterprise developer would ask.
2. Reference answers must be derived STRICTLY from the provided document content.
   Do NOT use external knowledge.
3. Each answer should be 2-5 sentences, clear and complete.
4. Include 2-3 key citation sentences from the document that support the answer.
5. Assign each question a type:
   - "factual_lookup": Direct fact retrieval (e.g., "What is X?")
   - "procedural": How-to questions (e.g., "How do I configure Y?")
   - "comparative": Comparing concepts (e.g., "What is the difference between A and B?")
   - "multi_hop": Requires synthesizing info from multiple parts of the document
   - "ambiguous": Question that could be interpreted in multiple ways
6. Ensure variety — avoid generating 3 factual_lookup questions for the same doc.
7. Questions must be self-contained — do not reference "the document" or "the text".
"""


async def generate_golden_qa(
    corpus_dir: str = "data/raw/official_docs",
    output_path: str = "data/eval/generation/golden_qa.json",
    target_count: int = 80,
    seed: int = 42,
) -> Path:
    """Generate the golden QA evaluation dataset.

    Parameters
    ----------
    corpus_dir:
        Path to the raw document corpus.
    output_path:
        Where to write the generated dataset.
    target_count:
        Target number of QA pairs (approximate).
    seed:
        Random seed for document sampling.

    Returns
    -------
    Path to the generated JSON file.
    """
    config = DatasetGenConfig()
    client = genai.Client(
        vertexai=True,
        project=config.project_id,
        location=config.location,
    )

    corpus_path = Path(corpus_dir)
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_path}")

    doc_files: list[Path] = []
    for domain_dir in sorted(corpus_path.iterdir()):
        if domain_dir.is_dir():
            md_files = list(domain_dir.glob("*.md"))
            doc_files.extend(md_files)

    if not doc_files:
        raise ValueError(f"No markdown files found in {corpus_path}")

    logger.info(
        "Found %d documents across %d domains.",
        len(doc_files),
        len(set(f.parent for f in doc_files)),
    )

    # Stratified sampling: pick ~target_count/2.5 docs (each generates 2-3 QA pairs)
    random.seed(seed)
    docs_needed = min(len(doc_files), max(10, target_count // 3))

    by_domain: dict[str, list[Path]] = {}
    for f in doc_files:
        domain = f.parent.name
        by_domain.setdefault(domain, []).append(f)

    selected: list[Path] = []
    per_domain = max(2, docs_needed // len(by_domain))
    for domain, files in by_domain.items():
        sampled = random.sample(files, min(per_domain, len(files)))
        selected.extend(sampled)

    if len(selected) > docs_needed:
        selected = random.sample(selected, docs_needed)

    logger.info("Selected %d documents for QA generation.", len(selected))

    all_pairs: list[dict[str, Any]] = []
    for idx, doc_path in enumerate(selected):
        domain = doc_path.parent.name
        relative_source = f"{domain}/{doc_path.name}"

        try:
            content = doc_path.read_text(encoding="utf-8")
            if len(content) > 12000:
                content = content[:12000] + "\n\n[... document truncated ...]"

            user_prompt = f"Source file: {relative_source}\n\n" f"Document content:\n{content}"

            response = await client.aio.models.generate_content(
                model=config.model,
                contents=user_prompt,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "response_schema": GeneratedQABatch,
                    "temperature": 0.3,
                },
            )

            batch: GeneratedQABatch | None = response.parsed

            # Fallback: if structured parsing returned None, try manual JSON parse
            if batch is None:
                import json as _json

                try:
                    raw = _json.loads(response.text)
                    batch = GeneratedQABatch(**raw)
                except Exception:
                    logger.warning(
                        "QA generator: structured parsing returned None for %s. "
                        "Skipping. Response text: %s",
                        relative_source,
                        (response.text or "")[:200],
                    )
                    continue

            for pair in batch.pairs:
                all_pairs.append(
                    {
                        "question": pair.question,
                        "reference_answer": pair.reference_answer,
                        "expected_source": relative_source,
                        "expected_citations": pair.key_citations,
                        "question_type": pair.question_type,
                        "domain": domain,
                    }
                )

            logger.info(
                "[%d/%d] Generated %d pairs from %s",
                idx + 1,
                len(selected),
                len(batch.pairs),
                relative_source,
            )

        except Exception as e:
            logger.error("Failed to generate QA for %s: %s", relative_source, e)

        await asyncio.sleep(0.5)

    logger.info("Generated %d total QA pairs.", len(all_pairs))

    type_counts: dict[str, int] = {}
    domain_counts: dict[str, int] = {}
    for pair in all_pairs:
        qt = pair.get("question_type", "unknown")
        type_counts[qt] = type_counts.get(qt, 0) + 1
        d = pair.get("domain", "unknown")
        domain_counts[d] = domain_counts.get(d, 0) + 1

    logger.info("Type distribution: %s", type_counts)
    logger.info("Domain distribution: %s", domain_counts)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        json.dump(all_pairs, fh, indent=2)

    logger.info("Golden QA dataset written to %s (%d pairs)", out, len(all_pairs))
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(generate_golden_qa())
