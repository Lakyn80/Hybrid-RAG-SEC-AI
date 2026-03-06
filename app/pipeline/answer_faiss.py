import os
import re
import sys
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INDEX_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks.index")
METADATA_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks_metadata.parquet")

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 8
MAX_SENTENCES = 6

RISK_HINT_WORDS = {
    "risk", "risks", "risky", "adverse", "adversely", "uncertain", "uncertainty",
    "legal", "litigation", "regulation", "regulatory", "economic", "economy",
    "supplier", "suppliers", "supply", "geopolitical", "trade", "conflict",
    "terrorism", "disaster", "public", "health", "privacy", "security",
    "competition", "market", "volatile", "volatility", "credit", "liquidity"
}


def parse_optional_arg(prefix: str, args: list[str]) -> str | None:
    for arg in args:
        if arg.startswith(prefix):
            return arg[len(prefix):].strip()
    return None


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


def sentence_keyword_score(sentence: str, query: str) -> int:
    sentence_lower = sentence.lower()
    query_words = re.findall(r"[a-zA-Z0-9\-]+", query.lower())
    base = sum(1 for word in query_words if len(word) > 2 and word in sentence_lower)
    risk_bonus = sum(1 for word in RISK_HINT_WORDS if word in sentence_lower)
    return base + risk_bonus


def is_good_sentence(sentence: str) -> bool:
    s = re.sub(r"\s+", " ", str(sentence)).strip()

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
    )
    if s.lower().startswith(bad_starts):
        return False

    if " in millions" in s.lower():
        return False

    if "$" in s and digit_count > 3:
        return False

    return True


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


def build_answer(query: str, results_df: pd.DataFrame) -> str:
    candidates = []

    for _, row in results_df.iterrows():
        sentences = split_sentences(row["chunk_text"])
        for sentence in sentences:
            if not is_good_sentence(sentence):
                continue

            score = sentence_keyword_score(sentence, query)
            if score <= 0:
                continue

            candidates.append({
                "sentence": sentence,
                "keyword_score": score,
                "retrieval_score": float(row["score"]),
                "company": row["company"],
                "form": row["form"],
                "filing_date": row["filing_date"],
            })

    if not candidates:
        return "No concise answer could be extracted from the retrieved chunks."

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
        selected.append(f"- {sentence} [{row['company']} | {row['form']} | {row['filing_date']}]")

        if len(selected) >= MAX_SENTENCES:
            break

    if not selected:
        return "No concise answer could be extracted from the retrieved chunks."

    return "\n".join(selected)


def main() -> int:
    args = sys.argv[1:]

    company_filter = parse_optional_arg("--company=", args)
    form_filter = parse_optional_arg("--form=", args)

    query_parts = [arg for arg in args if not arg.startswith("--company=") and not arg.startswith("--form=")]
    query = " ".join(query_parts).strip()

    if not query:
        print('Usage: python .\\app\\pipeline\\answer_faiss.py "your query here" [--company=Apple Inc.] [--form=10-K]')
        return 1

    print(f"QUERY: {query}")
    print(f"COMPANY_FILTER: {company_filter or infer_company_filter(query)}")
    print(f"FORM_FILTER: {form_filter or infer_form_filter(query)}")

    try:
        results_df = search_rows(query, company_filter=company_filter, form_filter=form_filter)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print("\n=== ANSWER ===\n")
    print(build_answer(query, results_df))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
