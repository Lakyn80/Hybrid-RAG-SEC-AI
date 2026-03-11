import os

import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.retrieval import resources
from app.retrieval.metadata_utils import normalize_metadata_value

DEFAULT_QDRANT_URL = "http://localhost:6333"
DEFAULT_COLLECTION_ALIAS = "sec_filings_chunks_current"
DEFAULT_HNSW_EF = 128
DEFAULT_QDRANT_TIMEOUT = 120.0

_qdrant_client: QdrantClient | None = None


def get_qdrant_url() -> str:
    raw_url = str(os.getenv("QDRANT_URL") or "").strip()
    if raw_url:
        return raw_url
    return DEFAULT_QDRANT_URL


def get_collection_alias() -> str:
    manifest = resources.load_runtime_manifest()
    alias = str(manifest.get("collection_alias") or "").strip()
    if alias:
        return alias

    env_alias = str(os.getenv("QDRANT_COLLECTION_ALIAS") or "").strip()
    if env_alias:
        return env_alias

    return DEFAULT_COLLECTION_ALIAS


def get_qdrant_timeout() -> float:
    raw_timeout = str(os.getenv("QDRANT_TIMEOUT") or "").strip()
    if raw_timeout:
        try:
            return max(1.0, float(raw_timeout))
        except ValueError:
            pass
    return DEFAULT_QDRANT_TIMEOUT


def get_runtime_collection_name() -> str:
    manifest = resources.load_runtime_manifest()
    collection_name = str(manifest.get("collection_name") or "").strip()
    if collection_name:
        return collection_name
    return get_collection_alias()


def get_qdrant_client() -> QdrantClient:
    global _qdrant_client

    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=get_qdrant_url(),
            timeout=get_qdrant_timeout(),
        )

    return _qdrant_client


def resolve_filter_values(field: str, value: str | None) -> list[str]:
    normalized_value = normalize_metadata_value(value)
    if not normalized_value:
        return []

    metadata_df = resources.get_metadata_df()
    norm_column = f"{field}_norm"

    if norm_column not in metadata_df.columns:
        normalized_series = metadata_df[field].astype(str).map(normalize_metadata_value)
    else:
        normalized_series = metadata_df[norm_column].astype(str)

    exact_matches = normalized_series[normalized_series == normalized_value].dropna().unique().tolist()
    if exact_matches:
        return sorted(set(exact_matches))

    contains_matches = normalized_series[
        normalized_series.str.contains(normalized_value, regex=False, na=False)
    ].dropna().unique().tolist()
    return sorted(set(contains_matches))


def build_query_filter(
    company_filter: str | None = None,
    form_filter: str | None = None,
) -> models.Filter | None:
    must_conditions: list[models.FieldCondition] = []

    company_values = resolve_filter_values("company", company_filter)
    if company_filter:
        if not company_values:
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="company_norm",
                        match=models.MatchValue(value="__no_match__"),
                    )
                ]
            )

        company_match = (
            models.MatchAny(any=company_values)
            if len(company_values) > 1
            else models.MatchValue(value=company_values[0])
        )
        must_conditions.append(
            models.FieldCondition(
                key="company_norm",
                match=company_match,
            )
        )

    form_values = resolve_filter_values("form", form_filter)
    if form_filter:
        if not form_values:
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="form_norm",
                        match=models.MatchValue(value="__no_match__"),
                    )
                ]
            )

        form_match = (
            models.MatchAny(any=form_values)
            if len(form_values) > 1
            else models.MatchValue(value=form_values[0])
        )
        must_conditions.append(
            models.FieldCondition(
                key="form_norm",
                match=form_match,
            )
        )

    if not must_conditions:
        return None

    return models.Filter(must=must_conditions)


def search_qdrant_rows(
    query: str,
    *,
    company_filter: str | None = None,
    form_filter: str | None = None,
    limit: int = 20,
    embedding_model_name: str = resources.DEFAULT_EMBEDDING_MODEL,
) -> pd.DataFrame:
    client = get_qdrant_client()
    collection_name = get_runtime_collection_name()
    query_filter = build_query_filter(company_filter=company_filter, form_filter=form_filter)

    model = resources.get_embedding_model(embedding_model_name)
    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    query_vector = np.asarray(query_embedding, dtype="float32")[0].tolist()

    try:
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
            search_params=models.SearchParams(
                hnsw_ef=DEFAULT_HNSW_EF,
                exact=False,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Qdrant search failed: {exc}") from exc

    results = list(getattr(response, "points", []) or [])
    rows = []
    for hit in results:
        payload = dict(hit.payload or {})
        payload["score"] = float(hit.score)
        rows.append(payload)

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
