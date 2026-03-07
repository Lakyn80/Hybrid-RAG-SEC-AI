# Hybrid RAG SEC AI

Produkční Python projekt pro dotazování nad SEC filingy pomocí hybridního RAG pipeline.

Projekt kombinuje:

- SEC EDGAR ingestion
- offline zpracování filingů do chunků
- FAISS vektorové vyhledávání
- BM25 lexikální vyhledávání
- hybridní merge výsledků
- LangGraph orchestration
- DeepSeek LLM answering
- jednoduchou knowledge graph vrstvu
- eval skripty pro API, retrieval a RAGAS

Tento README je napsaný jako kompletní handoff dokument. Má sloužit jak pro člověka, tak jako kontext pro další GPT, aby okamžitě chápal:

- co ten projekt dělá
- co je už hotové
- co je jen připravené, ale není v hlavním request flow
- jaké jsou vstupy, výstupy a datové artefakty
- jak projekt spouštět, testovat a rozšiřovat
- na co si dát pozor při dalších změnách

## 1. Co je cílem projektu

Primární cíl je odpovídat na otázky nad SEC firemními filingy tak, aby odpověď byla založená na reálně stažených dokumentech a dohledatelných zdrojích.

Typické dotazy:

- "What legal risks did Apple mention in its 10-K filings?"
- "What risks did NVIDIA mention in its annual report?"
- "What proxy issues did Apple discuss?"

Projekt je zaměřený hlavně na:

- finance
- risk analysis
- document QA
- retrieval quality
- dohledatelné sources

## 2. Co je v projektu reálně zapojené dnes

### Aktivně používané v hlavním `/api/ask` flow

- FastAPI endpoint
- LangGraph workflow
- query classification
- inferování company/form filtru z dotazu
- FAISS retrieval
- BM25 retrieval
- finální metadata filtering
- context builder
- DeepSeek LLM generation
- fallback answer mode
- cache vrstva
- source formatting

### Existuje v projektu, ale není to hlavní runtime cesta `/api/ask`

- CrossEncoder reranker modul
- knowledge graph builder
- entity extractor
- samostatné CLI utility pro FAISS search / FAISS-only answering

### Důležité upřesnění

Projekt má knowledge graph moduly, ale aktuální produkční odpověď v `/api/ask` je řízená hlavně hybridním retrieval + LLM flow. Knowledge graph dnes není centrální součástí online answer path.

## 3. Aktuální stav dat v repu

V repu už jsou hotová data a artefakty, takže projekt není prázdný skeleton.

Snapshot aktuálního stavu:

- `data/companies.csv`: 10 425 firem
- `data/raw/company_*.json`: 3 stažené company submission JSON soubory
- `data/raw/filings_html/*.html`: 360 HTML filingů
- `data/clean/filings_clean.parquet`: 3 011 řádků
- `data/clean/filings_parsed.parquet`: 360 dokumentů
- `data/clean/filings_chunks.parquet`: 13 424 chunků
- `data/vectorstore/faiss/filings_chunks_metadata.parquet`: 13 424 chunk metadata řádků
- `data/vectorstore/faiss/filings_chunks.index`: FAISS index
- `data/cache/answer_cache.json`: runtime cache
- `data/company_graph.gml`: uložený knowledge graph

Aktuálně zpracovaný subset firem v parsed/chunk/vector vrstvě:

- Apple Inc.
- NVIDIA CORP
- Alphabet Inc.

Aktuálně zpracované formy v parsed/chunk/vector vrstvě:

- 10-K
- 10-Q
- 8-K
- DEF 14A
- DEFA14A
- SC 13G
- SC 13G/A

## 4. Technologie a knihovny

Hlavní stack:

- Python 3.11
- FastAPI
- LangGraph
- LangChain
- DeepSeek přes OpenAI-compatible klienta
- FAISS
- sentence-transformers
- CrossEncoder reranker
- pandas
- pyarrow
- rank-bm25
- ragas
- datasets
- BeautifulSoup + lxml
- networkx

Z `requirements.txt` je důležité:

- `torch` se instaluje z CPU indexu
- embeddings a reranker běží přes sentence-transformers
- API je postavené na FastAPI + uvicorn

## 5. Hlavní adresářová struktura

```text
hybrid-rag/
├─ app/
│  ├─ main.py
│  ├─ services/
│  │  └─ answer_service.py
│  ├─ llm/
│  │  └─ langchain_chain.py
│  ├─ retrieval/
│  │  ├─ bm25_retriever.py
│  │  └─ reranker.py
│  ├─ router/
│  │  └─ query_router.py
│  ├─ pipeline/
│  │  ├─ data_cleaner.py
│  │  ├─ download_filing_html.py
│  │  ├─ parse_filing_html.py
│  │  ├─ chunk_filings.py
│  │  ├─ build_faiss_index.py
│  │  ├─ search_faiss.py
│  │  ├─ answer_faiss.py
│  │  └─ answer_with_llm.py
│  ├─ ingestion/
│  │  └─ sec_ingest.py
│  ├─ graph/
│  │  ├─ graph_builder.py
│  │  └─ entity_extractor.py
│  └─ core/
│     └─ logger.py
├─ data/
│  ├─ raw/
│  ├─ clean/
│  ├─ vectorstore/faiss/
│  └─ cache/
├─ tests/
│  ├─ run_eval.py
│  ├─ run_rag_eval.py
│  ├─ run_ragas_eval.py
│  ├─ eval_questions.json
│  ├─ rag_eval_questions.json
│  └─ ragas_dataset.json
├─ .env
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ README.md
```

## 6. Role jednotlivých částí

### `app/main.py`

Hlavní FastAPI vstup.

Exportuje:

- `GET /api/health`
- `POST /api/ask`

### `app/services/answer_service.py`

Centrální answer orchestration vrstva. Tohle je nejdůležitější runtime modul projektu.

Obsahuje:

- query classification
- inferování filtrů
- cache logiku
- hybrid retrieval flow
- context builder
- source formatter
- LLM call
- fallback answer konstrukci
- LangGraph workflow

### `app/llm/langchain_chain.py`

LLM helper vrstva.

Zodpovědnosti:

- načtení `.env`
- načtení `DEEPSEEK_API_KEY`
- model/base URL nastavení
- vytvoření `ChatOpenAI` klienta pro DeepSeek-compatible endpoint
- spuštění prompt chain

### `app/retrieval/bm25_retriever.py`

Lexikální retrieval přes BM25 nad `chunk_text`.

### `app/retrieval/reranker.py`

CrossEncoder reranker přes `cross-encoder/ms-marco-MiniLM-L-6-v2`.

Důležité:

- modul existuje
- hlavní produkční graf dnes běží přes hybrid merge cestu
- reranker je pořád součást projektu a používá se v jiných retrieval cestách / debug flow

### `app/router/query_router.py`

Jednoduchý query classifier:

- `risk`
- `financial`
- `compare`
- `general`

### `app/pipeline/*`

Offline zpracování dat od raw SEC JSONů po chunked dataset a FAISS index.

### `app/ingestion/*`

SEC ingestion utility skripty.

### `app/graph/*`

Knowledge graph utility vrstva.

## 7. Reálný online request flow

Když přijde `POST /api/ask`, děje se toto:

1. API přijme `query`, případně `company` a `form`.
2. `answer_query()` sestaví LangGraph state.
3. Query classifier určí typ dotazu.
4. Z dotazu se inferuje firma a forma, pokud uživatel filtr neposlal explicitně.
5. Cache lookup zkusí vrátit hotovou odpověď.
6. Pokud cache není použitelná, spustí se retrieval.
7. Retrieval kombinuje:
   - FAISS vector retrieval
   - BM25 lexical retrieval
8. Výsledky se sjednotí, finálně filtrují podle metadata podmínek, deduplikují a oříznou.
9. Z výsledků se vytvoří context.
10. LLM vytvoří finální answer.
11. Z výsledků se vytvoří `sources`.
12. Výsledek se případně uloží do cache.

### Hlavní LangGraph node flow

Aktuální workflow:

- `prepare`
- `cache_lookup`
- `cache_return` nebo `retrieve`
- `retrieval_failed` nebo `build_context`
- `llm`
- `save_cache`

## 8. Retrieval logika

### FAISS část

FAISS index je postavený nad embeddings z modelu:

- `all-MiniLM-L6-v2`

Vyhledávání probíhá nad metadata subsetem, který se nejdřív filtruje podle:

- company
- form

### BM25 část

BM25 běží nad stejným metadata dataframe a používá:

- tokenizaci přes regex
- `chunk_text`

### Hybrid merge

Produkční retrieval cesta v answer service dělá:

- FAISS retrieval
- BM25 retrieval
- spojení do jednoho dataframe
- finální metadata filter
- `drop_duplicates(subset=["chunk_text"])`
- limit na finální context rows

### Finální context limit

Finální runtime context je omezen na:

- 10 chunků

### Query-based metadata inference

Projekt dnes umí z textu dotazu odhadnout:

- firmu
- filing form

Příklady:

- `Apple` -> `Apple Inc.`
- `NVIDIA` -> `NVIDIA CORP`
- `Google` nebo `Alphabet` -> `Alphabet Inc.`
- `annual report` nebo `10-K` -> `10-K`
- `quarterly report` nebo `10-Q` -> `10-Q`
- `proxy` -> `DEF 14A`
- `8-K` -> `8-K`

## 9. LLM vrstva

Projekt používá:

- `DEEPSEEK_API_KEY` jako jediný secret key
- `LLM_MODEL` pro model name
- `LLM_API_URL` pro OpenAI-compatible DeepSeek endpoint

Aktuální default:

- model: `deepseek-chat`
- base endpoint: `https://api.deepseek.com/chat/completions`

### Důležité pravidlo

Secret se drží jen v env.

Používaný key:

- `DEEPSEEK_API_KEY`

Nepoužívané key názvy:

- `OPENAI_API_KEY`
- `LLM_API_KEY`

## 10. Cache vrstva

Cache soubor:

- `data/cache/answer_cache.json`

Cache ukládá:

- query
- company/form filter
- mode
- answer
- sources
- llm metadata
- errors
- timestamp

TTL:

- LLM answer cache: 24 hodin
- fallback cache: 10 minut

Důležitá behavior nuance:

- při aktivních metadata filtrech je cache bypassnutá

To je záměr, aby se nevracely staré nebo kontaminované výsledky napříč firmami/formami.

## 11. API kontrakt

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
  "answer": "....",
  "mode": "llm",
  "sources": "Sources:\n- Apple Inc. | 10-K | ...",
  "cache_hit": false
}
```

### Význam response polí

- `query`: finální query
- `answer`: vygenerovaná nebo fallback odpověď
- `mode`: `llm`, `fallback` nebo `cache`
- `sources`: formátované sources textově
- `cache_hit`: bool

### Důležitá poznámka

API kontrakt dnes nevrací přímo list `chunk_text` contextů. Eval skript pro RAGAS si je proto bere interně z retrieval stavu, aniž by měnil API response contract.

## 12. Environment proměnné

Minimální `.env`:

```env
DEEPSEEK_API_KEY=<your_deepseek_api_key>
LLM_MODEL=deepseek-chat
LLM_API_URL=https://api.deepseek.com/chat/completions
```

Volitelné pro RAGAS:

```env
RAGAS_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAGAS_MAX_TOKENS=8192
```

### Co je secret

Secret je jen:

- `DEEPSEEK_API_KEY`

### Co secret není

- `LLM_MODEL`
- `LLM_API_URL`
- `RAGAS_EMBEDDING_MODEL`
- `RAGAS_MAX_TOKENS`

## 13. Lokální instalace a spuštění

### Varianta A: Docker

Build a run:

```powershell
docker compose build
docker compose up -d
```

API:

- `http://localhost:8021`

Swagger:

- `http://localhost:8021/docs`

### Varianta B: Lokální Python

Typický Windows flow:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8021
```

## 14. Offline data pipeline krok za krokem

Toto je doporučené pořadí pro build dat od raw ingestion po index.

### Krok 1: stáhnout company list a submission JSONy

```powershell
python app/ingestion/sec_ingest.py
```

Vytvoří:

- `data/companies.csv`
- `data/raw/company_<CIK>.json`

Poznámka:

- skript aktuálně stahuje company list a filings pro první 3 firmy z CSV

### Krok 2: rychlá inspekce raw JSONů

```powershell
python app/pipeline/inspect_filings.py
```

### Krok 3: vyčistit raw filings metadata

```powershell
python app/pipeline/data_cleaner.py
```

Vytvoří:

- `data/clean/filings_clean.parquet`

### Krok 4: připravit `filings_text_html.csv`

Tohle je důležitý manuální nebo externí mezikrok.

Skript `download_filing_html.py` neočekává `filings_clean.parquet`, ale:

- `data/clean/filings_text_html.csv`

Tento CSV musí obsahovat:

- `cik`
- `company`
- `form`
- `filing_date`
- `document`
- `accession_number`
- `accession_nodash`
- `filing_url`

V repu už ten soubor existuje. Aktuálně má:

- 360 řádků

Prakticky slouží jako filtered metadata soubor určující, které filing HTML stránky se mají stáhnout.

### Krok 5: stáhnout filing HTML

```powershell
python app/pipeline/download_filing_html.py
```

Vytvoří:

- `data/raw/filings_html/*.html`

Poznámky:

- používá SEC request headers
- má delay mezi requesty
- stahuje podle `filing_url`

### Krok 6: parsovat HTML do textu

```powershell
python app/pipeline/parse_filing_html.py
```

Vytvoří:

- `data/clean/filings_parsed.parquet`

Obsahuje:

- company metadata
- filing metadata
- HTML title
- full extracted text

### Krok 7: chunkovat parsed filings

```powershell
python app/pipeline/chunk_filings.py
```

Vytvoří:

- `data/clean/filings_chunks.parquet`

Aktuální defaulty:

- `CHUNK_SIZE = 2000`
- `CHUNK_OVERLAP = 300`

### Krok 8: postavit FAISS index

```powershell
python app/pipeline/build_faiss_index.py
```

Vytvoří:

- `data/vectorstore/faiss/filings_chunks.index`
- `data/vectorstore/faiss/filings_chunks_metadata.parquet`

## 15. CLI utility skripty

### `app/pipeline/search_faiss.py`

FAISS-only search debug tool.

Příklad:

```powershell
python app/pipeline/search_faiss.py "What legal risks did Apple mention?" --company=Apple Inc. --form=10-K
```

Vrací:

- top retrieved chunky
- score
- metadata

### `app/pipeline/answer_faiss.py`

FAISS-only extractive answer bez DeepSeek LLM answer service orchestrace.

Příklad:

```powershell
python app/pipeline/answer_faiss.py "What risks did NVIDIA mention?" --company=NVIDIA CORP --form=10-K
```

### `app/pipeline/answer_with_llm.py`

Plná answer service cesta přes runtime logiku.

Příklad:

```powershell
python app/pipeline/answer_with_llm.py "What legal risks did Apple mention in its 10-K filings?"
```

Skript vypíše:

- query
- inferred filters
- model
- info o key přítomnosti
- cache mode
- případné chyby
- finální answer

## 16. Knowledge graph vrstva

### `app/graph/graph_builder.py`

Staví základní graph z `companies.csv`.

Nodes:

- company

Node atribut:

- ticker

Výstup:

- `data/company_graph.gml`

### `app/graph/entity_extractor.py`

Prochází `company_*.json` raw submission files a vytváří edge:

- `relation="co-mentioned"`

Pozor:

- jde o jednoduchou heuristiku
- není to sophisticated relation extraction
- hlavní QA flow na tom dnes nezávisí

## 17. Eval a test skripty

### `tests/run_eval.py`

Smoke/API eval nad endpointem.

Měří:

- průměrnou latenci
- kolik odpovědí bylo `llm`
- kolik odpovědí bylo `fallback`

Vstup:

- `tests/eval_questions.json`

Výstup:

- `tests/eval_results.json`

### `tests/run_rag_eval.py`

Jednoduchý retrieval eval přes kontrolu, zda se v `sources` objeví očekávaná firma a forma.

Měří:

- `hit_at_k`

Vstup:

- `tests/rag_eval_questions.json`

Výstup:

- `tests/rag_eval_results.json`

### `tests/run_ragas_eval.py`

RAGAS eval script.

Měří:

- faithfulness
- answer relevancy

Důležité:

- answer si bere z API
- retrieved contexts bere z reálných `chunk_text` retrieval výsledků
- nepoužívá `sources` jako pseudo-context
- nemění API contract

Vstup:

- `tests/ragas_dataset.json`

## 18. Jak projekt používáme v praxi

### Typický pracovní režim

1. Udržujeme lokální dataset filingů.
2. Přegenerujeme chunky a FAISS index, když se dataset mění.
3. API spouštíme lokálně nebo přes Docker.
4. Query chování ladíme přes:
   - `/api/ask`
   - `answer_with_llm.py`
   - `search_faiss.py`
5. Retrieval kvalitu kontrolujeme přes:
   - `run_rag_eval.py`
   - `run_ragas_eval.py`

### Kdy sahat do kterého souboru

- API problém: `app/main.py`
- orchestrace / retrieval flow: `app/services/answer_service.py`
- LLM config: `app/llm/langchain_chain.py`
- BM25: `app/retrieval/bm25_retriever.py`
- reranker: `app/retrieval/reranker.py`
- query routing: `app/router/query_router.py`
- offline pipeline: `app/pipeline/*`
- evaly: `tests/*`

## 19. Známé limity a technické nuance

### 1. Knowledge graph není centrální answer engine

V projektu je graph vrstva, ale dnešní `/api/ask` flow není graph-first systém.

### 2. `filings_text_html.csv` je mezikrok mimo plně automatizovanou pipeline

Tento soubor je dnes důležitý ruční/externí vstup pro HTML download a parse kroky.

### 3. Hlavní answer path má hybrid retrieval, ale ne každá utilita používá identický flow

Projekt obsahuje více debug a utility scriptů, které nejsou 1:1 shodné s produkční LangGraph answer flow.

### 4. RAGAS běhy jsou dražší a pomalejší

Kvůli LLM a embeddings vrstvě může `run_ragas_eval.py` trvat několik minut.

### 5. První běh může stahovat modely

První spuštění embeddings/reranker komponent může být pomalejší kvůli model downloadu.

### 6. Cache může měnit chování runtime

Při debugování answer flow je potřeba počítat s cache filem v `data/cache/answer_cache.json`.

### 7. Procesed subset je menší než full SEC universe

`companies.csv` má přes 10k firem, ale vectorstore dnes reprezentuje jen subset zpracovaných filingů.

## 20. Doporučený debugging workflow

Když něco nefunguje:

1. zkontroluj `.env`
2. zkontroluj existenci `filings_chunks.index` a metadata parquet
3. spusť `search_faiss.py` pro dotaz
4. spusť `answer_with_llm.py`
5. zkontroluj `data/cache/answer_cache.json`
6. zkontroluj, zda query inferuje správnou firmu a form
7. zkontroluj `sources` v API odpovědi
8. pak teprve řeš LLM prompting

## 21. Důležité vývojové zásady pro další práci

Pokud do projektu bude sahat další GPT nebo další vývojář, měl by respektovat:

- neměnit API contract bez explicitního požadavku
- nerefactorovat architekturu jen kvůli stylu
- držet modularitu podle `app/services`, `app/retrieval`, `app/llm`, `app/pipeline`, `tests`
- nehardcodovat secret do kódu
- používat jen `DEEPSEEK_API_KEY` pro secret
- při retrieval změnách ověřovat `run_rag_eval.py` a `run_ragas_eval.py`
- neplést si `sources` s reálnými retrieved contexty

## 22. Co by měl vědět další GPT hned na začátku

Pokud chceš tenhle projekt předat jinému GPT, můžeš mu poslat minimálně toto:

```text
Projekt je Python FastAPI + LangGraph hybrid RAG nad SEC filingy.

Hlavní runtime cesta:
- app/main.py
- app/services/answer_service.py
- app/llm/langchain_chain.py
- app/retrieval/bm25_retriever.py
- app/router/query_router.py

API:
- POST /api/ask
- request: query, optional company, optional form
- response: query, answer, mode, sources, cache_hit

Retrieval:
- FAISS + BM25 hybrid
- final metadata filtering
- final context limit 10 chunků

LLM:
- DeepSeek
- secret pouze DEEPSEEK_API_KEY z env

Data snapshot:
- parsed filings: 360
- chunks: 13 424
- companies in vectorstore: Apple, NVIDIA, Alphabet

Pipeline:
- sec_ingest.py
- data_cleaner.py
- download_filing_html.py
- parse_filing_html.py
- chunk_filings.py
- build_faiss_index.py

Eval:
- run_eval.py
- run_rag_eval.py
- run_ragas_eval.py

Knowledge graph existuje v projektu, ale dnes není hlavní součást /api/ask flow.

Důležité constraints:
- neměnit zbytečně architekturu
- neměnit API contract bez výslovného zadání
- neplést si sources a retrieved chunk contexts
- nepřidávat jiné secret key názvy než DEEPSEEK_API_KEY
```

## 23. Shrnutí v jedné větě

Hybrid RAG SEC AI je modulární lokální systém pro ingestion, zpracování, vyhledávání a LLM answer generation nad SEC filingy, kde hlavní produkční answer flow běží přes FastAPI + LangGraph + FAISS/BM25 hybrid retrieval + DeepSeek, a celý projekt je už připravený i na eval a další iteraci.
