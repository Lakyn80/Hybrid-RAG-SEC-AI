from __future__ import annotations

import asyncio
import hashlib
import json
import random
from datetime import UTC, datetime
from typing import Any

from app.core.logger import get_logger
from app.retrieval.resources import get_redis_client

logger = get_logger(__name__)

DEMO_KEY_PREFIX = "demo:question"
DEMO_DELAY_MIN_SECONDS = 1.5
DEMO_DELAY_MAX_SECONDS = 3.0


def normalize_question(question: str) -> str:
    return " ".join(str(question or "").strip().lower().split())


def build_demo_question_key(question: str) -> str:
    digest = hashlib.sha256(normalize_question(question).encode("utf-8")).hexdigest()
    return f"{DEMO_KEY_PREFIX}:{digest}"


def build_demo_record(question: str, answer: str) -> dict[str, Any]:
    return {
        "question": str(question or "").strip(),
        "answer": str(answer or "").strip(),
        "created_at": datetime.now(UTC).isoformat(),
        "type": "demo",
    }


def store_demo_response(question: str, answer: str) -> dict[str, Any]:
    payload = build_demo_record(question, answer)
    get_redis_client().set(build_demo_question_key(question), json.dumps(payload, ensure_ascii=False))
    return payload


def reset_demo_cache() -> int:
    client = get_redis_client()
    keys = list(client.scan_iter(match=f"{DEMO_KEY_PREFIX}:*"))
    if not keys:
        return 0
    return int(client.delete(*keys))


def build_fallback_demo_answer(question: str) -> str:
    question_text = str(question or "").strip() or "this filing topic"
    return (
        "Based on the retrieved filing excerpts, the company highlights a mix of legal, "
        "operational, regulatory and market risks that could affect future results. "
        "The filings emphasize compliance exposure, litigation uncertainty, data and "
        "cybersecurity issues, supply-chain execution risk, and macroeconomic pressure. "
        f"For the query \"{question_text}\", the most relevant takeaway is that management "
        "frames these issues as potentially material to operating performance and investor perception."
    )


async def get_demo_response(question: str) -> dict[str, Any]:
    normalized_question = normalize_question(question)
    if not normalized_question:
        payload = build_demo_record(question, build_fallback_demo_answer(question))
        payload["cache_hit"] = False
        return payload

    await asyncio.sleep(random.uniform(DEMO_DELAY_MIN_SECONDS, DEMO_DELAY_MAX_SECONDS))

    raw = None
    try:
        raw = get_redis_client().get(build_demo_question_key(question))
    except Exception as exc:
        logger.info("demo_cache_read_failed=%s", exc)

    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                payload.setdefault("question", str(question or "").strip())
                payload.setdefault("answer", build_fallback_demo_answer(question))
                payload.setdefault("created_at", datetime.now(UTC).isoformat())
                payload["type"] = "demo"
                payload["cache_hit"] = True
                logger.info("demo_cache_hit=True")
                return payload
        except Exception as exc:
            logger.info("demo_cache_parse_failed=%s", exc)

    logger.info("demo_cache_hit=False")
    payload = build_demo_record(question, build_fallback_demo_answer(question))
    payload["cache_hit"] = False
    return payload


__all__ = [
    "build_demo_question_key",
    "build_demo_record",
    "get_demo_response",
    "normalize_question",
    "reset_demo_cache",
    "store_demo_response",
]
