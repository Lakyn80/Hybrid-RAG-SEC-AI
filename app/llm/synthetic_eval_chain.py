import json
import re

from langchain_core.prompts import ChatPromptTemplate

from app.llm.langchain_chain import build_chat_llm

prompt = ChatPromptTemplate.from_template(
"""You are generating high-quality synthetic evaluation data for a production SEC filings RAG system.

Return exactly one JSON object with keys:
- question
- reference
- quality_score
- warmup_eligible

Rules:
- Use only the provided chunk text.
- The question must be answerable directly from the chunk.
- The question must be concise and natural.
- Do not mention "chunk", "text above", "passage", or "document excerpt".
- The reference must be a concise factual answer grounded in the chunk.
- quality_score must be a float between 0 and 1.
- warmup_eligible must be true only if the question is clear, factual, and safe for runtime warm-up.

Metadata:
- company: {company}
- form: {form}
- filing_date: {filing_date}
- query_type: {query_type}

Chunk text:
{chunk_text}
"""
)


def _extract_json_object(raw_text: str) -> dict | None:
    text = str(raw_text or "").strip()
    if not text:
        return None

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def generate_synthetic_eval_sample(
    *,
    company: str,
    form: str,
    filing_date: str,
    query_type: str,
    chunk_text: str,
) -> dict | None:
    llm = build_chat_llm(temperature=0.0)
    chain = prompt | llm

    response = chain.invoke(
        {
            "company": company,
            "form": form,
            "filing_date": filing_date,
            "query_type": query_type,
            "chunk_text": chunk_text,
        }
    )

    return _extract_json_object(response.content)
