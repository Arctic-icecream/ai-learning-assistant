# Day 10 Notes

## Today's Goal

Turn generated flashcards into usable study assets with review mode and Anki CSV
export.

## Review Mode

The frontend flashcard list now works like a simple review deck:

```text
Question side
  -> click card
Answer side
```

Each card tracks flip state in React state, so users can reveal answers one by
one.

## Anki CSV Export

The backend exposes:

```text
GET /documents/{document_id}/flashcards/export
```

It returns a CSV file with:

```text
Question,Answer
```

The backend uses Python's `csv` module instead of manual string concatenation so
commas, quotes, and newlines are escaped correctly.

## HTTP Download

The response uses:

```text
Content-Disposition: attachment
```

This tells the browser to download the CSV as a file instead of displaying it as
plain text.

## Next Step

Add quality controls for generated flashcards, such as editing, deleting, and
regenerating individual cards.

