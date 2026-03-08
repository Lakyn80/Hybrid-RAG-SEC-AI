# Hybrid RAG SEC AI - Development README

This document is the internal engineering log for the project.

Use it for:
- preserving the real development history
- handing project context to another GPT chat or engineer
- recording architectural decisions and why they were made
- appending future milestones without rewriting the whole story

This file is intentionally different from `README.md`.

- `README.md` is the presentation / project-facing document
- `README_DEV.md` is the development history and technical continuity document

## 1. Project Purpose

The project is a production-oriented Hybrid RAG system for question answering over SEC filings.

Core target:
- answer questions using filing text only
- keep answers grounded in retrieved evidence
- preserve source traceability
- support production-style caching, evaluation, and future scale

The system is not intended to be a toy demo. It is being developed as a modular architecture that can scale toward larger SEC datasets.

## 2. Current Runtime Snapshot

Current runtime flow:

```text
FastAPI
-> LangGraph orchestration
-> exact cache
-> semantic cache
-> retrieval cache
-> Qdrant vector retrieval
-> BM25 lexical retrieval
-> hybrid merge
-> CrossEncoder rerank
-> context builder
-> DeepSeek LLM
-> response
```

Current active production choices:
- vector backend: Qdrant
- lexical retrieval: BM25
- reranker: CrossEncoder
- LLM provider: DeepSeek
- secret policy: only `DEEPSEEK_API_KEY`
- API contract: preserved
- architecture style: modular, not collapsed

Current structure that must remain stable:

```text
app/services
app/retrieval
app/llm
app/pipeline
app/router
tests
```

## 3. Non-Negotiable Engineering Rules

These rules have been enforced during development and should continue to be enforced:

- do not refactor architecture for style
- do not collapse working modules together
- do not change API contract unless explicitly required
- do not introduce new secret names
- keep using only `DEEPSEEK_API_KEY`
- preserve LangGraph-based answer flow
- keep retrieval modular
- keep caching layered
- keep evaluation scripts working after each significant change

## 4. Development History

This section reconstructs the actual development path from the repository state and commit history.

### Phase 0 - Repository bootstrap

Commit anchor:
- `a1a03c7` - `Initialize public repo with FastAPI API and CI`

What happened:
- initial repository structure was created
- FastAPI entrypoint and base application layout were established
- CI/public repo baseline was introduced

Why it mattered:
- this created the stable base for later RAG work
- from the start the project was positioned as an application, not just a notebook or experiment

### Phase 1 - Baseline Hybrid RAG foundation

Commit anchor:
- `c8217b5` - `chore: checkpoint current hybrid rag state before production rollout`

What happened:
- ingestion pipeline was established
- SEC HTML download, parsing, cleaning, and chunking workflow were added
- baseline retrieval utilities were added
- FAISS-era utilities remained in the repo as legacy/offline tooling
- the project became a real end-to-end SEC filing QA system

Key modules that came out of this stage:
- `app/pipeline/download_filing_html.py`
- `app/pipeline/parse_filing_html.py`
- `app/pipeline/data_cleaner.py`
- `app/pipeline/chunk_filings.py`
- `app/pipeline/build_faiss_index.py`
- `app/pipeline/search_faiss.py`

Why it mattered:
- the project moved from skeleton state to working retrieval over filing chunks
- offline data processing became reproducible

### Phase 2 - Production retrieval architecture

Commit anchor:
- `d027133` - `feat: add production qdrant caching and eval tooling`

What happened:
- Qdrant became the active vector backend for runtime retrieval
- Redis retrieval cache was introduced
- semantic cache was introduced with safety boundaries
- exact answer cache remained in place
- hybrid retrieval was formalized as Qdrant + BM25 + rerank
- synthetic evaluation tooling and warm-up utilities were added

Key production modules introduced or stabilized:
- `app/retrieval/qdrant_store.py`
- `app/retrieval/retrieval_cache.py`
- `app/retrieval/resources.py`
- `app/services/semantic_cache.py`
- `app/pipeline/build_qdrant_index.py`
- `app/pipeline/generate_synthetic_eval_dataset.py`
- `app/pipeline/warm_up_runtime.py`
- `tests/run_retrieval_cache_eval.py`
- `tests/run_semantic_cache_eval.py`
- `tests/run_ragas_eval.py`
- `tests/run_synthetic_dataset_check.py`
- `tests/run_warmup_validation.py`

Important decisions made here:
- Qdrant is the long-term vector backend direction
- FAISS stays only as legacy/offline utility unless explicitly reactivated
- cache key boundaries must include company/form scope
- semantic cache must not be allowed to cross company/form boundaries

Why it mattered:
- this was the main productionization milestone
- the system gained persistence, layered caching, and evaluation-driven development

### Phase 3 - Grounding and retrieval safety hardening

Commit anchor:
- `a57588e` - `Improve grounding and SEC form handling`

What happened:
- answer prompt was tightened for grounded SEC QA
- context formatting was cleaned up to reduce noise
- final context was reduced to top 6 chunks
- answer post-processing was added to keep responses concise
- SEC form detection was corrected to trigger only on explicit form mentions
- aggressive heuristics such as forcing `10-K` from vague phrases were removed
- grounding regression tests were added

Files affected in this stage:
- `app/llm/langchain_chain.py`
- `app/router/query_router.py`
- `app/services/answer_service.py`
- `tests/test_answer_grounding.py`
- `tests/test_form_detection.py`

Why it mattered:
- retrieval correctness was protected from false form forcing
- answer quality improved without changing the architecture
- the system became safer for mixed-form queries

### Phase 4 - Performance stabilization

Commit anchor:
- `c9029da` - `Optimize RAG pipeline: reduce retrieval size, lower LLM concurrency, stabilize load test`

What happened:
- performance tuning focused on response stability and load behavior
- retrieval/LLM settings were adjusted to improve runtime behavior under load

Why it mattered:
- this stage shifted from correctness to operational stability
- it established the project as something testable under repeated traffic, not just single-query demos

### Phase 5 - Documentation pass

Commit anchors:
- `f9c7724` - `Revise README for production state and architecture details`
- `eecc5b6` - `Update README with full project documentation`

What happened:
- `README.md` was expanded into a project-facing explanation of architecture and usage
- operational and architecture details were documented for presentation and handoff

Why it mattered:
- the repo became easier to present externally
- the need for a second, development-focused README became obvious

### Phase 6 - Development continuity documentation

Current goal of this file:
- provide the missing internal development narrative
- capture the real sequence of decisions
- create a living place where future engineering milestones can be appended

## 5. Current Technical Map

### API and orchestration

- `app/main.py`
  - FastAPI entrypoint
- `app/services/answer_service.py`
  - main LangGraph runtime orchestration
  - prepare, retrieval, context build, LLM call, formatting
- `app/router/query_router.py`
  - query classification and explicit SEC form detection

### Retrieval

- `app/retrieval/qdrant_store.py`
  - Qdrant search and payload filtering
- `app/retrieval/bm25_retriever.py`
  - lexical retrieval
- `app/retrieval/reranker.py`
  - CrossEncoder reranking
- `app/retrieval/retrieval_cache.py`
  - Redis retrieval cache
- `app/retrieval/resources.py`
  - lazy-loaded shared retrieval resources

### LLM

- `app/llm/langchain_chain.py`
  - grounded answer generation prompt and LLM call setup
- `app/llm/synthetic_eval_chain.py`
  - synthetic evaluation generation support

### Offline pipeline

- `app/pipeline/download_filing_html.py`
- `app/pipeline/parse_filing_html.py`
- `app/pipeline/data_cleaner.py`
- `app/pipeline/chunk_filings.py`
- `app/pipeline/build_qdrant_index.py`
- `app/pipeline/generate_synthetic_eval_dataset.py`
- `app/pipeline/warm_up_runtime.py`

### Caching

- exact answer cache:
  - `data/cache/answer_cache.json`
- retrieval cache:
  - Redis
- semantic cache:
  - Redis with scope isolation

### Tests and validation

- `tests/run_rag_eval.py`
- `tests/run_ragas_eval.py`
- `tests/run_retrieval_cache_eval.py`
- `tests/run_semantic_cache_eval.py`
- `tests/run_synthetic_dataset_check.py`
- `tests/run_warmup_validation.py`
- `tests/test_answer_grounding.py`
- `tests/test_form_detection.py`

## 6. Important Design Decisions and Why

### Qdrant was chosen as the final vector backend

Reason:
- production persistence
- payload metadata filtering
- better long-term direction than continuing to optimize runtime FAISS for large scale

Impact:
- vector retrieval is now production-oriented
- runtime filtering can be enforced server-side

### BM25 was preserved

Reason:
- lexical retrieval still matters for SEC terminology, form names, legal wording, and exact filings language

Impact:
- hybrid retrieval remains more robust than pure vector search

### Layered caching was kept

Order:
- exact answer cache
- semantic cache
- retrieval cache

Reason:
- different cache layers solve different latency/cost problems
- semantic cache can accelerate paraphrases
- retrieval cache avoids repeated retrieval work

### Semantic cache safety was intentionally strict

Rules:
- disabled if effective company filter is missing
- disabled if effective form filter is missing

Reason:
- this prevents cross-company and cross-form contamination
- this matters especially for SEC retrieval, where incorrect entity or form scope is a serious answer-quality failure

### Form filter inference was narrowed to explicit mentions only

Reason:
- heuristic mapping such as `annual report -> 10-K` caused false restriction of retrieval
- broad financial questions often need cross-form retrieval unless the user explicitly names a filing form

Impact:
- retrieval is safer across mixed query styles

### Prompt and context shaping are used before larger architectural changes

Reason:
- answer quality can often improve significantly without destabilizing retrieval or cache layers

Impact:
- better faithfulness and answer relevancy without touching API or runtime contracts

## 7. Current Verified Baseline

Latest verified local baseline from the current development cycle:

- retrieval evaluation: `hit_at_k = 1.0`
- RAGAS faithfulness: `0.8256`
- RAGAS answer relevancy: `0.7669`
- retrieval cache eval:
  - first run miss
  - second run hit
  - latency improved from roughly `13165 ms` to `1.41 ms`
- semantic cache eval:
  - seed query served by LLM
  - paraphrase hit from semantic cache
  - missing-filter case did not use semantic cache
  - wrong-scope case did not use semantic cache

Interpretation:
- retrieval is stable
- answer relevancy is in a good range
- faithfulness improved but still remains an area for future hardening

## 8. Known Constraints

- API schema must remain stable unless there is an explicit product decision
- `DEEPSEEK_API_KEY` is the only allowed LLM secret
- Docker stack should not be changed casually
- cache logic must not be weakened in ways that break scope safety
- retrieval correctness is more important than overly aggressive heuristics
- README for presentation and README for development must stay separate

## 9. How to Use This File in Future Chats

When handing this project to another GPT chat, provide:
- `README.md`
- `README_DEV.md`
- the current task
- any exact constraints for the next change

This file is especially useful for telling the next agent:
- what has already been tried
- what architectural decisions are fixed
- what must not be broken
- which metrics matter

## 10. How to Append New Development Steps

Use append-only updates whenever possible.

Recommended entry template:

```text
## YYYY-MM-DD - Short milestone title

Goal
- what was being fixed or added

Changes
- what changed technically
- which modules were touched

Reason
- why the change was needed

Validation
- tests run
- metrics observed

Risks / open issues
- what still needs attention

Next step
- the most likely next engineering action
```

## 11. Next Append Section

Add all future milestones below this line.

## 2026-03-08 - Placeholder for next development milestone

Goal
- pending

Changes
- pending

Reason
- pending

Validation
- pending

Risks / open issues
- pending

Next step
- pending
