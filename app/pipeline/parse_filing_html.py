import os
import re
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, "data", "raw", "filings_html")
METADATA_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_text_html.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_parsed.parquet")


def extract_text_from_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()

    return title, text


def build_source_file_name(row: pd.Series) -> str:
    company = re.sub(r"[^a-z0-9]+", "_", str(row["company"]).strip().lower())
    company = re.sub(r"_+", "_", company).strip("_")

    form = re.sub(r"[^a-z0-9]+", "_", str(row["form"]).strip().lower())
    form = re.sub(r"_+", "_", form).strip("_")

    filing_date = str(row["filing_date"]).strip().replace("-", "_")

    accession_number = str(row["accession_number"]).strip().replace("-", "_")

    return f"{company}__{form}__{filing_date}__{accession_number}.html"


def parse_filings() -> int:
    print(f"INPUT_DIR: {INPUT_DIR}")
    print(f"METADATA_FILE: {METADATA_FILE}")
    print(f"OUTPUT_FILE: {OUTPUT_FILE}")

    if not os.path.isdir(INPUT_DIR):
        print("ERROR: filings_html directory does not exist.")
        return 1

    if not os.path.exists(METADATA_FILE):
        print("ERROR: filings_text_html.csv does not exist.")
        return 1

    df = pd.read_csv(METADATA_FILE)

    required_columns = [
        "company",
        "form",
        "filing_date",
        "accession_number",
        "filing_url",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        return 1

    records = []

    for index, row in df.iterrows():
        source_file = build_source_file_name(row)
        html_path = os.path.join(INPUT_DIR, source_file)

        if not os.path.exists(html_path):
            print(f"[{index}] SKIP MISSING FILE: {source_file}")
            continue

        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
        except Exception as exc:
            print(f"[{index}] ERROR READ: {source_file} -> {exc}")
            continue

        html_title, full_text = extract_text_from_html(html)

        records.append({
            "company": row["company"],
            "form": row["form"],
            "filing_date": row["filing_date"],
            "accession_number": row["accession_number"],
            "filing_url": row["filing_url"],
            "source_file": source_file,
            "html_title": html_title,
            "text_length": len(full_text),
            "full_text": full_text,
        })

    parsed_df = pd.DataFrame(records)

    print(f"Parsed DataFrame shape: {parsed_df.shape}")
    print(f"Parsed DataFrame columns: {parsed_df.columns.tolist()}")

    if parsed_df.empty:
        print("ERROR: No parsed records were created.")
        return 1

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    parsed_df.to_parquet(OUTPUT_FILE, index=False)

    print("Parsed dataset created")
    print("Rows:", len(parsed_df))
    print("Saved to:", OUTPUT_FILE)

    return 0


if __name__ == "__main__":
    raise SystemExit(parse_filings())
