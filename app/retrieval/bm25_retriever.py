from rank_bm25 import BM25Okapi
import pandas as pd
import re


def tokenize(text):
    return re.findall(r"\w+", str(text).lower())


def bm25_search(query, metadata_df, company_filter=None, form_filter=None, top_k=20):

    df = metadata_df.copy()

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

    corpus = df["chunk_text"].astype(str).tolist()
    tokenized_corpus = [tokenize(doc) for doc in corpus]

    bm25 = BM25Okapi(tokenized_corpus)

    tokenized_query = tokenize(query)

    scores = bm25.get_scores(tokenized_query)

    df = df.copy()
    df["score"] = scores

    df = df.sort_values("score", ascending=False)

    return df.head(top_k)