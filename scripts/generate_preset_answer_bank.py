from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "frontend" / "lib" / "presetQuestionCatalog.json"
OUTPUT_PATH = ROOT / "frontend" / "lib" / "presetAnswerBank.generated.json"
DEFAULT_BASE_URL = "http://localhost:8021"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate stored preset answers from the live /api/ask endpoint.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL. Default: http://localhost:8021",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=240,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="Delay between requests in seconds.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Ignore existing entries and regenerate the whole bank.",
    )
    return parser.parse_args()


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def load_existing_bank() -> dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {
            "version": 1,
            "generated_at": None,
            "backend_url": None,
            "entries": [],
        }

    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def save_bank(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def call_ask_api(base_url: str, query: str, timeout: int) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/ask"
    run_id = f"preset-{int(time.time() * 1000)}"
    body = json.dumps({"query": query}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Run-ID": run_id,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        header_run_id = response.headers.get("X-Run-ID")

    return {
        "query": payload["query"],
        "answer": payload["answer"],
        "sources": payload["sources"],
        "mode": payload.get("mode", "pipeline"),
        "cache_hit": bool(payload.get("cache_hit", False)),
        "run_id": header_run_id or run_id,
    }


def source_lines_with_label(sources: str, label: str | None = None) -> list[str]:
    lines: list[str] = []
    for raw_line in sources.splitlines():
        line = raw_line.strip()
        if not line or line.lower() == "sources:":
            continue

        if line.startswith("- "):
            line = line[2:]

        prefix = f"- {label} :: " if label else "- "
        lines.append(f"{prefix}{line}")

    return lines


def capture_entry(base_url: str, item: dict[str, Any], timeout: int) -> dict[str, Any]:
    composite_queries = item.get("compositeQueries")
    if isinstance(composite_queries, list) and composite_queries:
        sections: list[str] = []
        sources: list[str] = ["Sources:"]
        modes: list[str] = []
        cache_hits: list[bool] = []
        run_ids: list[str] = []

        for query_item in composite_queries:
            label = str(query_item.get("label") or "Preset").strip()
            query = str(query_item["query"]).strip()
            response = call_ask_api(base_url, query, timeout)
            sections.append(f"### {label}\n{response['answer'].strip()}")
            sources.extend(source_lines_with_label(response["sources"], label))
            modes.append(response["mode"])
            cache_hits.append(bool(response["cache_hit"]))
            run_ids.append(f"{label}:{response['run_id']}")

        return {
            "generation_query": None,
            "composite_queries": composite_queries,
            "answer": "\n\n".join(sections),
            "sources": "\n".join(sources),
            "mode": "llm" if "llm" in modes else (modes[0] if modes else "pipeline"),
            "cache_hit": all(cache_hits) if cache_hits else False,
            "run_id": " | ".join(run_ids),
        }

    generation_query = str(item.get("generationQuery") or item["query"]).strip()
    response = call_ask_api(base_url, generation_query, timeout)

    return {
        "generation_query": generation_query if generation_query != item["query"] else None,
        "composite_queries": None,
        "answer": response["answer"],
        "sources": response["sources"],
        "mode": response["mode"],
        "cache_hit": response["cache_hit"],
        "run_id": response["run_id"],
    }


def main() -> int:
    args = parse_args()
    catalog = load_catalog()
    bank = load_existing_bank()
    existing_entries = {
        entry["query"].strip().lower(): entry
        for entry in bank.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("query"), str)
    }
    next_entries: list[dict[str, Any]] = [] if args.overwrite else list(bank.get("entries", []))
    seen_queries = {
        entry["query"].strip().lower()
        for entry in next_entries
        if isinstance(entry, dict) and isinstance(entry.get("query"), str)
    }

    total = len(catalog)
    processed = 0

    for item in catalog:
        query = str(item["query"]).strip()
        normalized = query.lower()

        if not args.overwrite and normalized in existing_entries:
            processed += 1
            continue

        try:
            response = capture_entry(args.base_url, item, args.timeout)
        except urllib.error.HTTPError as exc:
            print(f"[error] {query} -> HTTP {exc.code}", file=sys.stderr)
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {query} -> {exc}", file=sys.stderr)
            return 1

        entry = {
            "id": item["id"],
            "query": query,
            "generation_query": response["generation_query"],
            "composite_queries": response["composite_queries"],
            "answer": response["answer"],
            "sources": response["sources"],
            "mode": response["mode"],
            "cache_hit": response["cache_hit"],
            "run_id": response["run_id"],
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }

        if normalized not in seen_queries:
            next_entries.append(entry)
            seen_queries.add(normalized)
        else:
            next_entries = [
                entry if existing.get("query", "").strip().lower() == normalized else existing
                for existing in next_entries
            ]

        processed += 1
        bank = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "backend_url": args.base_url,
            "entries": next_entries,
        }
        save_bank(bank)
        print(f"[ok] {processed}/{total} {query}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    bank = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend_url": args.base_url,
        "entries": next_entries,
    }
    save_bank(bank)
    print(f"[done] generated {len(next_entries)} preset answers into {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
