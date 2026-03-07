# Hybrid RAG SEC AI

Produkční Python RAG systém nad SEC filingy. Aktivní runtime je postavený jako:

`FastAPI -> LangGraph -> cache vrstvy -> hybrid retrieval -> rerank -> context build -> DeepSeek`

Projekt je určený pro:

- SEC filing QA
- retrieval debugging
- evaluaci faithfulness a retrieval quality
- postupný růst směrem k velkým SEC datasetům

README je napsané jako finální handoff dokument pro člověka i pro další GPT. Popisuje skutečný stav kódu po produkčním dokončení dne **2026-03-07**.

## 1. Co je cílem projektu

Primární cíl je odpovídat na otázky nad SEC filingy tak, aby odpověď:

- vycházela z reálných filing chunků
- měla dohledatelné zdroje
- držela company/form scope
- byla měřitelná přes retrieval eval i RAGAS

Typické dotazy:

- `What legal risks did Apple mention in its 10-K filings?`
- `What did NVIDIA disclose in its annual report?`
- `What governance topics did Apple discuss in its proxy statement?`

## 2. Finální produkční architektura

### Aktivní runtime v `/api/ask`

- FastAPI endpoint v `app/main.py`
- LangGraph orchestrace v `app/services/answer_service.py`
- query classification v `app/router/query_router.py`
- exact answer cache v `data/cache/answer_cache.json`
- semantic cache v Redis
- retrieval cache v Redis
- Qdrant vector retrieval s payload metadata filtry
- BM25 lexical retrieval
- hybrid merge
- CrossEncoder reranker
- finální metadata filtering
- context builder
- DeepSeek answer generation
- source formatter

### Co je v projektu, ale není hlavní runtime backend

- legacy FAISS build/search utility skripty
- knowledge graph utility vrstva
- entity extractor

FAISS už není aktivní produkční vector backend pro `/api/ask`. Qdrant je finální runtime směr. FAISS utility zůstávají v repu jen jako pomocné nebo historické skripty.

## 3. Ověřený snapshot dat a runtime artefaktů

Aktuální snapshot ověřený z lokálních artefaktů:

- `data/companies.csv`: 10 425 firem
- `data/raw/filings_html/*.html`: 360 HTML filingů
- `data/clean/filings_clean.parquet`: 3 011 řádků
- `data/clean/filings_parsed.parquet`: 360 dokumentů
- `data/clean/filings_chunks.parquet`: 13 424 chunků
- `data/vectorstore/faiss/filings_chunks_metadata.parquet`: 13 424 metadata řádků
- `data/vectorstore/runtime_manifest.json`: aktivní runtime manifest
- `data/cache/answer_cache.json`: exact answer cache soubor
- `tests/synthetic_eval_dataset.json`: 48 syntetických eval otázek

Aktivní runtime manifest:

- `backend`: `qdrant`
- `collection_alias`: `sec_filings_chunks_current`
- `collection_name`: `sec_filings_chunks_e6063e41814863e6508b7f69`
- `index_version`: `e6063e41814863e6508b7f69`
- `embedding_model`: `all-MiniLM-L6-v2`
- `points_count`: `13424`

Aktuálně zpracované firmy v runtime datech:

- Apple Inc.
- NVIDIA CORP
- Alphabet Inc.

Aktuálně zpracované formy:

- 10-K
- 10-Q
- 8-K
- DEF 14A
- DEFA14A
- SC 13G
- SC 13G/A

## 4. Adresářová struktura a role modulů

```text
hybrid-rag/
├─ app/
│  ├─ main.py
│  ├─ core/
│  │  ├─ logger.py
│  │  ├─ cache_stats.py
│  │  └─ cache_admin.py
│  ├─ services/
│  │  ├─ answer_service.py
│  │  └─ semantic_cache.py
│  ├─ retrieval/
│  │  ├─ resources.py
│  │  ├─ metadata_utils.py
│  │  ├─ retrieval_cache.py
│  │  ├─ qdrant_store.py
│  │  ├─ bm25_retriever.py
│  │  └─ reranker.py
│  ├─ llm/
│  │  ├─ langchain_chain.py
│  │  └─ synthetic_eval_chain.py
│  ├─ router/
│  │  └─ query_router.py
│  ├─ pipeline/
│  │  ├─ chunk_filings.py
│  │  ├─ build_qdrant_index.py
│  │  ├─ generate_synthetic_eval_dataset.py
│  │  ├─ warm_up_runtime.py
│  │  ├─ answer_with_llm.py
│  │  └─ legacy FAISS utility skripty
│  ├─ ingestion/
│  │  └─ sec_ingest.py
│  └─ graph/
│     ├─ graph_builder.py
│     └─ entity_extractor.py
├─ data/
│  ├─ raw/
│  ├─ clean/
│  ├─ vectorstore/
│  │  ├─ faiss/
│  │  └─ runtime_manifest.json
│  └─ cache/
├─ tests/
│  ├─ run_eval.py
│  ├─ run_rag_eval.py
│  ├─ run_ragas_eval.py
│  ├─ run_retrieval_cache_eval.py
│  ├─ run_semantic_cache_eval.py
│  ├─ run_synthetic_dataset_check.py
│  ├─ run_warmup_validation.py
│  └─ *.json eval artefakty
├─ docker-compose.yml
├─ requirements.txt
└─ README.md
```

### Klíčové runtime moduly

`app/services/answer_service.py`

- centrální LangGraph orchestrátor
- inferuje company/form
- sestavuje cache keys
- řídí retrieval, rerank, context, LLM, source formatting

`app/retrieval/resources.py`

- lazy load shared resource vrstvy
- metadata parquet loader
- embedding model loader
- FAISS loader pro legacy utility
- Redis client
- runtime manifest loader

`app/retrieval/qdrant_store.py`

- Qdrant client
- runtime collection resolution
- payload filter builder pro `company_norm` a `form_norm`
- vector query helper pro aktivní runtime

`app/retrieval/retrieval_cache.py`

- Redis retrieval cache read/write
- bezpečné keying podle backendu, indexu, filtrů a query

`app/services/semantic_cache.py`

- Redis semantic cache
- embedding similarity lookup
- token overlap safety guard
- company/form/query_type bucket boundaries

## 5. Online request flow

Když přijde `POST /api/ask`, děje se toto:

1. API přijme `query`, případně `company` a `form`.
2. `answer_query()` sestaví LangGraph state.
3. `prepare` node určí:
   - `query_type`
   - effective `company_filter`
   - effective `form_filter`
   - `retrieval_backend`
   - `index_version`
4. `cache_lookup` zkusí exact answer cache.
5. Pokud exact cache nevyhoví, `semantic_lookup` zkusí semantic cache.
6. Pokud semantic cache nevyhoví, `retrieve` node spustí retrieval cache check.
7. Při retrieval miss se spustí:
   - Qdrant vector retrieval
   - BM25 lexical retrieval
   - hybrid merge
   - CrossEncoder rerank
   - finální metadata filtering
   - `drop_duplicates(subset=["chunk_text"])`
   - context limit
8. `build_context` vytvoří prompt context a `sources`.
9. `llm` zavolá DeepSeek model.
10. `save_semantic_cache` uloží bezpečné LLM odpovědi do semantic cache.
11. `save_cache` uloží exact answer cache jen tam, kde to dává smysl.

### Aktivní LangGraph node flow

- `prepare`
- `cache_lookup`
- `cache_return` nebo `semantic_lookup`
- `semantic_return` nebo `retrieve`
- `retrieval_failed` nebo `build_context`
- `llm`
- `save_semantic_cache`
- `save_cache`

## 6. Retrieval vrstva

### Qdrant jako finální vector backend

Aktivní vector backend je Qdrant s:

- cosine similarity
- persistent storage
- HNSW indexem
- payload metadata filtry

Payload obsahuje:

- `company`
- `company_norm`
- `form`
- `form_norm`
- `filing_date`
- `accession_number`
- `filing_url`
- `source_file`
- `html_title`
- `document_text_length`
- `chunk_index`
- `chunk_text`
- `chunk_text_length`
- `chunk_hash`
- `vector_id`

### Company/form filtering

Company a form se filtrují server-side přímo v Qdrant přes payload filter nad:

- `company_norm`
- `form_norm`

To je zásadní rozdíl proti starému FAISS-only směru. Runtime už není závislý na čistě klientském post-filteru nad vector hity.

### BM25 zůstává

BM25 zůstává jako lexical polovina hybrid retrievalu:

- běží nad `chunk_text`
- používá sdílený metadata dataframe z `resources.py`
- nebuildí zbytečně celý stav per request

### Reranker

Rerank se dělá přes CrossEncoder:

- model: `cross-encoder/ms-marco-MiniLM-L-6-v2`

### Finální context limit

Aktuální finální context limit je:

- `10` chunků

### Legacy FAISS poznámka

V repu stále zůstávají FAISS utility a metadata adresář `data/vectorstore/faiss/`, ale produkční runtime `/api/ask` používá Qdrant. Parquet metadata soubor v tomto adresáři zůstává jako kompatibilní artefakt pro utility a offline skripty.

## 7. Cache vrstvy

Projekt má tři oddělené cache vrstvy.

### 1. Exact answer cache

Soubor:

- `data/cache/answer_cache.json`

Co ukládá:

- finální odpověď
- mode
- sources
- timestamps
- llm metadata

TTL:

- LLM answer: 24 hodin
- fallback: 10 minut

Důležitá nuance:

- pokud jsou aktivní metadata filtry, exact answer cache se bypassuje

### 2. Retrieval cache

Storage:

- Redis

Co ukládá:

- finální `results_rows` po merge, reranku, metadata filtru, dedupu a limitu

TTL:

- 24 hodin

Key zahrnuje:

- `backend`
- `index_version`
- `embedding_model`
- `reranker_version`
- normalized `company_filter`
- normalized `form_filter`
- hashed query
- retrieval limits

To brání stale nebo cross-scope reuse po změně indexu nebo filtrů.

### 3. Semantic cache

Storage:

- Redis

Co vrací:

- finální answer
- finální sources

Co nevrací:

- raw retrieval rows

TTL:

- 7 dní

Bezpečnostní pravidla:

- semantic cache je vypnutá, pokud chybí effective `company_filter`
- semantic cache je vypnutá, pokud chybí effective `form_filter`
- bucket je oddělený podle `index_version`, `company`, `form`, `query_type`
- lookup používá cosine similarity
- lookup navíc používá token overlap safety guard

Aktuální lookup guardy:

- similarity threshold: `0.82`
- top1/top2 margin: `0.015`
- token overlap ratio: `0.5`

## 8. API kontrakt

### `GET /api/health`

Response:

```json
{
  "status": "ok"
}
```

### `POST /api/ask`

Request:

```json
{
  "query": "What legal risks did Apple mention in its 10-K filings?",
  "company": "Apple Inc.",
  "form": "10-K"
}
```

`company` a `form` jsou volitelné.

Response:

```json
{
  "query": "What legal risks did Apple mention in its 10-K filings?",
  "answer": "...",
  "mode": "llm",
  "sources": "Sources:\n- Apple Inc. | 10-K | ...",
  "cache_hit": false
}
```

API kontrakt se záměrně neměnil. Runtime stále nevrací přímo `retrieved_contexts`. RAGAS eval si je bere interně z retrieval stavu, ne z response contractu.

## 9. Environment proměnné

Jediný secret key v projektu je:

- `DEEPSEEK_API_KEY`

Minimální `.env`:

```env
DEEPSEEK_API_KEY=<your_deepseek_api_key>
LLM_MODEL=deepseek-chat
LLM_API_URL=https://api.deepseek.com/chat/completions
```

Volitelné runtime / eval proměnné:

```env
RAGAS_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAGAS_MAX_TOKENS=8192
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_ALIAS=sec_filings_chunks_current
```

Nepoužívat:

- `OPENAI_API_KEY`
- `LLM_API_KEY`

## 10. Docker a lokální spuštění

### Docker

Stack obsahuje:

- `rag-api`
- `redis`
- `qdrant`

Spuštění:

```powershell
docker compose build
docker compose up -d
```

Endpointy:

- API: `http://localhost:8021`
- Swagger: `http://localhost:8021/docs`
- Qdrant: `http://localhost:6333`

### Lokální Python

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8021
```

Poznámka:

- pipeline a eval skripty byly upravené tak, aby šly spouštět přímo jako `python path/to/script.py` bez ručního nastavování `PYTHONPATH`

## 11. Offline pipeline

### Ingestion a parse

Typické pořadí:

```powershell
python app/ingestion/sec_ingest.py
python app/pipeline/data_cleaner.py
python app/pipeline/download_filing_html.py
python app/pipeline/parse_filing_html.py
python app/pipeline/chunk_filings.py
```

### Build produkčního vector backendu

Qdrant build:

```powershell
python app/pipeline/build_qdrant_index.py
```

Co dělá:

- načte `data/clean/filings_chunks.parquet`
- doplní `company_norm`, `form_norm`, `chunk_hash`
- vyrobí embeddings
- vytvoří novou Qdrant collection
- zapíše runtime manifest
- uloží kompatibilní metadata parquet

Výstupy:

- Qdrant collection
- `data/vectorstore/runtime_manifest.json`
- `data/vectorstore/faiss/filings_chunks_metadata.parquet`

### Legacy FAISS utility build

Legacy FAISS build zůstává v repu pro utility/debug, ale není hlavní runtime backend:

```powershell
python app/pipeline/build_faiss_index.py
```

## 12. Synthetic eval dataset

Generátor:

```powershell
python app/pipeline/generate_synthetic_eval_dataset.py
```

Zdroj:

- `data/clean/filings_chunks.parquet`

Výstup:

- `tests/synthetic_eval_dataset.json`

Schema každého záznamu:

- `id`
- `question`
- `reference`
- `company`
- `form`
- `filing_date`
- `accession_number`
- `query_type`
- `source_chunk_text`
- `source_chunk_hash`
- `quality_score`
- `warmup_eligible`

Aktuálně generované query typy:

- `risk_factor`
- `financial_metric`
- `date_or_period`
- `governance_or_proxy`
- `business_or_product`
- `legal_or_compliance`

## 13. Eval a validační skripty

### Smoke/API eval

```powershell
python tests/run_eval.py
```

Měří:

- avg latency
- p95 latency
- počet `llm` odpovědí
- počet fallbacků

### Retrieval eval

```powershell
python tests/run_rag_eval.py
python tests/run_rag_eval.py --dataset tests/synthetic_eval_dataset.json --output tests/rag_eval_results.synthetic.json
```

Měří:

- `hit_at_k` podle toho, zda `sources` obsahují očekávanou firmu a formu

### RAGAS eval

```powershell
python tests/run_ragas_eval.py
python tests/run_ragas_eval.py --dataset tests/synthetic_eval_dataset.json
```

Důležité:

- answer se bere z API
- retrieved contexts se berou z reálných `chunk_text` retrieval výsledků
- `sources` se nepoužívají jako fake context

### Retrieval cache eval

```powershell
python tests/run_retrieval_cache_eval.py
```

Měří:

- první retrieval miss
- druhý retrieval hit
- stejné `results_rows`

### Semantic cache eval

```powershell
python tests/run_semantic_cache_eval.py
```

Měří:

- seed write
- paraphrase hit
- miss při chybějících effective filtrech
- miss při jiném company/form scope

### Synthetic dataset check

```powershell
python tests/run_synthetic_dataset_check.py
```

Kontroluje:

- schema
- duplicate questions
- minimum quality
- overlap reference vs source chunk
- distribuci typů

### Warm-up validation

```powershell
python tests/run_warmup_validation.py
```

Pod kapotou:

- spustí `app/pipeline/warm_up_runtime.py`
- nejdřív flushne cache state
- udělá cold pass
- udělá warm pass
- zapíše reporty

Výstupy:

- `tests/warmup_report.json`
- `tests/warmup_details.json`

## 14. Warm-up runtime

Přímé spuštění:

```powershell
python app/pipeline/warm_up_runtime.py --flush-cache-state --verify-second-pass
```

Co dělá:

- načte curated a synthetic dataset
- volá živé `/api/ask`
- zahřívá retrieval cache
- zahřívá semantic cache
- zahřívá exact answer cache tam, kde je aktivní
- sbírá latency a hit/miss statistiky

Filtruje:

- low-quality synthetic řádky
- `warmup_eligible=false`
- duplicate kombinace query/company/form

## 15. Ověřené lokální validační výsledky

Následující výsledky byly ověřené lokálně dne **2026-03-07** na běžícím Docker stacku.

### Retrieval cache

`python tests/run_retrieval_cache_eval.py`

- první průchod: miss + write
- druhý průchod: hit
- naměřeno:
  - first latency: `28582.56 ms`
  - second latency: `1.13 ms`

### Semantic cache

`python tests/run_semantic_cache_eval.py`

- seed query: `llm`
- paraphrase: `cache_hit=true`
- missing effective filters: miss
- wrong scope: miss

### API eval

`python tests/run_eval.py`

- total queries: `3`
- avg latency: `6782.31 ms`
- p95 latency: `6643.96 ms`
- fallback answers: `0`

### Retrieval eval

`python tests/run_rag_eval.py`

- curated `hit_at_k`: `1.0`

`python tests/run_rag_eval.py --dataset tests/synthetic_eval_dataset.json`

- synthetic `hit_at_k`: `0.9167`

### RAGAS eval

`python tests/run_ragas_eval.py --dataset tests/synthetic_eval_dataset.json`

- faithfulness: `0.8785`
- answer relevancy: `0.8395`

### Warm-up validation

`python tests/run_warmup_validation.py`

- cold pass:
  - total: `53`
  - avg latency: `6364.79 ms`
  - p95 latency: `10535.49 ms`
- warm pass:
  - total: `53`
  - cache hits: `53`
  - avg latency: `102.0 ms`
  - p95 latency: `141.56 ms`

## 16. Debugging workflow

Když něco nefunguje, postupuj takto:

1. zkontroluj `.env`, hlavně `DEEPSEEK_API_KEY`
2. zkontroluj `docker compose ps`
3. zkontroluj `data/vectorstore/runtime_manifest.json`
4. zkontroluj, že Qdrant collection existuje a manifest ukazuje na správný `collection_name`
5. spusť `python app/pipeline/answer_with_llm.py "..."` pro konkrétní query
6. spusť `python tests/run_retrieval_cache_eval.py`
7. spusť `python tests/run_semantic_cache_eval.py`
8. zkontroluj `tests/warmup_report.json`
9. zkontroluj `data/cache/answer_cache.json`
10. až potom řeš prompting nebo LLM odpověď

## 17. Důležité technické zásady pro další práci

Další GPT nebo vývojář by měl respektovat:

- neměnit API kontrakt bez explicitního zadání
- nerefactorovat architekturu jen kvůli stylu
- zachovat modularitu podle `app/services`, `app/retrieval`, `app/llm`, `app/pipeline`, `app/router`, `tests`
- nepřidávat nové secret názvy
- secret je jen `DEEPSEEK_API_KEY`
- nemíchat `sources` s reálnými retrieved contexts
- při retrieval změnách vždy znovu spustit:
  - `tests/run_rag_eval.py`
  - `tests/run_ragas_eval.py`
  - `tests/run_retrieval_cache_eval.py`
- při cache změnách vždy znovu spustit:
  - `tests/run_semantic_cache_eval.py`
  - `tests/run_warmup_validation.py`

## 18. Co má vědět další GPT hned na začátku

Pokud to chceš předat dalšímu GPT, pošli mu minimálně tento blok:

```text
Projekt je produkční Python FastAPI + LangGraph hybrid RAG nad SEC filingy.

Aktivní runtime flow:
FastAPI -> exact answer cache -> semantic cache -> retrieval cache -> Qdrant + BM25 hybrid retrieval -> CrossEncoder rerank -> context -> DeepSeek.

Hlavní soubory:
- app/services/answer_service.py
- app/services/semantic_cache.py
- app/retrieval/resources.py
- app/retrieval/retrieval_cache.py
- app/retrieval/qdrant_store.py
- app/retrieval/bm25_retriever.py
- app/retrieval/reranker.py
- app/llm/langchain_chain.py
- app/pipeline/build_qdrant_index.py
- app/pipeline/generate_synthetic_eval_dataset.py
- app/pipeline/warm_up_runtime.py

API contract:
- POST /api/ask
- request: query, optional company, optional form
- response: query, answer, mode, sources, cache_hit

Vector backend:
- Qdrant is the active production backend
- runtime manifest: data/vectorstore/runtime_manifest.json
- metadata filters are server-side in Qdrant payload

Caching:
- exact answer cache: data/cache/answer_cache.json
- retrieval cache: Redis, final retrieval rows
- semantic cache: Redis, final answers
- semantic cache is disabled if effective company_filter is missing
- semantic cache is disabled if effective form_filter is missing

Secrets:
- use only DEEPSEEK_API_KEY
- do not introduce OPENAI_API_KEY or LLM_API_KEY

Eval:
- tests/run_eval.py
- tests/run_rag_eval.py
- tests/run_ragas_eval.py
- tests/run_retrieval_cache_eval.py
- tests/run_semantic_cache_eval.py
- tests/run_synthetic_dataset_check.py
- tests/run_warmup_validation.py
```

## 19. Shrnutí v jedné větě

Hybrid RAG SEC AI je modulární produkční SEC QA systém, kde `/api/ask` běží přes LangGraph, Qdrant + BM25 hybrid retrieval, vícevrstvou cache strategii, DeepSeek LLM a kompletní eval/warm-up tooling bez změny API kontraktu.
