from fastapi import APIRouter

from app.services.demo_service import reset_demo_cache

router = APIRouter()


@router.post("/api/demo/reset")
def reset_demo_answers():
    deleted_demo_keys = reset_demo_cache()

    return {
        "ok": True,
        "deleted_demo_keys": deleted_demo_keys,
    }
