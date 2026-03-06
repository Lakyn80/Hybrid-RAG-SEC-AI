import os
import json
import pandas as pd
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

GRAPH_FILE = os.path.join(DATA_DIR, "company_graph.gml")
COMPANIES_FILE = os.path.join(DATA_DIR, "companies.csv")


def load_graph():
    return nx.read_gml(GRAPH_FILE)


def save_graph(G):
    nx.write_gml(G, GRAPH_FILE)


def extract_relationships():

    companies = pd.read_csv(COMPANIES_FILE)
    company_names = set(companies["name"].str.lower())

    G = load_graph()

    if not os.path.isdir(RAW_DIR):
        print(f"Raw data directory not found: {RAW_DIR}")
        return

    for file in os.listdir(RAW_DIR):

        if not file.startswith("company_") or not file.endswith(".json"):
            continue

        path = os.path.join(RAW_DIR, file)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        company_name = data.get("name", "").lower()

        filings = data.get("filings", {}).get("recent", {})

        forms = filings.get("form", [])

        for form in forms:

            text = str(form).lower()

            for other_company in company_names:

                if other_company == company_name:
                    continue

                if other_company in text:

                    if not G.has_edge(company_name, other_company):

                        G.add_edge(company_name, other_company, relation="co-mentioned")

    save_graph(G)

    print("Updated graph")
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())


if __name__ == "__main__":
    extract_relationships()
