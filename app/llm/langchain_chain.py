from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
import time
from contextlib import contextmanager
from uuid import uuid4
from dotenv import load_dotenv

from app.core.logger import build_log_payload, get_logger, log_structured
from app.retrieval.resources import get_redis_client

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_FILE, override=False)

logger = get_logger(__name__)
LLM_LIMIT_PREFIX = "llm:slot"
LLM_SLOT_LEASE_SECONDS = 300
LLM_ACQUIRE_TIMEOUT_SECONDS = 120

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a financial document analysis assistant specialized in SEC filings.

Your task is to answer questions strictly using the provided filing excerpts.

Rules:

1. Use ONLY the information explicitly stated in the context.
2. Do NOT use external knowledge.
3. Do NOT add facts that are not stated in the context.
4. You may paraphrase and synthesize multiple excerpts into a clearer summary, but only if the underlying facts are explicitly present in the context.
5. If a detail is not explicitly stated in the excerpts, do NOT include it.
6. If the answer cannot be found in the context, say exactly:
   "The provided filings do not contain this information."
7. Focus only on the information relevant to the question.
8. Do not summarize unrelated sections of the filing.
9. Write like a concise analyst note for a human reader.
10. Do not add introductory text like "Based solely on the provided excerpts".

Answer style:

- Return a concise human-readable summary.
- Use either:
  a) one short paragraph followed by 3-5 bullet points, or
  b) 3-5 bullet points only
- combine overlapping facts into cleaner themes instead of repeating similar excerpt language
- do not mention excerpt numbers in the final answer
- factual statements only
- avoid speculation""",
        ),
        (
            "human",
            """Question:
{question}

Context:
{context}""",
        ),
    ]
)

def normalize_base_url(raw_url: str | None) -> str | None:
    if not raw_url:
        return None

    base_url = raw_url.strip().rstrip("/")
    suffix = "/chat/completions"

    if base_url.endswith(suffix):
        return base_url[: -len(suffix)]

    return base_url


def get_llm_settings() -> tuple[str, str, str | None]:
    model_name = str(os.getenv("LLM_MODEL") or "").strip() or "deepseek-chat"
    api_key = str(os.getenv("DEEPSEEK_API_KEY") or "").strip()
    base_url = normalize_base_url(
        str(os.getenv("LLM_API_URL") or "").strip() or "https://api.deepseek.com/chat/completions"
    )

    if not api_key:
        raise ValueError("Missing DEEPSEEK_API_KEY for the configured DeepSeek provider.")

    return model_name, api_key, base_url


def build_chat_llm(temperature: float = 0.0) -> ChatOpenAI:
    model_name, api_key, base_url = get_llm_settings()

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )


def get_llm_max_concurrency() -> int:
    try:
        return max(1, int(str(os.getenv("LLM_MAX_CONCURRENCY") or "2").strip()))
    except ValueError:
        return 2


def _release_slot(slot_key: str, token: str) -> None:
    try:
        get_redis_client().eval(
            """
            if redis.call('get', KEYS[1]) == ARGV[1] then
                return redis.call('del', KEYS[1])
            end
            return 0
            """,
            1,
            slot_key,
            token,
        )
    except Exception as exc:
        logger.info("llm_limiter_release_failed=%s", exc)


@contextmanager
def distributed_llm_limiter():
    token = uuid4().hex
    deadline = time.time() + LLM_ACQUIRE_TIMEOUT_SECONDS
    slot_key: str | None = None

    try:
        client = get_redis_client()
    except Exception as exc:
        logger.info("llm_limiter_unavailable=%s", exc)
        yield
        return

    while time.time() < deadline and slot_key is None:
        for slot_index in range(get_llm_max_concurrency()):
            candidate_key = f"{LLM_LIMIT_PREFIX}:{slot_index}"
            try:
                acquired = client.set(
                    candidate_key,
                    token,
                    nx=True,
                    ex=LLM_SLOT_LEASE_SECONDS,
                )
            except Exception as exc:
                logger.info("llm_limiter_acquire_failed=%s", exc)
                acquired = False

            if acquired:
                slot_key = candidate_key
                break

        if slot_key is None:
            time.sleep(0.1)

    if slot_key is None:
        raise TimeoutError("Global LLM concurrency limit reached.")

    try:
        yield
    finally:
        _release_slot(slot_key, token)


def extract_usage_metrics(response) -> dict:
    usage_metadata = getattr(response, "usage_metadata", None) or {}
    response_metadata = getattr(response, "response_metadata", None) or {}
    token_usage = {}

    if isinstance(response_metadata, dict):
        token_usage = (
            response_metadata.get("token_usage")
            or response_metadata.get("usage")
            or {}
        )

    prompt_tokens = usage_metadata.get("input_tokens") or token_usage.get("prompt_tokens")
    completion_tokens = usage_metadata.get("output_tokens") or token_usage.get("completion_tokens")
    total_tokens = usage_metadata.get("total_tokens") or token_usage.get("total_tokens")

    return {
        "prompt_tokens": int(prompt_tokens) if prompt_tokens is not None else None,
        "completion_tokens": int(completion_tokens) if completion_tokens is not None else None,
        "total_tokens": int(total_tokens) if total_tokens is not None else None,
    }


def run_chain(
    question: str,
    context: str,
    *,
    run_id: str | None = None,
    retrieved_documents: list[str] | None = None,
) -> str:
    llm = build_chat_llm(temperature=0.0)

    chain = prompt | llm

    start_time = time.time()

    try:
        with distributed_llm_limiter():
            response = chain.invoke({
                "question": question,
                "context": context,
            })
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.exception(
            build_log_payload(
                "llm_error",
                run_id=run_id,
                query=question,
                model=getattr(llm, "model_name", None) or getattr(llm, "model", None),
                latency_ms=latency_ms,
                retrieved_documents=retrieved_documents or [],
                error=str(exc),
            )
        )
        raise

    response_text = str(getattr(response, "content", "") or "")
    latency_ms = round((time.time() - start_time) * 1000, 2)
    usage = extract_usage_metrics(response)

    log_structured(
        logger,
        "llm_call",
        run_id=run_id,
        query=question,
        model=getattr(llm, "model_name", None) or getattr(llm, "model", None),
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
        total_tokens=usage["total_tokens"],
        prompt_length=len(str(question or "")) + len(str(context or "")),
        completion_length=len(response_text),
        latency_ms=latency_ms,
        retrieved_documents=retrieved_documents or [],
        response_length=len(response_text),
    )

    return response_text
