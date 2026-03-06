# Hybrid RAG SEC AI

AI projekt pro analýzu finančních dokumentů z **SEC EDGAR**.

Cílem projektu je vytvořit **hybridní RAG systém**, který kombinuje:

- document retrieval
- knowledge graph
- AI reasoning

---

# Architektura projektu

SEC EDGAR API  
↓  
Data Ingestion  
↓  
Document Processing  
↓  
Entity Extraction  
↓  
Knowledge Graph  
↓  
Hybrid Retrieval  
↓  
AI Query System

---

# Struktura projektu


hybrid-rag
│
├─ app
│ ├─ api
│ ├─ ingestion
│ │ └ sec_ingest.py
│ ├─ graph
│ │ ├ graph_builder.py
│ │ └ entity_extractor.py
│ └ main.py
│
├─ data
│
├─ scripts
│
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ README.md


---

# Pipeline

## 1 Data Ingestion

Stahuje data z SEC EDGAR API.


python app/ingestion/sec_ingest.py


Výstup:


data/
companies.csv
company_XXXXXXXX.json


---

## 2 Graph Builder

Vytvoří graph všech firem.


python app/graph/graph_builder.py


---

## 3 Entity Extraction

Extrahuje vztahy mezi firmami.


python app/graph/entity_extractor.py


---

# Knowledge Graph

Graph obsahuje:

Nodes

- companies

Edges

- relationships between companies

Example


Tesla → partnership → Panasonic
Microsoft → acquisition → Activision


---

# Další kroky

- document parsing
- vector embeddings
- hybrid RAG
- LangGraph orchestration
- AI agent queries

---

# Run project

Docker


docker compose up --build


API


http://localhost:8021


Docs


http://localhost:8021/docs


---

# Project goal

Vytvořit **AI systém pro analýzu finančních dokumentů a vztahů mezi firmami**.

Projekt demonstruje:

- data pipelines
- knowledge graph
- hybrid RAG
- AI orchestration

---

# Author

AI-Driven Technical Product Architect / Full-Stack Developer
