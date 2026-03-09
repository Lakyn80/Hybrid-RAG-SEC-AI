import json
import os

from app.retrieval import resources

REDIS_CACHE_PREFIXES = (
    "answer:v1",
    "retrieval:v2",
    "semantic:v1:bucket",
    "semantic:v1:entry",
    "question_bank_v1",
    "stats:retrieval_cache",
    "stats:semantic_cache",
    "stats:answer_cache",
)


def clear_answer_cache_file(cache_file: str) -> bool:
    try:
        client = resources.get_redis_client()
        keys = list(client.scan_iter(match="answer:v1:*"))
        if keys:
            client.delete(*keys)
        return True
    except Exception:
        return False


def clear_redis_prefixes(prefixes: tuple[str, ...] = REDIS_CACHE_PREFIXES) -> int:
    client = resources.get_redis_client()
    keys_to_delete = []

    for prefix in prefixes:
        try:
            keys_to_delete.extend(client.scan_iter(match=f"{prefix}*"))
        except Exception:
            continue

    if not keys_to_delete:
        return 0

    deleted = 0
    for start in range(0, len(keys_to_delete), 500):
        batch = keys_to_delete[start:start + 500]
        try:
            deleted += int(client.delete(*batch))
        except Exception:
            continue

    return deleted
