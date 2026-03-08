import re


SEC_FORM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b10[\s-]?k\b", flags=re.IGNORECASE), "10-K"),
    (re.compile(r"\b10[\s-]?q\b", flags=re.IGNORECASE), "10-Q"),
    (re.compile(r"\b8[\s-]?k\b", flags=re.IGNORECASE), "8-K"),
    (re.compile(r"\bdefa\s*14a\b", flags=re.IGNORECASE), "DEFA14A"),
    (re.compile(r"\bdef\s*14a\b", flags=re.IGNORECASE), "DEF 14A"),
    (re.compile(r"\bsc\s*13g\s*/\s*a\b", flags=re.IGNORECASE), "SC 13G/A"),
    (re.compile(r"\bsc\s*13g\/a\b", flags=re.IGNORECASE), "SC 13G/A"),
    (re.compile(r"\bsc\s*13g\b", flags=re.IGNORECASE), "SC 13G"),
]

SEC_FORM_SYNONYMS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bannual report(s)?\b", flags=re.IGNORECASE), "10-K"),
    (re.compile(r"\bquarterly report(s)?\b", flags=re.IGNORECASE), "10-Q"),
    (re.compile(r"\bproxy statement(s)?\b", flags=re.IGNORECASE), "DEF 14A"),
    (re.compile(r"\bcurrent report(s)?\b", flags=re.IGNORECASE), "8-K"),
]

COMPANY_ALIASES: list[tuple[str, tuple[str, ...]]] = [
    ("Apple Inc.", ("apple",)),
    ("NVIDIA CORP", ("nvidia",)),
    ("Alphabet Inc.", ("alphabet", "google")),
    ("MICROSOFT CORP", ("microsoft",)),
    ("TESLA, INC.", ("tesla",)),
]

DISPLAY_COMPANY_NAMES = {
    "Apple Inc.": "Apple",
    "NVIDIA CORP": "NVIDIA",
    "Alphabet Inc.": "Alphabet",
    "MICROSOFT CORP": "Microsoft",
    "TESLA, INC.": "Tesla",
}

TOPIC_FILLER_WORDS = {
    "a", "about", "all", "an", "and", "any", "are", "by", "can", "compare", "company",
    "describe", "described", "did", "disclose", "disclosed", "discuss", "discussed",
    "does", "filing", "filings", "how", "in", "its", "it", "mention", "mentioned",
    "of", "on", "or", "report", "reported", "reports", "say", "says", "the", "their",
    "them", "these", "this", "to", "vs", "versus", "what", "which", "with",
}

TOPIC_NORMALIZATION_RULES: list[tuple[tuple[str, ...], str]] = [
    (("executive", "compensation"), "executive compensation topics"),
    (("proxy",), "governance topics"),
    (("governance",), "governance topics"),
    (("board",), "governance topics"),
    (("cybersecurity",), "cybersecurity risks"),
    (("security",), "cybersecurity risks"),
    (("supply", "chain"), "supply chain risks"),
    (("intellectual", "property"), "intellectual property disputes"),
    (("litigation",), "litigation risks"),
    (("legal",), "legal risks"),
    (("regulatory",), "regulatory risks"),
    (("competition",), "competitive risks"),
    (("liquidity",), "liquidity"),
    (("revenue",), "revenue trends"),
    (("earnings",), "financial results"),
    (("income",), "financial results"),
    (("financial",), "financial results"),
    (("demand",), "demand fluctuations"),
]


def detect_sec_form(query: str) -> str | None:
    text = str(query or "").strip()

    for pattern, canonical_form in SEC_FORM_PATTERNS:
        if pattern.search(text):
            return canonical_form

    for pattern, canonical_form in SEC_FORM_SYNONYMS:
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


def detect_companies(query: str) -> list[str]:
    text = str(query or "")
    matches: list[tuple[int, str]] = []

    for canonical_name, aliases in COMPANY_ALIASES:
        earliest_match: int | None = None
        for alias in aliases:
            match = re.search(rf"\b{re.escape(alias)}\b", text, flags=re.IGNORECASE)
            if match and (earliest_match is None or match.start() < earliest_match):
                earliest_match = match.start()

        if earliest_match is not None:
            matches.append((earliest_match, canonical_name))

    matches.sort(key=lambda item: item[0])

    ordered_companies: list[str] = []
    seen: set[str] = set()
    for _, canonical_name in matches:
        if canonical_name in seen:
            continue
        ordered_companies.append(canonical_name)
        seen.add(canonical_name)

    return ordered_companies


def detect_primary_company(query: str) -> str | None:
    companies = detect_companies(query)
    return companies[0] if companies else None


def get_company_display_name(company_name: str) -> str:
    return DISPLAY_COMPANY_NAMES.get(company_name, company_name)


def strip_form_references(text: str) -> str:
    cleaned = str(text)

    for pattern, _ in SEC_FORM_PATTERNS:
        cleaned = pattern.sub(" ", cleaned)

    for pattern, _ in SEC_FORM_SYNONYMS:
        cleaned = pattern.sub(" ", cleaned)

    cleaned = re.sub(r"\bfilings?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\breports?\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdocuments?\b", " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def extract_query_topic(query: str) -> str:
    lowered = strip_form_references(query.lower())

    for _, aliases in COMPANY_ALIASES:
        for alias in aliases:
            lowered = re.sub(rf"\b{re.escape(alias)}\b", " ", lowered, flags=re.IGNORECASE)

    lowered = re.sub(r"\b(compare|comparison|versus|vs|between|with|and)\b", " ", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"[^\w\s]", " ", lowered)

    tokens = [
        token for token in re.findall(r"[a-z0-9]+", lowered)
        if len(token) > 2 and token not in TOPIC_FILLER_WORDS
    ]

    token_set = set(tokens)
    for required_tokens, topic in TOPIC_NORMALIZATION_RULES:
        if all(required in token_set for required in required_tokens):
            return topic

    if not tokens:
        return "the filing topic"

    phrase = " ".join(tokens[:4]).strip()
    return phrase or "the filing topic"


def build_company_subquery(
    query: str,
    company_name: str,
    form_filter: str | None = None,
) -> str:
    topic = extract_query_topic(query)
    query_type = classify_query(query)
    company_display = get_company_display_name(company_name)

    if form_filter:
        form_clause = f" in its {form_filter} filings"
        filings_phrase = f"{company_display}'s {form_filter} filings"
    else:
        form_clause = ""
        filings_phrase = f"{company_display}'s filings"

    if topic.endswith("risks"):
        return f"What {topic} did {company_display} mention{form_clause}?"

    if query_type == "financial" or topic in {"financial results", "revenue trends", "liquidity"}:
        verb = "report" if topic in {"financial results", "revenue trends"} else "disclose"
        return f"What did {company_display} {verb} about {topic}{form_clause}?"

    if "governance" in topic or "compensation" in topic:
        return f"What {topic} are discussed in {filings_phrase}?"

    return f"What does {company_display} disclose about {topic}{form_clause}?"


def build_multi_company_subqueries(
    query: str,
    companies: list[str],
    form_filter: str | None = None,
) -> list[dict[str, str]]:
    return [
        {
            "company": company_name,
            "subquery": build_company_subquery(query, company_name, form_filter=form_filter),
        }
        for company_name in companies
    ]


__all__ = [
    "build_company_subquery",
    "build_multi_company_subqueries",
    "classify_query",
    "detect_companies",
    "detect_primary_company",
    "detect_sec_form",
    "extract_query_topic",
    "get_company_display_name",
]
