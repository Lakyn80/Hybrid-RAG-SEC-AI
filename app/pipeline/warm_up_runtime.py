import argparse
import json
import os
import sys
import time

import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.cache_admin import clear_answer_cache_file, clear_redis_prefixes
from app.core.cache_stats import get_cache_stats, reset_cache_stats

DEFAULT_DATASETS = [
    os.path.join(BASE_DIR, "tests", "eval_questions.json"),
    os.path.join(BASE_DIR, "tests", "rag_eval_questions.json"),
    os.path.join(BASE_DIR, "tests", "synthetic_eval_dataset.json"),
]
DEFAULT_REPORT_FILE = os.path.join(BASE_DIR, "tests", "warmup_report.json")
DEFAULT_DETAILS_FILE = os.path.join(BASE_DIR, "tests", "warmup_details.json")
DEFAULT_API_URL = "http://localhost:8021/api/ask"


def load_rows(dataset_paths: list[str], min_quality: float, limit: int | None) -> tuple[list[dict], dict]:
    stats = {
        "input_rows": 0,
        "eligible_rows": 0,
        "skipped_missing_file": 0,
        "skipped_low_quality": 0,
        "skipped_not_eligible": 0,
        "skipped_duplicate": 0,
    }
    rows = []
    seen = set()

    for dataset_path in dataset_paths:
        if not os.path.exists(dataset_path):
            stats["skipped_missing_file"] += 1
            continue

        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for row in data:
            stats["input_rows"] += 1

            query = row.get("query") or row.get("question")
            company = row.get("company")
            form = row.get("form")
            quality_score = row.get("quality_score")
            warmup_eligible = row.get("warmup_eligible")

            if quality_score is not None:
                try:
                    if float(quality_score) < min_quality:
                        stats["skipped_low_quality"] += 1
                        continue
                except Exception:
                    stats["skipped_low_quality"] += 1
                    continue

            if warmup_eligible is False:
                stats["skipped_not_eligible"] += 1
                continue

            key = (str(query), str(company), str(form))
            if key in seen:
                stats["skipped_duplicate"] += 1
                continue

            seen.add(key)
            rows.append(
                {
                    "query": query,
                    "company": company,
                    "form": form,
                    "dataset": dataset_path,
                }
            )
            stats["eligible_rows"] += 1

            if limit and len(rows) >= limit:
                return rows, stats

    return rows, stats


def run_pass(rows: list[dict], api_url: str, label: str) -> dict:
    details = []
    latencies = []
    cache_hits = 0
    llm_answers = 0
    fallback_answers = 0
    failures = 0

    for row in rows:
        payload = {"query": row["query"]}
        if row.get("company"):
            payload["company"] = row["company"]
        if row.get("form"):
            payload["form"] = row["form"]

        start = time.time()
        try:
            response = requests.post(api_url, json=payload, timeout=180)
            response.raise_for_status()
            result = response.json()
            status = "ok"
        except Exception as exc:
            latency_ms = round((time.time() - start) * 1000, 2)
            latencies.append(latency_ms)
            failures += 1
            details.append(
                {
                    "pass": label,
                    "query": row["query"],
                    "dataset": row["dataset"],
                    "latency_ms": latency_ms,
                    "status": "error",
                    "error": str(exc),
                }
            )
            continue

        latency_ms = round((time.time() - start) * 1000, 2)
        latencies.append(latency_ms)

        if result.get("cache_hit"):
            cache_hits += 1

        if result.get("mode") == "llm":
            llm_answers += 1
        elif result.get("mode") == "fallback":
            fallback_answers += 1

        details.append(
            {
                "pass": label,
                "query": row["query"],
                "dataset": row["dataset"],
                "latency_ms": latency_ms,
                "status": status,
                "mode": result.get("mode"),
                "cache_hit": bool(result.get("cache_hit")),
            }
        )

    return {
        "summary": {
            "pass": label,
            "total": len(rows),
            "failures": failures,
            "cache_hits": cache_hits,
            "llm_answers": llm_answers,
            "fallback_answers": fallback_answers,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "p95_latency_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2) if latencies else 0.0,
        },
        "details": details,
    }


def reset_all_stats() -> None:
    for namespace in ("retrieval_cache", "semantic_cache", "answer_cache"):
        reset_cache_stats(namespace)


def collect_all_stats() -> dict[str, dict[str, int]]:
    return {
        "retrieval_cache": get_cache_stats("retrieval_cache"),
        "semantic_cache": get_cache_stats("semantic_cache"),
        "answer_cache": get_cache_stats("answer_cache"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--min-quality", type=float, default=0.82)
    parser.add_argument("--verify-second-pass", action="store_true")
    parser.add_argument("--flush-cache-state", action="store_true")
    parser.add_argument("--report", default=DEFAULT_REPORT_FILE)
    parser.add_argument("--details", default=DEFAULT_DETAILS_FILE)
    args = parser.parse_args()

    dataset_paths = args.dataset or DEFAULT_DATASETS
    rows, row_stats = load_rows(dataset_paths, min_quality=args.min_quality, limit=args.limit)

    if not rows:
        print("ERROR: No eligible warm-up rows found.")
        return 1

    flush_summary = {
        "redis_keys_deleted": 0,
        "answer_cache_cleared": False,
    }
    if args.flush_cache_state:
        flush_summary["redis_keys_deleted"] = clear_redis_prefixes()
        flush_summary["answer_cache_cleared"] = clear_answer_cache_file(
            os.path.join(BASE_DIR, "data", "cache", "answer_cache.json")
        )

    reset_all_stats()
    cold_run = run_pass(rows, api_url=args.api_url, label="cold")
    cold_stats = collect_all_stats()

    runs = [
        {
            "summary": cold_run["summary"],
            "cache_stats": cold_stats,
        }
    ]
    details = list(cold_run["details"])

    if args.verify_second_pass:
        warm_run = run_pass(rows, api_url=args.api_url, label="warm")
        warm_stats = collect_all_stats()
        runs.append(
            {
                "summary": warm_run["summary"],
                "cache_stats": warm_stats,
            }
        )
        details.extend(warm_run["details"])

    report = {
        "datasets": dataset_paths,
        "row_stats": row_stats,
        "flush_summary": flush_summary,
        "runs": runs,
    }

    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(args.details), exist_ok=True)
    with open(args.details, "w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
