import argparse
import json
import os
import sys

import requests
from datasets import Dataset
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ragas import evaluate
from ragas.llms import llm_factory
from ragas.metrics._answer_relevance import ResponseRelevancy
from ragas.metrics._faithfulness import Faithfulness

from app.llm.langchain_chain import get_llm_settings
from app.services.answer_service import node_parallel_retrieve, node_prepare

load_dotenv()

DEFAULT_DATASET = "tests/ragas_dataset.json"


class LocalSentenceTransformerEmbeddings:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()


API_URL = "http://localhost:8021/api/ask"
EMBEDDING_MODEL = str(os.getenv("RAGAS_EMBEDDING_MODEL") or "").strip() or "all-MiniLM-L6-v2"
RAGAS_MAX_TOKENS = int(str(os.getenv("RAGAS_MAX_TOKENS") or "").strip() or "8192")

model_name, api_key, base_url = get_llm_settings()
ragas_client = OpenAI(api_key=api_key, base_url=base_url)
ragas_llm = llm_factory(
    model_name,
    client=ragas_client,
    temperature=0,
    max_tokens=RAGAS_MAX_TOKENS,
)
ragas_embeddings = LocalSentenceTransformerEmbeddings(EMBEDDING_MODEL)


def normalize_context_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    contexts = []
    for value in values:
        text = str(value).strip()
        if text:
            contexts.append(text)
    return contexts


def extract_retrieved_contexts(api_result: dict, query: str) -> list[str]:
    for key in ("contexts", "retrieved_chunks", "retrieved_contexts"):
        contexts = normalize_context_list(api_result.get(key))
        if contexts:
            return contexts

    state = node_prepare({"query": query})
    retrieval_state = node_parallel_retrieve(state)

    if retrieval_state.get("retrieval_error"):
        raise ValueError(
            f"Failed to collect retrieved contexts for evaluation: {retrieval_state['retrieval_error']}"
        )

    rows = retrieval_state.get("results_rows") or []
    contexts = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        chunk_text = str(row.get("chunk_text", "")).strip()
        if chunk_text:
            contexts.append(chunk_text)

    if not contexts:
        raise ValueError("No retrieved chunk_text contexts available for evaluation.")

    return contexts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    answers = []
    contexts = []
    ground_truths = []

    for row in data:
        question = row.get("question") or row.get("query")
        if not question:
            continue

        response = requests.post(API_URL, json={"query": question})
        response.raise_for_status()
        result = response.json()

        reference = row.get("ground_truth") or row.get("reference")
        if not reference:
            continue

        questions.append(question)
        answers.append(result.get("answer", ""))
        contexts.append(extract_retrieved_contexts(result, question))
        ground_truths.append(reference)

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "retrieved_contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    result = evaluate(
        dataset,
        metrics=[
            Faithfulness(llm=ragas_llm),
            ResponseRelevancy(llm=ragas_llm, strictness=1),
        ],
        embeddings=ragas_embeddings,
    )

    print("\nRAGAS EVALUATION\n")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
