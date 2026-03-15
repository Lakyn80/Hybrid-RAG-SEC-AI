# Hybrid RAG SEC AI - Development README

This document is the internal engineering reference for the project.

Use it for:
- preserving the real technical state of the system
- handing the project to another engineer or GPT chat
- recording architectural decisions and why they were made
- keeping operational context separate from the presentation-facing `README.md`

This file is intentionally different from `README.md`.

- `README.md` = product / presentation document
- `README_DEV.md` = engineering continuity, runtime truth, operational notes

## 1. Project Identity

Project name:
- `Hybrid RAG SEC AI`

Purpose:
- answer questions over SEC filings using Retrieval-Augmented Generation
- keep answers grounded in filing text
- keep source traceability
- support production-oriented runtime behavior, caching, evaluation, observability, and deployment

This is not a notebook experiment or toy demo. It is a modular production-style RAG system.

## 2. Current High-Level Architecture

Backend:
- FastAPI
- LangGraph orchestration
- Qdrant vector retrieval
- BM25 lexical retrieval
- CrossEncoder reranking
- DeepSeek LLM via OpenAI-compatible API
- Redis for shared cache, shared stream state, shared concurrency coordination

Frontend:
- Next.js App Router
- React
- TailwindCSS
- live execution view
- execution log
- answer panel
- query history
- suggested questions
- lightweight telemetry display after answer completion

Infrastructure:
- Docker / Docker Compose
- Redis
- Qdrant
- GitHub Actions CI/CD
- Nginx / domain routing in deployment environment

## 3. Current Runtime Flow

Current answer flow:

```text
POST /api/ask
-> FastAPI
-> answer_service.answer_query()
-> query routing
-> exact answer cache lookup
-> semantic cache lookup
-> hybrid retrieval (Qdrant + BM25)
-> rerank
-> context build
-> query guard
-> DeepSeek LLM
-> response formatting
-> cache write
-> response
```

Live execution flow:

```text
Frontend generates run_id
-> opens /api/stream?run_id=...
-> sends POST /api/ask with X-Run-ID
-> backend publishes pipeline events under run_id
-> Redis stream + Pub/Sub carry events
-> frontend updates execution log and pipeline view
```

Important:
- `/api/ask` response schema stays stable:
  - `query`
  - `answer`
  - `mode`
  - `sources`
  - `cache_hit`
- `run_id` is carried via `X-Run-ID` header, not in the public JSON response contract

## 4. Stable Module Structure

This structure is intentionally preserved:

```text
app/services
app/retrieval
app/llm
app/pipeline
app/router
app/api
tests
frontend
```

Engineering rule:
- do not collapse modules together
- do not refactor architecture for style
- do not change API contracts casually

## 5. What the System Is Designed to Answer

The system is designed to answer filing-based questions about indexed SEC documents.

Primary supported domains:
- risk factors
- legal proceedings
- litigation
- regulatory risks
- governance
- board / proxy topics
- executive compensation
- financial results
- revenue / profitability / liquidity
- cybersecurity risks
- supply chain risks
- global operations risks
- product defect risks
- acquisition / transaction related disclosures

Primary indexed company scope at the current stage:
- Apple
- NVIDIA
- Alphabet

Primary filing forms handled:
- `10-K`
- `10-Q`
- `8-K`
- `DEF 14A`
- `DEFA14A`
- `SC 13G`
- `SC 13G/A`

SEC form synonyms currently supported in query routing:
- `annual report` -> `10-K`
- `quarterly report` -> `10-Q`
- `proxy statement` -> `DEF 14A`
- `current report` -> `8-K`

## 6. Data Layer and Storage

The project already uses Parquet for core SEC datasets.

Important data artifacts:
- `data/clean/filings_clean.parquet`
- `data/clean/filings_parsed.parquet`
- `data/clean/filings_chunks.parquet`
- `data/vectorstore/faiss/filings_chunks_metadata.parquet`

Supporting small lookup data may still exist as CSV, for example:
- `data/companies.csv`

Design rule:
- large analytical / runtime datasets should live in Parquet
- small helper or lookup tables may remain CSV if there is no runtime penalty

## 7. Retrieval Architecture

Current active retrieval design:
- vector retrieval from Qdrant
- lexical retrieval from BM25
- hybrid candidate merge
- CrossEncoder rerank
- blended final ranking policy
- context diversity selection before answer generation

Important runtime modules:
- `app/retrieval/qdrant_store.py`
- `app/retrieval/bm25_retriever.py`
- `app/retrieval/reranker.py`
- `app/retrieval/resources.py`
- `app/services/answer_service.py`

Important production design decisions:
- Qdrant is the active production vector backend
- BM25 remains because SEC questions benefit from lexical matching
- reranker is not treated as the sole signal anymore
- final ranking uses blended scoring to reduce boilerplate dominance

## 8. Query Routing and Decomposition

Current routing behavior:
- single-company queries run normally
- multi-company compare queries are decomposed into company-specific subqueries
- subqueries run through the existing answer pipeline independently
- outputs are aggregated into one answer string without changing API schema

Current routing modules:
- `app/router/query_router.py`
- `app/services/answer_service.py`

Important routing behavior:
- compare queries can split into Apple / NVIDIA / Alphabet subqueries if multiple supported companies are detected
- explicit SEC form detection takes precedence
- synonym mapping is used if the user names a filing by natural-language label
- if no form is explicit or inferable by synonym, retrieval can search across all forms

## 9. Query Guard

The system now has a frontend prompt guidance layer and a backend query guard.

Frontend:
- encourages document-domain questions only
- warns on obvious off-domain prompts
- does not block submission

Backend:
- `app/services/query_guard.py`
- inserted after `context build` and before `LLM generation`
- blocks obviously irrelevant questions before tokens are spent

Blocked response behavior:
- answer: `This system answers questions only about SEC filings and company disclosures.`
- sources: `Sources:\n- query_guard`

This preserves API response shape while preventing wasted LLM calls.

## 10. Caching and Shared State

Current cache layers:

1. Exact answer cache
- Redis
- key pattern:
  - `answer:v1:{cache_key}`
- TTL:
  - `86400`

2. Semantic cache
- Redis
- strict scope isolation by company/form/query scope

3. Retrieval cache
- Redis
- keyed by query + filters + index version + ranking version

Important runtime principle:
- worker-shared state must not live only in one process
- request-relevant shared state uses Redis

Current worker-safe state moved out of process:
- exact answer cache
- retrieval cache
- semantic cache
- live stream event history
- live stream Pub/Sub channel
- global LLM concurrency limiter
- BM25 index version invalidation signal

## 11. Streaming and Multi-Worker Safety

The streaming system was upgraded specifically for multi-worker deployment.

Current design:
- frontend generates or carries a `run_id`
- `run_id` goes into:
  - `X-Run-ID` header for `/api/ask`
  - `run_id` query param for `/api/stream`
- backend publishes events under:
  - `pipeline_stream:{run_id}`
- event history is persisted under:
  - `pipeline_run:{run_id}`

Why this matters:
- two identical queries from different users no longer share a stream
- reconnect can replay event history
- subquery events for multi-company compare go into the same parent run
- behavior is safe under Gunicorn multi-worker deployment

Core files:
- `app/services/stream_service.py`
- `app/router/stream_router.py`
- `frontend/hooks/useEventStream.ts`
- `frontend/lib/streamClient.ts`
- `frontend/hooks/useAskPipeline.ts`

## 12. LLM Layer

Current LLM runtime:
- model provider secret: `DEEPSEEK_API_KEY`
- provider access through OpenAI-compatible endpoint
- no extra secret names are allowed
- prompt is tuned for strict grounding

Core file:
- `app/llm/langchain_chain.py`

Current answer style design:
- human-readable analyst summary
- concise
- grounded in context
- no external knowledge
- no invented facts
- no excerpt numbers in final user-facing answer

Current concurrency control:
- Redis-based distributed limiter
- shared across workers
- prevents per-process-only concurrency bugs

## 13. Monitoring / Observability Mindset

Yes, this is now part of the project and it should stay part of the project.

The intended mindset is:
- trace every request
- correlate retrieval and LLM behavior
- observe latency and token usage
- make debugging possible from logs without guessing

### Current observability capabilities

Every request is expected to have a `run_id`.

Current structured telemetry covers:
- pipeline step progression
- retrieval candidates
- rerank output
- final retrieval result
- built context
- LLM call metrics
- generated response summary
- LLM errors
- query guard blocks

Important structured log events currently emitted:
- `pipeline_step`
- `request_received`
- `retrieval_candidates`
- `rerank_result`
- `retrieval_result`
- `context_built`
- `llm_call`
- `response_generated`
- `llm_error`
- `QUERY_BLOCKED_BY_GUARD`
- `question_bank_static`

### What is logged for LLM calls

Current telemetry fields include:
- `run_id`
- `query`
- `model`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- fallback `prompt_length`
- `response_length`
- `latency_ms`
- `retrieved_documents`
- `error` if the call fails

### What is logged for retrieval

Current retrieval trace includes:
- `run_id`
- `query`
- `top_k`
- `retrieved_document_ids`
- `rerank_scores`
- `final_scores`
- latency for rerank / retrieval stages

### Practical observability workflow

When debugging:
- check `run_id`
- inspect `retrieval_candidates`
- inspect `rerank_result`
- inspect `retrieval_result`
- inspect `llm_call`
- inspect `response_generated`

This is the current production observability pattern.

### What we do NOT yet have

The project currently has:
- strong structured logs
- request traceability
- stream event traceability

The project does not yet have a full metrics stack such as:
- Prometheus
- Grafana
- OpenTelemetry collector pipeline

That is acceptable for the current stage, but the logging/traceability mindset is already established and should not be removed.

## 14. Frontend Runtime Behavior

Frontend lives in:
- `frontend/`

Key UI features:
- prompt panel
- quick audit cards
- suggested questions
- query history with replayable local snapshot state
- pipeline view
- execution log
- answer block
- small LLM run info panel under the answer

Important frontend behavior:
- query history stores snapshots locally and can reopen them without rerunning backend
- `Run again` triggers a fresh backend request
- `Delete cache` calls backend cache clear
- `Refresh` button is intentionally just a hard page reload helper
- suggested questions are fixed curated questions, not LLM-generated
- the visible suggested list is now pinned to the first 20 questions from `frontend/lib/presetQuestionCatalog.json`
- quick audit cards and suggested questions can resolve to a stored preset answer bank before the LLM step
- if a query exists in the preset catalog and also in `frontend/lib/presetAnswerBank.generated.json`, frontend replays the pipeline UI locally and injects the stored answer without calling `/api/ask`
- preset replay intentionally stops before `LLM` in the UI while still rendering the final answer panel

Important frontend files:
- `frontend/components/Dashboard.tsx`
- `frontend/components/PromptPanel.tsx`
- `frontend/components/QueryHistory.tsx`
- `frontend/components/ExecutionLog.tsx`
- `frontend/components/PipelineVisualizer.tsx`
- `frontend/components/AnswerResult.tsx`
- `frontend/components/SuggestedQuestions.tsx`
- `frontend/hooks/useAskPipeline.ts`
- `frontend/lib/api.ts`
- `frontend/lib/presetCatalog.ts`
- `frontend/lib/presetQuestionCatalog.json`
- `frontend/lib/presetAnswerBank.ts`
- `frontend/lib/presetAnswerBank.generated.json`

## 15. Question Bank

Question bank used in frontend suggestions:
- is static and curated
- is not generated by LLM at request time
- is designed to stay inside supported indexed company scope
- has a pinned frontend subset used for deterministic offline replay

Relevant files:
- `app/data/question_bank.py`
- `app/services/question_bank_service.py`
- `app/api/question_bank.py`
- `frontend/lib/presetQuestionCatalog.json`
- `scripts/generate_preset_answer_bank.py`
- `frontend/lib/presetAnswerBank.generated.json`

Reason:
- no latency spike
- no suggestion / guard mismatch
- no off-domain or unsupported-company suggestions

Preset answer bank workflow:
- run `python scripts/generate_preset_answer_bank.py --base-url http://localhost:8021 --overwrite`
- the script calls live `/api/ask` for all entries in `frontend/lib/presetQuestionCatalog.json`
- quick audit entries may define an optional `generationQuery` or `compositeQueries`; the generator uses them for capture quality but still stores the result under the visible UI `query`
- answers and sources are persisted to `frontend/lib/presetAnswerBank.generated.json`
- frontend can then replay those questions without spending more LLM tokens

## 16. Deployment and Bootstrap

Current deployment style:
- GitHub Actions CI
- GitHub Actions CD
- deploy to VPS via SSH
- Docker Compose restart/build on target server

Important files:
- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `docker-compose.yml`

Important current deployment behavior:
- `rag-api` starts through:
  - `python app/scripts/bootstrap_qdrant.py && gunicorn ...`
- deploy workflow also explicitly runs:
  - `docker compose exec -T rag-api python app/scripts/bootstrap_qdrant.py`

Why this matters:
- if Qdrant collection is missing after deploy, bootstrap runs automatically
- manual recovery after deploy should not be needed just to rebuild the index

Qdrant bootstrap file:
- `app/scripts/bootstrap_qdrant.py`

Qdrant persistence:
- Docker volume:
  - `qdrant_data:/qdrant/storage`

## 17. Evaluation and Test Tooling

Current test and evaluation surface includes:
- retrieval eval
- RAGAS eval
- retrieval cache eval
- semantic cache eval
- synthetic dataset validation
- warm-up validation
- routing unit tests
- question bank unit tests
- query guard unit tests

Important scripts:
- `tests/run_rag_eval.py`
- `tests/run_ragas_eval.py`
- `tests/run_retrieval_cache_eval.py`
- `tests/run_semantic_cache_eval.py`
- `tests/run_synthetic_dataset_check.py`
- `tests/run_warmup_validation.py`
- `tests/run_full_rag_eval.py`

Important unit tests:
- `tests/test_form_detection.py`
- `tests/test_query_routing.py`
- `tests/test_query_guard.py`
- `tests/test_question_bank.py`

## 18. Known Constraints and Real Limitations

Current hard constraints:
- do not change `/api/ask` schema casually
- do not introduce new LLM secret names
- keep using only `DEEPSEEK_API_KEY`
- do not weaken company/form scope isolation in cache logic
- keep modular structure stable
- do not casually refactor working modules

Known practical limitations:
- answer quality still depends on retrieval coverage quality
- compare answers are routed and aggregated, but can still need further formatting improvement for perfect analyst-style comparisons
- companies not present in index cannot be answered reliably
- logs are strong, but external metrics stack is not yet installed
- frontend deploys can look stale if browser keeps old bundle; hard refresh may still be needed after deployment

## 19. Current Engineering Priorities

Current priorities, in order:
- keep retrieval correctness stable
- keep cache scope safe
- keep multi-worker behavior stable
- keep observability strong enough for debugging
- keep deployment automatic and recoverable
- avoid accidental regressions in frontend behavior during backend work

## 20. Development History Summary

This is the compact version of the real project evolution.

### Phase 0 - Repository bootstrap
- FastAPI base app
- CI baseline
- initial public repository structure

### Phase 1 - Baseline SEC RAG foundation
- SEC filing download / parse / clean / chunk pipeline
- early vector tooling
- working end-to-end filing QA baseline

### Phase 2 - Production retrieval architecture
- Qdrant became active vector backend
- Redis retrieval cache
- semantic cache
- hybrid retrieval stabilized
- evaluation tooling added

### Phase 3 - Grounding and retrieval safety
- stricter answer prompt
- safer form handling
- less noisy context shaping
- grounding tests

### Phase 4 - Runtime stability
- retrieval / rerank tuning
- load stability improvements
- startup warm-up

### Phase 5 - Frontend dashboard and live execution UI
- Next.js frontend
- live execution stream
- query history
- suggested questions
- answer telemetry panel

### Phase 6 - Multi-worker safety and observability
- Redis-backed shared state
- run_id-based stream isolation
- event persistence for stream replay
- Redis answer cache
- structured retrieval / LLM logs
- distributed LLM limiter
- Qdrant bootstrap on deploy

## 21. How to Handoff This Project

When handing this repository to another engineer or GPT chat, provide:
- `README.md`
- `README_DEV.md`
- current task
- exact constraints for the next change
- if possible, one recent `run_id` and matching backend logs

That is enough to reconstruct:
- what the system does
- how the system is deployed
- how state is shared
- where to debug retrieval vs LLM vs streaming vs cache

## 22. Append-Only Update Template

Use append-only updates whenever possible.

Template:

```text
## YYYY-MM-DD - Milestone title

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

Observability
- what logs, metrics, or traces were added or relied on

Risks / open issues
- what still needs attention

Next step
- likely next engineering action
```

## 23. Next Append Section

Add all future milestones below this line.

## 2026-03-09 - Placeholder for next development milestone

Goal
- pending

Changes
- pending

Reason
- pending

Validation
- pending

Observability
- pending

Risks / open issues
- pending

Next step
- pending

## 2026-03-15 - Stored preset answer bank for offline replay

Goal
- make the 20 suggested questions and 4 quick audit cards reproducible without live LLM calls after one capture pass

Changes
- added shared preset question catalog in `frontend/lib/presetQuestionCatalog.json`
- added frontend catalog helpers in `frontend/lib/presetCatalog.ts`
- added generated answer bank loader in `frontend/lib/presetAnswerBank.ts`
- added persisted generated bank file in `frontend/lib/presetAnswerBank.generated.json`
- updated `frontend/hooks/useAskPipeline.ts` to serve stored answers locally and stop before the LLM step in UI
- updated `frontend/components/SuggestedQuestions.tsx` to use the pinned first 20 catalog questions
- updated `frontend/components/PromptPanel.tsx` to source quick audit cards from the same catalog
- added generator script `scripts/generate_preset_answer_bank.py`
- added optional `generationQuery` and `compositeQueries` support in the preset catalog so broad UI audit cards can capture stronger stored answers without changing runtime lookup

Reason
- live RAG/LLM responses were not deterministic enough for presentation-grade preset questions
- the project needed a one-time capture workflow so fixed demo questions could later run without further token spend

Validation
- ran `python scripts/generate_preset_answer_bank.py --base-url http://localhost:8021 --timeout 300 --overwrite`
- generated 24 stored preset answers successfully
- frontend build still passes after wiring the new bank

Observability
- each generated preset answer keeps its original `run_id`, `mode`, `sources`, and `captured_at` metadata in the generated bank

Risks / open issues
- stored answers reflect whatever the live backend returned at capture time; if retrieval quality changes later, the bank must be regenerated
- generated bank content is repository state now and should be refreshed intentionally, not implicitly

Next step
- optionally add a small admin action or script alias to refresh the preset bank before releases
