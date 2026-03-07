import argparse
import json
import time

import requests

API_URL = "http://localhost:8021/api/ask"
DEFAULT_DATASET = "tests/eval_questions.json"
DEFAULT_OUTPUT = "tests/eval_results.json"


def p95(values: list[float]) -> float:
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = max(0, int(len(sorted_values) * 0.95) - 1)
    return sorted_values[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as f:
        questions = json.load(f)

    results = []
    latencies = []

    for row in questions:
        query = row.get("query") or row.get("question")
        start = time.time()

        r = requests.post(API_URL, json={"query": query})
        r.raise_for_status()
        data = r.json()

        latency = (time.time() - start) * 1000
        latencies.append(latency)

        result = {
            "query": query,
            "mode": data.get("mode"),
            "cache_hit": data.get("cache_hit"),
            "sources": data.get("sources", ""),
            "latency_ms": round(latency, 2),
        }

        results.append(result)

    summary = {
        "dataset": args.dataset,
        "total_queries": len(results),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "p95_latency_ms": round(p95(latencies), 2),
        "llm_answers": sum(1 for r in results if r["mode"] == "llm"),
        "fallback_answers": sum(1 for r in results if r["mode"] == "fallback"),
    }

    print("\nEVAL SUMMARY\n")
    print(json.dumps(summary, indent=2))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "results": results,
            },
            f,
            indent=2,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
