from fastapi import APIRouter, HTTPException, Query

from app.services.stream_service import create_streaming_response


router = APIRouter()


@router.get("/api/stream")
async def stream(
    query: str | None = Query(default=None, min_length=1),
    run_id: str | None = Query(default=None, min_length=1),
):
    stream_key = str(run_id or query or "").strip()
    if not stream_key:
        raise HTTPException(status_code=400, detail="Missing query or run_id parameter.")
    return create_streaming_response(stream_key)
