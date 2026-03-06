import os
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_chunks.parquet")
INDEX_DIR = os.path.join(BASE_DIR, "data", "vectorstore", "faiss")
INDEX_FILE = os.path.join(INDEX_DIR, "filings_chunks.index")
METADATA_FILE = os.path.join(INDEX_DIR, "filings_chunks_metadata.parquet")

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 64


def build_index() -> int:
    print(f"INPUT_FILE: {INPUT_FILE}")
    print(f"INDEX_FILE: {INDEX_FILE}")
    print(f"METADATA_FILE: {METADATA_FILE}")
    print(f"MODEL_NAME: {MODEL_NAME}")

    if not os.path.exists(INPUT_FILE):
        print("ERROR: filings_chunks.parquet does not exist.")
        return 1

    df = pd.read_parquet(INPUT_FILE)

    required_columns = [
        "company",
        "form",
        "filing_date",
        "accession_number",
        "filing_url",
        "source_file",
        "html_title",
        "document_text_length",
        "chunk_index",
        "chunk_text",
        "chunk_text_length",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        return 1

    df = df.copy()
    df["chunk_text"] = df["chunk_text"].fillna("").astype(str).str.strip()
    df = df[df["chunk_text"] != ""].reset_index(drop=True)

    if df.empty:
        print("ERROR: No valid chunk_text rows found.")
        return 1

    print(f"Rows for embedding: {len(df)}")

    texts = df["chunk_text"].tolist()

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    print(f"Embeddings shape: {embeddings.shape}")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_FILE)

    metadata_df = df[
        [
            "company",
            "form",
            "filing_date",
            "accession_number",
            "filing_url",
            "source_file",
            "html_title",
            "document_text_length",
            "chunk_index",
            "chunk_text",
            "chunk_text_length",
        ]
    ].copy()

    metadata_df.insert(0, "vector_id", range(len(metadata_df)))
    metadata_df.to_parquet(METADATA_FILE, index=False)

    print("FAISS index created")
    print(f"Vectors stored: {index.ntotal}")
    print(f"Index saved to: {INDEX_FILE}")
    print(f"Metadata saved to: {METADATA_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(build_index())
