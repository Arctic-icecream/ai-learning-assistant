# Day 8 Notes

## Today's Goal

Make RAG answers easier to verify and add a way to reprocess existing
documents.

## Reprocess Flow

```text
Existing document
  -> read storage_path
  -> parse PDF again
  -> delete old chunks
  -> create fresh chunks
  -> create fresh embeddings
  -> return updated document status
```

## New API

```text
POST /documents/{document_id}/reprocess
```

This is useful for old documents that were uploaded before parsing, chunking, or
embedding existed.

## Source-Aware Answers

Answers now ask the local LLM to cite retrieved chunks with labels such as:

```text
[Source 1]
[Source 2]
```

The frontend also shows the exact sources used:

- filename
- chunk index
- vector distance
- chunk preview

## Concepts

- RAG answers should be inspectable, not magical.
- Sources help users verify whether an answer is grounded in uploaded material.
- Reprocessing is a retry mechanism for old or failed data.
- Deleting old chunks before reprocessing prevents duplicate chunks.
- Idempotent processing means running the same operation again should not create
  messy duplicate state.

