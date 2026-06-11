# Day 6 Notes

## Today's Goal

Generate local embeddings for document chunks using Ollama and store them in
PostgreSQL with pgvector.

## Request Flow

```text
Upload PDF
  -> Extract text
  -> Split text into chunks
  -> Send each chunk to Ollama nomic-embed-text
  -> Store embedding vector in document_chunks.embedding
  -> Store embedding_status and embedding_error
  -> Frontend shows embedded_count and per-chunk embedding status
```

## Local Model

The project uses:

```text
nomic-embed-text
```

through the local Ollama API:

```text
http://127.0.0.1:11434/api/embeddings
```

## Why Embeddings Matter

Embeddings turn text into fixed-size vectors. Similar meanings should produce
vectors that are close to each other. This is the foundation for semantic
search and RAG.

## pgvector

The database uses the pgvector extension and stores vectors in:

```text
document_chunks.embedding vector(768)
```

The next step is to embed a user's question and search for the closest chunks.

