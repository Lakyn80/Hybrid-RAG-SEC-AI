import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

DEFAULT_API_URL = "http://localhost:8021/api/ask"
DEFAULT_TIMEOUT = 180

EVAL_QUERIES = [
    {
        "query": "What legal risks did Apple mention in its 10-K filings?",
        "company": "Apple",
        "form": "10-K",
        "type": "risk",
    },
    {
        "query": "What legal risks did NVIDIA mention in its 10-K filings?",
        "company": "NVIDIA",
        "form": "10-K",
        "type": "risk",
    },
    {
        "query": "Summarize the risk factors described in Apple's annual report.",
        "company": "Apple",
        "form": "10-K",
        "type": "risk",
    },
    {
        "query": "What cybersecurity risks are described in NVIDIA filings?",
        "company": "NVIDIA",
        "form": None,
        "type": "risk",
    },
    {
        "query": "Compare the risk factors mentioned by Apple and NVIDIA.",
        "company": ["Apple", "NVIDIA"],
        "form": None,
        "type": "compare",
    },
    {
        "query": "What supply chain risks does Apple describe?",
        "company": "Apple",
        "form": None,
        "type": "risk",
    },
    {
        "query": "What regulatory risks does NVIDIA report?",
        "company": "NVIDIA",
        "form": None,
        "type": "risk",
    },
    {
        "query": "What risks related to global operations does Apple mention?",
        "company": "Apple",
        "form": None,
        "type": "risk",
    },
    {
        "query": "What risks are associated with product defects in Apple filings?",
        "company": "Apple",
        "form": None,
        "type": "risk",
    },
    {
        "query": "What legal proceedings are mentioned in NVIDIA filings?",
        "company": "NVIDIA",
        "form": None,
        "type": "legal",
    },
]

GROUNDING_KEYWORDS = {
    "risk",
    "litigation",
    "regulation",
    "regulatory",
    "supply",
    "competition",
    "cybersecurity",
    "legal",
    "proceedings",
    "operations",
    "product",
}

REJECT_PHRASES = (
    "the provided filings do not contain this information",
    "does not contain this information",
)


def normalize_company_values(company_field):
    if isinstance(company_field, list):
        return [str(value).strip() for value in company_field if str(value).strip()]
    if company_field:
        return [str(company_field).strip()]
    return []


def has_expected_company(answer_text: str, companies: list[str]) -> bool:
    answer_lower = answer_text.lower()
    return all(company.lower() in answer_lower for company in companies)


def has_grounding_signal(answer_text: str) -> bool:
    answer_lower = answer_text.lower()
    return any(keyword in answer_lower for keyword in GROUNDING_KEYWORDS)


def is_rejected_answer(answer_text: str) -> bool:
    answer_lower = answer_text.lower()
    return any(phrase in answer_lower for phrase in REJECT_PHRASES)


def evaluate_single_query(api_url: str, row: dict, timeout: int) -> dict:
    started = time.time()
    result = {
        "query": row["query"],
        "company": row["company"],
        "form": row["form"],
        "type": row["type"],
        "ok": False,
        "http_ok": False,
        "sources_present": False,
        "company_check": False,
        "grounding_check": False,
        "compare_check": True,
        "rejected_answer": False,
        "error": None,
        "duration_s": 0.0,
        "mode": None,
        "cache_hit": None,
    }

    try:
        response = requests.post(api_url, json={"query": row["query"]}, timeout=timeout)
        result["http_ok"] = response.ok
        response.raise_for_status()
        payload = response.json()

        answer = str(payload.get("answer", "") or "")
        sources = str(payload.get("sources", "") or "")
        companies = normalize_company_values(row.get("company"))

        result["mode"] = payload.get("mode")
        result["cache_hit"] = payload.get("cache_hit")
        result["sources_present"] = bool(sources.strip())
        result["company_check"] = has_expected_company(answer, companies) if companies else True
        result["grounding_check"] = has_grounding_signal(answer)
        result["rejected_answer"] = is_rejected_answer(answer)

        if row.get("type") == "compare":
            result["compare_check"] = has_expected_company(answer, companies)

        result["ok"] = (
            result["http_ok"]
            and result["sources_present"]
            and result["company_check"]
            and result["grounding_check"]
            and result["compare_check"]
            and not result["rejected_answer"]
        )
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        result["duration_s"] = round(time.time() - started, 2)

    return result


def run_eval(api_url: str, timeout: int, parallel: bool, workers: int) -> list[dict]:
    if not parallel:
        return [evaluate_single_query(api_url, row, timeout) for row in EVAL_QUERIES]

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(evaluate_single_query, api_url, row, timeout): row["query"]
            for row in EVAL_QUERIES
        }
        for future in as_completed(futures):
            results.append(future.result())

    query_order = {row["query"]: index for index, row in enumerate(EVAL_QUERIES)}
    results.sort(key=lambda row: query_order.get(row["query"], 9999))
    return results


def print_detailed_results(results: list[dict]) -> None:
    print("\nDETAILED RESULTS\n")
    for row in results:
        print(f"Query: {row['query']}")
        print(
            json.dumps(
                {
                    "ok": row["ok"],
                    "mode": row["mode"],
                    "cache_hit": row["cache_hit"],
                    "sources_present": row["sources_present"],
                    "company_check": row["company_check"],
                    "grounding_check": row["grounding_check"],
                    "compare_check": row["compare_check"],
                    "rejected_answer": row["rejected_answer"],
                    "duration_s": row["duration_s"],
                    "error": row["error"],
                },
                ensure_ascii=False,
            )
        )
        print("")


def print_summary(results: list[dict]) -> None:
    total_queries = len(results)
    successful_answers = sum(1 for row in results if row["ok"])
    failed_answers = total_queries - successful_answers
    empty_sources = sum(1 for row in results if not row["sources_present"])
    compare_failures = sum(1 for row in results if not row["compare_check"])
    grounding_failures = sum(1 for row in results if not row["grounding_check"])
    success_rate = (successful_answers / total_queries) if total_queries else 0.0

    print("\nRAG EVALUATION SUMMARY\n")
    print(f"Total queries: {total_queries}")
    print(f"Successful answers: {successful_answers}")
    print(f"Failures: {failed_answers}")
    print(f"Empty sources: {empty_sources}")
    print(f"Compare failures: {compare_failures}")
    print(f"Grounding failures: {grounding_failures}")
    print(f"Success rate: {success_rate:.0%}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    results = run_eval(
        api_url=args.api_url,
        timeout=args.timeout,
        parallel=args.parallel,
        workers=args.workers,
    )

    print_detailed_results(results)
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
