import json
import os
import requests
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "lukas@lukiora.com"
}

CIK_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"

def download_company_list():
    resp = requests.get(CIK_TICKER_URL, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    records = []
    for _, item in data.items():
        records.append({
            "cik": str(item["cik_str"]).zfill(10),
            "ticker": item["ticker"],
            "name": item["title"]
        })

    df = pd.DataFrame(records)
    path = os.path.join(DATA_DIR, "companies.csv")
    df.to_csv(path, index=False)

    print(f"Saved {len(df)} companies to {path}")
    return df

def download_company_filings(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    data = resp.json()

    path = os.path.join(RAW_DIR, f"company_{cik}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Saved filings for {cik} to {path}")

if __name__ == "__main__":
    df = download_company_list()

    for cik in df["cik"].head(3):
        download_company_filings(cik)
