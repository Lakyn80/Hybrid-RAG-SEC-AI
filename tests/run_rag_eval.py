import json
import requests

API_URL = "http://localhost:8021/api/ask"

with open("tests/rag_eval_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

hit = 0
total = len(questions)

results = []

for q in questions:

    r = requests.post(API_URL, json={"query": q["query"]})
    data = r.json()

    sources = str(data.get("sources", ""))

    company_hit = q["company"] in sources
    form_hit = q["form"] in sources

    hit_result = company_hit and form_hit

    if hit_result:
        hit += 1

    results.append({
        "query": q["query"],
        "expected_company": q["company"],
        "expected_form": q["form"],
        "hit": hit_result
    })

summary = {
    "total_queries": total,
    "hit_at_k": hit / total
}

print("\nRAG RETRIEVAL EVALUATION\n")
print(json.dumps(summary, indent=2))

with open("tests/rag_eval_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "summary": summary,
        "results": results
    }, f, indent=2)

