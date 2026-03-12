from fastapi import FastAPI, Header, Response
from pydantic import BaseModel

from app.api.cache_admin import router as cache_admin_router
from app.api.demo_admin import router as demo_admin_router
from app.api.question_bank import router as question_bank_router
from app.core.logger import get_logger
from app.retrieval import resources as retrieval_resources
from app.retrieval.qdrant_store import get_qdrant_client, get_runtime_collection_name
from app.retrieval.reranker import get_model as get_reranker_model
from app.router.stream_router import router as stream_router
from app.services.answer_service import answer_query

logger = get_logger(__name__)

app = FastAPI(title="Hybrid RAG SEC AI")
app.include_router(stream_router)
app.include_router(question_bank_router)
app.include_router(cache_admin_router)
app.include_router(demo_admin_router)


class AskRequest(BaseModel):
    query: str
    company: str | None = None
    form: str | None = None


@app.on_event("startup")
def startup_warmup():
    try:
        retrieval_resources.get_metadata_df()
        logger.info("startup_warmup=metadata_ready")
    except Exception as exc:
        logger.info("startup_warmup_metadata_failed=%s", exc)

    try:
        retrieval_resources.get_embedding_model()
        logger.info("startup_warmup=embedding_ready")
    except Exception as exc:
        logger.info("startup_warmup_embedding_failed=%s", exc)

    try:
        get_reranker_model()
        logger.info("startup_warmup=reranker_ready")
    except Exception as exc:
        logger.info("startup_warmup_reranker_failed=%s", exc)

    try:
        retrieval_resources.get_redis_client().ping()
        logger.info("startup_warmup=redis_ready")
    except Exception as exc:
        logger.info("startup_warmup_redis_failed=%s", exc)

    try:
        get_qdrant_client().get_collection(get_runtime_collection_name())
        logger.info("startup_warmup=qdrant_ready")
    except Exception as exc:
        logger.info("startup_warmup_qdrant_failed=%s", exc)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/ask")
def ask(
    data: AskRequest,
    response: Response,
    x_run_id: str | None = Header(default=None, alias="X-Run-ID"),
):
    result = answer_query(
        data.query,
        company_filter=data.company,
        form_filter=data.form,
        run_id=x_run_id,
    )
    if result.get("run_id"):
        response.headers["X-Run-ID"] = str(result["run_id"])

    return {
        "query": result["query"],
        "answer": result["answer"],
        "mode": result["mode"],
        "sources": result["sources_text"],
        "cache_hit": result["cache_hit"],
    }
