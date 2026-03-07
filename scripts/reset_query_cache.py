import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.cache_admin import clear_answer_cache_file, clear_redis_prefixes


def main() -> int:
    answer_cache_file = os.path.join(BASE_DIR, "data", "cache", "answer_cache.json")

    deleted_redis_keys = clear_redis_prefixes()
    answer_cache_cleared = clear_answer_cache_file(answer_cache_file)

    print(
        json.dumps(
            {
                "answer_cache_cleared": answer_cache_cleared,
                "redis_keys_deleted": deleted_redis_keys,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
