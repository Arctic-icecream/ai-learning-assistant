# Day 5 Notes

## Today's Goal

Split extracted PDF text into smaller chunks and store them in a new
`document_chunks` table.

## Request Flow

```text
Upload PDF
  -> Extract text
  -> chunk_text(extracted_text)
  -> Insert rows into document_chunks
  -> Return chunk_count
  -> Frontend shows chunk count and chunk previews
```

## Why Chunking Matters

Large PDFs are too long to send to an AI model every time. RAG systems search
for the most relevant chunks first, then send only those chunks to the model.

## Chunk Settings

The first version uses:

- `chunk_size = 1200` characters
- `overlap = 200` characters

Overlap keeps context from being lost when an idea crosses a chunk boundary.

## Database Relationship

One document can have many chunks:

```text
documents.id
  -> document_chunks.document_id
```

This is a one-to-many relationship. The `chunk_index` field preserves the
original reading order.

## Next Step

The next major step is embeddings. Each chunk will get a vector so the app can
find relevant chunks for a user's question.

