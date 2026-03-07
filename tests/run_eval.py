import json
import time
import requests

API_URL = "http://localhost:8021/api/ask"

with open("tests/eval_questions.json", "r", encoding="utf-8") as f:
    questions = json.load(f)

results = []
latencies = []

for q in questions:
    start = time.time()

    r = requests.post(API_URL, json={"query": q["query"]})
    data = r.json()

    latency = (time.time() - start) * 1000
    latencies.append(latency)

    result = {
        "query": q["query"],
        "mode": data.get("mode"),
        "cache_hit": data.get("cache_hit"),
        "sources": data.get("sources", "")
    }

    results.append(result)

summary = {
    "total_queries": len(results),
    "avg_latency_ms": sum(latencies) / len(latencies),
    "llm_answers": sum(1 for r in results if r["mode"] == "llm"),
    "fallback_answers": sum(1 for r in results if r["mode"] == "fallback")
}

print("\nEVAL SUMMARY\n")
print(json.dumps(summary, indent=2))

with open("tests/eval_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "summary": summary,
        "results": results
    }, f, indent=2)
