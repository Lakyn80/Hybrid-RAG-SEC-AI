import json
import os
import pandas as pd
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=DEEPSEEK_API_KEY,
    openai_api_base="https://api.deepseek.com",
    temperature=0.2
)

df = pd.read_parquet("data/clean/filings_chunks.parquet")

dataset = []

sample_df = df.sample(50)

for _, row in sample_df.iterrows():

    chunk = str(row["chunk_text"])

    prompt = f"""
Create one factual question that can be answered from this text.

Text:
{chunk}

Return only the question.
"""

    response = llm.invoke(prompt)
    question = response.content.strip()

    dataset.append({
        "question": question,
        "ground_truth": chunk[:500]
    })

with open("tests/ragas_dataset.json", "w", encoding="utf-8") as f:
    json.dump(dataset, f, indent=2)

print("Dataset created:", len(dataset))
