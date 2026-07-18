# Day 20 - Study Chat With Conversation Memory

Today we added saved multi-turn study chats.

## Why

The previous `/answer` endpoint handled one isolated question at a time. That works for direct questions, but it cannot understand follow-ups like:

- "Give me an example."
- "How is it different from DSR?"
- "Turn that into exam questions."

A study assistant needs memory inside a learning session.

## What Changed

- `backend/app/models.py`
  - Added `ChatSession`.
  - Added `ChatMessage`.

- `backend/app/main.py`
  - Added APIs to create and list sessions for a document.
  - Added APIs to read and send chat messages.
  - Study chat retrieval is scoped to the selected document.

- `backend/app/llm.py`
  - Added conversation-history formatting.
  - Added `generate_chat_answer`, which passes recent messages plus retrieved chunks to the local model.

- `frontend/src/app/page.tsx`
  - Added a Study Chat panel.
  - Added session selection, new chat creation, saved message loading, and source display.

- `scripts/reset-dev-data.ps1`
  - Clears chat sessions and messages when resetting local test data.

## Data Model

`chat_sessions` is the parent table.

`chat_messages` is the child table.

One session can have many messages:

```text
chat_sessions.id
  -> chat_messages.session_id
```

This is a classic one-to-many relationship.

## RAG Flow

When you send a study chat message:

1. The user message is saved.
2. The backend retrieves relevant chunks from the selected document.
3. The backend loads the recent chat history.
4. The local model receives history + retrieved context + current question.
5. The assistant answer is saved with source chunk snapshots.

The important change is that follow-up questions now have memory.
