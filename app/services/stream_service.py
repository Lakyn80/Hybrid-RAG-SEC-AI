import asyncio
import contextlib
from collections.abc import AsyncGenerator

from fastapi.responses import StreamingResponse

from app.core.logger import get_logger
from app.services.answer_service import answer_query


logger = get_logger(__name__)

TERMINAL_EVENTS = {"answer_generated", "error"}
HEARTBEAT_INTERVAL_SECONDS = 10.0


def format_sse_event(event_name: str) -> str:
    return f"data: {str(event_name).strip()}\n\n"


def format_sse_comment(comment: str = "keep-alive") -> str:
    return f": {comment}\n\n"


async def _run_observed_query(
    query: str,
    queue: asyncio.Queue[str],
) -> None:
    loop = asyncio.get_running_loop()
    seen_terminal = False

    def emit_event(event_name: str) -> None:
        nonlocal seen_terminal
        normalized_event = str(event_name).strip()
        if not normalized_event:
            return
        if normalized_event in TERMINAL_EVENTS:
            seen_terminal = True
        loop.call_soon_threadsafe(queue.put_nowait, normalized_event)

    try:
        await asyncio.to_thread(
            answer_query,
            query,
            None,
            None,
            emit_event,
            True,
        )
        if not seen_terminal:
            emit_event("answer_generated")
    except Exception as exc:
        logger.info(f"stream_observer_error={exc}")
        if not seen_terminal:
            emit_event("error")


async def stream_pipeline(query: str) -> AsyncGenerator[str, None]:
    queue: asyncio.Queue[str] = asyncio.Queue()
    observer_task = asyncio.create_task(_run_observed_query(query, queue))

    try:
        while True:
            try:
                event_name = await asyncio.wait_for(
                    queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except asyncio.TimeoutError:
                if observer_task.done() and queue.empty():
                    break
                yield format_sse_comment()
                continue

            if not event_name:
                continue

            yield format_sse_event(event_name)

            if event_name in TERMINAL_EVENTS:
                break
    except asyncio.CancelledError:
        observer_task.cancel()
        raise
    except Exception as exc:
        logger.info(f"stream_generator_error={exc}")
        yield format_sse_event("error")
    finally:
        if not observer_task.done():
            observer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await observer_task


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
