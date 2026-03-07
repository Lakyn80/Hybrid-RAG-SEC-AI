import hashlib
import json
import math
import re
import time
from typing import Any

from app.core.cache_stats import increment_cache_stat
from app.retrieval import resources
from app.retrieval.metadata_utils import build_chunk_hash
from app.retrieval.retrieval_cache import normalize_cache_value, normalize_query

SEMANTIC_CACHE_BUCKET_PREFIX = "semantic:v1:bucket"
SEMANTIC_CACHE_ENTRY_PREFIX = "semantic:v1:entry"
SEMANTIC_CACHE_STATS_NAMESPACE = "semantic_cache"
SEMANTIC_CACHE_TTL_SECONDS = 60 * 60 * 24 * 7
SEMANTIC_CACHE_BUCKET_SIZE = 200
SEMANTIC_CACHE_MIN_SIMILARITY = 0.82
SEMANTIC_CACHE_MIN_MARGIN = 0.015
SEMANTIC_CACHE_MIN_TOKEN_OVERLAP = 0.5
SEMANTIC_PROMPT_VERSION = "answer_context_v1"
SEMANTIC_CACHE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "its",
    "made",
    "make",
    "made",
    "mention",
    "mentioned",
    "of",
    "on",
    "or",
    "summarize",
    "summarise",
    "that",
    "the",
    "their",
    "this",
    "to",
    "what",
    "which",
    "with",
}


def semantic_cache_enabled(
    company_filter: str | None,
    form_filter: str | None,
) -> bool:
    return bool(normalize_cache_value(company_filter) and normalize_cache_value(form_filter))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return -1.0

    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))

    if left_norm == 0 or right_norm == 0:
        return -1.0

    return numerator / (left_norm * right_norm)


def normalize_query_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9\\-]+", normalize_query(text))
    return [token for token in tokens if len(token) > 1 and token not in SEMANTIC_CACHE_STOPWORDS]


def query_token_overlap_ratio(left_tokens: list[str], right_tokens: list[str]) -> float:
    left = set(left_tokens)
    right = set(right_tokens)

    if not left or not right:
        return 0.0

    return len(left & right) / len(left)


def build_bucket_key(
    *,
    index_version: str,
    company_filter: str,
    form_filter: str,
    query_type: str,
) -> str:
    return ":".join(
        [
            SEMANTIC_CACHE_BUCKET_PREFIX,
            normalize_cache_value(index_version) or "unknown",
            normalize_cache_value(company_filter),
            normalize_cache_value(form_filter),
            normalize_cache_value(query_type) or "general",
        ]
    )


def build_entry_id(
    query: str,
    *,
    company_filter: str,
    form_filter: str,
    query_type: str,
    index_version: str,
    llm_model: str,
) -> str:
    raw = json.dumps(
        {
            "query": normalize_query(query),
            "company_filter": normalize_cache_value(company_filter),
            "form_filter": normalize_cache_value(form_filter),
            "query_type": normalize_cache_value(query_type),
            "index_version": normalize_cache_value(index_version),
            "llm_model": normalize_cache_value(llm_model),
            "prompt_version": SEMANTIC_PROMPT_VERSION,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_entry_key(entry_id: str) -> str:
    return f"{SEMANTIC_CACHE_ENTRY_PREFIX}:{entry_id}"


def build_retrieval_signature(results_rows: list[dict[str, Any]] | None) -> str:
    rows = results_rows or []
    chunk_markers = []

    for row in rows:
        chunk_hash = str(row.get("chunk_hash") or "").strip()
        if not chunk_hash:
            chunk_hash = build_chunk_hash(str(row.get("chunk_text") or ""))
        chunk_markers.append(chunk_hash)

    raw = "|".join(chunk_markers)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def embed_query(query: str, embedding_model_name: str) -> list[float]:
    model = resources.get_embedding_model(embedding_model_name)
    vector = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vector[0].tolist()


def lookup_semantic_cache(
    query: str,
    *,
    company_filter: str | None,
    form_filter: str | None,
    query_type: str,
    index_version: str,
    embedding_model_name: str,
) -> dict[str, Any] | None:
    if not semantic_cache_enabled(company_filter, form_filter):
        return None

    bucket_key = build_bucket_key(
        index_version=index_version,
        company_filter=str(company_filter),
        form_filter=str(form_filter),
        query_type=query_type,
    )

    try:
        client = resources.get_redis_client()
        entry_ids = client.lrange(bucket_key, 0, SEMANTIC_CACHE_BUCKET_SIZE - 1)
        if not entry_ids:
            increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "miss")
            return None

        entry_payloads = client.mget([build_entry_key(entry_id) for entry_id in entry_ids])
    except Exception:
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "errors")
        return None

    candidates = []
    query_embedding = embed_query(query, embedding_model_name)
    query_tokens = normalize_query_tokens(query)

    for payload in entry_payloads:
        if not payload:
            continue

        try:
            entry = json.loads(payload)
        except Exception:
            continue

        if not isinstance(entry, dict):
            continue

        similarity = cosine_similarity(query_embedding, entry.get("embedding") or [])
        if similarity < SEMANTIC_CACHE_MIN_SIMILARITY:
            continue

        token_overlap = query_token_overlap_ratio(
            query_tokens,
            normalize_query_tokens(str(entry.get("normalized_query") or entry.get("query") or "")),
        )
        if token_overlap < SEMANTIC_CACHE_MIN_TOKEN_OVERLAP:
            continue

        entry["similarity"] = float(similarity)
        entry["token_overlap"] = float(token_overlap)
        candidates.append(entry)

    if not candidates:
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "miss")
        return None

    candidates.sort(key=lambda item: item["similarity"], reverse=True)
    best = candidates[0]
    second_best = candidates[1]["similarity"] if len(candidates) > 1 else -1.0
    margin = best["similarity"] - second_best

    if best["similarity"] < SEMANTIC_CACHE_MIN_SIMILARITY:
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "miss")
        return None

    if len(candidates) > 1 and margin < SEMANTIC_CACHE_MIN_MARGIN:
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "miss")
        return None

    increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "hit")
    return best


def save_semantic_cache(
    query: str,
    *,
    answer: str,
    sources_text: str,
    company_filter: str | None,
    form_filter: str | None,
    query_type: str,
    llm_model: str,
    index_version: str,
    results_rows: list[dict[str, Any]] | None,
    embedding_model_name: str,
) -> bool:
    if not semantic_cache_enabled(company_filter, form_filter):
        return False

    if len(results_rows or []) < 2:
        return False

    answer_text = str(answer or "").strip()
    sources = str(sources_text or "").strip()
    if not answer_text or not sources:
        return False

    query_embedding = embed_query(query, embedding_model_name)
    entry_id = build_entry_id(
        query,
        company_filter=str(company_filter),
        form_filter=str(form_filter),
        query_type=query_type,
        index_version=index_version,
        llm_model=llm_model,
    )
    bucket_key = build_bucket_key(
        index_version=index_version,
        company_filter=str(company_filter),
        form_filter=str(form_filter),
        query_type=query_type,
    )
    entry_key = build_entry_key(entry_id)

    payload = {
        "entry_id": entry_id,
        "query": query,
        "normalized_query": normalize_query(query),
        "embedding": query_embedding,
        "answer": answer_text,
        "sources_text": sources,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "query_type": query_type,
        "llm_model": llm_model,
        "prompt_version": SEMANTIC_PROMPT_VERSION,
        "index_version": index_version,
        "retrieval_signature": build_retrieval_signature(results_rows),
        "created_at": time.time(),
    }

    try:
        client = resources.get_redis_client()
        client.setex(
            entry_key,
            SEMANTIC_CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False),
        )
        client.lrem(bucket_key, 0, entry_id)
        client.lpush(bucket_key, entry_id)
        client.ltrim(bucket_key, 0, SEMANTIC_CACHE_BUCKET_SIZE - 1)
        client.expire(bucket_key, SEMANTIC_CACHE_TTL_SECONDS)
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "write")
        return True
    except Exception:
        increment_cache_stat(SEMANTIC_CACHE_STATS_NAMESPACE, "errors")
        return False
