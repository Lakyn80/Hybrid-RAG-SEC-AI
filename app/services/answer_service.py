import os
import re
import json
import time
import hashlib
import numpy as np
import pandas as pd
import faiss
import requests
from app.retrieval.reranker import rerank
from dotenv import dotenv_values, load_dotenv
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
INDEX_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks.index")
METADATA_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks_metadata.parquet")
CACHE_DIR = os.path.join(BASE_DIR, "data", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "answer_cache.json")

load_dotenv(dotenv_path=ENV_FILE, override=False)
DOTENV_CONFIG = dotenv_values(ENV_FILE) if os.path.exists(ENV_FILE) else {}

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5
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


def resolve_setting(name: str, default: str = "") -> str:
    env_value = normalize_env_value(os.getenv(name))
    if env_value:
        return env_value

    dotenv_value = normalize_env_value(DOTENV_CONFIG.get(name))
    if dotenv_value:
        os.environ[name] = dotenv_value
        return dotenv_value

    return default


def llm_api_key_present() -> bool:
    return bool(LLM_API_KEY)


LLM_API_URL = resolve_setting("LLM_API_URL", "https://api.deepseek.com/chat/completions")
LLM_API_KEY = resolve_setting("LLM_API_KEY", "")
LLM_MODEL = resolve_setting("LLM_MODEL", "deepseek-chat")


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


def search_rows(query: str, company_filter: str | None = None, form_filter: str | None = None) -> pd.DataFrame:
    if not os.path.exists(INDEX_FILE):
        raise FileNotFoundError("FAISS index does not exist.")

    if not os.path.exists(METADATA_FILE):
        raise FileNotFoundError("Metadata parquet does not exist.")

    metadata_df = pd.read_parquet(METADATA_FILE)
    index = faiss.read_index(INDEX_FILE)

    inferred_company = company_filter or infer_company_filter(query)
    inferred_form = form_filter or infer_form_filter(query)

    filtered_df = metadata_df.copy()

    if inferred_company:
        filtered_df = filtered_df[
            filtered_df["company"].astype(str).str.lower() == inferred_company.lower()
        ].copy()

    if inferred_form:
        filtered_df = filtered_df[
            filtered_df["form"].astype(str).str.lower() == inferred_form.lower()
        ].copy()

    if filtered_df.empty:
        raise ValueError("No rows match the requested metadata filters.")

    vector_ids = filtered_df["vector_id"].to_numpy(dtype="int64")
    filtered_vectors = np.vstack([index.reconstruct(int(i)) for i in vector_ids]).astype("float32")

    filtered_index = faiss.IndexFlatIP(filtered_vectors.shape[1])
    filtered_index.add(filtered_vectors)

    model = SentenceTransformer(MODEL_NAME)
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    top_k = min(TOP_K, len(filtered_df))
    scores, indices = filtered_index.search(query_embedding, top_k)

    result_rows = []
    for score, local_idx in zip(scores[0], indices[0]):
        if local_idx < 0 or local_idx >= len(filtered_df):
            continue

        row = filtered_df.iloc[int(local_idx)].copy()
        row["score"] = float(score)
        result_rows.append(row)

    if not result_rows:
        raise ValueError("No search results found.")

    return pd.DataFrame(result_rows)


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


from app.llm.langchain_chain import run_chain

def call_llm(query: str, context: str) -> str:
    if not llm_api_key_present():
        raise ValueError("LLM_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are a financial document analysis assistant. "
        "Answer only from the provided SEC filing context. "
        "If the context is insufficient, say so clearly. "
        "Write a concise, factual answer in English. "
        "After the answer, add a short Sources section with filing date, form, and URL."
    )

    user_prompt = (
        f"Question:\n{query}\n\n"
        f"Retrieved SEC filing context:\n{context}\n\n"
        "Task:\n"
        "1. Answer the question only from the context.\n"
        "2. Summarize the main points clearly.\n"
        "3. Do not invent facts.\n"
        "4. Add a short Sources section at the end."
    )

    payload = {
        "model": LLM_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    response = requests.post(
        LLM_API_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()

    try:
        return run_chain(query, context)
    except Exception:
        raise ValueError(f"Unexpected LLM response format: {json.dumps(data)[:1000]}")


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


def answer_query(
    query: str,
    company_filter: str | None = None,
    form_filter: str | None = None,
) -> dict:
    query = str(query).strip()
    inferred_company = company_filter or infer_company_filter(query)
    inferred_form = form_filter or infer_form_filter(query)

    cache_key = build_cache_key(query, inferred_company, inferred_form)
    cache_data = cleanup_expired_cache(load_cache())

    cached_entry = get_valid_cached_entry(cache_data, cache_key)
    if cached_entry:
        save_cache(cache_data)
        return _build_result(
            query=query,
            company_filter=inferred_company,
            form_filter=inferred_form,
            mode="cache",
            answer=str(cached_entry.get("answer", "")),
            cache_hit=True,
            cache_mode=str(cached_entry.get("mode", "")).strip().lower() or None,
            llm_model=str(cached_entry.get("llm_model") or LLM_MODEL),
            sources_text=str(cached_entry.get("sources_text") or ""),
            retrieval_error=str(cached_entry.get("retrieval_error")) if cached_entry.get("retrieval_error") else None,
            llm_error=str(cached_entry.get("llm_error")) if cached_entry.get("llm_error") else None,
        )

    try:
        results_df = search_rows(query, company_filter=company_filter, form_filter=form_filter)
        results_df = rerank(query, results_df, top_k=TOP_K)
    except Exception as exc:
        save_cache(cache_data)
        return _build_result(
            query=query,
            company_filter=inferred_company,
            form_filter=inferred_form,
            mode="fallback",
            answer="",
            cache_hit=False,
            cache_mode=None,
            sources_text="",
            retrieval_error=str(exc),
            llm_error=None,
        )

    context = build_context(results_df)
    sources_text = format_sources(results_df)
    llm_error = None

    try:
        answer = call_llm(query, context)
        mode = "llm"
    except Exception as exc:
        llm_error = str(exc)
        answer = build_fallback_answer(query, results_df)
        mode = "fallback"

    cache_data[cache_key] = {
        "query": query,
        "company_filter": inferred_company,
        "form_filter": inferred_form,
        "mode": mode,
        "llm_model": LLM_MODEL,
        "answer": answer,
        "sources_text": sources_text,
        "retrieval_error": None,
        "llm_error": llm_error,
        "created_at": time.time(),
    }
    save_cache(cache_data)

    return _build_result(
        query=query,
        company_filter=inferred_company,
        form_filter=inferred_form,
        mode=mode,
        answer=answer,
        cache_hit=False,
        cache_mode=None,
        llm_model=LLM_MODEL,
        sources_text=sources_text,
        retrieval_error=None,
        llm_error=llm_error,
    )


__all__ = [
    "LLM_MODEL",
    "answer_query",
    "llm_api_key_present",
]


