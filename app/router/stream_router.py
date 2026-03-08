from fastapi import APIRouter, Query

from app.services.stream_service import create_streaming_response


router = APIRouter()


@router.get("/api/stream")
async def stream(query: str = Query(..., min_length=1)):
    return create_streaming_response(query)
