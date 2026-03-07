import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.cache_stats import get_cache_stats, reset_cache_stats
from app.retrieval import resources
from app.services.answer_service import node_parallel_retrieve, node_prepare

PAYLOAD = {
    "query": "What legal risks did Apple mention in its 10-K filings?",
    "company": "Apple Inc.",
    "form": "10-K",
}


def call_retrieval(payload: dict, clear_existing: bool = False) -> tuple[dict, float]:
    state = node_prepare(payload)
    if clear_existing:
        resources.get_redis_client().delete(state["retrieval_cache_key"])

    start = time.time()
    result = node_parallel_retrieve(state)
    latency_ms = round((time.time() - start) * 1000, 2)
    return result, latency_ms


def main() -> int:
    reset_cache_stats("retrieval_cache")

    first_result, first_latency_ms = call_retrieval(PAYLOAD, clear_existing=True)
    first_stats = get_cache_stats("retrieval_cache")

    second_result, second_latency_ms = call_retrieval(PAYLOAD)
    second_stats = get_cache_stats("retrieval_cache")

    summary = {
        "first_latency_ms": first_latency_ms,
        "second_latency_ms": second_latency_ms,
        "first_cache_hit": bool(first_result.get("retrieval_cache_hit")),
        "second_cache_hit": bool(second_result.get("retrieval_cache_hit")),
        "same_rows": first_result.get("results_rows") == second_result.get("results_rows"),
        "row_count": len(second_result.get("results_rows") or []),
        "stats_after_first": first_stats,
        "stats_after_second": second_stats,
    }

    print("\nRETRIEVAL CACHE EVAL\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
