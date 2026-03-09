from rank_bm25 import BM25Okapi
import pandas as pd
import re

from app.retrieval import resources

_tokenized_corpus = None
_tokenized_corpus_version = None
INDEX_VERSION_KEY = "rag:index_version"


def tokenize(text):
    return re.findall(r"\w+", str(text).lower())


def get_tokenized_corpus() -> list[list[str]]:
    global _tokenized_corpus, _tokenized_corpus_version

    current_index_version = resources.get_vector_index_version()
    redis_index_version = None

    try:
        client = resources.get_redis_client()
        redis_index_version = client.get(INDEX_VERSION_KEY)
        if redis_index_version != current_index_version:
            client.set(INDEX_VERSION_KEY, current_index_version)
            redis_index_version = current_index_version
    except Exception:
        redis_index_version = current_index_version

    if (
        _tokenized_corpus is None
        or _tokenized_corpus_version != current_index_version
        or _tokenized_corpus_version != redis_index_version
    ):
        metadata_df = resources.get_metadata_df()
        _tokenized_corpus = [
            tokenize(doc)
            for doc in metadata_df["chunk_text"].astype(str).tolist()
        ]
        _tokenized_corpus_version = current_index_version

    return _tokenized_corpus


def bm25_search(query, metadata_df=None, company_filter=None, form_filter=None, top_k=20):

    base_df = metadata_df if metadata_df is not None else resources.get_metadata_df()

    df = base_df.copy()

    if company_filter:
        df = df[
            df["company"].astype(str).str.contains(
                str(company_filter).strip(),
                case=False,
                na=False,
                regex=False,
            )
        ]

    if form_filter:
        df = df[
            df["form"].astype(str).str.upper()
            == str(form_filter).strip().upper()
        ]

    if df.empty:
        return df

    full_tokenized_corpus = get_tokenized_corpus()
    tokenized_corpus = [full_tokenized_corpus[int(idx)] for idx in df.index.tolist()]

    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = tokenize(query)

    scores = bm25.get_scores(tokenized_query)

    df = df.copy()
    df["score"] = scores

    df = df.sort_values("score", ascending=False)

    return df.head(top_k)
