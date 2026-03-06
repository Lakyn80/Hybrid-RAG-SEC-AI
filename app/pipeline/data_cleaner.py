import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEAN_DIR = os.path.join(BASE_DIR, "data", "clean")

OUTPUT_FILE = os.path.join(CLEAN_DIR, "filings_clean.parquet")


def clean_filings():
    print(f"RAW_DIR: {RAW_DIR}")
    print(f"RAW_DIR exists: {os.path.isdir(RAW_DIR)}")

    if not os.path.isdir(RAW_DIR):
        print("ERROR: Raw data directory does not exist. Run ingestion first.")
        return 1

    raw_files = sorted(
        file
        for file in os.listdir(RAW_DIR)
        if file.startswith("company_") and file.endswith(".json")
    )

    print(f"Found company JSON files: {len(raw_files)}")

    if not raw_files:
        print("ERROR: No company_*.json files found in data/raw. Run ingestion first.")
        return 1

    records = []

    for file in raw_files:
        path = os.path.join(RAW_DIR, file)

        if os.path.getsize(path) == 0:
            print(f"Skipping empty file: {path}")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Skipping invalid JSON: {path} ({exc})")
            continue

        cik = data.get("cik")
        company = data.get("name")

        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        docs = filings.get("primaryDocument", [])
        accessions = filings.get("accessionNumber", [])

        max_len = max(len(forms), len(dates), len(docs), len(accessions))

        for i in range(max_len):
            record = {
                "cik": cik,
                "company": company,
                "form": forms[i] if i < len(forms) else None,
                "filing_date": dates[i] if i < len(dates) else None,
                "document": docs[i] if i < len(docs) else None,
                "accession_number": accessions[i] if i < len(accessions) else None,
            }
            records.append(record)

    df = pd.DataFrame(records)

    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    print("DataFrame head(5):")
    print(df.head())

    if df.empty:
        print("ERROR: No filing records were extracted from the raw JSON input.")
        return 1

    required_columns = ["cik", "form"]
    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        print(f"ERROR: Missing required columns: {missing_columns}")
        return 1

    df.dropna(subset=required_columns, inplace=True)

    if df.empty:
        print("ERROR: All extracted rows were removed because cik/form are missing.")
        return 1

    os.makedirs(CLEAN_DIR, exist_ok=True)
    df.to_parquet(OUTPUT_FILE, index=False)

    print("Clean dataset created")
    print("Rows:", len(df))
    print("Saved to:", OUTPUT_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(clean_filings())
