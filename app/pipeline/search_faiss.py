import os
import sys
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INDEX_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks.index")
METADATA_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "faiss", "filings_chunks_metadata.parquet")

MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5


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


def search_faiss(query: str, company_filter: str | None = None, form_filter: str | None = None) -> int:
    print(f"INDEX_FILE: {INDEX_FILE}")
    print(f"METADATA_FILE: {METADATA_FILE}")
    print(f"MODEL_NAME: {MODEL_NAME}")
    print(f"QUERY: {query}")

    inferred_company = company_filter or infer_company_filter(query)
    inferred_form = form_filter or infer_form_filter(query)

    print(f"COMPANY_FILTER: {inferred_company}")
    print(f"FORM_FILTER: {inferred_form}")

    if not os.path.exists(INDEX_FILE):
        print("ERROR: FAISS index does not exist.")
        return 1

    if not os.path.exists(METADATA_FILE):
        print("ERROR: Metadata parquet does not exist.")
        return 1

    metadata_df = pd.read_parquet(METADATA_FILE)
    index = faiss.read_index(INDEX_FILE)

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
        print("ERROR: No rows match the requested metadata filters.")
        return 1

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

    print("\n=== TOP RESULTS ===\n")

    for rank, (score, local_idx) in enumerate(zip(scores[0], indices[0]), start=1):
        if local_idx < 0 or local_idx >= len(filtered_df):
            continue

        row = filtered_df.iloc[local_idx]

        print(f"Result #{rank}")
        print(f"Score: {score:.4f}")
        print(f"Company: {row['company']}")
        print(f"Form: {row['form']}")
        print(f"Filing date: {row['filing_date']}")
        print(f"Chunk index: {row['chunk_index']}")
        print(f"URL: {row['filing_url']}")
        print("Chunk text:")
        print(str(row["chunk_text"])[:1500])
        print("\n" + "=" * 120 + "\n")

    return 0


if __name__ == "__main__":
    args = sys.argv[1:]

    company_filter = parse_optional_arg("--company=", args)
    form_filter = parse_optional_arg("--form=", args)

    query_parts = [arg for arg in args if not arg.startswith("--company=") and not arg.startswith("--form=")]
    query = " ".join(query_parts).strip()

    if not query:
        print('Usage: python .\\app\\pipeline\\search_faiss.py "your query here" [--company=Apple Inc.] [--form=10-K]')
        raise SystemExit(1)

    raise SystemExit(search_faiss(query, company_filter=company_filter, form_filter=form_filter))
