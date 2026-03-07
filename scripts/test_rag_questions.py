import json
import sys
from pathlib import Path

import requests

API_URL = "http://localhost:8021/api/ask"
QUESTIONS = [
    "What legal risks did Apple mention in its 10-K filings?",
    "Summarize the legal risk disclosures Apple reported in its 10-K filings.",
    "What types of legal proceedings does Apple say it may face according to its 10-K reports?",
    "What legal uncertainties are described in Apple’s annual reports?",
    "Which legal claims or litigation risks are mentioned in Apple’s filings?",
    "Describe the legal risk factors discussed by Apple in its 10-K reports.",
    "What legal liabilities could affect Apple based on its SEC filings?",
    "According to Apple’s 10-K documents, what legal issues could impact the company?",
    "What risks related to lawsuits or legal actions does Apple report in its filings?",
    "Explain the legal risks Apple highlights in its annual SEC reports.",
    "Which legal proceedings are referenced in Apple’s 10-K reports?",
    "What legal challenges could Apple face based on its filings?",
    "Summarize any litigation-related risks mentioned in Apple’s 10-K.",
    "What regulatory or legal compliance risks appear in Apple’s filings?",
    "What potential penalties or legal consequences does Apple warn about in its reports?",
    "What risks related to intellectual property litigation does Apple mention in its filings?",
    "Does Apple mention any legal disputes or claims in its 10-K reports?",
    "What uncertainties related to legal proceedings are described in Apple’s filings?",
    "What possible legal exposures does Apple disclose in its annual reports?",
    "Based on Apple’s 10-K filings, what legal risk factors should investors be aware of?",
]
BANNED_FORMS = ("10-Q", "8-K", "DEF 14A")


def evaluate_sources(sources_text: str) -> tuple[bool, list[str]]:
    sources = str(sources_text or "")
    problems = []

    if "| 10-K |" not in sources:
        problems.append("missing 10-K source")

    for banned_form in BANNED_FORMS:
        if f"| {banned_form} |" in sources:
            problems.append(f"contains {banned_form}")

    return not problems, problems


def main() -> int:
    failures = []
    results = []

    for index, question in enumerate(QUESTIONS, start=1):
        response = requests.post(API_URL, json={"query": question}, timeout=180)
        response.raise_for_status()
        data = response.json()

        ok, problems = evaluate_sources(data.get("sources", ""))
        result = {
            "index": index,
            "question": question,
            "mode": data.get("mode"),
            "cache_hit": bool(data.get("cache_hit")),
            "ok": ok,
            "problems": problems,
        }
        results.append(result)

        if not ok:
            failures.append(
                {
                    **result,
                    "sources": data.get("sources", ""),
                }
            )

    summary = {
        "total": len(QUESTIONS),
        "passed": len(QUESTIONS) - len(failures),
        "failed": len(failures),
        "all_only_10k": len(failures) == 0,
    }

    print("\nRAG QUESTION TEST\n")
    print(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))

    if failures:
        failure_report = Path("tests") / "rag_question_failures.json"
        failure_report.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
