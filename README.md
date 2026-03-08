Hybrid RAG SEC AI














Hybrid RAG SEC AI is a production-style Retrieval-Augmented Generation system built for question answering over SEC filings.

The system combines:

FastAPI API layer

LangGraph orchestration

multi-layer caching

hybrid retrieval (Qdrant + BM25)

CrossEncoder reranking

DeepSeek LLM inference

The project demonstrates a real production RAG architecture, not a simple demo.

Architecture
User Query
   ↓
FastAPI
   ↓
LangGraph Orchestrator
   ↓
Cache Layer
   ├ Exact Answer Cache
   ├ Semantic Cache
   └ Retrieval Cache
   ↓
Hybrid Retrieval
   ├ Qdrant Vector Search
   └ BM25 Lexical Search
   ↓
CrossEncoder Reranker
   ↓
Context Builder
   ↓
DeepSeek LLM
   ↓
Answer + Sources

Key design goals:

deterministic retrieval

grounded answers

traceable sources

scalable architecture

Performance

Load test results:

Requests: 1000

Average latency: ~2.0 s

Error rate: ~1.1 %

Retrieval metrics

Hit@k: ~0.91

RAGAS evaluation

Faithfulness: ~0.87

Answer relevancy: ~0.84

Warm cache latency

~100 ms

API Example
Request

POST /api/ask

{
  "query": "What legal risks did Apple mention in its 10-K filings?",
  "company": "Apple Inc.",
  "form": "10-K"
}
Response
{
  "query": "...",
  "answer": "...",
  "mode": "llm",
  "sources": "Apple Inc. | 10-K | ...",
  "cache_hit": false
}
Dataset Snapshot

Current indexed dataset

Companies: 10,425

Filings parsed: 360

Chunks indexed: 13,424

Embedding model: all-MiniLM-L6-v2

Vector backend: Qdrant

Indexed companies include:

Apple Inc.

NVIDIA

Alphabet Inc.

Indexed filing types:

10-K

10-Q

8-K

DEF 14A

DEFA14A

SC 13G

SC 13G/A

Project Structure
hybrid-rag/
├ app/
│  ├ main.py
│  ├ services/
│  ├ retrieval/
│  ├ llm/
│  ├ router/
│  ├ pipeline/
│  ├ ingestion/
│  └ graph/
├ data/
├ tests/
├ docker-compose.yml
├ requirements.txt
└ README.md

Important modules:

answer_service.py

semantic_cache.py

qdrant_store.py

bm25_retriever.py

reranker.py

langchain_chain.py

Cache Architecture

Three cache layers are used.

Exact Answer Cache

File storage

data/cache/answer_cache.json

TTL

24 hours
Retrieval Cache

Stored in Redis

Caches retrieval results

TTL

24 hours
Semantic Cache

Stored in Redis

Caches answers using semantic similarity.

Safety rules:

similarity threshold 0.82

token overlap guard

company/form isolation

TTL

7 days
Environment Variables

Required

DEEPSEEK_API_KEY

Minimal .env

DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-chat
LLM_API_URL=https://api.deepseek.com/chat/completions

Optional

REDIS_URL
QDRANT_URL
RAGAS_EMBEDDING_MODEL
Running the System
Docker
docker compose build
docker compose up -d

Services

API
http://localhost:8021

Swagger
http://localhost:8021/docs

Qdrant
http://localhost:6333

Local Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8021
Evaluation Suite

Evaluation scripts

run_eval.py
run_rag_eval.py
run_ragas_eval.py
run_retrieval_cache_eval.py
run_semantic_cache_eval.py
run_warmup_validation.py

Measured metrics:

latency

retrieval accuracy

faithfulness

answer relevancy

cache performance

Data Pipeline

Pipeline flow

SEC ingest
→ HTML download
→ parsing
→ chunking
→ embeddings
→ Qdrant indexing

Important scripts

sec_ingest.py
chunk_filings.py
build_qdrant_index.py
generate_synthetic_eval_dataset.py
warm_up_runtime.py
Debugging Workflow

If something breaks

check .env

check Docker containers

verify runtime manifest

verify Qdrant collection

run answer_with_llm.py

run cache tests

check warmup reports

Summary

Hybrid RAG SEC AI is a modular production RAG architecture for financial document QA, combining

FastAPI

LangGraph orchestration

hybrid retrieval

multi-layer caching

DeepSeek LLM inference

evaluation pipelines
