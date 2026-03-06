import json
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")


def inspect_filings():
    print(f"RAW_DIR: {RAW_DIR}")
    print(f"RAW_DIR exists: {os.path.isdir(RAW_DIR)}")

    if not os.path.isdir(RAW_DIR):
        print("Souborova slozka raw neexistuje.")
        return 1

    raw_files = sorted(
        file
        for file in os.listdir(RAW_DIR)
        if file.startswith("company_") and file.endswith(".json")
    )

    print(f"Found company JSON files: {len(raw_files)}")

    if not raw_files:
        print("Nebyly nalezeny zadne company_*.json soubory.")
        return 1

    records = []

    for file in raw_files:
        path = os.path.join(RAW_DIR, file)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        docs = filings.get("primaryDocument", [])

        for i in range(len(forms)):
            records.append({
                "cik": data.get("cik"),
                "company": data.get("name"),
                "form": forms[i] if i < len(forms) else None,
                "filing_date": dates[i] if i < len(dates) else None,
                "document": docs[i] if i < len(docs) else None,
            })

    df = pd.DataFrame(records)

    print("\n=== TVAR DATAFRAME ===")
    print(df.shape)

    print("\n=== SLOUPCE ===")
    print(df.columns.tolist())

    print("\n=== PRVNICH 5 RADKU ===")
    print(df.head())

    return 0


if __name__ == "__main__":
    raise SystemExit(inspect_filings())
