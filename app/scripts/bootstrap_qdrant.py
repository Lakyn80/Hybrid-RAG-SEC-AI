import os
import sys

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.logger import get_logger
from app.pipeline.build_qdrant_index import build_qdrant_index
from app.retrieval.qdrant_store import get_qdrant_url, get_runtime_collection_name

logger = get_logger(__name__)


def collection_exists(qdrant_url: str, collection_name: str) -> bool:
    url = f"{qdrant_url.rstrip('/')}/collections/{collection_name}/exists"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    payload = response.json()
    return bool((payload.get("result") or {}).get("exists"))


def bootstrap_qdrant() -> int:
    collection_name = get_runtime_collection_name()
    qdrant_url = get_qdrant_url()

    try:
        if collection_exists(qdrant_url, collection_name):
            logger.info("Qdrant collection exists – skipping ingest")
            return 0
    except Exception as exc:
        logger.info("qdrant_collection_exists_check_failed=%s", exc)

    logger.info("Qdrant collection missing – running ingest")
    return build_qdrant_index()


if __name__ == "__main__":
    raise SystemExit(bootstrap_qdrant())
