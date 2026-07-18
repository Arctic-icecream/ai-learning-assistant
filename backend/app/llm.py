import os
import json
import re

import httpx

from .embeddings import OLLAMA_URL

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3-coder:30b")
SUMMARY_MAP_CHUNKS = 6
SUMMARY_REDUCE_ITEMS = 8
MIND_MAP_MAX_DEPTH = 4
MIND_MAP_MAX_CHILDREN = 5
MIND_MAP_MAX_NODES = 40


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


def format_chat_history(messages: list[dict[str, str]]) -> str:
    if not messages:
        return "No previous conversation."

    lines = []
    for message in messages[-8:]:
        role = message["role"].strip().title()
        content = message["content"].strip()
        if role and content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No previous conversation."


def generate_chat_answer(
    question: str, context: str, history: list[dict[str, str]]
) -> str:
    prompt = f"""You are an AI learning assistant inside a saved study chat.

Answer the current question using only the provided retrieved context and the conversation history.
The conversation history helps you resolve follow-up wording like "it", "that idea", or "the previous protocol".
If the retrieved context does not contain enough information, say that the uploaded material does not provide enough information.
When you use information from the retrieved context, cite it with source labels like [Source 1] or [Source 2].

Conversation history:
{format_chat_history(history)}

Retrieved context:
{context}

Current question:
{question}

Answer:"""

    return request_local_model(prompt, timeout=180)


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


def extract_json_object(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError("Model did not return a JSON object")

    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Mind map response must be a JSON object")
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


def generate_quiz_questions(context: str, count: int) -> list[dict[str, object]]:
    prompt = f"""Create {count} exam-style questions from the provided course material.

Return only a JSON array. Do not include markdown or commentary.

Use a mix of question types:
- "multiple_choice"
- "short_answer"
- "true_false"

Each item must have:
- "question_type": one of the three types above
- "question": the exam question
- "choices": an array of answer choices for multiple_choice or true_false, otherwise []
- "correct_answer": the correct answer
- "explanation": a short explanation grounded in the material

For multiple_choice and true_false, correct_answer must exactly match one item in choices.

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
        timeout=300,
    )
    response.raise_for_status()

    questions = extract_json_array(response.json()["response"])
    normalized_questions: list[dict[str, object]] = []
    allowed_types = {"multiple_choice", "short_answer", "true_false"}

    for question_item in questions[:count]:
        question_type = str(question_item.get("question_type", "")).strip()
        if question_type not in allowed_types:
            question_type = "short_answer"

        question = str(question_item.get("question", "")).strip()
        correct_answer = str(question_item.get("correct_answer", "")).strip()
        explanation = str(question_item.get("explanation", "")).strip()
        raw_choices = question_item.get("choices", [])
        choices = [
            str(choice).strip()
            for choice in raw_choices
            if str(choice).strip()
        ] if isinstance(raw_choices, list) else []

        if question and correct_answer and explanation:
            normalized_questions.append(
                {
                    "question_type": question_type,
                    "question": question,
                    "choices": choices,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                }
            )

    if not normalized_questions:
        raise ValueError("No valid quiz questions were generated")

    return normalized_questions


def request_local_model(prompt: str, timeout: int = 300) -> str:
    response = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["response"].strip()


def group_items(items: list[str], group_size: int) -> list[list[str]]:
    if group_size < 1:
        raise ValueError("group_size must be positive")
    return [items[index:index + group_size] for index in range(0, len(items), group_size)]


def summarize_source_batch(chunks: list[str]) -> str:
    context = "\n\n".join(
        f"Chunk {index + 1}:\n{chunk}" for index, chunk in enumerate(chunks)
    )
    prompt = f"""Summarize this portion of a learning document using only the provided text.

Preserve important definitions, relationships, examples, and qualifications.
Do not add outside facts. Write compact factual notes in the source language.

Document portion:
{context}

Factual notes:"""
    return request_local_model(prompt)


def reduce_summary_notes(notes: list[str]) -> str:
    context = "\n\n".join(
        f"Note set {index + 1}:\n{note}" for index, note in enumerate(notes)
    )
    prompt = f"""Merge these notes from one learning document into a smaller coherent set of notes.

Remove repetition while preserving important definitions, relationships, examples, and qualifications.
Use only the supplied notes and write in their language.

Notes:
{context}

Merged notes:"""
    return request_local_model(prompt)


def write_final_summary(notes: list[str], mode: str) -> str:
    context = "\n\n".join(notes)
    if mode == "brief":
        format_instructions = """Create a concise Markdown study summary with:
- a short overview paragraph
- 5 to 8 key bullet points
- a short review checklist"""
    else:
        format_instructions = """Create a detailed Markdown study summary with:
- an overview
- clearly titled sections for the main concepts
- important definitions, relationships, examples, and qualifications
- a final review checklist"""

    prompt = f"""{format_instructions}

Use only the supplied document notes. Do not add outside facts.
Write in the same language as the notes. Do not wrap the result in a code fence.

Document notes:
{context}

Final summary:"""
    return request_local_model(prompt)


def generate_document_summary(chunks: list[str], mode: str) -> tuple[str, int]:
    if not chunks:
        raise ValueError("Cannot summarize an empty document")
    if mode not in {"brief", "detailed"}:
        raise ValueError("Summary mode must be brief or detailed")

    model_call_count = 0
    if len(chunks) <= SUMMARY_MAP_CHUNKS:
        return write_final_summary(chunks, mode), 1

    notes = []
    for batch in group_items(chunks, SUMMARY_MAP_CHUNKS):
        notes.append(summarize_source_batch(batch))
        model_call_count += 1

    while len(notes) > SUMMARY_REDUCE_ITEMS:
        reduced_notes = []
        for batch in group_items(notes, SUMMARY_REDUCE_ITEMS):
            reduced_notes.append(reduce_summary_notes(batch))
            model_call_count += 1
        notes = reduced_notes

    summary = write_final_summary(notes, mode)
    return summary, model_call_count + 1


def normalize_mind_map_tree(raw_tree: object) -> tuple[dict[str, object], int]:
    node_count = 0

    def normalize_node(raw_node: object, depth: int) -> dict[str, object]:
        nonlocal node_count
        if not isinstance(raw_node, dict):
            raise ValueError("Every mind map node must be an object")

        title = str(raw_node.get("title", "")).strip()
        if not title:
            raise ValueError("Every mind map node must have a title")

        node_count += 1
        detail = str(raw_node.get("detail", "")).strip()
        normalized: dict[str, object] = {
            "title": title[:80],
            "detail": detail[:240],
            "children": [],
        }

        raw_children = raw_node.get("children", [])
        if not isinstance(raw_children, list):
            raise ValueError("Mind map children must be an array")

        children: list[dict[str, object]] = []
        if depth < MIND_MAP_MAX_DEPTH:
            for child in raw_children[:MIND_MAP_MAX_CHILDREN]:
                if node_count >= MIND_MAP_MAX_NODES:
                    break
                children.append(normalize_node(child, depth + 1))
        normalized["children"] = children
        return normalized

    tree = normalize_node(raw_tree, 1)
    return tree, node_count


def generate_mind_map(summary: str) -> tuple[dict[str, object], int]:
    prompt = f"""Create a study mind map from this document summary.

Return only one JSON object. Do not include markdown or commentary.
Use the same language as the summary and only information found in it.

Every node must have exactly these fields:
- "title": a short label, at most 8 words
- "detail": one concise explanatory sentence, or an empty string
- "children": an array of child nodes

Structure rules:
- one root representing the whole document
- at most {MIND_MAP_MAX_DEPTH} levels including the root
- at most {MIND_MAP_MAX_CHILDREN} children per node
- group related concepts under meaningful parent nodes
- avoid duplicate concepts

Document summary:
{summary}

JSON mind map:"""
    raw_tree = extract_json_object(request_local_model(prompt))
    return normalize_mind_map_tree(raw_tree)
