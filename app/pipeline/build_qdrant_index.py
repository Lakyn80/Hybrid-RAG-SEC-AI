import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from qdrant_client.http import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.retrieval import resources
from app.retrieval.metadata_utils import build_chunk_hash, normalize_metadata_value
from app.retrieval.qdrant_store import get_collection_alias, get_qdrant_client

INPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_chunks.parquet")
METADATA_FILE = resources.METADATA_FILE
RUNTIME_MANIFEST_FILE = resources.RUNTIME_MANIFEST_FILE

BATCH_SIZE = 128
MODEL_NAME = resources.DEFAULT_EMBEDDING_MODEL
HNSW_M = 16
HNSW_EF_CONSTRUCT = 200


def compute_index_version(input_file: str, row_count: int, model_name: str) -> str:
    path = Path(input_file)
    stat = path.stat()
    raw = f"{path.name}:{int(stat.st_mtime)}:{stat.st_size}:{row_count}:{model_name}"
    return build_chunk_hash(raw)


def ensure_runtime_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "company_norm" not in out.columns:
        out["company_norm"] = out["company"].astype(str).map(normalize_metadata_value)

    if "form_norm" not in out.columns:
        out["form_norm"] = out["form"].astype(str).map(normalize_metadata_value)

    if "chunk_hash" not in out.columns:
        out["chunk_hash"] = out["chunk_text"].astype(str).map(build_chunk_hash)

    return out


def swap_collection_alias(client, collection_name: str, alias_name: str) -> None:
    actions: list[models.CreateAliasOperation | models.DeleteAliasOperation] = []

    try:
        aliases_response = client.get_aliases()
        aliases = getattr(aliases_response, "aliases", []) or []
        if any(getattr(alias, "alias_name", "") == alias_name for alias in aliases):
            actions.append(
                models.DeleteAliasOperation(
                    delete_alias=models.DeleteAlias(alias_name=alias_name),
                )
            )
    except Exception:
        pass

    actions.append(
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(
                collection_name=collection_name,
                alias_name=alias_name,
            )
        )
    )

    client.update_collection_aliases(change_aliases_operations=actions)


def build_qdrant_index() -> int:
    print(f"INPUT_FILE: {INPUT_FILE}")
    print(f"METADATA_FILE: {METADATA_FILE}")
    print(f"MODEL_NAME: {MODEL_NAME}")

    if not os.path.exists(INPUT_FILE):
        print("ERROR: filings_chunks.parquet does not exist.")
        return 1

    df = pd.read_parquet(INPUT_FILE)
    df = ensure_runtime_columns(df)

    required_columns = [
        "company",
        "company_norm",
        "form",
        "form_norm",
        "filing_date",
        "accession_number",
        "filing_url",
        "source_file",
        "html_title",
        "document_text_length",
        "chunk_index",
        "chunk_text",
        "chunk_text_length",
        "chunk_hash",
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

    index_version = compute_index_version(INPUT_FILE, len(df), MODEL_NAME)
    collection_name = f"sec_filings_chunks_{index_version}"
    alias_name = get_collection_alias()

    print(f"INDEX_VERSION: {index_version}")
    print(f"COLLECTION_NAME: {collection_name}")
    print(f"COLLECTION_ALIAS: {alias_name}")
    print(f"ROWS FOR EMBEDDING: {len(df)}")

    model = resources.get_embedding_model(MODEL_NAME)
    embeddings = model.encode(
        df["chunk_text"].tolist(),
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype="float32")

    client = get_qdrant_client()
    vector_size = int(embeddings.shape[1])

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
        hnsw_config=models.HnswConfigDiff(
            m=HNSW_M,
            ef_construct=HNSW_EF_CONSTRUCT,
        ),
    )

    client.create_payload_index(
        collection_name=collection_name,
        field_name="company_norm",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
    client.create_payload_index(
        collection_name=collection_name,
        field_name="form_norm",
        field_schema=models.PayloadSchemaType.KEYWORD,
        wait=True,
    )

    metadata_df = df[
        [
            "company",
            "company_norm",
            "form",
            "form_norm",
            "filing_date",
            "accession_number",
            "filing_url",
            "source_file",
            "html_title",
            "document_text_length",
            "chunk_index",
            "chunk_text",
            "chunk_text_length",
            "chunk_hash",
        ]
    ].copy()
    metadata_df.insert(0, "vector_id", range(len(metadata_df)))

    for start in range(0, len(metadata_df), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(metadata_df))
        batch_rows = metadata_df.iloc[start:end]
        batch_vectors = embeddings[start:end]

        points = []
        for row, vector in zip(batch_rows.to_dict(orient="records"), batch_vectors, strict=True):
            point_id = int(row["vector_id"])
            payload = dict(row)
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload=payload,
                )
            )

        client.upsert(
            collection_name=collection_name,
            points=points,
            wait=True,
        )

    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    metadata_df.to_parquet(METADATA_FILE, index=False)

    manifest = {
        "backend": "qdrant",
        "collection_alias": alias_name,
        "collection_name": collection_name,
        "index_version": index_version,
        "embedding_model": MODEL_NAME,
        "points_count": len(metadata_df),
        "built_at": int(time.time()),
    }

    os.makedirs(os.path.dirname(RUNTIME_MANIFEST_FILE), exist_ok=True)
    with open(RUNTIME_MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    try:
        swap_collection_alias(client, collection_name=collection_name, alias_name=alias_name)
    except Exception as exc:
        print(f"WARNING: alias swap skipped: {exc}")

    print("Qdrant collection created")
    print(f"Points stored: {len(metadata_df)}")
    print(f"Metadata saved to: {METADATA_FILE}")
    print(f"Manifest saved to: {RUNTIME_MANIFEST_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(build_qdrant_index())
