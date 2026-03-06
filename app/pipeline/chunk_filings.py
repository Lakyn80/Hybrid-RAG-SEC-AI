import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_parsed.parquet")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_chunks.parquet")

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 300


def normalize_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    text = normalize_text(text)

    if not text:
        return []

    chunks = []
    start = 0
    step = chunk_size - chunk_overlap

    if step <= 0:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start += step

    return chunks


def chunk_filings() -> int:
    print(f"INPUT_FILE: {INPUT_FILE}")
    print(f"OUTPUT_FILE: {OUTPUT_FILE}")
    print(f"CHUNK_SIZE: {CHUNK_SIZE}")
    print(f"CHUNK_OVERLAP: {CHUNK_OVERLAP}")

    if not os.path.exists(INPUT_FILE):
        print("ERROR: filings_parsed.parquet does not exist.")
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
        "text_length",
        "full_text",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        return 1

    records = []

    for doc_index, row in df.iterrows():
        full_text = normalize_text(row["full_text"])

        if not full_text:
            print(f"[{doc_index}] SKIP EMPTY TEXT: {row['source_file']}")
            continue

        chunks = split_text(
            text=full_text,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        for chunk_index, chunk_text in enumerate(chunks):
            records.append({
                "company": row["company"],
                "form": row["form"],
                "filing_date": row["filing_date"],
                "accession_number": row["accession_number"],
                "filing_url": row["filing_url"],
                "source_file": row["source_file"],
                "html_title": row["html_title"],
                "document_text_length": row["text_length"],
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "chunk_text_length": len(chunk_text),
            })

    chunks_df = pd.DataFrame(records)

    print(f"Chunks DataFrame shape: {chunks_df.shape}")
    print(f"Chunks DataFrame columns: {chunks_df.columns.tolist()}")

    if chunks_df.empty:
        print("ERROR: No chunks were created.")
        return 1

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    chunks_df.to_parquet(OUTPUT_FILE, index=False)

    print("Chunks dataset created")
    print("Rows:", len(chunks_df))
    print("Saved to:", OUTPUT_FILE)

    return 0


if __name__ == "__main__":
    raise SystemExit(chunk_filings())
