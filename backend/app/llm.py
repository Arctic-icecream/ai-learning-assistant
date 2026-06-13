import os

import httpx

from .embeddings import OLLAMA_URL

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3-coder:30b")


def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are an AI learning assistant. Answer the question using only the provided context.

If the context does not contain enough information, say that the uploaded material does not provide enough information.

Context:
{context}

Question:
{question}

Answer:"""

    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"].strip()

