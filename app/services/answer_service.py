def limit_context_rows(results_df, max_chunks=None):
    if results_df is None:
        return results_df
    return results_df.head(max_chunks or TOP_K)
from collections import Counter
import os
import re
import json
import time
import hashlib
from uuid import uuid4
from typing import Any, Callable, TypedDict

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from app.core.cache_stats import increment_cache_stat
from app.core.logger import get_logger, log_structured
from app.retrieval import resources as retrieval_resources
from app.retrieval.reranker import MODEL_NAME as RERANKER_MODEL_NAME, rerank
from app.retrieval.retrieval_cache import (
    build_retrieval_cache_key,
    read_retrieval_cache,
    write_retrieval_cache,
)
from app.llm.langchain_chain import run_chain
from app.router.query_router import (
    build_multi_company_subqueries,
    classify_query,
    detect_companies,
    detect_primary_company,
    detect_sec_form,
    extract_query_topic,
    get_company_display_name,
)
from app.services.query_guard import is_query_allowed
from app.services.semantic_cache import lookup_semantic_cache, save_semantic_cache

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
INDEX_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks.index")
METADATA_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks_metadata.parquet")
load_dotenv(dotenv_path=ENV_FILE, override=False)

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 10
RETRIEVAL_CANDIDATES = 50
VECTOR_SEARCH_K = 50
MAX_FALLBACK_SENTENCES = 5
MAX_ANSWER_SENTENCES = 6
RANKING_POLICY_VERSION = "content_rank_v3"

LLM_CACHE_TTL_SECONDS = 60 * 60 * 24
FALLBACK_CACHE_TTL_SECONDS = 60 * 10
ANSWER_CACHE_PREFIX = "answer:v1"
ANSWER_CACHE_TTL_SECONDS = 60 * 60 * 24

RISK_HINT_WORDS = {
    "risk", "risks", "risky", "adverse", "adversely", "uncertain", "uncertainty",
    "legal", "litigation", "regulation", "regulatory", "economic", "economy",
    "supplier", "suppliers", "supply", "geopolitical", "trade", "conflict",
    "terrorism", "disaster", "public", "health", "privacy", "security",
    "competition", "market", "volatile", "volatility", "credit", "liquidity"
}

RANKING_STOP_WORDS = {
    "a", "about", "according", "all", "an", "and", "annual", "any", "are", "as", "at",
    "based", "be", "by", "company", "did", "disclose", "discussed", "documents", "does",
    "filing", "filings", "for", "from", "how", "in", "into", "is", "its", "it", "may",
    "mention", "mentioned", "of", "on", "or", "over", "please", "report", "reports",
    "related", "regarding", "sec", "should", "summarize", "tell", "the", "their", "them",
    "these", "this", "to", "what", "which", "who", "with", "would",
}

LEGAL_QUERY_TERMS = {
    "legal", "litigation", "lawsuit", "lawsuits", "claims", "claim", "regulatory",
    "proceedings", "proceeding", "contingencies", "contingency", "penalties",
    "penalty", "disputes", "dispute", "intellectual", "property", "liability",
    "liabilities", "compliance", "investigations", "investigation", "fiduciary",
}

FINANCIAL_QUERY_TERMS = {
    "revenue", "income", "profit", "profits", "earnings", "margin", "cash", "liquidity",
    "balance", "sheet", "assets", "liabilities", "debt", "operating", "expenses",
    "financial", "results",
}

GOVERNANCE_QUERY_TERMS = {
    "governance", "proxy", "board", "director", "directors", "committee",
    "compensation", "shareholder", "shareholders", "stockholder", "stockholders",
    "nominee", "election",
}

COMPARE_QUERY_TERMS = {
    "compare", "difference", "differences", "versus", "vs", "between",
}

TABLE_OF_CONTENTS_PATTERNS = (
    "table of contents",
    "item 1. business",
    "item 1a. risk factors",
    "item 7. management",
    "item 8. financial statements",
)

FORWARD_LOOKING_PATTERNS = (
    "forward-looking statements",
    "private securities litigation reform act",
    "actual results could differ materially",
    "speak only as of the date",
    "undertake no obligation to update",
)

RISK_INTRO_PATTERNS = (
    "we discuss many of these risks",
    "you should read this annual report",
    "the risks described below",
    "any of the following risks",
    "the order in which the risks are presented",
)

LOW_VALUE_CONTENT_BUCKETS = {
    "table_of_contents",
    "forward_looking_boilerplate",
    "risk_intro",
}

CONTENT_BUCKET_LABELS = (
    "table_of_contents",
    "forward_looking_boilerplate",
    "risk_intro",
    "legal_substantive",
    "risk_substantive",
    "financial_substantive",
    "mda_substantive",
    "governance_substantive",
    "generic",
)

PipelineEventCallback = Callable[[str], None]


def normalize_env_value(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


LLM_API_URL = normalize_env_value(os.getenv("LLM_API_URL")) or "https://api.deepseek.com/chat/completions"
LLM_MODEL = normalize_env_value(os.getenv("LLM_MODEL")) or "deepseek-chat"


def llm_api_key_present() -> bool:
    return bool(normalize_env_value(os.getenv("DEEPSEEK_API_KEY")))


def infer_company_filter(query: str) -> str | None:
    return detect_primary_company(query)


def infer_form_filter(query: str) -> str | None:
    return detect_sec_form(query)


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def clean_sentence_text(sentence: str) -> str:
    s = re.sub(r"\s+", " ", str(sentence)).strip()
    s = re.sub(r"^\|\s*\d{4}\s+Form\s+[A-Z0-9\-\/ ]+\s*\|\s*\d+\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^[A-Za-z0-9 .,;&()\-]{0,40}\|\s*\d{4}\s+Form\s+[A-Z0-9\-\/ ]+\s*\|\s*\d+\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\|\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sentence_keyword_score(sentence: str, query: str) -> int:
    sentence_lower = sentence.lower()
    query_words = re.findall(r"[a-zA-Z0-9\-]+", query.lower())
    base = sum(1 for word in query_words if len(word) > 2 and word in sentence_lower)
    risk_bonus = sum(1 for word in RISK_HINT_WORDS if word in sentence_lower)
    return base + risk_bonus


def is_good_sentence(sentence: str) -> bool:
    s = clean_sentence_text(sentence)

    if len(s) < 60:
        return False

    if s.endswith(":"):
        return False

    if not re.search(r"[A-Za-z]", s):
        return False

    if s.count(" ") < 8:
        return False

    digit_count = sum(ch.isdigit() for ch in s)
    alpha_count = sum(ch.isalpha() for ch in s)

    if alpha_count == 0:
        return False

    if digit_count > alpha_count * 0.35:
        return False

    bad_starts = (
        "apple inc.",
        "item ",
        "part ",
        "table of contents",
        "©",
        "copyright",
        "|",
    )
    if s.lower().startswith(bad_starts):
        return False

    if re.match(r"^\d{4}\s+form\s+", s.lower()):
        return False

    if " in millions" in s.lower():
        return False

    if "$" in s and digit_count > 3:
        return False

    return True


def format_sources(results_df: pd.DataFrame) -> str:
    source_lines = []
    seen = set()

    for _, row in results_df.iterrows():
        key = (str(row["company"]), str(row["form"]), str(row["filing_date"]), str(row["filing_url"]))
        if key in seen:
            continue
        seen.add(key)
        source_lines.append(
            f"- {row['company']} | {row['form']} | {row['filing_date']} | {row['filing_url']}"
        )

    if not source_lines:
        return "Sources:\n- No sources available."

    return "Sources:\n" + "\n".join(source_lines)


def emit_pipeline_event(state: "GraphState", event_name: str) -> None:
    log_structured(
        logger,
        "pipeline_step",
        run_id=state.get("run_id"),
        query=state.get("query"),
        step=str(event_name).strip(),
    )
    try:
        from app.services.stream_service import publish_pipeline_event

        publish_pipeline_event(state.get("run_id", ""), str(event_name).strip())
    except Exception as exc:
        logger.info(f"stream_event_publish_failed={exc}")

    callback = state.get("event_callback")
    if not callable(callback):
        return

    try:
        callback(str(event_name).strip())
    except Exception as exc:
        logger.info(f"stream_event_emit_failed={exc}")


def filters_are_active(company_filter: str | None, form_filter: str | None) -> bool:
    return bool(str(company_filter or "").strip() or str(form_filter or "").strip())


def build_effective_index_version(index_version: str) -> str:
    base_version = str(index_version or "unknown").strip() or "unknown"
    return f"{base_version}:ranking:{RANKING_POLICY_VERSION}"


def tokenize_rank_terms(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", str(text).lower())
    return [
        token for token in tokens
        if len(token) > 2 and token not in RANKING_STOP_WORDS and not token.isdigit()
    ]


def tokenize_similarity_terms(text: str) -> set[str]:
    return set(tokenize_rank_terms(text))


def normalize_score_series(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).astype(float)
    if numeric.empty:
        return numeric

    min_value = float(numeric.min())
    max_value = float(numeric.max())

    if max_value - min_value < 1e-9:
        if max_value <= 0:
            return pd.Series(0.0, index=numeric.index)
        return pd.Series(1.0, index=numeric.index)

    return (numeric - min_value) / (max_value - min_value)


def contains_any_phrase(text: str, phrases: tuple[str, ...] | set[str]) -> bool:
    lowered = str(text).lower()
    return any(phrase in lowered for phrase in phrases)


def count_phrase_matches(text: str, phrases: tuple[str, ...] | set[str]) -> int:
    lowered = str(text).lower()
    return sum(1 for phrase in phrases if phrase in lowered)


def detect_query_focus(query: str, query_type: str) -> dict[str, bool]:
    tokens = set(tokenize_rank_terms(query))

    return {
        "risk": query_type == "risk" or bool(tokens & RISK_HINT_WORDS),
        "legal": bool(tokens & LEGAL_QUERY_TERMS),
        "financial": query_type == "financial" or bool(tokens & FINANCIAL_QUERY_TERMS),
        "governance": bool(tokens & GOVERNANCE_QUERY_TERMS),
        "compare": query_type == "compare" or bool(tokens & COMPARE_QUERY_TERMS),
    }


def build_semantic_scope(query: str, query_type: str) -> str:
    topic = extract_query_topic(query)
    normalized_topic = "_".join(tokenize_rank_terms(topic)[:4]) or "general_topic"
    return f"{query_type}:{normalized_topic}"


def classify_chunk_content(chunk_text: str) -> str:
    text = str(chunk_text or "").lower()

    if contains_any_phrase(text, TABLE_OF_CONTENTS_PATTERNS):
        item_hits = len(re.findall(r"\bitem\s+\d+[a-z]?\b", text))
        if item_hits >= 2 or "table of contents" in text:
            return "table_of_contents"

    if contains_any_phrase(text, FORWARD_LOOKING_PATTERNS):
        return "forward_looking_boilerplate"

    legal_hits = count_phrase_matches(
        text,
        {
            "legal proceedings",
            "we are involved in",
            "we are engaged in",
            "lawsuit",
            "lawsuits",
            "litigation",
            "claims",
            "claim",
            "regulatory action",
            "regulatory proceeding",
            "government investigation",
            "government investigations",
            "intellectual property",
            "loss contingencies",
            "loss contingency",
            "breach of fiduciary duty",
            "exchange act",
            "damages",
            "injunctive relief",
            "civil action",
            "civil actions",
        },
    )
    if legal_hits >= 2 or contains_any_phrase(
        text,
        {
            "accounting for loss contingencies",
            "the lawsuits assert claims",
            "we are engaged in legal actions",
            "intellectual property litigation",
        },
    ):
        return "legal_substantive"

    if contains_any_phrase(
        text,
        {
            "management's discussion and analysis",
            "results of operations",
            "liquidity and capital resources",
        },
    ):
        return "mda_substantive"

    financial_hits = count_phrase_matches(
        text,
        {
            "revenue",
            "net income",
            "operating income",
            "gross margin",
            "cash flow",
            "cash flows",
            "balance sheets",
            "liquidity",
            "debt",
            "accounts receivable",
            "inventory",
            "fair value",
            "operating expenses",
        },
    )
    if financial_hits >= 2:
        return "financial_substantive"

    governance_hits = count_phrase_matches(
        text,
        {
            "board of directors",
            "audit committee",
            "executive compensation",
            "proxy statement",
            "stockholder",
            "shareholder",
            "governance",
            "director nominee",
        },
    )
    if governance_hits >= 2:
        return "governance_substantive"

    if contains_any_phrase(text, RISK_INTRO_PATTERNS):
        return "risk_intro"

    risk_hits = count_phrase_matches(
        text,
        {
            "risk factor",
            "risk factors",
            "could adversely affect",
            "material adverse effect",
            "subject to risks",
            "subject to a variety of risks",
            "could harm",
            "uncertainties",
            "adverse effect",
        },
    )
    if risk_hits >= 2:
        return "risk_substantive"

    return "generic"


def calculate_boilerplate_penalty(content_bucket: str, chunk_text: str) -> float:
    penalty = 0.0
    text = str(chunk_text or "").lower()

    if content_bucket == "table_of_contents":
        penalty += 0.60
    if content_bucket == "forward_looking_boilerplate":
        penalty += 0.55
    if content_bucket == "risk_intro":
        penalty += 0.25
    if "available information" in text or "www." in text:
        penalty += 0.20
    if "annual report on form 10-k" in text and "you should read" in text:
        penalty += 0.20

    return penalty


def calculate_query_overlap(query: str, chunk_text: str) -> float:
    query_tokens = tokenize_similarity_terms(query)
    if not query_tokens:
        return 0.0

    chunk_tokens = tokenize_similarity_terms(chunk_text)
    if not chunk_tokens:
        return 0.0

    overlap = len(query_tokens & chunk_tokens) / len(query_tokens)
    return min(max(overlap, 0.0), 1.0)


def calculate_form_boost(
    query_focus: dict[str, bool],
    form_value: str,
    form_filter: str | None,
) -> float:
    if form_filter:
        return 0.0

    form = str(form_value or "").strip().upper()
    if not form:
        return 0.0

    boost = 0.0

    if query_focus["governance"]:
        if form == "DEF 14A":
            boost += 0.22
        elif form == "8-K":
            boost -= 0.04
        elif form in {"10-K", "10-Q"}:
            boost -= 0.06
        return boost

    if query_focus["financial"]:
        if form == "10-Q":
            boost += 0.16
        elif form == "10-K":
            boost += 0.12
        elif form == "8-K":
            boost -= 0.08
        elif form == "DEF 14A":
            boost -= 0.18
        return boost

    if query_focus["risk"] or query_focus["legal"]:
        if form == "10-K":
            boost += 0.18
        elif form == "10-Q":
            boost += 0.08
        elif form == "8-K":
            boost -= 0.10
        elif form == "DEF 14A":
            boost -= 0.14
        return boost

    if query_focus["compare"]:
        if form == "10-K":
            boost += 0.08
        elif form == "10-Q":
            boost += 0.03
        elif form == "DEF 14A":
            boost -= 0.05

    return boost


def calculate_topic_specific_boost(query: str, chunk_text: str) -> float:
    topic_tokens = tokenize_similarity_terms(extract_query_topic(query))
    if not topic_tokens:
        return 0.0

    chunk_tokens = tokenize_similarity_terms(chunk_text)
    if not chunk_tokens:
        return 0.0

    overlap = len(topic_tokens & chunk_tokens)
    if overlap >= 3:
        return 0.14
    if overlap >= 2:
        return 0.10
    if overlap == 1 and len(topic_tokens) == 1:
        return 0.06
    return 0.0


def calculate_content_boost(
    query_focus: dict[str, bool],
    content_bucket: str,
    chunk_text: str,
) -> float:
    boost = 0.0
    text = str(chunk_text or "").lower()

    if query_focus["risk"]:
        if content_bucket == "risk_substantive":
            boost += 0.18
        if content_bucket == "legal_substantive":
            boost += 0.20

    if query_focus["legal"]:
        if content_bucket == "legal_substantive":
            boost += 0.28
        elif "legal proceedings" in text or "loss contingencies" in text:
            boost += 0.14

    if query_focus["financial"]:
        if content_bucket == "financial_substantive":
            boost += 0.24
        if content_bucket == "mda_substantive":
            boost += 0.14

    if query_focus["governance"]:
        if content_bucket == "governance_substantive":
            boost += 0.26

    if query_focus["compare"] and content_bucket in {
        "risk_substantive",
        "legal_substantive",
        "financial_substantive",
        "mda_substantive",
        "governance_substantive",
    }:
        boost += 0.08

    if not any(query_focus.values()) and content_bucket not in LOW_VALUE_CONTENT_BUCKETS:
        boost += 0.05

    return boost


def prepare_retrieval_source(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    prepared = df.copy()
    prepared["retrieval_source"] = source_name
    prepared["raw_retrieval_score"] = pd.to_numeric(prepared.get("score", 0.0), errors="coerce").fillna(0.0)
    prepared["retrieval_score_norm"] = normalize_score_series(prepared["raw_retrieval_score"])
    if "chunk_hash" in prepared.columns:
        merge_key = prepared["chunk_hash"].astype(str).str.strip()
        prepared["merge_key"] = merge_key.where(merge_key.ne(""), prepared["chunk_text"].astype(str))
    else:
        prepared["merge_key"] = prepared["chunk_text"].astype(str)
    return prepared


def merge_retrieval_candidates(*frames: pd.DataFrame) -> pd.DataFrame:
    prepared_frames = [frame for frame in frames if frame is not None and not frame.empty]
    if not prepared_frames:
        return pd.DataFrame()

    merged = pd.concat(prepared_frames, ignore_index=True)
    records: list[dict[str, Any]] = []

    for _, group in merged.groupby("merge_key", sort=False):
        ranked_group = group.sort_values(
            by=["retrieval_score_norm", "raw_retrieval_score"],
            ascending=[False, False],
            kind="mergesort",
        )
        base_row = ranked_group.iloc[0].copy()
        sources = sorted(set(ranked_group["retrieval_source"].astype(str).tolist()))
        source_count = len(sources)
        retrieval_signal = float(ranked_group["retrieval_score_norm"].max()) + (0.08 * max(source_count - 1, 0))

        base_row["retrieval_source"] = "+".join(sources)
        base_row["source_count"] = source_count
        base_row["duplicate_count"] = int(len(ranked_group))
        base_row["vector_score"] = float(
            ranked_group.loc[ranked_group["retrieval_source"] == "vector", "raw_retrieval_score"].max()
        ) if "vector" in sources else 0.0
        base_row["bm25_score"] = float(
            ranked_group.loc[ranked_group["retrieval_source"] == "bm25", "raw_retrieval_score"].max()
        ) if "bm25" in sources else 0.0
        base_row["retrieval_signal"] = min(retrieval_signal, 1.0)
        base_row["score"] = base_row["retrieval_signal"]
        records.append(base_row.to_dict())

    return pd.DataFrame(records)


def build_chunk_preview(chunk_text: str, max_length: int = 180) -> str:
    preview = re.sub(r"\s+", " ", str(chunk_text or "")).strip()
    if len(preview) <= max_length:
        return preview
    return preview[: max_length - 3].rstrip() + "..."


def safe_round_score(value: Any) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return 0.0
    return round(float(numeric), 4)


def log_top_chunk_scores(results_df: pd.DataFrame, label: str, limit: int = 5) -> None:
    if results_df is None or results_df.empty:
        logger.info(f"{label}=[]")
        return

    sort_columns = [
        column
        for column in ("final_score", "rerank_score", "retrieval_signal", "score")
        if column in results_df.columns
    ]
    sorted_df = results_df.sort_values(
        by=sort_columns or ["chunk_text"],
        ascending=[False] * len(sort_columns) if sort_columns else [True],
        kind="mergesort",
    )

    entries: list[dict[str, Any]] = []
    for _, row in sorted_df.head(limit).iterrows():
        entry = {
            "company": str(row.get("company", "")),
            "form": str(row.get("form", "")),
            "filing_date": str(row.get("filing_date", "")),
            "content_bucket": str(row.get("content_bucket", "")),
            "retrieval_source": str(row.get("retrieval_source", "")),
            "score": safe_round_score(row.get("score", 0.0)),
            "retrieval_signal": safe_round_score(row.get("retrieval_signal", 0.0)),
            "rerank_score": safe_round_score(row.get("rerank_score", 0.0)),
            "final_score": safe_round_score(row.get("final_score", 0.0)),
            "chunk_preview": build_chunk_preview(str(row.get("chunk_text", ""))),
        }
        entries.append(entry)

    logger.info(f"{label}={json.dumps(entries, ensure_ascii=False)}")


def build_document_id(row: pd.Series | dict[str, Any]) -> str:
    data = row if isinstance(row, dict) else row.to_dict()
    chunk_hash = str(data.get("chunk_hash") or "").strip()
    if chunk_hash:
        return chunk_hash

    vector_id = str(data.get("vector_id") or "").strip()
    if vector_id:
        return vector_id

    accession_number = str(data.get("accession_number") or "").strip()
    chunk_index = str(data.get("chunk_index") or "").strip()
    if accession_number and chunk_index:
        return f"{accession_number}:{chunk_index}"

    filing_url = str(data.get("filing_url") or "").strip()
    if filing_url and chunk_index:
        return f"{filing_url}#{chunk_index}"

    return hashlib.sha256(str(data.get("chunk_text") or "").encode("utf-8")).hexdigest()[:16]


def summarize_retrieval_trace(results_df: pd.DataFrame, limit: int = 10) -> tuple[list[str], list[float], list[float]]:
    if results_df is None or results_df.empty:
        return [], [], []

    sort_columns = [
        column
        for column in ("final_score", "rerank_score", "retrieval_signal", "score")
        if column in results_df.columns
    ]
    sorted_df = results_df.sort_values(
        by=sort_columns or ["chunk_text"],
        ascending=[False] * len(sort_columns) if sort_columns else [True],
        kind="mergesort",
    )

    document_ids: list[str] = []
    rerank_scores: list[float] = []
    final_scores: list[float] = []

    for _, row in sorted_df.head(limit).iterrows():
        document_ids.append(build_document_id(row))
        rerank_scores.append(safe_round_score(row.get("rerank_score", 0.0)))
        final_scores.append(safe_round_score(row.get("final_score", row.get("score", 0.0))))

    return document_ids, rerank_scores, final_scores


def apply_blended_ranking(
    results_df: pd.DataFrame,
    query: str,
    query_type: str,
    form_filter: str | None = None,
) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return results_df

    ranked_df = results_df.copy()
    ranked_df["content_bucket"] = ranked_df["chunk_text"].astype(str).apply(classify_chunk_content)
    ranked_df["rerank_score_norm"] = normalize_score_series(ranked_df["rerank_score"])
    ranked_df["retrieval_signal"] = pd.to_numeric(
        ranked_df.get("retrieval_signal", ranked_df.get("score", 0.0)),
        errors="coerce",
    ).fillna(0.0)
    ranked_df["retrieval_signal_norm"] = normalize_score_series(ranked_df["retrieval_signal"])

    query_focus = detect_query_focus(query, query_type)
    ranked_df["query_overlap"] = ranked_df["chunk_text"].astype(str).apply(
        lambda text: calculate_query_overlap(query, text)
    )
    ranked_df["boilerplate_penalty"] = ranked_df.apply(
        lambda row: calculate_boilerplate_penalty(str(row.get("content_bucket", "generic")), str(row.get("chunk_text", ""))),
        axis=1,
    )
    ranked_df["content_boost"] = ranked_df.apply(
        lambda row: calculate_content_boost(query_focus, str(row.get("content_bucket", "generic")), str(row.get("chunk_text", ""))),
        axis=1,
    )
    ranked_df["form_boost"] = ranked_df.apply(
        lambda row: calculate_form_boost(query_focus, str(row.get("form", "")), form_filter),
        axis=1,
    )
    ranked_df["topic_boost"] = ranked_df["chunk_text"].astype(str).apply(
        lambda text: calculate_topic_specific_boost(query, text)
    )
    ranked_df["final_score"] = (
        (0.62 * ranked_df["rerank_score_norm"])
        + (0.24 * ranked_df["retrieval_signal_norm"])
        + (0.14 * ranked_df["query_overlap"])
        + ranked_df["content_boost"]
        + ranked_df["form_boost"]
        + ranked_df["topic_boost"]
        - ranked_df["boilerplate_penalty"]
    )
    ranked_df = ranked_df.sort_values("final_score", ascending=False, kind="mergesort")

    bucket_counts = Counter(ranked_df["content_bucket"].tolist())
    logger.info(f"content_bucket_counts={json.dumps(dict(bucket_counts), sort_keys=True)}")
    log_top_chunk_scores(ranked_df, "top_chunks_ranked", limit=8)
    return ranked_df


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def select_diverse_context_rows(results_df: pd.DataFrame, max_chunks: int) -> pd.DataFrame:
    if results_df is None or results_df.empty:
        return results_df

    sorted_df = results_df.copy()
    sort_column = "final_score" if "final_score" in sorted_df.columns else "rerank_score" if "rerank_score" in sorted_df.columns else "score"
    sorted_df = sorted_df.sort_values(sort_column, ascending=False, kind="mergesort")

    selected_rows = []
    selected_tokens: list[set[str]] = []
    low_value_counts: Counter[str] = Counter()
    selected_keys: set[Any] = set()

    for _, row in sorted_df.iterrows():
        bucket = str(row.get("content_bucket", "generic"))
        merge_key = row.get("merge_key") or row.get("chunk_hash") or row.get("chunk_text")
        if merge_key in selected_keys:
            continue

        if bucket in LOW_VALUE_CONTENT_BUCKETS and low_value_counts[bucket] >= 1:
            continue

        token_set = tokenize_similarity_terms(str(row.get("chunk_text", "")))
        if token_set and any(jaccard_similarity(token_set, existing) >= 0.82 for existing in selected_tokens):
            continue

        selected_rows.append(row.to_dict())
        selected_keys.add(merge_key)
        selected_tokens.append(token_set)
        if bucket in LOW_VALUE_CONTENT_BUCKETS:
            low_value_counts[bucket] += 1

        if len(selected_rows) >= max_chunks:
            break

    if len(selected_rows) < max_chunks:
        for _, row in sorted_df.iterrows():
            merge_key = row.get("merge_key") or row.get("chunk_hash") or row.get("chunk_text")
            if merge_key in selected_keys:
                continue

            selected_rows.append(row.to_dict())
            selected_keys.add(merge_key)
            if len(selected_rows) >= max_chunks:
                break

    return pd.DataFrame(selected_rows)


def apply_metadata_filters(
    results_df: pd.DataFrame,
    company_filter: str | None = None,
    form_filter: str | None = None,
) -> pd.DataFrame:
    filtered_df = results_df.copy()

    if company_filter:
        company_value = str(company_filter).strip()
        filtered_df = filtered_df[
            filtered_df["company"].astype(str).str.contains(
                company_value,
                case=False,
                na=False,
                regex=False,
            )
        ].copy()

    if form_filter:
        form_value = str(form_filter).strip().upper()
        filtered_df = filtered_df[
            filtered_df["form"].astype(str).str.upper() == form_value
        ].copy()

    return filtered_df


def finalize_results_df(
    results_df: pd.DataFrame,
    company_filter: str | None = None,
    form_filter: str | None = None,
) -> pd.DataFrame:
    logger.info(f"retrieved_rows={len(results_df)}")

    filtered_df = results_df.copy()

    if company_filter:
        filtered_df = apply_metadata_filters(filtered_df, company_filter=company_filter)
    logger.info(f"filtered_company_rows={len(filtered_df)}")

    if form_filter:
        filtered_df = apply_metadata_filters(filtered_df, form_filter=form_filter)
    logger.info(f"filtered_form_rows={len(filtered_df)}")

    if filtered_df.empty:
        raise ValueError("Filtered retrieval returned no rows")

    if "final_score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("final_score", ascending=False, kind="mergesort")
    elif "rerank_score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("rerank_score", ascending=False, kind="mergesort")
    elif "score" in filtered_df.columns:
        filtered_df = filtered_df.sort_values("score", ascending=False, kind="mergesort")

    filtered_df = filtered_df.drop_duplicates(subset=["chunk_text"])
    filtered_df = select_diverse_context_rows(filtered_df, max_chunks=TOP_K)
    logger.info(f"final_context_rows={len(filtered_df)}")
    log_top_chunk_scores(filtered_df, "top_chunks_context", limit=min(TOP_K, 10))
    return filtered_df


def normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def build_cache_key(query: str, company_filter: str | None, form_filter: str | None) -> str:
    payload = {
        "query": normalize_query(query),
        "company_filter": (company_filter or "").strip().lower(),
        "form_filter": (form_filter or "").strip().lower(),
        "llm_model": LLM_MODEL.strip().lower(),
        "ranking_policy_version": RANKING_POLICY_VERSION,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_answer_cache_key(cache_key: str) -> str:
    return f"{ANSWER_CACHE_PREFIX}:{cache_key}"


def load_cache() -> dict:
    try:
        client = retrieval_resources.get_redis_client()
        keys = list(client.scan_iter(match=f"{ANSWER_CACHE_PREFIX}:*"))
        if not keys:
            return {}

        payloads = client.mget(keys)
    except Exception:
        return {}

    cache_data: dict[str, dict[str, Any]] = {}
    for key, payload in zip(keys, payloads, strict=False):
        if not payload:
            continue

        try:
            entry = json.loads(payload)
        except Exception:
            continue

        if not isinstance(entry, dict):
            continue

        bare_key = str(key).split(f"{ANSWER_CACHE_PREFIX}:", 1)[-1]
        cache_data[bare_key] = entry

    return cache_data


def read_cached_answer(cache_key: str) -> dict | None:
    try:
        raw = retrieval_resources.get_redis_client().get(build_answer_cache_key(cache_key))
    except Exception:
        return None

    if not raw:
        return None

    try:
        data = json.loads(raw)
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def write_cached_answer(cache_key: str, entry: dict[str, Any]) -> None:
    if not isinstance(entry, dict):
        return

    try:
        retrieval_resources.get_redis_client().setex(
            build_answer_cache_key(str(cache_key)),
            ANSWER_CACHE_TTL_SECONDS,
            json.dumps(entry, ensure_ascii=False),
        )
    except Exception:
        return


def save_cache(cache_data: dict) -> None:
    if not isinstance(cache_data, dict):
        return

    try:
        client = retrieval_resources.get_redis_client()
        existing_keys = list(client.scan_iter(match=f"{ANSWER_CACHE_PREFIX}:*"))
        provided_keys = {
            build_answer_cache_key(str(cache_key))
            for cache_key, entry in cache_data.items()
            if isinstance(entry, dict)
        }
        keys_to_delete = [key for key in existing_keys if key not in provided_keys]
        if keys_to_delete:
            client.delete(*keys_to_delete)
    except Exception:
        return

    for cache_key, entry in cache_data.items():
        if isinstance(entry, dict):
            write_cached_answer(str(cache_key), entry)


def get_cache_ttl_for_mode(mode: str) -> int:
    if str(mode).strip().lower() == "llm":
        return LLM_CACHE_TTL_SECONDS
    return FALLBACK_CACHE_TTL_SECONDS


def cleanup_expired_cache(cache_data: dict) -> dict:
    return cache_data if isinstance(cache_data, dict) else {}


def get_valid_cached_entry(cache_data: dict, cache_key: str) -> dict | None:
    entry = read_cached_answer(cache_key)

    if not isinstance(entry, dict):
        return None

    mode = str(entry.get("mode", "")).strip().lower()
    created_at = entry.get("created_at")

    if not isinstance(created_at, (int, float)):
        return None

    if mode == "fallback" and llm_api_key_present():
        return None

    age = time.time() - float(created_at)

    if age > ANSWER_CACHE_TTL_SECONDS:
        return None

    return entry


def search_rows(query: str, company_filter: str | None = None, form_filter: str | None = None) -> pd.DataFrame:
    backend = retrieval_resources.get_runtime_vector_backend()

    if backend == "qdrant":
        from app.retrieval.qdrant_store import search_qdrant_rows

        results_df = search_qdrant_rows(
            query,
            company_filter=company_filter,
            form_filter=form_filter,
            limit=VECTOR_SEARCH_K,
            embedding_model_name=MODEL_NAME,
        )
    else:
        if not os.path.exists(INDEX_FILE):
            raise FileNotFoundError("FAISS index does not exist.")

        if not os.path.exists(METADATA_FILE):
            raise FileNotFoundError("Metadata parquet does not exist.")

        metadata_df = retrieval_resources.get_metadata_df()
        index = retrieval_resources.get_faiss_index()

        model = retrieval_resources.get_embedding_model(MODEL_NAME)

        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        query_embedding = np.asarray(query_embedding, dtype="float32")

        search_k = min(VECTOR_SEARCH_K, len(metadata_df))
        scores, indices = index.search(query_embedding, search_k)

        result_rows = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(metadata_df):
                continue

            row = metadata_df.iloc[int(idx)].copy()
            row["score"] = float(score)
            result_rows.append(row)

        if not result_rows:
            raise ValueError("No search results found.")

        results_df = pd.DataFrame(result_rows)

    results_df = apply_metadata_filters(
        results_df,
        company_filter=company_filter,
        form_filter=form_filter,
    )

    if results_df.empty:
        raise ValueError("No rows match the requested metadata filters.")

    return results_df


def build_context(results_df: pd.DataFrame) -> str:
    if "final_score" in results_df.columns:
        results_df = results_df.sort_values("final_score", ascending=False, kind="mergesort")
    elif "rerank_score" in results_df.columns:
        results_df = results_df.sort_values("rerank_score", ascending=False, kind="mergesort")
    elif "score" in results_df.columns:
        results_df = results_df.sort_values("score", ascending=False, kind="mergesort")

    results_df = select_diverse_context_rows(results_df, max_chunks=TOP_K)
    blocks = []

    for index, (_, row) in enumerate(results_df.iterrows(), start=1):
        header = (
            f"[Excerpt {index} | Company: {row.get('company', '')} | "
            f"Form: {row.get('form', '')} | "
            f"Date: {row.get('filing_date', '')}]"
        )
        chunk_text = re.sub(r"\s+", " ", str(row.get("chunk_text", ""))).strip()
        blocks.append(f"{header}\n{chunk_text}")

    return "\n\n".join(blocks)


def build_fallback_answer(query: str, results_df: pd.DataFrame) -> str:
    candidates = []

    for _, row in results_df.iterrows():
        sentences = split_sentences(row["chunk_text"])
        for sentence in sentences:
            cleaned = clean_sentence_text(sentence)

            if not is_good_sentence(cleaned):
                continue

            score = sentence_keyword_score(cleaned, query)
            if score <= 0:
                continue

            candidates.append({
                "sentence": cleaned,
                "keyword_score": score,
                "retrieval_score": float(row["score"]),
            })

    if not candidates:
        return "Fallback answer was triggered, but no concise answer could be extracted from the retrieved chunks.\n\n" + format_sources(results_df)

    candidates_df = pd.DataFrame(candidates).sort_values(
        by=["keyword_score", "retrieval_score"],
        ascending=[False, False],
    )

    selected = []
    seen = set()

    for _, row in candidates_df.iterrows():
        sentence = row["sentence"].strip()
        key = sentence.lower()

        if key in seen:
            continue

        seen.add(key)
        selected.append(f"- {sentence}")

        if len(selected) >= MAX_FALLBACK_SENTENCES:
            break

    if not selected:
        return "Fallback answer was triggered, but no concise answer could be extracted from the retrieved chunks.\n\n" + format_sources(results_df)

    return "LLM fallback mode was used.\n\n" + "\n".join(selected) + "\n\n" + format_sources(results_df)


def call_llm(
    query: str,
    context: str,
    *,
    run_id: str | None = None,
    retrieved_documents: list[str] | None = None,
) -> str:
    if not llm_api_key_present():
        raise ValueError("DEEPSEEK_API_KEY is not set.")
    return run_chain(
        query,
        context,
        run_id=run_id,
        retrieved_documents=retrieved_documents or [],
    )


def post_process_answer(answer: str) -> str:
    text = str(answer or "").strip()
    if not text:
        return ""

    text = re.sub(r"\s*\[Excerpt\s+\d+(?:\s*,\s*Excerpt\s+\d+)*\]", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?is)^based solely on the provided excerpts[^:\n]*:\s*",
        "",
        text,
    ).strip()
    text = re.sub(
        r"(?is)^based solely on the provided excerpts[^.\n]*\.\s*",
        "",
        text,
    ).strip()
    text = re.sub(r"(?m)^\s*\d+\.\s*", "- ", text)

    if "\n" in text or re.search(r"(^|\s)(\d+\.)", text) or re.search(r"(^|\n)\s*[-*]\s+", text):
        cleaned_lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in text.splitlines()
            if re.sub(r"\s+", " ", line).strip()
        ]
        bullet_lines = [
            line
            for line in cleaned_lines
            if re.match(r"^[-*]\s+", line)
        ]
        if bullet_lines:
            text = "\n".join(bullet_lines[:5]).strip()
        else:
            text = "\n".join(cleaned_lines[:5]).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
        sentences = split_sentences(text)
        if sentences:
            text = " ".join(sentences[:MAX_ANSWER_SENTENCES]).strip()

    return text


def _build_result(
    query: str,
    run_id: str | None,
    company_filter: str | None,
    form_filter: str | None,
    mode: str,
    answer: str,
    cache_hit: bool,
    cache_mode: str | None,
    sources_text: str,
    retrieval_error: str | None,
    llm_error: str | None,
    llm_model: str = LLM_MODEL,
) -> dict:
    return {
        "query": query,
        "run_id": run_id,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "mode": mode,
        "answer": post_process_answer(answer),
        "cache_hit": cache_hit,
        "cache_mode": cache_mode,
        "llm_model": llm_model,
        "sources_text": sources_text,
        "retrieval_error": retrieval_error,
        "llm_error": llm_error,
    }


class GraphState(TypedDict, total=False):
    query: str
    run_id: str
    company_filter: str | None
    form_filter: str | None
    event_callback: PipelineEventCallback | None
    observation_only: bool
    query_type: str
    semantic_scope: str
    retrieval_backend: str
    index_version: str
    retrieval_cache_key: str
    retrieval_cache_hit: bool
    cache_key: str
    cache_data: dict
    cached_entry: dict | None
    semantic_cached_entry: dict | None
    results_rows: list[dict[str, Any]] | None
    context: str
    query_allowed: bool
    sources_text: str
    answer: str
    mode: str
    cache_hit: bool
    cache_mode: str | None
    retrieval_error: str | None
    llm_error: str | None
    llm_model: str


def dataframe_to_records(results_df: pd.DataFrame) -> list[dict[str, Any]]:
    if results_df.empty:
        return []
    return json.loads(results_df.to_json(orient="records", date_format="iso"))


def records_to_dataframe(records: list[dict[str, Any]] | None) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def node_prepare(state: GraphState) -> GraphState:
    emit_pipeline_event(state, "query_received")
    query = str(state["query"]).strip()
    run_id = str(state.get("run_id") or "").strip() or uuid4().hex
    company_filter = state.get("company_filter") or infer_company_filter(query)
    form_filter = state.get("form_filter") or infer_form_filter(query)
    query_type = classify_query(query)
    semantic_scope = build_semantic_scope(query, query_type)
    retrieval_backend = retrieval_resources.get_runtime_vector_backend()
    index_version = build_effective_index_version(retrieval_resources.get_vector_index_version())
    retrieval_cache_key = build_retrieval_cache_key(
        query,
        company_filter,
        form_filter,
        backend=retrieval_backend,
        index_version=index_version,
        embedding_model=MODEL_NAME,
        reranker_version=RERANKER_MODEL_NAME,
        vector_k=VECTOR_SEARCH_K,
        bm25_k=RETRIEVAL_CANDIDATES,
        top_k=TOP_K,
    )
    cache_key = build_cache_key(query, company_filter, form_filter)

    logger.info(f"query_type={query_type}")
    logger.info(f"semantic_scope={semantic_scope}")
    log_structured(
        logger,
        "request_received",
        run_id=run_id,
        query=query,
        company_filter=company_filter,
        form_filter=form_filter,
        query_type=query_type,
        retrieval_backend=retrieval_backend,
        index_version=index_version,
    )

    return {
        "query": query,
        "run_id": run_id,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "query_type": query_type,
        "semantic_scope": semantic_scope,
        "retrieval_backend": retrieval_backend,
        "index_version": index_version,
        "retrieval_cache_key": retrieval_cache_key,
        "retrieval_cache_hit": False,
        "cache_key": cache_key,
        "llm_model": LLM_MODEL,
        "cache_hit": False,
        "cache_mode": None,
        "retrieval_error": None,
        "llm_error": None,
        "semantic_cached_entry": None,
        "sources_text": "",
        "answer": "",
    }


def node_cache_lookup(state: GraphState) -> GraphState:
    if state.get("observation_only"):
        logger.info("cache_hit=False cache_bypass=observation")
        return {"cached_entry": None}

    if filters_are_active(state.get("company_filter"), state.get("form_filter")):
        logger.info("cache_hit=False cache_bypass=filters")
        return {"cached_entry": None}

    cached_entry = get_valid_cached_entry({}, state["cache_key"])

    if cached_entry:
        logger.info(f"cache_hit=True cache_mode={cached_entry.get('mode')}")
        increment_cache_stat("answer_cache", "hit")
    else:
        logger.info("cache_hit=False")
        increment_cache_stat("answer_cache", "miss")

    return {"cached_entry": cached_entry}


def route_after_cache(state: GraphState) -> str:
    return "cache_return" if state.get("cached_entry") else "semantic_lookup"


def node_cache_return(state: GraphState) -> GraphState:
    cached_entry = state["cached_entry"]
    emit_pipeline_event(state, "answer_generated")

    return {
        "mode": "cache",
        "answer": str(cached_entry.get("answer", "")),
        "cache_hit": True,
        "cache_mode": str(cached_entry.get("mode", "")).strip().lower() or None,
        "llm_model": str(cached_entry.get("llm_model") or LLM_MODEL),
        "sources_text": str(cached_entry.get("sources_text") or ""),
        "retrieval_error": str(cached_entry.get("retrieval_error")) if cached_entry.get("retrieval_error") else None,
        "llm_error": str(cached_entry.get("llm_error")) if cached_entry.get("llm_error") else None,
    }


def node_semantic_cache_lookup(state: GraphState) -> GraphState:
    if state.get("observation_only"):
        logger.info("semantic_cache_hit=False cache_bypass=observation")
        return {
            "semantic_cached_entry": None,
        }

    semantic_entry = lookup_semantic_cache(
        state["query"],
        company_filter=state.get("company_filter"),
        form_filter=state.get("form_filter"),
        query_type=state.get("semantic_scope", state.get("query_type", "general")),
        index_version=state["index_version"],
        embedding_model_name=MODEL_NAME,
    )

    if semantic_entry:
        logger.info("semantic_cache_hit=True")
    else:
        logger.info("semantic_cache_hit=False")

    return {
        "semantic_cached_entry": semantic_entry,
    }


def route_after_semantic_cache(state: GraphState) -> str:
    return "semantic_return" if state.get("semantic_cached_entry") else "retrieve"


def node_semantic_cache_return(state: GraphState) -> GraphState:
    semantic_entry = state["semantic_cached_entry"]
    emit_pipeline_event(state, "answer_generated")

    return {
        "mode": "cache",
        "answer": str(semantic_entry.get("answer", "")),
        "cache_hit": True,
        "cache_mode": "semantic",
        "llm_model": str(semantic_entry.get("llm_model") or LLM_MODEL),
        "sources_text": str(semantic_entry.get("sources_text") or ""),
        "retrieval_error": None,
        "llm_error": None,
    }


def node_parallel_retrieve(state: GraphState) -> GraphState:
    try:
        query = state["query"]
        retrieval_cache_key = state["retrieval_cache_key"]
        observation_only = bool(state.get("observation_only", False))

        cached_retrieval = None if observation_only else read_retrieval_cache(retrieval_cache_key)
        if cached_retrieval and cached_retrieval.get("rows"):
            logger.info("retrieval_cache_hit=True")
            cached_df = records_to_dataframe(cached_retrieval["rows"])
            cached_doc_ids, cached_rerank_scores, cached_final_scores = summarize_retrieval_trace(cached_df)
            log_structured(
                logger,
                "retrieval_result",
                run_id=state.get("run_id"),
                query=query,
                top_k=len(cached_df),
                retrieved_document_ids=cached_doc_ids,
                rerank_scores=cached_rerank_scores,
                final_scores=cached_final_scores,
                cache_hit=True,
            )
            return {
                "results_rows": cached_retrieval["rows"],
                "retrieval_error": None,
                "retrieval_cache_hit": True,
            }

        if observation_only:
            logger.info("retrieval_cache_hit=False cache_bypass=observation")
        else:
            logger.info("retrieval_cache_hit=False")
        start_retrieval = time.time()
        emit_pipeline_event(state, "embedding_created")
        emit_pipeline_event(state, "hybrid_retrieval_started")

        vector_df = search_rows(
            query,
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
        )

        from app.retrieval.bm25_retriever import bm25_search
        metadata_df = retrieval_resources.get_metadata_df()

        bm25_df = bm25_search(
            query,
            metadata_df,
            state.get("company_filter"),
            state.get("form_filter"),
            top_k=RETRIEVAL_CANDIDATES,
        )

        vector_candidates = prepare_retrieval_source(vector_df, "vector")
        bm25_candidates = prepare_retrieval_source(bm25_df, "bm25")
        merged = merge_retrieval_candidates(vector_candidates, bm25_candidates)
        logger.info(f"parallel_retrieval_rows={len(merged)}")
        candidate_doc_ids, candidate_rerank_scores, candidate_final_scores = summarize_retrieval_trace(merged)
        log_structured(
            logger,
            "retrieval_candidates",
            run_id=state.get("run_id"),
            query=query,
            top_k=len(merged),
            retrieved_document_ids=candidate_doc_ids,
            rerank_scores=candidate_rerank_scores,
            final_scores=candidate_final_scores,
        )

        start_rerank = time.time()
        emit_pipeline_event(state, "reranking_started")
        reranked_df = rerank(
            query,
            merged,
            top_k=None,
        )
        ranked_df = apply_blended_ranking(
            reranked_df,
            query=query,
            query_type=state.get("query_type", "general"),
            form_filter=state.get("form_filter"),
        )
        rerank_ms = int((time.time() - start_rerank) * 1000)
        logger.info(f"rerank_ms={rerank_ms}")
        logger.info(f"reranked_rows={len(ranked_df)}")
        ranked_doc_ids, ranked_rerank_scores, ranked_final_scores = summarize_retrieval_trace(ranked_df)
        log_structured(
            logger,
            "rerank_result",
            run_id=state.get("run_id"),
            query=query,
            top_k=len(ranked_df),
            retrieved_document_ids=ranked_doc_ids,
            rerank_scores=ranked_rerank_scores,
            final_scores=ranked_final_scores,
            latency_ms=rerank_ms,
            model=RERANKER_MODEL_NAME,
        )

        results_df = finalize_results_df(
            ranked_df,
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
        )
        retrieval_ms = int((time.time() - start_retrieval) * 1000)
        logger.info(f"retrieval_ms={retrieval_ms}")
        final_doc_ids, final_rerank_scores, final_final_scores = summarize_retrieval_trace(results_df)
        log_structured(
            logger,
            "retrieval_result",
            run_id=state.get("run_id"),
            query=query,
            top_k=len(results_df),
            retrieved_document_ids=final_doc_ids,
            rerank_scores=final_rerank_scores,
            final_scores=final_final_scores,
            latency_ms=retrieval_ms,
        )

        results_rows = dataframe_to_records(results_df)
        if observation_only:
            cache_written = False
        else:
            cache_written = write_retrieval_cache(
                retrieval_cache_key,
                query=query,
                company_filter=state.get("company_filter"),
                form_filter=state.get("form_filter"),
                backend=state["retrieval_backend"],
                index_version=state["index_version"],
                rows=results_rows,
            )
        logger.info(f"retrieval_cache_write={cache_written}")

        return {
            "results_rows": results_rows,
            "retrieval_error": None,
            "retrieval_cache_hit": False,
        }
    except Exception as exc:
        logger.info(f"retrieval_error={exc}")
        return {
            "results_rows": None,
            "retrieval_error": str(exc),
            "retrieval_cache_hit": False,
            "mode": "fallback",
            "answer": "",
            "sources_text": "",
        }


def node_retrieve(state: GraphState) -> GraphState:
    try:
        start_retrieval = time.time()
        results_df = search_rows(
            state["query"],
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
        )
        retrieval_ms = int((time.time() - start_retrieval) * 1000)
        logger.info(f"retrieval_ms={retrieval_ms}")
        logger.info(f"retrieved_rows={len(results_df)}")

        if results_df.empty:
            raise ValueError("No rows returned from retrieval.")

        results_df = prepare_retrieval_source(results_df, "vector")
        results_df = merge_retrieval_candidates(results_df)

        start_rerank = time.time()
        results_df = rerank(state["query"], results_df, top_k=None)
        results_df = apply_blended_ranking(
            results_df,
            query=state["query"],
            query_type=state.get("query_type", "general"),
            form_filter=state.get("form_filter"),
        )
        rerank_ms = int((time.time() - start_rerank) * 1000)
        logger.info(f"rerank_ms={rerank_ms}")
        logger.info(f"reranked_rows={len(results_df)}")
        ranked_doc_ids, ranked_rerank_scores, ranked_final_scores = summarize_retrieval_trace(results_df)
        log_structured(
            logger,
            "rerank_result",
            run_id=state.get("run_id"),
            query=state.get("query"),
            top_k=len(results_df),
            retrieved_document_ids=ranked_doc_ids,
            rerank_scores=ranked_rerank_scores,
            final_scores=ranked_final_scores,
            latency_ms=rerank_ms,
            model=RERANKER_MODEL_NAME,
        )

        if results_df.empty:
            raise ValueError("No rows returned after rerank.")

        results_df = finalize_results_df(
            results_df,
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
        )
        final_doc_ids, final_rerank_scores, final_final_scores = summarize_retrieval_trace(results_df)
        log_structured(
            logger,
            "retrieval_result",
            run_id=state.get("run_id"),
            query=state.get("query"),
            top_k=len(results_df),
            retrieved_document_ids=final_doc_ids,
            rerank_scores=final_rerank_scores,
            final_scores=final_final_scores,
            latency_ms=retrieval_ms,
        )

        return {
            "results_rows": dataframe_to_records(results_df),
            "retrieval_error": None,
        }
    except Exception as exc:
        logger.info(f"retrieval_error={exc}")
        return {
            "results_rows": None,
            "retrieval_error": str(exc),
            "mode": "fallback",
            "answer": "",
            "sources_text": "",
        }


def route_after_retrieve(state: GraphState) -> str:
    return "retrieval_failed" if state.get("retrieval_error") else "build_context"


def node_retrieval_failed(state: GraphState) -> GraphState:
    return {}


def node_build_context(state: GraphState) -> GraphState:
    emit_pipeline_event(state, "context_build_started")
    results_df = records_to_dataframe(state.get("results_rows"))
    results_df = select_diverse_context_rows(results_df, max_chunks=TOP_K)
    context = build_context(results_df)
    logger.info(f"context_length={len(context)}")
    context_doc_ids, _, context_final_scores = summarize_retrieval_trace(results_df)
    log_structured(
        logger,
        "context_built",
        run_id=state.get("run_id"),
        query=state.get("query"),
        top_k=len(results_df),
        retrieved_document_ids=context_doc_ids,
        final_scores=context_final_scores,
        context_length=len(context),
    )
    return {
        "results_rows": dataframe_to_records(results_df),
        "context": context,
        "sources_text": format_sources(results_df),
    }


def node_query_guard(state: GraphState) -> GraphState:
    query_allowed = is_query_allowed(state.get("query", ""))
    if query_allowed:
        return {
            "query_allowed": True,
        }

    logger.info("QUERY_BLOCKED_BY_GUARD")
    emit_pipeline_event(state, "answer_generated")
    return {
        "query_allowed": False,
        "answer": "This system answers questions only about SEC filings and company disclosures.",
        "mode": "fallback",
        "sources_text": "Sources:\n- query_guard",
        "llm_error": None,
        "retrieval_error": None,
    }


def route_after_query_guard(state: GraphState) -> str:
    return "llm" if state.get("query_allowed", False) else "save_semantic_cache"


def node_llm(state: GraphState) -> GraphState:
    try:
        emit_pipeline_event(state, "llm_generation_started")
        logger.info("calling_llm")
        start_llm = time.time()
        retrieved_documents = [
            build_document_id(row)
            for row in (state.get("results_rows") or [])[:TOP_K]
        ]
        answer = post_process_answer(
            call_llm(
                state["query"],
                state["context"],
                run_id=state.get("run_id"),
                retrieved_documents=retrieved_documents,
            )
        )
        llm_ms = int((time.time() - start_llm) * 1000)
        logger.info(f"llm_ms={llm_ms}")
        log_structured(
            logger,
            "response_generated",
            run_id=state.get("run_id"),
            query=state.get("query"),
            model=state.get("llm_model", LLM_MODEL),
            response_length=len(str(answer or "")),
            latency_ms=llm_ms,
        )
        emit_pipeline_event(state, "answer_generated")

        return {
            "answer": answer,
            "mode": "llm",
            "llm_error": None,
        }
    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "llm_error",
                    "run_id": state.get("run_id"),
                    "query": state.get("query"),
                    "model": state.get("llm_model", LLM_MODEL),
                    "error": str(exc),
                },
                ensure_ascii=False,
            )
        )
        results_df = records_to_dataframe(state.get("results_rows"))
        return {
            "answer": build_fallback_answer(state["query"], results_df),
            "mode": "fallback",
            "llm_error": str(exc),
        }


def node_save_semantic_cache(state: GraphState) -> GraphState:
    if state.get("observation_only"):
        return state

    if state.get("cache_hit") or state.get("retrieval_error") or state.get("llm_error"):
        return state

    if state.get("mode") != "llm":
        return state

    semantic_saved = save_semantic_cache(
        state["query"],
        answer=state.get("answer", ""),
        sources_text=state.get("sources_text", ""),
        company_filter=state.get("company_filter"),
        form_filter=state.get("form_filter"),
        query_type=state.get("semantic_scope", state.get("query_type", "general")),
        llm_model=state.get("llm_model", LLM_MODEL),
        index_version=state["index_version"],
        results_rows=state.get("results_rows"),
        embedding_model_name=MODEL_NAME,
    )
    logger.info(f"semantic_cache_write={semantic_saved}")
    return state


def node_save_cache(state: GraphState) -> GraphState:
    if state.get("observation_only"):
        return state

    if state.get("cache_hit") or state.get("retrieval_error"):
        return state

    if filters_are_active(state.get("company_filter"), state.get("form_filter")):
        logger.info("cache_save_skipped=True cache_bypass=filters")
        return state

    cache_entry = {
        "query": state["query"],
        "company_filter": state.get("company_filter"),
        "form_filter": state.get("form_filter"),
        "mode": state.get("mode"),
        "llm_model": state.get("llm_model", LLM_MODEL),
        "answer": state.get("answer", ""),
        "sources_text": state.get("sources_text", ""),
        "retrieval_error": state.get("retrieval_error"),
        "llm_error": state.get("llm_error"),
        "created_at": time.time(),
    }
    write_cached_answer(state["cache_key"], cache_entry)
    increment_cache_stat("answer_cache", "write")
    return state


_graph = None


def get_answer_graph():
    global _graph
    if _graph is not None:
        return _graph

    workflow = StateGraph(GraphState)

    workflow.add_node("prepare", node_prepare)
    workflow.add_node("cache_lookup", node_cache_lookup)
    workflow.add_node("cache_return", node_cache_return)
    workflow.add_node("semantic_lookup", node_semantic_cache_lookup)
    workflow.add_node("semantic_return", node_semantic_cache_return)
    workflow.add_node("retrieve", node_parallel_retrieve)
    workflow.add_node("retrieval_failed", node_retrieval_failed)
    workflow.add_node("build_context", node_build_context)
    workflow.add_node("query_guard", node_query_guard)
    workflow.add_node("llm", node_llm)
    workflow.add_node("save_semantic_cache", node_save_semantic_cache)
    workflow.add_node("save_cache", node_save_cache)

    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "cache_lookup")
    workflow.add_conditional_edges(
        "cache_lookup",
        route_after_cache,
        {
            "cache_return": "cache_return",
            "semantic_lookup": "semantic_lookup",
        },
    )
    workflow.add_edge("cache_return", END)
    workflow.add_conditional_edges(
        "semantic_lookup",
        route_after_semantic_cache,
        {
            "semantic_return": "semantic_return",
            "retrieve": "retrieve",
        },
    )
    workflow.add_edge("semantic_return", END)
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "retrieval_failed": "retrieval_failed",
            "build_context": "build_context",
        },
    )
    workflow.add_edge("retrieval_failed", END)
    workflow.add_edge("build_context", "query_guard")
    workflow.add_conditional_edges(
        "query_guard",
        route_after_query_guard,
        {
            "llm": "llm",
            "save_semantic_cache": "save_semantic_cache",
        },
    )
    workflow.add_edge("llm", "save_semantic_cache")
    workflow.add_edge("save_semantic_cache", "save_cache")
    workflow.add_edge("save_cache", END)

    _graph = workflow.compile()
    return _graph


def _answer_single_query(
    query: str,
    company_filter: str | None = None,
    form_filter: str | None = None,
    event_callback: PipelineEventCallback | None = None,
    observation_only: bool = False,
    run_id: str | None = None,
) -> dict:
    graph = get_answer_graph()

    final_state = graph.invoke({
        "query": query,
        "run_id": run_id,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "event_callback": event_callback,
        "observation_only": observation_only,
    })

    if final_state.get("retrieval_error") or final_state.get("llm_error"):
        if callable(event_callback):
            try:
                event_callback("error")
            except Exception as exc:
                logger.info(f"stream_event_emit_failed={exc}")

    return _build_result(
        query=final_state["query"],
        run_id=final_state.get("run_id"),
        company_filter=final_state.get("company_filter"),
        form_filter=final_state.get("form_filter"),
        mode=final_state.get("mode", "fallback"),
        answer=final_state.get("answer", ""),
        cache_hit=bool(final_state.get("cache_hit", False)),
        cache_mode=final_state.get("cache_mode"),
        llm_model=final_state.get("llm_model", LLM_MODEL),
        sources_text=final_state.get("sources_text", ""),
        retrieval_error=final_state.get("retrieval_error"),
        llm_error=final_state.get("llm_error"),
    )


def combine_multi_company_answers(
    original_query: str,
    company_results: list[dict[str, Any]],
    form_filter: str | None,
) -> dict:
    answer_blocks = []
    source_lines = ["Sources:"]
    seen_source_lines: set[str] = set()
    mode = "cache"
    cache_hit = True
    llm_model = LLM_MODEL
    retrieval_errors: list[str] = []
    llm_errors: list[str] = []

    for result in company_results:
        company_name = str(result.get("company_filter") or "").strip() or "Unknown company"
        display_name = get_company_display_name(company_name)
        answer_text = str(result.get("answer") or "").strip() or "The provided filings do not contain this information."

        answer_blocks.append(
            f"Company: {display_name}\nAnswer: {answer_text}"
        )

        llm_model = str(result.get("llm_model") or llm_model)
        cache_hit = cache_hit and bool(result.get("cache_hit", False))

        result_mode = str(result.get("mode") or "").strip().lower()
        if result_mode == "fallback":
            mode = "fallback"
        elif result_mode == "llm" and mode != "fallback":
            mode = "llm"

        retrieval_error = result.get("retrieval_error")
        if retrieval_error:
            retrieval_errors.append(f"{display_name}: {retrieval_error}")

        llm_error = result.get("llm_error")
        if llm_error:
            llm_errors.append(f"{display_name}: {llm_error}")

        sources_text = str(result.get("sources_text") or "").splitlines()
        for line in sources_text:
            stripped = line.strip()
            if not stripped or stripped == "Sources:":
                continue
            labeled_line = f"- {display_name} :: {stripped.lstrip('-').strip()}"
            if labeled_line in seen_source_lines:
                continue
            seen_source_lines.add(labeled_line)
            source_lines.append(labeled_line)

    if len(source_lines) == 1:
        source_lines.append("- No sources available.")

    aggregated = _build_result(
        query=original_query,
        run_id=company_results[0].get("run_id") if company_results else None,
        company_filter=None,
        form_filter=form_filter,
        mode=mode,
        answer="\n\n".join(answer_blocks),
        cache_hit=cache_hit,
        cache_mode="multi" if cache_hit else None,
        llm_model=llm_model,
        sources_text="\n".join(source_lines),
        retrieval_error=" | ".join(retrieval_errors) if retrieval_errors else None,
        llm_error=" | ".join(llm_errors) if llm_errors else None,
    )
    aggregated["answer"] = "\n\n".join(answer_blocks)
    return aggregated


def answer_query(
    query: str,
    company_filter: str | None = None,
    form_filter: str | None = None,
    event_callback: PipelineEventCallback | None = None,
    observation_only: bool = False,
    run_id: str | None = None,
) -> dict:
    effective_form_filter = form_filter or detect_sec_form(query)

    if company_filter is None:
        detected_companies = detect_companies(query)
        if len(detected_companies) > 1:
            logger.info(f"multi_company_query companies={detected_companies}")
            subqueries = build_multi_company_subqueries(
                query,
                detected_companies,
                form_filter=effective_form_filter,
            )
            company_results = []

            for item in subqueries:
                company_name = item["company"]
                subquery = item["subquery"]
                logger.info(f"multi_company_subquery company={company_name} subquery={subquery}")
                company_results.append(
                    _answer_single_query(
                        query=subquery,
                        company_filter=company_name,
                        form_filter=effective_form_filter,
                        event_callback=event_callback,
                        observation_only=observation_only,
                        run_id=run_id,
                    )
                )

            return combine_multi_company_answers(
                original_query=query,
                company_results=company_results,
                form_filter=effective_form_filter,
            )

    return _answer_single_query(
        query=query,
        company_filter=company_filter,
        form_filter=effective_form_filter,
        event_callback=event_callback,
        observation_only=observation_only,
        run_id=run_id,
    )


__all__ = [
    "LLM_MODEL",
    "answer_query",
    "llm_api_key_present",
    "get_answer_graph",
]













