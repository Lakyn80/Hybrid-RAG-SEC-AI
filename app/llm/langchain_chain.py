from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os

MODEL_NAME = os.getenv("LLM_MODEL", "deepseek-chat")

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

def run_chain(question: str, context: str) -> str:

    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.2,
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_API_URL")
    )

    chain = prompt | llm

    response = chain.invoke({
        "question": question,
        "context": context
    })

    return response.content
