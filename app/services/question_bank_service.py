from __future__ import annotations

import re

from app.core.logger import get_logger
from app.data.question_bank import CURATED_QUESTION_BANK

logger = get_logger(__name__)

QUESTION_BANK_LIMIT = 100


def _clean_question(question: str) -> str:
    text = re.sub(r"\s+", " ", str(question or "").strip())
    return text.rstrip(" .") + "?" if text and not text.endswith("?") else text


def _dedupe_questions(questions: list[str], limit: int = QUESTION_BANK_LIMIT) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()

    for question in questions:
        cleaned = _clean_question(question)
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(cleaned)
        if len(deduped) >= limit:
            break

    return deduped


def build_question_bank() -> list[str]:
    final_questions = _dedupe_questions(CURATED_QUESTION_BANK, limit=QUESTION_BANK_LIMIT)
    logger.info("question_bank_static count=%s", len(final_questions))
    return final_questions
