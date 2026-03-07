import argparse
import json

import requests

API_URL = "http://localhost:8021/api/ask"
DEFAULT_DATASET = "tests/rag_eval_questions.json"
DEFAULT_OUTPUT = "tests/rag_eval_results.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    with open(args.dataset, "r", encoding="utf-8") as f:
        questions = json.load(f)

    hit = 0
    total = len(questions)
    results = []

    for row in questions:
        query = row.get("query") or row.get("question")
        expected_company = row.get("company")
        expected_form = row.get("form")

        r = requests.post(API_URL, json={"query": query})
        r.raise_for_status()
        data = r.json()

        sources = str(data.get("sources", ""))
        company_hit = expected_company in sources if expected_company else False
        form_hit = expected_form in sources if expected_form else False
        hit_result = company_hit and form_hit

        if hit_result:
            hit += 1

        results.append(
            {
                "query": query,
                "expected_company": expected_company,
                "expected_form": expected_form,
                "query_type": row.get("query_type"),
                "hit": hit_result,
            }
        )

    summary = {
        "dataset": args.dataset,
        "total_queries": total,
        "hit_at_k": (hit / total) if total else 0.0,
    }

    print("\nRAG RETRIEVAL EVALUATION\n")
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
