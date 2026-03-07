def limit_context_rows(results_df, max_chunks=10):
    if results_df is None:
        return results_df
    return results_df.head(max_chunks)
import os
import re
import json
import time
import hashlib
from typing import Any, TypedDict

import numpy as np
import pandas as pd
import faiss
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langgraph.graph import StateGraph, END

from app.core.logger import get_logger
from app.retrieval.reranker import rerank
from app.llm.langchain_chain import run_chain
from app.router.query_router import classify_query

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
INDEX_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks.index")
METADATA_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks_metadata.parquet")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "answer_cache.json")

load_dotenv(dotenv_path=ENV_FILE, override=False)
# --- GLOBAL DATA LOAD (performance) ---
_metadata_df = None
_faiss_index = None

def get_metadata_df():
    global _metadata_df
    if _metadata_df is None:
        _metadata_df = pd.read_parquet(METADATA_FILE)
    return _metadata_df

def get_faiss_index():
    global _faiss_index
    if _faiss_index is None:
        _faiss_index = faiss.read_index(INDEX_FILE)
    return _faiss_index

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 10
RETRIEVAL_CANDIDATES = 20
MAX_FALLBACK_SENTENCES = 5

LLM_CACHE_TTL_SECONDS = 60 * 60 * 24
FALLBACK_CACHE_TTL_SECONDS = 60 * 10

RISK_HINT_WORDS = {
    "risk", "risks", "risky", "adverse", "adversely", "uncertain", "uncertainty",
    "legal", "litigation", "regulation", "regulatory", "economic", "economy",
    "supplier", "suppliers", "supply", "geopolitical", "trade", "conflict",
    "terrorism", "disaster", "public", "health", "privacy", "security",
    "competition", "market", "volatile", "volatility", "credit", "liquidity"
}


def normalize_env_value(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


LLM_API_URL = normalize_env_value(os.getenv("LLM_API_URL")) or "https://api.deepseek.com/chat/completions"
LLM_MODEL = normalize_env_value(os.getenv("LLM_MODEL")) or "deepseek-chat"


def llm_api_key_present() -> bool:
    return bool(normalize_env_value(os.getenv("DEEPSEEK_API_KEY")))


def infer_company_filter(query: str) -> str | None:
    q = query.lower()

    if "apple" in q:
        return "Apple Inc."
    if "nvidia" in q:
        return "NVIDIA CORP"
    if "alphabet" in q or "google" in q:
        return "Alphabet Inc."

    return None


def infer_form_filter(query: str) -> str | None:
    q = query.lower()

    if "annual report" in q or "10-k" in q:
        return "10-K"

    if "quarterly report" in q or "10-q" in q or "quarter report" in q:
        return "10-Q"

    if "proxy" in q or "proxy statement" in q:
        return "DEF 14A"

    if "current report" in q or "8-k" in q:
        return "8-K"

    if "ownership" in q or "beneficial ownership" in q or "13g" in q:
        return "SC 13G/A"

    return None


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


def filters_are_active(company_filter: str | None, form_filter: str | None) -> bool:
    return bool(str(company_filter or "").strip() or str(form_filter or "").strip())


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

    filtered_df = filtered_df.drop_duplicates(subset=["chunk_text"])
    filtered_df = limit_context_rows(filtered_df, max_chunks=10)
    logger.info(f"final_context_rows={len(filtered_df)}")
    return filtered_df


def normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def build_cache_key(query: str, company_filter: str | None, form_filter: str | None) -> str:
    payload = {
        "query": normalize_query(query),
        "company_filter": (company_filter or "").strip().lower(),
        "form_filter": (form_filter or "").strip().lower(),
        "llm_model": LLM_MODEL.strip().lower(),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(cache_data: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)


def get_cache_ttl_for_mode(mode: str) -> int:
    if str(mode).strip().lower() == "llm":
        return LLM_CACHE_TTL_SECONDS
    return FALLBACK_CACHE_TTL_SECONDS


def cleanup_expired_cache(cache_data: dict) -> dict:
    cleaned = {}

    for key, entry in cache_data.items():
        if not isinstance(entry, dict):
            continue

        mode = str(entry.get("mode", "")).strip().lower()
        created_at = entry.get("created_at")

        if not isinstance(created_at, (int, float)):
            continue

        ttl = get_cache_ttl_for_mode(mode)
        age = time.time() - float(created_at)

        if age <= ttl:
            cleaned[key] = entry

    return cleaned


def get_valid_cached_entry(cache_data: dict, cache_key: str) -> dict | None:
    entry = cache_data.get(cache_key)

    if not isinstance(entry, dict):
        return None

    mode = str(entry.get("mode", "")).strip().lower()
    created_at = entry.get("created_at")

    if not isinstance(created_at, (int, float)):
        return None

    if mode == "fallback" and llm_api_key_present():
        return None

    ttl = get_cache_ttl_for_mode(mode)
    age = time.time() - float(created_at)

    if age > ttl:
        return None

    return entry


_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(MODEL_NAME)
    return _embedding_model


def search_rows(query: str, company_filter: str | None = None, form_filter: str | None = None) -> pd.DataFrame:
    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError("FAISS index does not exist.")

    if not os.path.exists(METADATA_FILE):
        raise FileNotFoundError("Metadata parquet does not exist.")

    metadata_df = pd.read_parquet(METADATA_FILE)
    index = faiss.read_index(INDEX_FILE)

    model = get_embedding_model()

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    search_k = 50
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
    blocks = []

    for i, (_, row) in enumerate(results_df.iterrows(), start=1):
        block = [
            f"[SOURCE {i}]",
            f"Company: {row['company']}",
            f"Form: {row['form']}",
            f"Filing date: {row['filing_date']}",
            f"URL: {row['filing_url']}",
            f"Score: {row['score']:.4f}",
            "Text:",
            str(row["chunk_text"]),
        ]
        blocks.append("\n".join(block))

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


def call_llm(query: str, context: str) -> str:
    if not llm_api_key_present():
        raise ValueError("DEEPSEEK_API_KEY is not set.")
    return run_chain(query, context)


def _build_result(
    query: str,
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
        "company_filter": company_filter,
        "form_filter": form_filter,
        "mode": mode,
        "answer": answer,
        "cache_hit": cache_hit,
        "cache_mode": cache_mode,
        "llm_model": llm_model,
        "sources_text": sources_text,
        "retrieval_error": retrieval_error,
        "llm_error": llm_error,
    }


class GraphState(TypedDict, total=False):
    query: str
    company_filter: str | None
    form_filter: str | None
    query_type: str
    cache_key: str
    cache_data: dict
    cached_entry: dict | None
    results_rows: list[dict[str, Any]] | None
    context: str
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
    query = str(state["query"]).strip()
    company_filter = state.get("company_filter") or infer_company_filter(query)
    form_filter = state.get("form_filter") or infer_form_filter(query)
    query_type = classify_query(query)
    cache_data = cleanup_expired_cache(load_cache())
    cache_key = build_cache_key(query, company_filter, form_filter)

    logger.info(f"query_type={query_type}")

    return {
        "query": query,
        "company_filter": company_filter,
        "form_filter": form_filter,
        "query_type": query_type,
        "cache_data": cache_data,
        "cache_key": cache_key,
        "llm_model": LLM_MODEL,
        "cache_hit": False,
        "cache_mode": None,
        "retrieval_error": None,
        "llm_error": None,
        "sources_text": "",
        "answer": "",
    }


def node_cache_lookup(state: GraphState) -> GraphState:
    if filters_are_active(state.get("company_filter"), state.get("form_filter")):
        logger.info("cache_hit=False cache_bypass=filters")
        return {"cached_entry": None}

    cached_entry = get_valid_cached_entry(state["cache_data"], state["cache_key"])

    if cached_entry:
        logger.info(f"cache_hit=True cache_mode={cached_entry.get('mode')}")
    else:
        logger.info("cache_hit=False")

    return {"cached_entry": cached_entry}


def route_after_cache(state: GraphState) -> str:
    return "cache_return" if state.get("cached_entry") else "retrieve"


def node_cache_return(state: GraphState) -> GraphState:
    cached_entry = state["cached_entry"]

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


def node_parallel_retrieve(state: GraphState) -> GraphState:
    try:
        query = state["query"]

        vector_df = search_rows(
            query,
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
        )

        from app.retrieval.bm25_retriever import bm25_search
        metadata_df = pd.read_parquet(METADATA_FILE)

        bm25_df = bm25_search(
            query,
            metadata_df,
            state.get("company_filter"),
            state.get("form_filter"),
        )

        merged = pd.concat([vector_df, bm25_df], ignore_index=True)
        logger.info(f"parallel_retrieval_rows={len(merged)}")

        results_df = finalize_results_df(
            merged,
            company_filter=state.get("company_filter"),
            form_filter=state.get("form_filter"),
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

        start_rerank = time.time()
        results_df = rerank(state["query"], results_df, top_k=TOP_K)
        rerank_ms = int((time.time() - start_rerank) * 1000)
        logger.info(f"rerank_ms={rerank_ms}")
        logger.info(f"reranked_rows={len(results_df)}")

        if results_df.empty:
            raise ValueError("No rows returned after rerank.")

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
    results_df = records_to_dataframe(state.get("results_rows"))
    context = build_context(results_df)
    logger.info(f"context_length={len(context)}")
    return {
        "results_rows": dataframe_to_records(results_df),
        "context": context,
        "sources_text": format_sources(results_df),
    }


def node_llm(state: GraphState) -> GraphState:
    try:
        logger.info("calling_llm")
        start_llm = time.time()
        answer = call_llm(state["query"], state["context"])
        llm_ms = int((time.time() - start_llm) * 1000)
        logger.info(f"llm_ms={llm_ms}")

        return {
            "answer": answer,
            "mode": "llm",
            "llm_error": None,
        }
    except Exception as exc:
        logger.info(f"llm_error={exc}")
        results_df = records_to_dataframe(state.get("results_rows"))
        return {
            "answer": build_fallback_answer(state["query"], results_df),
            "mode": "fallback",
            "llm_error": str(exc),
        }


def node_save_cache(state: GraphState) -> GraphState:
    if state.get("cache_hit") or state.get("retrieval_error"):
        return state

    if filters_are_active(state.get("company_filter"), state.get("form_filter")):
        logger.info("cache_save_skipped=True cache_bypass=filters")
        return state

    cache_data = state["cache_data"]
    cache_data[state["cache_key"]] = {
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
    save_cache(cache_data)
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
    workflow.add_node("retrieve", node_parallel_retrieve)
    workflow.add_node("retrieval_failed", node_retrieval_failed)
    workflow.add_node("build_context", node_build_context)
    workflow.add_node("llm", node_llm)
    workflow.add_node("save_cache", node_save_cache)

    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "cache_lookup")
    workflow.add_conditional_edges(
        "cache_lookup",
        route_after_cache,
        {
            "cache_return": "cache_return",
            "retrieve": "retrieve",
        },
    )
    workflow.add_edge("cache_return", END)
    workflow.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "retrieval_failed": "retrieval_failed",
            "build_context": "build_context",
        },
    )
    workflow.add_edge("retrieval_failed", END)
    workflow.add_edge("build_context", "llm")
    workflow.add_edge("llm", "save_cache")
    workflow.add_edge("save_cache", END)

    _graph = workflow.compile()
    return _graph


def answer_query(
    query: str,
    company_filter: str | None = None,
    form_filter: str | None = None,
) -> dict:
    graph = get_answer_graph()

    final_state = graph.invoke({
        "query": query,
        "company_filter": company_filter,
        "form_filter": form_filter,
    })

    if final_state.get("cache_hit"):
        save_cache(final_state["cache_data"])

    return _build_result(
        query=final_state["query"],
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


__all__ = [
    "LLM_MODEL",
    "answer_query",
    "llm_api_key_present",
    "get_answer_graph",
]












