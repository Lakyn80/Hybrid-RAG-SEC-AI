import re


ALLOWED_COMPANY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bapple\b", flags=re.IGNORECASE),
    re.compile(r"\bnvidia\b", flags=re.IGNORECASE),
    re.compile(r"\balphabet\b", flags=re.IGNORECASE),
    re.compile(r"\bgoogle\b", flags=re.IGNORECASE),
)

ALLOWED_FORM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b10[\s-]?k\b", flags=re.IGNORECASE),
    re.compile(r"\b10[\s-]?q\b", flags=re.IGNORECASE),
    re.compile(r"\b8[\s-]?k\b", flags=re.IGNORECASE),
    re.compile(r"\bdefa\s*14a\b", flags=re.IGNORECASE),
    re.compile(r"\bdef\s*14a\b", flags=re.IGNORECASE),
    re.compile(r"\bsc\s*13g(?:\s*/\s*a|/a)?\b", flags=re.IGNORECASE),
)

ALLOWED_TOPIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bsec filing(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bcompany disclosure(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\brisk factor(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\blegal proceeding(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\blitigation\b", flags=re.IGNORECASE),
    re.compile(r"\bgovernance\b", flags=re.IGNORECASE),
    re.compile(r"\bboard\b", flags=re.IGNORECASE),
    re.compile(r"\bproxy statement(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bexecutive compensation\b", flags=re.IGNORECASE),
    re.compile(r"\bfinancial result(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\brevenue\b", flags=re.IGNORECASE),
    re.compile(r"\bliquidity\b", flags=re.IGNORECASE),
    re.compile(r"\bregulatory risk(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bcybersecurity risk(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bsupply chain risk(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\brisk(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bregulation\b", flags=re.IGNORECASE),
    re.compile(r"\bregulatory\b", flags=re.IGNORECASE),
    re.compile(r"\bfinancial\b", flags=re.IGNORECASE),
    re.compile(r"\bdisclosure(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\bfiling(s)?\b", flags=re.IGNORECASE),
    re.compile(r"\breport(s)?\b", flags=re.IGNORECASE),
)


def is_query_allowed(query: str) -> bool:
    text = str(query or "").strip()
    if not text:
        return False

    for pattern in ALLOWED_COMPANY_PATTERNS:
        if pattern.search(text):
            return True

    for pattern in ALLOWED_FORM_PATTERNS:
        if pattern.search(text):
            return True

    for pattern in ALLOWED_TOPIC_PATTERNS:
        if pattern.search(text):
            return True

    return False


__all__ = ["is_query_allowed"]
