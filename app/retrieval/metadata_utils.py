import hashlib
import re


def normalize_metadata_value(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def build_chunk_hash(text: str) -> str:
    normalized_text = re.sub(r"\s+", " ", str(text or "")).strip()
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:24]
