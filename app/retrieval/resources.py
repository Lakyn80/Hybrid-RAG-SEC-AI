import hashlib
import json
import os
from pathlib import Path
from typing import Any

import faiss
import pandas as pd
from dotenv import load_dotenv
from redis import Redis
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "data", "vectorstore", "faiss")
INDEX_FILE = os.path.join(VECTORSTORE_DIR, "filings_chunks.index")
METADATA_FILE = os.path.join(VECTORSTORE_DIR, "filings_chunks_metadata.parquet")
RUNTIME_MANIFEST_FILE = os.path.join(BASE_DIR, "data", "vectorstore", "runtime_manifest.json")

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

load_dotenv(dotenv_path=ENV_FILE, override=False)

_metadata_df: pd.DataFrame | None = None
_metadata_mtime: float | None = None
_faiss_index = None
_faiss_index_mtime: float | None = None
_embedding_models: dict[str, SentenceTransformer] = {}
_redis_client: Redis | None = None
_runtime_manifest: dict[str, Any] | None = None
_runtime_manifest_mtime: float | None = None


def _read_json_file(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_runtime_manifest() -> dict[str, Any]:
    global _runtime_manifest, _runtime_manifest_mtime

    current_mtime = os.path.getmtime(RUNTIME_MANIFEST_FILE) if os.path.exists(RUNTIME_MANIFEST_FILE) else None
    if _runtime_manifest is None or _runtime_manifest_mtime != current_mtime:
        _runtime_manifest = _read_json_file(RUNTIME_MANIFEST_FILE)
        _runtime_manifest_mtime = current_mtime

    return _runtime_manifest


def get_runtime_vector_backend() -> str:
    manifest = load_runtime_manifest()
    backend = str(manifest.get("backend") or "").strip().lower()
    if backend:
        return backend
    return "faiss"


def _file_signature(paths: list[str]) -> str:
    hasher = hashlib.sha256()

    for raw_path in paths:
        path = Path(raw_path)
        hasher.update(str(path.name).encode("utf-8"))

        if path.exists():
            stat = path.stat()
            hasher.update(str(int(stat.st_mtime)).encode("utf-8"))
            hasher.update(str(stat.st_size).encode("utf-8"))
        else:
            hasher.update(b"missing")

    return hasher.hexdigest()[:16]


def get_vector_index_version() -> str:
    manifest = load_runtime_manifest()
    index_version = str(manifest.get("index_version") or "").strip()
    if index_version:
        return index_version

    return _file_signature([INDEX_FILE, METADATA_FILE])


def get_metadata_df() -> pd.DataFrame:
    global _metadata_df, _metadata_mtime

    current_mtime = os.path.getmtime(METADATA_FILE) if os.path.exists(METADATA_FILE) else None
    if _metadata_df is None or _metadata_mtime != current_mtime:
        _metadata_df = pd.read_parquet(METADATA_FILE).reset_index(drop=True)
        _metadata_mtime = current_mtime

    return _metadata_df


def get_faiss_index():
    global _faiss_index, _faiss_index_mtime

    current_mtime = os.path.getmtime(INDEX_FILE) if os.path.exists(INDEX_FILE) else None
    if _faiss_index is None or _faiss_index_mtime != current_mtime:
        _faiss_index = faiss.read_index(INDEX_FILE)
        _faiss_index_mtime = current_mtime

    return _faiss_index


def get_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> SentenceTransformer:
    if model_name not in _embedding_models:
        _embedding_models[model_name] = SentenceTransformer(model_name)

    return _embedding_models[model_name]


def get_redis_url() -> str:
    raw_url = str(os.getenv("REDIS_URL") or "").strip()
    if raw_url:
        return raw_url
    return DEFAULT_REDIS_URL


def get_redis_client() -> Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = Redis.from_url(
            get_redis_url(),
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
        )

    return _redis_client
