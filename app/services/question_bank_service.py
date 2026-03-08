from __future__ import annotations

import json
import re

import pandas as pd

from app.core.logger import get_logger
from app.llm.langchain_chain import build_chat_llm
from app.retrieval import resources
from app.retrieval.qdrant_store import search_qdrant_rows
from app.utils.topic_extractor import extract_topics_from_chunks

logger = get_logger(__name__)

QUESTION_BANK_CACHE_KEY = "question_bank_v1"
QUESTION_BANK_CACHE_TTL_SECONDS = 60 * 60 * 6
QUESTION_BANK_LIMIT = 100
QUESTION_BANK_TOPIC_LIMIT = 20
QUESTION_BANK_CHUNK_QUERY = (
    "risk factors legal financial business operations management discussion"
)
QUESTION_BANK_CHUNK_LIMIT = 200

QUESTION_TEMPLATES = (
    "What risks related to {topic} are mentioned in the filing?",
    "How does the report describe {topic}?",
    "What challenges related to {topic} does the company identify?",
    "What risks associated with {topic} are discussed?",
    "What factors related to {topic} could impact the company?",
)


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


def _load_cached_question_bank() -> list[str] | None:
    try:
        client = resources.get_redis_client()
        raw_payload = client.get(QUESTION_BANK_CACHE_KEY)
        if not raw_payload:
            return None

        payload = json.loads(raw_payload)
        if not isinstance(payload, dict):
            return None

        cached_version = str(payload.get("index_version") or "").strip()
        current_version = resources.get_vector_index_version()
        if cached_version and cached_version != current_version:
            return None

        questions = payload.get("questions")
        if not isinstance(questions, list):
            return None

        return _dedupe_questions([str(question) for question in questions])
    except Exception as exc:
        logger.info("question_bank_cache_read_failed=%s", exc)
        return None


def _save_cached_question_bank(questions: list[str]) -> None:
    try:
        client = resources.get_redis_client()
        payload = {
            "index_version": resources.get_vector_index_version(),
            "questions": questions,
        }
        client.setex(
            QUESTION_BANK_CACHE_KEY,
            QUESTION_BANK_CACHE_TTL_SECONDS,
            json.dumps(payload, ensure_ascii=False),
        )
    except Exception as exc:
        logger.info("question_bank_cache_write_failed=%s", exc)


def _select_representative_chunks(results_df: pd.DataFrame) -> list[str]:
    if results_df is None or results_df.empty or "chunk_text" not in results_df.columns:
        return []

    deduped = results_df.drop_duplicates(subset=["chunk_text"]).head(QUESTION_BANK_CHUNK_LIMIT)
    return [
        str(chunk_text).strip()
        for chunk_text in deduped["chunk_text"].tolist()
        if str(chunk_text).strip()
    ]


def _generate_template_questions(topics: list[str]) -> list[str]:
    questions: list[str] = []

    for topic in topics:
        for template in QUESTION_TEMPLATES:
            questions.append(template.format(topic=topic))

    return _dedupe_questions(questions)


def _parse_llm_question_lines(raw_text: str) -> list[str]:
    questions: list[str] = []
    for raw_line in str(raw_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^[\-\*\d\.\)\s]+", "", line).strip()
        if not line:
            continue
        if "?" not in line:
            continue
        questions.append(line)

    return _dedupe_questions(questions)


def _refine_questions_with_llm(topics: list[str], fallback_questions: list[str]) -> list[str]:
    try:
        llm = build_chat_llm(temperature=0.0)
        prompt = (
            "Generate clear analytical questions a financial analyst might ask about SEC filings "
            "based on these topics.\n\n"
            f"Topics:\n- " + "\n- ".join(topics[:QUESTION_BANK_TOPIC_LIMIT]) + "\n\n"
            "Return 100 concise questions, one per line, with no numbering and no extra explanation."
        )
        response = llm.invoke(prompt)
        refined = _parse_llm_question_lines(getattr(response, "content", ""))
        if len(refined) < 20:
            return fallback_questions

        merged = _dedupe_questions(refined + fallback_questions)
        return merged[:QUESTION_BANK_LIMIT]
    except Exception as exc:
        logger.info("question_bank_llm_refinement_failed=%s", exc)
        return fallback_questions


def _retrieve_question_bank_chunks() -> list[str]:
    results_df = search_qdrant_rows(
        QUESTION_BANK_CHUNK_QUERY,
        limit=QUESTION_BANK_CHUNK_LIMIT,
    )
    return _select_representative_chunks(results_df)


def build_question_bank() -> list[str]:
    cached_questions = _load_cached_question_bank()
    if cached_questions:
        logger.info("question_bank_cache_hit=True count=%s", len(cached_questions))
        return cached_questions[:QUESTION_BANK_LIMIT]

    chunks = _retrieve_question_bank_chunks()
    topics = extract_topics_from_chunks(chunks, limit=QUESTION_BANK_TOPIC_LIMIT)
    template_questions = _generate_template_questions(topics)
    questions = _refine_questions_with_llm(topics, template_questions)
    final_questions = _dedupe_questions(questions, limit=QUESTION_BANK_LIMIT)

    _save_cached_question_bank(final_questions)
    logger.info("question_bank_generated count=%s topics=%s", len(final_questions), len(topics))
    return final_questions
