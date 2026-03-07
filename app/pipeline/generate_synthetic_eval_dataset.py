import argparse
import json
import os
import re
import sys
from collections import defaultdict

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.llm.synthetic_eval_chain import generate_synthetic_eval_sample
from app.retrieval.metadata_utils import build_chunk_hash

INPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_chunks.parquet")
OUTPUT_FILE = os.path.join(BASE_DIR, "tests", "synthetic_eval_dataset.json")

ALLOWED_FORMS = {"10-K", "10-Q", "DEF 14A", "8-K"}
QUERY_TYPES = [
    "risk_factor",
    "financial_metric",
    "date_or_period",
    "governance_or_proxy",
    "business_or_product",
    "legal_or_compliance",
]
BANNED_QUESTION_PHRASES = (
    "according to the text",
    "based on the excerpt",
    "in the passage",
    "in this chunk",
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9\-]+", normalize_text(text).lower())


def token_overlap_ratio(reference: str, chunk_text: str) -> float:
    ref_tokens = set(tokenize(reference))
    chunk_tokens = set(tokenize(chunk_text))

    if not ref_tokens or not chunk_tokens:
        return 0.0

    return len(ref_tokens & chunk_tokens) / len(ref_tokens)


def is_high_quality_chunk(row: pd.Series) -> bool:
    form = str(row.get("form") or "").strip().upper()
    text = normalize_text(str(row.get("chunk_text") or ""))

    if form not in ALLOWED_FORMS:
        return False

    if len(text) < 350:
        return False

    alpha_chars = sum(ch.isalpha() for ch in text)
    digit_chars = sum(ch.isdigit() for ch in text)
    if alpha_chars == 0:
        return False

    if digit_chars > alpha_chars * 0.35:
        return False

    lowered = text.lower()
    if lowered.count("us-gaap") > 3 or lowered.count("xbrli:") > 2:
        return False

    if lowered.startswith(("table of contents", "index", "part i", "item 1.")):
        return False

    return True


def detect_query_types(row: pd.Series) -> list[str]:
    text = normalize_text(str(row.get("chunk_text") or "")).lower()
    form = str(row.get("form") or "").strip().upper()
    types = []

    if any(word in text for word in ("risk", "uncertainty", "adverse", "supplier", "competition")):
        types.append("risk_factor")

    if any(word in text for word in ("revenue", "income", "cash", "expense", "dividend", "earnings", "$")):
        types.append("financial_metric")

    if any(word in text for word in ("as of", "ended", "fiscal year", "quarter ended", "date:")):
        types.append("date_or_period")

    if form == "DEF 14A" or any(word in text for word in ("board", "stockholder", "proposal", "director", "vote")):
        types.append("governance_or_proxy")

    if any(word in text for word in ("product", "service", "platform", "customer", "market", "software", "hardware", "device")):
        types.append("business_or_product")

    if any(word in text for word in ("legal", "litigation", "regulatory", "compliance", "privacy", "antitrust")):
        types.append("legal_or_compliance")

    if not types:
        types.append("business_or_product")

    ordered = []
    for query_type in QUERY_TYPES:
        if query_type in types:
            ordered.append(query_type)
    return ordered


def validate_generated_sample(sample: dict | None, chunk_text: str, min_quality: float) -> dict | None:
    if not isinstance(sample, dict):
        return None

    question = normalize_text(str(sample.get("question") or ""))
    reference = normalize_text(str(sample.get("reference") or ""))

    if not question or not reference:
        return None

    if any(phrase in question.lower() for phrase in BANNED_QUESTION_PHRASES):
        return None

    if len(question) < 12 or len(question) > 220:
        return None

    if len(reference) < 20 or len(reference) > 600:
        return None

    overlap = token_overlap_ratio(reference, chunk_text)
    if overlap < 0.35 and reference.lower() not in chunk_text.lower():
        return None

    try:
        quality_score = float(sample.get("quality_score", 0))
    except Exception:
        return None

    quality_score = max(0.0, min(1.0, quality_score))
    if quality_score < min_quality:
        return None

    warmup_eligible = bool(sample.get("warmup_eligible")) and quality_score >= 0.82

    return {
        "question": question,
        "reference": reference,
        "quality_score": quality_score,
        "warmup_eligible": warmup_eligible,
    }


def build_output_record(row: pd.Series, query_type: str, sample: dict) -> dict:
    question = sample["question"]
    chunk_hash = str(row.get("chunk_hash") or build_chunk_hash(str(row.get("chunk_text") or "")))
    record_id = build_chunk_hash(f"{row['accession_number']}|{chunk_hash}|{question}")

    return {
        "id": record_id,
        "question": question,
        "reference": sample["reference"],
        "company": row["company"],
        "form": row["form"],
        "filing_date": str(row["filing_date"]),
        "accession_number": row["accession_number"],
        "query_type": query_type,
        "source_chunk_text": str(row["chunk_text"]),
        "source_chunk_hash": chunk_hash,
        "quality_score": sample["quality_score"],
        "warmup_eligible": sample["warmup_eligible"],
    }


def generate_dataset(limit: int, max_per_type: int, min_quality: float) -> list[dict]:
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    df = pd.read_parquet(INPUT_FILE)
    if "chunk_hash" not in df.columns:
        df["chunk_hash"] = df["chunk_text"].astype(str).map(build_chunk_hash)

    df = df[df.apply(is_high_quality_chunk, axis=1)].reset_index(drop=True)
    if df.empty:
        raise ValueError("No high-quality chunks available for synthetic eval generation.")

    seen_questions = set()
    type_counts = defaultdict(int)
    company_form_type_counts = defaultdict(int)
    records = []

    for _, row in df.iterrows():
        for query_type in detect_query_types(row):
            if len(records) >= limit:
                break

            if type_counts[query_type] >= max_per_type:
                continue

            scope_key = (row["company"], row["form"], query_type)
            if company_form_type_counts[scope_key] >= 3:
                continue

            sample = generate_synthetic_eval_sample(
                company=str(row["company"]),
                form=str(row["form"]),
                filing_date=str(row["filing_date"]),
                query_type=query_type,
                chunk_text=str(row["chunk_text"]),
            )
            validated_sample = validate_generated_sample(
                sample,
                chunk_text=str(row["chunk_text"]),
                min_quality=min_quality,
            )
            if not validated_sample:
                continue

            question_key = normalize_text(validated_sample["question"]).lower()
            if question_key in seen_questions:
                continue

            record = build_output_record(row, query_type, validated_sample)
            seen_questions.add(question_key)
            records.append(record)
            type_counts[query_type] += 1
            company_form_type_counts[scope_key] += 1

        if len(records) >= limit:
            break

    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=48)
    parser.add_argument("--max-per-type", type=int, default=8)
    parser.add_argument("--min-quality", type=float, default=0.72)
    parser.add_argument("--output", default=OUTPUT_FILE)
    args = parser.parse_args()

    records = generate_dataset(
        limit=args.limit,
        max_per_type=args.max_per_type,
        min_quality=args.min_quality,
    )

    if not records:
        print("ERROR: No synthetic eval records were generated.")
        return 1

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Synthetic eval records created: {len(records)}")
    print(f"Saved to: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
