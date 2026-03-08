# Hybrid RAG SEC AI

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-production-green)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-purple)
![VectorDB](https://img.shields.io/badge/VectorDB-Qdrant-orange)
![Retrieval](https://img.shields.io/badge/Retrieval-Hybrid-red)
![LLM](https://img.shields.io/badge/LLM-DeepSeek-black)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Hybrid RAG SEC AI is a production-style Retrieval-Augmented Generation system for question answering over SEC filings.

It combines FastAPI, LangGraph orchestration, multi-layer caching, hybrid retrieval (Qdrant + BM25), CrossEncoder reranking, and DeepSeek LLM inference into a production-oriented RAG pipeline.

## Architecture

```text
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

## Highlights

- Production-style FastAPI API
- LangGraph orchestration
- Qdrant vector retrieval
- BM25 lexical retrieval
- Hybrid retrieval merge
- CrossEncoder reranking
- Exact answer cache
- Semantic cache
- Retrieval cache
- Synthetic evaluation dataset generation
- RAGAS evaluation pipeline
- Warm-up runtime tooling
- Load testing support

## Performance

Verified local results:

- Load test: 1000 requests
- Average latency: ~2.0 s
- Error rate: ~1.1%
- Hit@k: ~0.91
- Faithfulness: ~0.87
- Answer relevancy: ~0.84
- Warm cache latency: ~100 ms

## API Example

### Request

`POST /api/ask`

```json
{
  "query": "What legal risks did Apple mention in its 10-K filings?",
  "company": "Apple Inc.",
  "form": "10-K"
}
```

### Response

```json
{
  "query": "What legal risks did Apple mention in its 10-K filings?",
  "answer": "...",
  "mode": "llm",
  "sources": "Sources:\n- Apple Inc. | 10-K | ...",
  "cache_hit": false
}
```

## Project Goal

The system is built to answer questions over SEC filings such that responses:

- come from real filing chunks
- include traceable sources
- respect company/form scope
- can be measured through retrieval evaluation and RAGAS

Example queries:

- `What legal risks did Apple mention in its 10-K filings?`
- `What did NVIDIA disclose in its annual report?`
- `What governance topics did Apple discuss in its proxy statement?`

## Dataset Snapshot

Current verified local snapshot:

- Companies: 10,425
- Filing HTML documents: 360
- Parsed documents: 360
- Indexed chunks: 13,424
- Embedding model: `all-MiniLM-L6-v2`
- Active vector backend: `Qdrant`

Indexed companies include:

- Apple Inc.
- NVIDIA CORP
- Alphabet Inc.

Indexed filing types include:

- 10-K
- 10-Q
- 8-K
- DEF 14A
- DEFA14A
- SC 13G
- SC 13G/A

## Project Structure

```text
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

Important runtime modules:

- `app/services/answer_service.py`
- `app/services/semantic_cache.py`
- `app/retrieval/resources.py`
- `app/retrieval/retrieval_cache.py`
- `app/retrieval/qdrant_store.py`
- `app/retrieval/bm25_retriever.py`
- `app/retrieval/reranker.py`
- `app/llm/langchain_chain.py`

## Runtime Flow

The active runtime behind `/api/ask` works as follows:

1. FastAPI receives the query, optionally with `company` and `form`.
2. LangGraph prepares runtime state.
3. Exact answer cache lookup runs first.
4. Semantic cache lookup runs next.
5. Retrieval cache lookup runs next.
6. On cache miss, the system performs:
   - Qdrant vector retrieval
   - BM25 lexical retrieval
   - hybrid merge
   - CrossEncoder rerank
   - metadata filtering
   - deduplication
   - context limiting
7. Context is built from the final retrieval rows.
8. DeepSeek generates the answer.
9. Semantic cache and exact cache are updated when safe.

## Retrieval Layer

The active production vector backend is Qdrant with:

- cosine similarity
- persistent storage
- HNSW indexing
- payload metadata filters

The payload includes fields such as:

- `company`
- `company_norm`
- `form`
- `form_norm`
- `filing_date`
- `accession_number`
- `filing_url`
- `source_file`
- `html_title`
- `chunk_index`
- `chunk_text`
- `chunk_hash`
- `vector_id`

BM25 remains the lexical side of the hybrid retriever.

The reranker model is:

- `cross-encoder/ms-marco-MiniLM-L-6-v2`

## Cache Architecture

The system uses three cache layers.

### 1. Exact Answer Cache

File:

```text
data/cache/answer_cache.json
```

Stores:

- final answer
- mode
- sources
- timestamps
- LLM metadata

TTL:

- LLM answer: 24 hours
- fallback: 10 minutes

### 2. Retrieval Cache

Storage:

- Redis

Stores:

- final retrieval rows after merge, rerank, metadata filtering, deduplication, and limit

TTL:

- 24 hours

### 3. Semantic Cache

Storage:

- Redis

Stores:

- final answer
- final sources

Does not store:

- raw retrieval rows

TTL:

- 7 days

Safety rules:

- disabled if effective `company_filter` is missing
- disabled if effective `form_filter` is missing
- isolated by `index_version`, `company`, `form`, and `query_type`
- cosine similarity lookup
- token overlap safety guard

Current guards:

- similarity threshold: `0.82`
- top1/top2 margin: `0.015`
- token overlap ratio: `0.5`

## Environment Variables

Required:

```env
DEEPSEEK_API_KEY=your_key
```

Minimal `.env`:

```env
DEEPSEEK_API_KEY=your_key
LLM_MODEL=deepseek-chat
LLM_API_URL=https://api.deepseek.com/chat/completions
```

Optional:

```env
RAGAS_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAGAS_MAX_TOKENS=8192
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_ALIAS=sec_filings_chunks_current
```

## Running the System

### Docker

```bash
docker compose build
docker compose up -d
```

Endpoints:

- API: `http://localhost:8021`
- Swagger: `http://localhost:8021/docs`
- Qdrant: `http://localhost:6333`

### Local Python

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8021
```

## Offline Pipeline

Typical order:

```powershell
python app/ingestion/sec_ingest.py
python app/pipeline/data_cleaner.py
python app/pipeline/download_filing_html.py
python app/pipeline/parse_filing_html.py
python app/pipeline/chunk_filings.py
python app/pipeline/build_qdrant_index.py
```

## Evaluation Suite

Available scripts:

- `tests/run_eval.py`
- `tests/run_rag_eval.py`
- `tests/run_ragas_eval.py`
- `tests/run_retrieval_cache_eval.py`
- `tests/run_semantic_cache_eval.py`
- `tests/run_synthetic_dataset_check.py`
- `tests/run_warmup_validation.py`

Measured metrics include:

- latency
- retrieval quality
- faithfulness
- answer relevancy
- cache behavior

## Debugging Workflow

If something breaks:

1. check `.env`, especially `DEEPSEEK_API_KEY`
2. check `docker compose ps`
3. verify `data/vectorstore/runtime_manifest.json`
4. verify the Qdrant collection exists
5. run `python app/pipeline/answer_with_llm.py "..."`
6. run retrieval cache and semantic cache tests
7. inspect warm-up reports
8. inspect `data/cache/answer_cache.json`

## Summary

Hybrid RAG SEC AI is a modular production-style SEC filing QA system built with FastAPI, LangGraph, Qdrant + BM25 hybrid retrieval, multi-layer caching, DeepSeek LLM inference, and a complete evaluation pipeline.
