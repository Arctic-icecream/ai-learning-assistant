# Day 7 Notes

## Today's Goal

Add semantic search over embedded chunks and create the first local RAG answer
flow.

## Search Flow

```text
User question
  -> nomic-embed-text embedding
  -> pgvector cosine distance search
  -> top_k closest chunks
  -> frontend displays source chunks and distance
```

## Answer Flow

```text
User question
  -> semantic search
  -> build context from top chunks
  -> send context + question to qwen3-coder:30b through Ollama
  -> return answer and sources
```

## New APIs

```text
POST /search
POST /answer
```

`/search` returns relevant chunks. `/answer` retrieves chunks and asks the
local LLM to answer using only those chunks.

## Concepts

- Semantic search uses meaning, not exact keyword matching.
- The query and chunks must use the same embedding model.
- pgvector's `<=>` operator computes cosine distance.
- Lower distance means the query and chunk are more semantically similar.
- RAG has two parts: retrieval first, generation second.

## Local Models

- `nomic-embed-text`: turns questions and chunks into vectors.
- `qwen3-coder:30b`: generates the first local answer from retrieved context.

