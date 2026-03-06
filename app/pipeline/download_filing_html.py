import os
import re
import time
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "clean", "filings_text_html.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "raw", "filings_html")

HEADERS = {
    "User-Agent": "lukas@lukiora.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov",
}

REQUEST_DELAY_SECONDS = 0.3
REQUEST_TIMEOUT_SECONDS = 30


def safe_name(value: str) -> str:
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


def build_output_filename(row: pd.Series) -> str:
    company = safe_name(row.get("company", "unknown_company"))
    form = safe_name(row.get("form", "unknown_form"))
    filing_date = safe_name(row.get("filing_date", "unknown_date"))
    accession_number = safe_name(row.get("accession_number", "no_accession"))
    return f"{company}__{form}__{filing_date}__{accession_number}.html"


def download_filings() -> int:
    print(f"INPUT_FILE: {INPUT_FILE}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")

    if not os.path.exists(INPUT_FILE):
        print("ERROR: Input CSV does not exist. Run the previous filtering step first.")
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(INPUT_FILE)

    print(f"Rows in input CSV: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")

    required_columns = ["company", "form", "filing_date", "accession_number", "filing_url"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        return 1

    success_count = 0
    skip_count = 0
    error_count = 0

    session = requests.Session()
    session.headers.update(HEADERS)

    for index, row in df.iterrows():
        filing_url = str(row["filing_url"]).strip()

        if not filing_url:
            print(f"[{index}] SKIP: Empty filing_url")
            skip_count += 1
            continue

        output_filename = build_output_filename(row)
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        if os.path.exists(output_path):
            print(f"[{index}] SKIP EXISTS: {output_filename}")
            skip_count += 1
            continue

        try:
            response = session.get(
                filing_url,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(response.text)

            print(f"[{index}] SAVED: {output_filename}")
            success_count += 1

        except Exception as exc:
            print(f"[{index}] ERROR: {filing_url} -> {exc}")
            error_count += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    print("\nDownload finished.")
    print(f"Saved: {success_count}")
    print(f"Skipped: {skip_count}")
    print(f"Errors: {error_count}")
    print(f"Files directory: {OUTPUT_DIR}")

    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(download_filings())
