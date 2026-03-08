from fastapi import FastAPI
from pydantic import BaseModel

from app.router.stream_router import router as stream_router
from app.services.answer_service import answer_query


app = FastAPI(title="Hybrid RAG SEC AI")
app.include_router(stream_router)


class AskRequest(BaseModel):
    query: str
    company: str | None = None
    form: str | None = None


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask(data: AskRequest):
    result = answer_query(
        data.query,
        company_filter=data.company,
        form_filter=data.form,
    )

    return {
        "query": result["query"],
        "answer": result["answer"],
        "mode": result["mode"],
        "sources": result["sources_text"],
        "cache_hit": result["cache_hit"],
    }
