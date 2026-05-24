import re

# Standard regexes for common PII patterns
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def redact_local_pii(text: str, mask_char: str = "*") -> str:
    """Redacts standard PII from text using local compiled regular expressions.

    Serves as a high-speed, zero-latency first line of defense before calling
    advanced external services like Private AI.
    """
    if not text:
        return text

    text = EMAIL_REGEX.sub(lambda m: mask_char * len(m.group(0)), text)

    text = SSN_REGEX.sub(lambda m: mask_char * len(m.group(0)), text)

    text = CREDIT_CARD_REGEX.sub(lambda m: mask_char * len(m.group(0)), text)

    text = PHONE_REGEX.sub(lambda m: mask_char * len(m.group(0)), text)

    return text


def contains_pii_local(text: str) -> bool:
    """Quick check to see if text likely contains PII."""
    if not text:
        return False

    return bool(
        EMAIL_REGEX.search(text)
        or SSN_REGEX.search(text)
        or CREDIT_CARD_REGEX.search(text)
        or PHONE_REGEX.search(text)
    )


JAILBREAK_KEYWORDS = [
    "ignore all previous",
    "ignore previous instructions",
    "system override",
    "system instruction override",
    "dan mode",
    "do anything now",
    "bypass corporate",
    "bypass firewall",
    "unrestricted assistant",
]

OFF_TOPIC_KEYWORDS = [
    "recipe",
    "bake",
    "cookie",
    "capital of france",
    "capital of",
    "creative story",
    "wizard exploring",
    "fantasy story",
]


def contains_jailbreak_local(text: str) -> bool:
    """Zero-latency heuristic filter to block common jailbreaks."""
    if not text:
        return False
    lowered = text.lower()
    return any(kw in lowered for kw in JAILBREAK_KEYWORDS)


# TODO: Improve off-topic handling
def contains_off_topic_local(text: str) -> bool:
    """Zero-latency heuristic filter to block common off-topic queries."""
    if not text:
        return False
    lowered = text.lower()
    return any(kw in lowered for kw in OFF_TOPIC_KEYWORDS)
