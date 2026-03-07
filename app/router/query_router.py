import re


SEC_FORM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b10[\s-]?k\b", flags=re.IGNORECASE), "10-K"),
    (re.compile(r"\b10[\s-]?q\b", flags=re.IGNORECASE), "10-Q"),
    (re.compile(r"\b8[\s-]?k\b", flags=re.IGNORECASE), "8-K"),
    (re.compile(r"\bdefa\s*14a\b", flags=re.IGNORECASE), "DEFA14A"),
    (re.compile(r"\bdef\s*14a\b", flags=re.IGNORECASE), "DEF 14A"),
    (re.compile(r"\bproxy statement\b", flags=re.IGNORECASE), "DEF 14A"),
    (re.compile(r"\bsc\s*13g\s*/\s*a\b", flags=re.IGNORECASE), "SC 13G/A"),
    (re.compile(r"\bsc\s*13g\/a\b", flags=re.IGNORECASE), "SC 13G/A"),
    (re.compile(r"\bsc\s*13g\b", flags=re.IGNORECASE), "SC 13G"),
]


def detect_sec_form(query: str) -> str | None:
    text = str(query or "").strip()

    for pattern, canonical_form in SEC_FORM_PATTERNS:
        if pattern.search(text):
            return canonical_form

    return None


def classify_query(query: str) -> str:
    q = query.lower()

    risk_words = ["risk", "risks", "uncertainty", "adverse"]
    financial_words = ["revenue", "income", "profit", "earnings", "financial"]
    compare_words = ["compare", "difference", "versus", "vs"]

    if any(w in q for w in compare_words):
        return "compare"

    if any(w in q for w in financial_words):
        return "financial"

    if any(w in q for w in risk_words):
        return "risk"

    return "general"
