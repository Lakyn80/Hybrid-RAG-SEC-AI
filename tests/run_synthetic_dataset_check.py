import json
from collections import Counter
import re

DATASET_FILE = "tests/synthetic_eval_dataset.json"
REQUIRED_KEYS = {
    "id",
    "question",
    "reference",
    "company",
    "form",
    "filing_date",
    "accession_number",
    "query_type",
    "source_chunk_text",
    "source_chunk_hash",
    "quality_score",
    "warmup_eligible",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9\\-]+", normalize_text(text))


def token_overlap_ratio(reference: str, source_text: str) -> float:
    reference_tokens = set(tokenize(reference))
    source_tokens = set(tokenize(source_text))

    if not reference_tokens or not source_tokens:
        return 0.0

    return len(reference_tokens & source_tokens) / len(reference_tokens)


def main() -> int:
    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    total = len(data)
    missing_schema = 0
    duplicate_questions = 0
    low_quality = 0
    weak_overlap = 0

    seen_questions = set()
    type_counter = Counter()
    company_counter = Counter()
    form_counter = Counter()

    for row in data:
        if not REQUIRED_KEYS.issubset(row):
            missing_schema += 1

        question_key = str(row.get("question", "")).strip().lower()
        if question_key in seen_questions:
            duplicate_questions += 1
        seen_questions.add(question_key)

        try:
            if float(row.get("quality_score", 0)) < 0.72:
                low_quality += 1
        except Exception:
            low_quality += 1

        reference = str(row.get("reference", ""))
        source_text = str(row.get("source_chunk_text", ""))
        overlap = token_overlap_ratio(reference, source_text)
        if normalize_text(reference) not in normalize_text(source_text) and overlap < 0.35:
            weak_overlap += 1

        type_counter.update([row.get("query_type")])
        company_counter.update([row.get("company")])
        form_counter.update([row.get("form")])

    summary = {
        "total": total,
        "missing_schema": missing_schema,
        "duplicate_questions": duplicate_questions,
        "low_quality_rows": low_quality,
        "weak_overlap_rows": weak_overlap,
        "query_type_counts": dict(type_counter),
        "company_counts": dict(company_counter),
        "form_counts": dict(form_counter),
    }

    print("\nSYNTHETIC DATASET CHECK\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
