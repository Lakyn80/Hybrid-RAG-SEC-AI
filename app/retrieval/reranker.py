from sentence_transformers import CrossEncoder
import pandas as pd

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model = None


def get_model():
    global _model
    if _model is None:
        _model = CrossEncoder(MODEL_NAME)
    return _model


def rerank(query: str, df: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """
    Rerank výsledky retrievalu podle relevance vůči dotazu.
    """

    if df.empty:
        return df

    model = get_model()

    pairs = [(query, str(text)) for text in df["chunk_text"].tolist()]
    scores = model.predict(pairs)

    df = df.copy()
    df["rerank_score"] = scores

    df = df.sort_values("rerank_score", ascending=False)

    return df.head(top_k)
