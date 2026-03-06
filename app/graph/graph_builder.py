import os
import pandas as pd
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

COMPANIES_FILE = os.path.join(DATA_DIR, "companies.csv")
GRAPH_FILE = os.path.join(DATA_DIR, "company_graph.gml")


def build_company_graph():

    df = pd.read_csv(COMPANIES_FILE)

    G = nx.Graph()

    for _, row in df.iterrows():
        company = row["name"]
        ticker = row["ticker"]

        G.add_node(company, ticker=ticker)

    nx.write_gml(G, GRAPH_FILE)

    print("Graph created")
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())


if __name__ == "__main__":
    build_company_graph()
