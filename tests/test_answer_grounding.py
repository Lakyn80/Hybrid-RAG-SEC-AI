import os
import re
import subprocess
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.answer_service import (
    build_context,
    call_llm,
    node_parallel_retrieve,
    node_prepare,
    post_process_answer,
    records_to_dataframe,
    split_sentences,
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "in", "into", "is", "it", "its", "of", "on", "or", "that", "the", "their",
    "this", "to", "was", "were", "what", "which", "with",
}


def tokenize(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-zA-Z0-9\-]+", str(text or "").lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def sentence_supported_by_context(sentence: str, context_tokens: set[str]) -> bool:
    sentence_tokens = tokenize(sentence)
    if not sentence_tokens:
        return True

    overlap_ratio = len(sentence_tokens & context_tokens) / len(sentence_tokens)
    return overlap_ratio >= 0.2


class AnswerGroundingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run(
            [sys.executable, os.path.join("scripts", "reset_query_cache.py")],
            cwd=BASE_DIR,
            check=False,
        )

    def get_answer_and_context(self, query: str) -> tuple[str, list[str]]:
        state = node_prepare({"query": query})
        retrieval_state = node_parallel_retrieve(state)

        self.assertIsNone(retrieval_state.get("retrieval_error"))

        results_df = records_to_dataframe(retrieval_state.get("results_rows"))
        self.assertFalse(results_df.empty)

        context = build_context(results_df)
        answer = post_process_answer(call_llm(query, context))
        contexts = [str(row.get("chunk_text", "")).strip() for row in retrieval_state.get("results_rows") or []]
        return answer, contexts

    def assert_answer_is_grounded(self, answer: str, contexts: list[str]) -> None:
        context_tokens = tokenize(" ".join(contexts))
        self.assertNotEqual(answer, "The provided filings do not contain this information.")

        for sentence in split_sentences(answer):
            self.assertTrue(
                sentence_supported_by_context(sentence, context_tokens),
                msg=f"Ungrounded sentence detected: {sentence}",
            )

    def test_legal_risks_answer_is_grounded(self) -> None:
        answer, contexts = self.get_answer_and_context("What legal risks did Apple mention?")
        self.assert_answer_is_grounded(answer, contexts)

    def test_10k_disclosure_answer_uses_context_only(self) -> None:
        answer, contexts = self.get_answer_and_context("What did Apple disclose in its 10-K?")
        self.assert_answer_is_grounded(answer, contexts)

    def test_litigation_answer_is_concise(self) -> None:
        answer, _ = self.get_answer_and_context("What risks did Apple mention related to litigation?")
        self.assertLessEqual(len(split_sentences(answer)), 4)


if __name__ == "__main__":
    unittest.main()
