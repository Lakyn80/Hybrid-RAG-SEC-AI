import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse

from app.core.logger import get_logger
from app.retrieval.resources import get_redis_client


logger = get_logger(__name__)

TERMINAL_EVENTS = {"answer_generated", "error"}
HEARTBEAT_INTERVAL_SECONDS = 10.0
STREAM_CHANNEL_PREFIX = "pipeline_stream"
STREAM_HISTORY_PREFIX = "pipeline_run"
STREAM_EVENT_TTL_SECONDS = 60 * 60 * 24


def normalize_stream_key(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def format_sse_event(event_name: str) -> str:
    return f"data: {str(event_name).strip()}\n\n"


def format_sse_comment(comment: str = "keep-alive") -> str:
    return f": {comment}\n\n"


def build_stream_channel(run_id: str) -> str:
    return f"{STREAM_CHANNEL_PREFIX}:{normalize_stream_key(run_id)}"


def build_stream_history_key(run_id: str) -> str:
    return f"{STREAM_HISTORY_PREFIX}:{normalize_stream_key(run_id)}"


def _parse_stream_id(value: str) -> tuple[int, int]:
    raw = str(value or "").strip()
    if "-" not in raw:
        return (0, 0)

    left, right = raw.split("-", 1)
    try:
        return (int(left), int(right))
    except ValueError:
        return (0, 0)


def _history_message_payload(record_id: str, event_name: str) -> str:
    return json.dumps(
        {
            "id": record_id,
            "event": str(event_name).strip(),
        },
        ensure_ascii=False,
    )


def publish_pipeline_event(run_id: str, event_name: str) -> None:
    normalized_event = str(event_name or "").strip()
    normalized_run_id = normalize_stream_key(run_id)
    if not normalized_event or not normalized_run_id:
        return

    try:
        client = get_redis_client()
        history_key = build_stream_history_key(normalized_run_id)
        record_id = client.xadd(
            history_key,
            {
                "event": normalized_event,
            },
        )
        client.expire(history_key, STREAM_EVENT_TTL_SECONDS)
        client.publish(
            build_stream_channel(normalized_run_id),
            _history_message_payload(record_id, normalized_event),
        )
    except Exception as exc:
        logger.info(f"stream_publish_failed={exc}")


def read_stream_history(run_id: str) -> list[tuple[str, str]]:
    normalized_run_id = normalize_stream_key(run_id)
    if not normalized_run_id:
        return []

    try:
        raw_entries = get_redis_client().xrange(build_stream_history_key(normalized_run_id))
    except Exception as exc:
        logger.info(f"stream_history_read_failed={exc}")
        return []

    history: list[tuple[str, str]] = []
    for record_id, payload in raw_entries:
        event_name = str((payload or {}).get("event") or "").strip()
        if not event_name:
            continue
        history.append((str(record_id), event_name))
    return history


async def stream_pipeline(run_id: str) -> AsyncGenerator[str, None]:
    pubsub = get_redis_client().pubsub(ignore_subscribe_messages=True)
    normalized_run_id = normalize_stream_key(run_id)
    channel = build_stream_channel(normalized_run_id)
    pubsub.subscribe(channel)
    last_seen_stream_id = (0, 0)

    try:
        for record_id, event_name in read_stream_history(normalized_run_id):
            stream_id = _parse_stream_id(record_id)
            if stream_id <= last_seen_stream_id:
                continue
            last_seen_stream_id = stream_id
            yield format_sse_event(event_name)
            if event_name in TERMINAL_EVENTS:
                return

        while True:
            message = await asyncio.to_thread(
                pubsub.get_message,
                True,
                HEARTBEAT_INTERVAL_SECONDS,
            )

            if message is None:
                yield format_sse_comment()
                continue

            raw_payload = str(message.get("data") or "").strip()
            if not raw_payload:
                continue

            try:
                payload = json.loads(raw_payload)
            except Exception:
                payload = {"event": raw_payload, "id": "0-0"}

            event_name = str(payload.get("event") or "").strip()
            stream_id = _parse_stream_id(str(payload.get("id") or "0-0"))

            if not event_name or stream_id <= last_seen_stream_id:
                continue

            last_seen_stream_id = stream_id
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


def create_streaming_response(run_id: str) -> StreamingResponse:
    return StreamingResponse(
        stream_pipeline(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
