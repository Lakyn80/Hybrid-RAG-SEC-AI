from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
CATALOG_PATH = ROOT / "frontend" / "lib" / "presetQuestionCatalog.json"
ANSWER_BANK_PATH = ROOT / "frontend" / "lib" / "presetAnswerBank.generated.json"
OUTPUT_PATH = ROOT / "frontend" / "lib" / "presetLocalization.generated.json"

load_dotenv(ENV_FILE)

DEEPSEEK_API_KEY = str(os.getenv("DEEPSEEK_API_KEY") or "").strip()
LLM_MODEL = str(os.getenv("LLM_MODEL") or "").strip() or "deepseek-chat"
LLM_API_BASE = "https://api.deepseek.com"


def clean_json_payload(payload: str) -> str:
    text = payload.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_first_json_object(payload: str) -> str:
    text = clean_json_payload(payload)
    start = text.find("{")
    if start < 0:
        return text

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return text


def build_llm() -> ChatOpenAI:
    if not DEEPSEEK_API_KEY:
        raise ValueError("Missing DEEPSEEK_API_KEY in environment.")

    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=LLM_API_BASE,
        temperature=0.0,
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_existing_entries() -> dict[str, dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}

    try:
        payload = load_json(OUTPUT_PATH)
    except Exception:  # noqa: BLE001
        return {}

    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return {}

    return {
        str(entry["id"]): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def translate_entry(llm: ChatOpenAI, item: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
You are translating preset content for a financial SEC filing analysis web app.

Return strict JSON only. No markdown fences. Keep the exact schema below.

Schema:
{{
  "query": {{"en": string, "cs": string, "ru": string}},
  "title": null | {{"en": string, "cs": string, "ru": string}},
  "description": null | {{"en": string, "cs": string, "ru": string}},
  "answer": null | {{"en": string, "cs": string, "ru": string}},
  "sources": null | {{"en": string, "cs": string, "ru": string}}
}}

Rules:
- Preserve meaning exactly. Do not add or remove facts.
- Preserve markdown structure, bullets, headings, URLs, company names, SEC form codes, Qdrant, BM25, LLM, run_id.
- Translate prose only.
- Preserve line breaks.
- For sources, translate labels like "Sources:" but keep URLs, company names, filing types, and dates intact.
- If a field is null, return null for that field.
- Russian must be fully natural Russian. Czech must be fully natural Czech. English must be fully natural English.

Input JSON:
{json.dumps(item, ensure_ascii=False)}
"""

    response = llm.invoke(prompt)
    return json.loads(extract_first_json_object(str(response.content)))


def translate_value_to_locale(
    llm: ChatOpenAI,
    *,
    field_name: str,
    value: str,
    target_locale: str,
) -> str:
    prompt = f"""
Translate the following financial web app field into {target_locale}.

Rules:
- Preserve meaning exactly.
- Preserve markdown, bullet markers, headings, URLs, company names, filing codes, and line breaks.
- Translate prose only.
- Return only the translated text. No JSON. No commentary. No code fences.

Field name: {field_name}
Text:
{value}
"""
    response = llm.invoke(prompt)
    return clean_json_payload(str(response.content))


def translate_field_bundle(
    llm: ChatOpenAI,
    *,
    field_name: str,
    value: str | None,
    source_locale: str,
) -> dict[str, str] | None:
    if value is None:
        return None

    translations = {"en": None, "cs": None, "ru": None}
    translations[source_locale] = value

    locale_labels = {
        "en": "English",
        "cs": "Czech",
        "ru": "Russian",
    }

    for target_locale, target_label in locale_labels.items():
        if translations[target_locale] is not None:
            continue
        translations[target_locale] = translate_value_to_locale(
            llm,
            field_name=field_name,
            value=value,
            target_locale=target_label,
        )

    return translations


def translate_entry_with_fallback(llm: ChatOpenAI, item: dict[str, Any]) -> dict[str, Any]:
    try:
        return translate_entry(llm, item)
    except Exception:
        source_locale = "cs" if item.get("kind") == "quick_audit" else "en"
        return {
            "query": translate_field_bundle(
                llm,
                field_name="query",
                value=item.get("query"),
                source_locale=source_locale,
            ),
            "title": translate_field_bundle(
                llm,
                field_name="title",
                value=item.get("title"),
                source_locale=source_locale,
            ),
            "description": translate_field_bundle(
                llm,
                field_name="description",
                value=item.get("description"),
                source_locale=source_locale,
            ),
            "answer": translate_field_bundle(
                llm,
                field_name="answer",
                value=item.get("answer"),
                source_locale=source_locale,
            ),
            "sources": translate_field_bundle(
                llm,
                field_name="sources",
                value=item.get("sources"),
                source_locale=source_locale,
            ),
        }


def main() -> int:
    catalog = load_json(CATALOG_PATH)
    answer_bank = load_json(ANSWER_BANK_PATH)
    answers_by_id = {
        entry["id"]: entry
        for entry in answer_bank.get("entries", [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }

    llm = build_llm()
    existing_entries = load_existing_entries()
    next_entries: list[dict[str, Any]] = []

    for index, catalog_item in enumerate(catalog, start=1):
        entry_id = str(catalog_item["id"])
        if entry_id in existing_entries:
            next_entries.append(existing_entries[entry_id])
            print(f"[skip] {index}/{len(catalog)} {entry_id}")
            continue

        answer_entry = answers_by_id.get(entry_id)
        payload = {
            "id": entry_id,
            "kind": catalog_item.get("kind"),
            "query": catalog_item.get("query"),
            "title": catalog_item.get("title"),
            "description": catalog_item.get("description"),
            "answer": answer_entry.get("answer") if answer_entry else None,
            "sources": answer_entry.get("sources") if answer_entry else None,
        }

        try:
            translated = translate_entry_with_fallback(llm, payload)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {entry_id} -> {exc}", file=sys.stderr)
            return 1

        next_entries.append(
            {
                "id": entry_id,
                "kind": catalog_item.get("kind"),
                "query": translated["query"],
                "title": translated.get("title"),
                "description": translated.get("description"),
                "answer": translated.get("answer"),
                "sources": translated.get("sources"),
            }
        )
        save_json(
            OUTPUT_PATH,
            {
                "version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "entries": next_entries,
            },
        )
        print(f"[ok] {index}/{len(catalog)} {entry_id}")
        time.sleep(0.2)

    save_json(
        OUTPUT_PATH,
        {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": next_entries,
        },
    )
    print(f"[done] wrote localized preset content to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
