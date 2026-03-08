import os

from fastapi import APIRouter

from app.core.cache_admin import clear_answer_cache_file, clear_redis_prefixes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "data", "cache", "answer_cache.json")

router = APIRouter()


@router.post("/api/cache/clear")
def clear_runtime_cache():
    deleted_redis_keys = clear_redis_prefixes()
    answer_cache_cleared = clear_answer_cache_file(CACHE_FILE)

    return {
        "ok": True,
        "redis_keys_deleted": deleted_redis_keys,
        "answer_cache_cleared": answer_cache_cleared,
    }
