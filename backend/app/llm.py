import os
import json
import re

import httpx

from .embeddings import OLLAMA_URL

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3-coder:30b")


def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are an AI learning assistant. Answer the question using only the provided context.

If the context does not contain enough information, say that the uploaded material does not provide enough information.
When you use information from the context, cite it with source labels like [Source 1] or [Source 2].

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


def extract_json_array(text: str) -> list[dict[str, str]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\[[\s\S]*\]", cleaned)
    if not match:
        raise ValueError("Model did not return a JSON array")

    data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("Flashcard response must be a JSON array")

    return data


def generate_flashcards(context: str, count: int) -> list[dict[str, str]]:
    prompt = f"""Create {count} study flashcards from the provided course material.

Return only a JSON array. Do not include markdown or commentary.

Each item must have:
- "question": a clear recall question
- "answer": a concise answer grounded in the material

Course material:
{context}

JSON array:"""

    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=240,
    )
    response.raise_for_status()

    cards = extract_json_array(response.json()["response"])
    normalized_cards: list[dict[str, str]] = []
    for card in cards[:count]:
        question = str(card.get("question", "")).strip()
        answer = str(card.get("answer", "")).strip()
        if question and answer:
            normalized_cards.append({"question": question, "answer": answer})

    if not normalized_cards:
        raise ValueError("No valid flashcards were generated")

    return normalized_cards
