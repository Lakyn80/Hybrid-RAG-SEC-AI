import json
import os
import sys
import time

import requests

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.cache_stats import get_cache_stats, reset_cache_stats
from app.retrieval import resources
from app.services.answer_service import build_cache_key, load_cache, save_cache
from app.services.semantic_cache import build_bucket_key, build_entry_key

API_URL = "http://localhost:8021/api/ask"
SEED_PAYLOAD = {
    "query": "What legal risks did Apple mention in its 10-K filings?",
    "company": "Apple Inc.",
    "form": "10-K",
}
PARAPHRASE_PAYLOAD = {
    "query": "Summarize the legal risk disclosures Apple made in its 10-K.",
    "company": "Apple Inc.",
    "form": "10-K",
}
MISSING_FILTER_PAYLOAD = {
    "query": "Summarize the legal risk disclosures.",
}
WRONG_SCOPE_PAYLOAD = {
    "query": "Summarize the legal risk disclosures Apple made in its 10-K.",
    "company": "NVIDIA CORP",
    "form": "10-K",
}


def clear_semantic_scope(company_filter: str, form_filter: str, query_type: str) -> None:
    client = resources.get_redis_client()
    bucket_key = build_bucket_key(
        index_version=resources.get_vector_index_version(),
        company_filter=company_filter,
        form_filter=form_filter,
        query_type=query_type,
    )
    entry_ids = client.lrange(bucket_key, 0, -1)
    entry_keys = [build_entry_key(entry_id) for entry_id in entry_ids]
    if entry_keys:
        client.delete(*entry_keys)
    client.delete(bucket_key)


def clear_answer_cache_entry(query: str, company_filter: str | None = None, form_filter: str | None = None) -> None:
    cache_data = load_cache()
    cache_key = build_cache_key(query, company_filter, form_filter)
    if cache_key in cache_data:
        del cache_data[cache_key]
        save_cache(cache_data)


def call_api(payload: dict) -> tuple[dict, float]:
    start = time.time()
    response = requests.post(API_URL, json=payload, timeout=180)
    response.raise_for_status()
    latency_ms = round((time.time() - start) * 1000, 2)
    return response.json(), latency_ms


def main() -> int:
    reset_cache_stats("semantic_cache")
    clear_semantic_scope("Apple Inc.", "10-K", "risk")
    clear_semantic_scope("NVIDIA CORP", "10-K", "risk")
    clear_answer_cache_entry(MISSING_FILTER_PAYLOAD["query"])

    seed_result, seed_latency_ms = call_api(SEED_PAYLOAD)
    stats_after_seed = get_cache_stats("semantic_cache")

    paraphrase_result, paraphrase_latency_ms = call_api(PARAPHRASE_PAYLOAD)
    stats_after_paraphrase = get_cache_stats("semantic_cache")

    missing_result, missing_latency_ms = call_api(MISSING_FILTER_PAYLOAD)
    stats_after_missing = get_cache_stats("semantic_cache")

    wrong_scope_result, wrong_scope_latency_ms = call_api(WRONG_SCOPE_PAYLOAD)
    stats_after_wrong_scope = get_cache_stats("semantic_cache")

    summary = {
        "seed": {
            "latency_ms": seed_latency_ms,
            "mode": seed_result.get("mode"),
        },
        "paraphrase": {
            "latency_ms": paraphrase_latency_ms,
            "mode": paraphrase_result.get("mode"),
            "cache_hit": paraphrase_result.get("cache_hit"),
        },
        "missing_filter": {
            "latency_ms": missing_latency_ms,
            "mode": missing_result.get("mode"),
            "cache_hit": missing_result.get("cache_hit"),
        },
        "wrong_scope": {
            "latency_ms": wrong_scope_latency_ms,
            "mode": wrong_scope_result.get("mode"),
            "cache_hit": wrong_scope_result.get("cache_hit"),
        },
        "stats_after_seed": stats_after_seed,
        "stats_after_paraphrase": stats_after_paraphrase,
        "stats_after_missing_filter": stats_after_missing,
        "stats_after_wrong_scope": stats_after_wrong_scope,
    }

    print("\nSEMANTIC CACHE EVAL\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
