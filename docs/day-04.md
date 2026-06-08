# Day 4 Notes

## Today's Goal

Extract text from uploaded PDF files and store the parsing result in the
database.

## Request Flow

```text
Upload PDF
  -> Save original file to backend/storage/uploads
  -> Run pypdf text extraction
  -> Store extracted_text, text_char_count, parse_status, parse_error
  -> Return parse metadata to the frontend
  -> Show parse status in the document list
```

## Concepts

- PDF files are binary documents, not plain text files.
- A PDF parser reads page objects and attempts to extract text from each page.
- `extracted_text` is the raw material for future chunking and RAG.
- `parse_status` helps the UI and backend know whether extraction succeeded.
- `parse_error` stores the failure reason instead of losing it in logs.

## Parse Status Values

- `parsed`: text was extracted successfully.
- `empty`: the PDF was readable but no text was extracted.
- `failed`: parsing raised an error.
- `skipped`: the uploaded file was not treated as a PDF.

## Database Note

Today uses a small development-time schema upgrade with
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. This is enough for learning, but a
production project should use migrations such as Alembic.

