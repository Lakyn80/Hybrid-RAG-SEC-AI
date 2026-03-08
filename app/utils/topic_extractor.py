from __future__ import annotations

import re
from collections import Counter

TOPIC_LIMIT = 20

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "this", "to",
    "was", "were", "with", "within", "may", "can", "could", "would", "should",
    "will", "our", "your", "these", "those", "about", "through", "over",
}

CANONICAL_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "risk factors": ("risk factors",),
    "legal proceedings": ("legal proceedings", "litigation", "lawsuit", "lawsuits", "claims"),
    "regulatory compliance": ("regulatory", "regulation", "compliance", "government regulation"),
    "cybersecurity": ("cybersecurity", "cyber security", "data security", "privacy", "breach"),
    "supply chain": ("supply chain", "supplier", "suppliers", "manufacturing", "components"),
    "competition": ("competition", "competitive", "competitors"),
    "financial condition": ("financial condition", "financial results", "liquidity", "cash flows"),
    "governance": ("governance", "board of directors", "audit committee", "proxy statement"),
    "international operations": ("international operations", "foreign", "international", "global operations"),
    "product development": ("product development", "research and development", "new products"),
    "intellectual property": ("intellectual property", "patent", "copyright", "trademark"),
    "customer demand": ("customer demand", "consumer demand", "demand"),
    "economic conditions": ("economic conditions", "macroeconomic", "inflation", "interest rates"),
    "acquisitions": ("acquisitions", "acquisition", "merger", "business combination"),
    "management discussion": ("management discussion", "management discussion and analysis", "md&a"),
    "government regulation": ("government regulation", "governmental regulation"),
}

DEFAULT_TOPICS = [
    "risk factors",
    "legal proceedings",
    "regulatory compliance",
    "cybersecurity",
    "supply chain",
    "competition",
    "financial condition",
    "governance",
    "international operations",
    "product development",
]


def _normalize_topic(topic: str) -> str:
    text = re.sub(r"\s+", " ", str(topic or "").strip().lower())
    return text


def _extract_heading_candidates(chunk_text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in str(chunk_text or "").splitlines():
        line = raw_line.strip()
        if len(line) < 6 or len(line) > 90:
            continue
        if len(re.findall(r"[A-Za-z]", line)) < 5:
            continue
        if re.match(r"^item\s+\d+[a-z]?\.", line.lower()):
            cleaned = re.sub(r"^item\s+\d+[a-z]?\.\s*", "", line, flags=re.IGNORECASE)
            if cleaned:
                candidates.append(cleaned)
            continue
        if line == line.upper() or line.istitle():
            candidates.append(line)
    return candidates


def _extract_ngram_candidates(chunk_text: str) -> Counter[str]:
    text = re.sub(r"[^a-zA-Z0-9\s\-]", " ", str(chunk_text or "").lower())
    tokens = [token for token in text.split() if len(token) > 2 and token not in STOP_WORDS]
    counts: Counter[str] = Counter()

    for size in (1, 2, 3):
        for start in range(0, max(len(tokens) - size + 1, 0)):
            phrase = " ".join(tokens[start:start + size])
            if len(phrase) < 5:
                continue
            counts[phrase] += 1

    return counts


def extract_topics_from_chunks(chunks: list[str], limit: int = TOPIC_LIMIT) -> list[str]:
    canonical_counts: Counter[str] = Counter()
    heading_counts: Counter[str] = Counter()
    ngram_counts: Counter[str] = Counter()

    for chunk_text in chunks:
        normalized_text = _normalize_topic(chunk_text)
        if not normalized_text:
            continue

        for topic, patterns in CANONICAL_TOPIC_PATTERNS.items():
            if any(pattern in normalized_text for pattern in patterns):
                canonical_counts[topic] += 1

        for heading in _extract_heading_candidates(chunk_text):
            normalized_heading = _normalize_topic(heading)
            if normalized_heading and normalized_heading not in STOP_WORDS:
                heading_counts[normalized_heading] += 1

        ngram_counts.update(_extract_ngram_candidates(chunk_text))

    ranked_topics: list[str] = []
    for topic, _ in canonical_counts.most_common():
        ranked_topics.append(topic)

    for heading, count in heading_counts.most_common():
        if count < 2:
            continue
        if heading not in ranked_topics:
            ranked_topics.append(heading)

    for phrase, count in ngram_counts.most_common():
        if count < 4:
            continue
        if phrase in ranked_topics:
            continue
        if any(word in STOP_WORDS for word in phrase.split()):
            continue
        if len(phrase.split()) > 3:
            continue
        ranked_topics.append(phrase)

    for fallback in DEFAULT_TOPICS:
        if fallback not in ranked_topics:
            ranked_topics.append(fallback)

    return ranked_topics[:limit]
