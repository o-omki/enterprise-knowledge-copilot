import logging
import re

logger = logging.getLogger("packages.safety.citation")

# find standard brackets citations like [1], [2], [Source 3], etc.
CITATION_REGEX = re.compile(r"\[(?:Source\s*)?(\d+)\]")


def parse_citations(text: str) -> list[int]:
    """Extracts all citation numbers referenced in the generated text."""
    if not text:
        return []

    matches = CITATION_REGEX.findall(text)
    return sorted(list(set(int(m) for m in matches)))


def verify_citations_bounds(text: str, retrieved_count: int) -> bool:
    """Verifies that all parsed citations in the text are within the bounds of retrieved documents.

    If the text cites '[3]' but only 2 documents were retrieved, this indicates
    a citation mismatch/hallucination.
    """
    if not text:
        return True

    citations = parse_citations(text)
    if not citations:
        return True

    for cit in citations:
        # Citations are usually 1-indexed
        if cit <= 0 or cit > retrieved_count:
            logger.warning(
                "Citation mismatch detected: answer cited [%s] but retrieved count is %s",
                cit,
                retrieved_count,
            )
            return False

    return True
