import re

def classify_query(query: str) -> str:
    q = query.lower()

    risk_words = ["risk", "risks", "uncertainty", "adverse"]
    financial_words = ["revenue", "income", "profit", "earnings", "financial"]
    compare_words = ["compare", "difference", "versus", "vs"]

    if any(w in q for w in compare_words):
        return "compare"

    if any(w in q for w in financial_words):
        return "financial"

    if any(w in q for w in risk_words):
        return "risk"

    return "general"
