# Day 9 Notes

## Today's Goal

Generate study flashcards from uploaded course materials and store them in the
database.

## Flashcard Flow

```text
Document chunks
  -> build course-material context
  -> send context to local qwen3-coder:30b
  -> request JSON flashcards
  -> validate question/answer pairs
  -> store cards in flashcards table
  -> frontend displays cards
```

## New APIs

```text
GET /documents/{document_id}/flashcards
POST /documents/{document_id}/flashcards/generate
```

The generate endpoint replaces existing flashcards for the document so repeated
generation does not create duplicates.

## Database Table

```text
flashcards
  id
  document_id
  question
  answer
  source_chunk_index
  created_at
```

## Concepts

- Flashcards are reusable learning artifacts, not one-off chat responses.
- They should be tied to a source document.
- The model returns JSON so the backend can store structured cards.
- Reprocessing a document clears old cards because the chunks may change.

## Next Step

Export generated cards to a format that can be imported into Anki.

