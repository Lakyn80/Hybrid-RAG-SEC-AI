from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(dotenv_path=ENV_FILE, override=False)

prompt = ChatPromptTemplate.from_template(
"""Answer the question using the context.

Question:
{question}

Context:
{context}

Rules:
- Use only the provided context
- If information is missing say so
- Answer concisely
"""
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


def build_chat_llm(temperature: float = 0.2) -> ChatOpenAI:
    model_name, api_key, base_url = get_llm_settings()

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )


def run_chain(question: str, context: str) -> str:
    llm = build_chat_llm(temperature=0.2)

    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "context": context
    })

    return response.content
