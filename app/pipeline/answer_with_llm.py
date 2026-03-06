import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.answer_service import answer_query, llm_api_key_present


def parse_optional_arg(prefix: str, args: list[str]) -> str | None:
    for arg in args:
        if arg.startswith(prefix):
            return arg[len(prefix):].strip()
    return None


def main() -> int:
    args = sys.argv[1:]

    company_filter = parse_optional_arg("--company=", args)
    form_filter = parse_optional_arg("--form=", args)

    query_parts = [
        arg for arg in args
        if not arg.startswith("--company=") and not arg.startswith("--form=")
    ]
    query = " ".join(query_parts).strip()

    if not query:
        print('Usage: python .\\app\\pipeline\\answer_with_llm.py "your query here" [--company=Apple Inc.] [--form=10-K]')
        return 1

    result = answer_query(
        query,
        company_filter=company_filter,
        form_filter=form_filter,
    )

    print(f"QUERY: {result['query']}")
    print(f"COMPANY_FILTER: {result['company_filter']}")
    print(f"FORM_FILTER: {result['form_filter']}")
    print(f"LLM_MODEL: {result['llm_model']}")
    print(f"LLM_API_KEY_PRESENT: {llm_api_key_present()}")

    if result["cache_hit"]:
        print(f"CACHE_MODE: {result['cache_mode']}")

    if result["retrieval_error"]:
        print(f"RETRIEVAL ERROR: {result['retrieval_error']}")
        return 1

    if result["llm_error"]:
        print(f"LLM ERROR: {result['llm_error']}")

    print(f"\n=== ANSWER ({result['mode'].upper()}) ===\n")
    print(result["answer"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
