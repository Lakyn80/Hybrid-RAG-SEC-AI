import asyncio
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse

from app.core.logger import get_logger
from app.retrieval.resources import get_redis_client


logger = get_logger(__name__)

TERMINAL_EVENTS = {"answer_generated", "error"}
HEARTBEAT_INTERVAL_SECONDS = 10.0
STREAM_CHANNEL_PREFIX = "pipeline_stream"


def normalize_stream_key(query: str) -> str:
    return " ".join(str(query or "").strip().lower().split())


def format_sse_event(event_name: str) -> str:
    return f"data: {str(event_name).strip()}\n\n"


def format_sse_comment(comment: str = "keep-alive") -> str:
    return f": {comment}\n\n"


def build_stream_channel(query: str) -> str:
    return f"{STREAM_CHANNEL_PREFIX}:{normalize_stream_key(query)}"


def publish_pipeline_event(query: str, event_name: str) -> None:
    normalized_event = str(event_name or "").strip()
    if not normalized_event:
        return

    try:
        get_redis_client().publish(build_stream_channel(query), normalized_event)
    except Exception as exc:
        logger.info(f"stream_publish_failed={exc}")


async def stream_pipeline(query: str) -> AsyncGenerator[str, None]:
    pubsub = get_redis_client().pubsub(ignore_subscribe_messages=True)
    channel = build_stream_channel(query)
    pubsub.subscribe(channel)

    try:
        while True:
            message = await asyncio.to_thread(
                pubsub.get_message,
                True,
                HEARTBEAT_INTERVAL_SECONDS,
            )

            if message is None:
                yield format_sse_comment()
                continue

            event_name = str(message.get("data") or "").strip()
            if not event_name:
                continue

            yield format_sse_event(event_name)

            if event_name in TERMINAL_EVENTS:
                break
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.info(f"stream_generator_error={exc}")
        yield format_sse_event("error")
    finally:
        try:
            pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            pubsub.close()
        except Exception:
            pass


def create_streaming_response(query: str) -> StreamingResponse:
    return StreamingResponse(
        stream_pipeline(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
