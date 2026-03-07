import hashlib
import json
import re
import time
from typing import Any

from app.core.cache_stats import increment_cache_stat
from app.retrieval import resources

RETRIEVAL_CACHE_PREFIX = "retrieval:v2"
RETRIEVAL_CACHE_TTL_SECONDS = 60 * 60 * 24
RETRIEVAL_CACHE_STATS_NAMESPACE = "retrieval_cache"


def normalize_cache_value(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def hash_query(text: str) -> str:
    return hashlib.sha256(normalize_query(text).encode("utf-8")).hexdigest()


def build_retrieval_cache_key(
    query: str,
    company_filter: str | None,
    form_filter: str | None,
    *,
    backend: str,
    index_version: str,
    embedding_model: str,
    reranker_version: str,
    vector_k: int,
    bm25_k: int,
    top_k: int,
) -> str:
    company_key = normalize_cache_value(company_filter) or "__all__"
    form_key = normalize_cache_value(form_filter) or "__all__"

    return ":".join(
        [
            RETRIEVAL_CACHE_PREFIX,
            normalize_cache_value(backend) or "unknown",
            normalize_cache_value(index_version) or "unknown",
            normalize_cache_value(embedding_model) or "unknown",
            normalize_cache_value(reranker_version) or "unknown",
            company_key,
            form_key,
            hash_query(query),
            str(int(vector_k)),
            str(int(bm25_k)),
            str(int(top_k)),
        ]
    )


def read_retrieval_cache(cache_key: str) -> dict[str, Any] | None:
    try:
        raw = resources.get_redis_client().get(cache_key)
    except Exception:
        increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "errors")
        return None

    if not raw:
        increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "miss")
        return None

    try:
        data = json.loads(raw)
    except Exception:
        increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "errors")
        return None

    increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "hit")
    return data if isinstance(data, dict) else None


def write_retrieval_cache(
    cache_key: str,
    *,
    query: str,
    company_filter: str | None,
    form_filter: str | None,
    backend: str,
    index_version: str,
    rows: list[dict[str, Any]],
) -> bool:
    if not rows:
        return False

    payload = {
        "query": query,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "backend": backend,
        "index_version": index_version,
        "created_at": time.time(),
        "rows": rows,
    }

    try:
        resources.get_redis_client().setex(
            cache_key,
            RETRIEVAL_CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False),
        )
        increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "write")
        return True
    except Exception:
        increment_cache_stat(RETRIEVAL_CACHE_STATS_NAMESPACE, "errors")
        return False
