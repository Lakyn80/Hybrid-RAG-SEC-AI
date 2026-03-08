```markdown
# Hybrid RAG SEC AI

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-production-green)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-purple)
![VectorDB](https://img.shields.io/badge/VectorDB-Qdrant-orange)
![Retrieval](https://img.shields.io/badge/Retrieval-Hybrid-red)
![LLM](https://img.shields.io/badge/LLM-DeepSeek-black)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

<<<<<<< HEAD
Hybrid RAG SEC AI is a **production-style Retrieval-Augmented Generation system** built for **question answering over SEC filings**.

The system combines:

- FastAPI API layer  
- LangGraph orchestration  
- multi-layer caching  
- hybrid retrieval (Qdrant + BM25)  
- CrossEncoder reranking  
- DeepSeek LLM inference  

The project is designed as a **production-ready RAG architecture**, not a toy demo.

Primary use cases:

- SEC filing question answering  
- retrieval debugging  
- faithfulness and retrieval quality evaluation  
- scalable architecture for large SEC datasets  

This README documents the **actual production state of the system as of 2026-03-07**.

---

# Architecture

```

User Query
↓
FastAPI
↓
LangGraph Orchestrator
↓
Cache Layer
├─ Exact Answer Cache
├─ Semantic Cache
└─ Retrieval Cache
↓
Hybrid Retrieval
├─ Qdrant Vector Search
└─ BM25 Lexical Search
↓
CrossEncoder Reranker
↓
Context Builder
↓
DeepSeek LLM
↓
Answer + Sources

```

Key design principles:
=======
Hybrid RAG SEC AI is a production-style Retrieval-Augmented Generation system built for question answering over SEC filings.

The system combines:

- FastAPI API layer
- LangGraph orchestration
- multi-layer caching
- hybrid retrieval (Qdrant + BM25)
- CrossEncoder reranking
- DeepSeek LLM inference

The project demonstrates a full production RAG pipeline including retrieval, reranking, caching, evaluation and load testing.

---

# Architecture

User Query  
↓  
FastAPI  
↓  
LangGraph Orchestrator  
↓  
Cache Layer  
• Exact Answer Cache  
• Semantic Cache  
• Retrieval Cache  
↓  
Hybrid Retrieval  
• Qdrant Vector Search  
• BM25 Lexical Search  
↓  
CrossEncoder Reranker  
↓  
Context Builder  
↓  
DeepSeek LLM  
↓  
Answer + Sources

Design principles:

- deterministic retrieval
- grounded answers
- traceable sources
- evaluation driven development

---

# Performance

Load test results (1000 requests)

Average latency: ~2.0 s  
p95 latency: ~12 s  
Error rate: ~1.1 %

Retrieval metrics

Hit@k: ~0.91

RAGAS metrics

Faithfulness: ~0.87  
Answer relevancy: ~0.84

Warm cache latency

~100 ms

---

# API Example

POST /api/ask
>>>>>>> 4c11a1b (Update README with full project documentation)

- deterministic retrieval
- strict context grounding
- multi-layer caching
- evaluation-first architecture

---

# Performance

Load test results (1000 requests)

```

Average latency: ~2.0 s
p95 latency: ~12 s
Error rate: ~1.1 %

```

Retrieval quality

```

Hit@k: ~0.91

```

RAGAS evaluation

```

Faithfulness: ~0.87
Answer relevancy: ~0.84

```

Warm cache latency

```

~100 ms

```

---

# API Example

### Request

```

POST /api/ask

````

{
"query": "What legal risks did Apple mention in its 10-K filings?",
"company": "Apple Inc.",
"form": "10-K"
}
<<<<<<< HEAD
````

### Response
=======

Response:
>>>>>>> 4c11a1b (Update README with full project documentation)

{
<<<<<<< HEAD
  "query": "...",
  "answer": "...",
  "mode": "llm",
  "sources": "Apple Inc. | 10-K | ...",
  "cache_hit": false
=======
"query": "...",
"answer": "...",
"mode": "llm",
"sources": "Apple Inc. | 10-K | ...",
"cache_hit": false
>>>>>>> 4c11a1b (Update README with full project documentation)
}

---

# Project Goal

<<<<<<< HEAD
The primary objective is answering questions over SEC filings such that answers:

* come strictly from filing text
* contain traceable sources
* respect company/form scope
* are measurable using retrieval evaluation and RAGAS

Example queries

```
What legal risks did Apple mention in its 10-K filings?
What did NVIDIA disclose in its annual report?
What governance topics did Apple discuss in its proxy statement?
```

---

# Production Runtime Architecture

The active runtime pipeline behind `/api/ask`:

* FastAPI endpoint (`app/main.py`)
* LangGraph orchestration (`app/services/answer_service.py`)
* query classification (`app/router/query_router.py`)
* exact answer cache
* semantic cache (Redis)
* retrieval cache (Redis)
* Qdrant vector retrieval
* BM25 lexical retrieval
* hybrid merge
* CrossEncoder reranker
* metadata filtering
* context builder
* DeepSeek LLM inference
* source formatting

Legacy utilities included but not active in runtime:

* FAISS utilities
* knowledge graph helpers
* entity extraction utilities

Qdrant is the **active production vector backend**.

---

# Verified Dataset Snapshot

Current verified local dataset snapshot:

```
companies.csv: 10,425 companies
filings_html: 360 filings
filings_clean.parquet: 3,011 rows
filings_parsed.parquet: 360 documents
filings_chunks.parquet: 13,424 chunks
```

Runtime manifest:

```
backend: qdrant
embedding_model: all-MiniLM-L6-v2
points_count: 13,424
```

Currently indexed companies:

* Apple Inc.
* NVIDIA CORP
* Alphabet Inc.

Indexed filing types:

```
10-K
10-Q
8-K
DEF 14A
DEFA14A
SC 13G
SC 13G/A
```

---

# Repository Structure

```
hybrid-rag/
├─ app/
│  ├─ main.py
│  ├─ core/
│  ├─ services/
│  ├─ retrieval/
│  ├─ llm/
│  ├─ router/
│  ├─ pipeline/
│  ├─ ingestion/
│  └─ graph/
├─ data/
├─ tests/
├─ docker-compose.yml
├─ requirements.txt
└─ README.md
```

Important runtime modules

```
answer_service.py
semantic_cache.py
qdrant_store.py
bm25_retriever.py
reranker.py
langchain_chain.py
```
=======
The system answers questions over SEC filings while ensuring:

- answers come strictly from filing text
- sources are traceable
- company/form scope is respected
- retrieval and answer quality are measurable

Example questions:

What legal risks did Apple mention in its 10-K filings?  
What did NVIDIA disclose in its annual report?  
What governance topics did Apple discuss in its proxy statement?

---

# Dataset Snapshot

Current indexed dataset:

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

---

# Project Structure

hybrid-rag/

app/  
 ├ main.py  
 ├ services/  
 ├ retrieval/  
 ├ llm/  
 ├ router/  
 ├ pipeline/  
 ├ ingestion/  
 └ graph/

data/  
tests/  
docker-compose.yml  
requirements.txt  
README.md

Important runtime modules:

answer_service.py  
semantic_cache.py  
qdrant_store.py  
bm25_retriever.py  
reranker.py  
langchain_chain.py
>>>>>>> 4c11a1b (Update README with full project documentation)

---

# Cache Architecture

<<<<<<< HEAD
The system uses **three cache layers**.

### Exact Answer Cache

```
data/cache/answer_cache.json
```

Stores final responses.

TTL

```
24 hours
```

---

### Retrieval Cache

Redis based cache storing retrieval results.

TTL

```
24 hours
```

---

### Semantic Cache

Redis based semantic similarity cache.

Safety guards

```
similarity threshold: 0.82
token overlap guard
company/form scope isolation
```

TTL

```
7 days
```
=======
Three cache layers are used.

Exact Answer Cache  
Stored in:

data/cache/answer_cache.json

TTL: 24 hours

Retrieval Cache  
Stored in Redis.  
Caches retrieval results.

TTL: 24 hours

Semantic Cache  
Stored in Redis.  
Caches answers using semantic similarity.

Safety rules:

similarity threshold 0.82  
token overlap guard  
company/form isolation

TTL: 7 days
>>>>>>> 4c11a1b (Update README with full project documentation)

---

# Environment Variables

<<<<<<< HEAD
Required

```
DEEPSEEK_API_KEY
```

Minimal `.env`

```
DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-chat
=======
Required:

DEEPSEEK_API_KEY

Minimal .env:

DEEPSEEK_API_KEY=your_key  
LLM_MODEL=deepseek-chat  
>>>>>>> 4c11a1b (Update README with full project documentation)
LLM_API_URL=https://api.deepseek.com/chat/completions

<<<<<<< HEAD
Optional

```
REDIS_URL
QDRANT_URL
RAGAS_EMBEDDING_MODEL
```
=======
Optional:

REDIS_URL  
QDRANT_URL  
RAGAS_EMBEDDING_MODEL
>>>>>>> 4c11a1b (Update README with full project documentation)

---

# Running the System
<<<<<<< HEAD

### Docker

```
docker compose build
=======

Docker

docker compose build  
>>>>>>> 4c11a1b (Update README with full project documentation)
docker compose up -d

<<<<<<< HEAD
Endpoints

```
API: http://localhost:8021
Swagger: http://localhost:8021/docs
Qdrant: http://localhost:6333
```

---

### Local Python

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
=======
Services

API  
http://localhost:8021

Swagger  
http://localhost:8021/docs

Qdrant  
http://localhost:6333

---

Local Python

python -m venv .venv  
.venv\Scripts\activate  
pip install -r requirements.txt  
>>>>>>> 4c11a1b (Update README with full project documentation)
uvicorn app.main:app --host 0.0.0.0 --port 8021

---

# Evaluation Suite

<<<<<<< HEAD
Evaluation scripts include

```
run_eval.py
run_rag_eval.py
run_ragas_eval.py
run_retrieval_cache_eval.py
run_semantic_cache_eval.py
run_synthetic_dataset_check.py
run_warmup_validation.py
```

Metrics measured

```
latency
retrieval accuracy
faithfulness
answer relevancy
cache performance
```

---

# Offline Data Pipeline

Typical ingestion pipeline

```
SEC ingest
→ HTML download
→ parsing
→ chunking
→ embeddings
→ Qdrant indexing
```

Scripts

```
sec_ingest.py
chunk_filings.py
build_qdrant_index.py
generate_synthetic_eval_dataset.py
warm_up_runtime.py
```

---

# Debugging Workflow

If something breaks:

1. verify `.env`
2. check Docker containers
3. verify runtime manifest
4. verify Qdrant collection
5. run `answer_with_llm.py`
6. run cache tests
7. check warmup reports

---

# Summary

Hybrid RAG SEC AI is a **production-oriented RAG architecture for financial document QA**, combining:

* FastAPI
* LangGraph orchestration
* hybrid retrieval
* multi-layer caching
* DeepSeek LLM inference
* full evaluation pipelines

```
```
=======
Evaluation scripts include:

run_eval.py  
run_rag_eval.py  
run_ragas_eval.py  
run_retrieval_cache_eval.py  
run_semantic_cache_eval.py  
run_synthetic_dataset_check.py  
run_warmup_validation.py

Measured metrics:

latency  
retrieval accuracy  
faithfulness  
answer relevancy  
cache performance

---

# Data Pipeline

SEC ingest  
HTML download  
parsing  
chunking  
embeddings  
Qdrant indexing

Important scripts:

sec_ingest.py  
chunk_filings.py  
build_qdrant_index.py  
generate_synthetic_eval_dataset.py  
warm_up_runtime.py

---

# Debugging Workflow

If something breaks:

1. check .env
2. check docker containers
3. verify runtime manifest
4. verify Qdrant collection
5. run answer_with_llm.py
6. run cache tests
7. check warmup reports

---

# Summary

Hybrid RAG SEC AI is a modular production RAG architecture for financial document QA combining:

FastAPI  
LangGraph orchestration  
hybrid retrieval  
multi-layer caching  
DeepSeek LLM inference  
evaluation pipelines
>>>>>>> 4c11a1b (Update README with full project documentation)
