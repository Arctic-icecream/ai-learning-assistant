# Day 13 - Word and PowerPoint Parsing

## Goal

Extend the existing PDF pipeline so the application also accepts modern Word
and PowerPoint files without duplicating chunking, embedding, or database code.

## Supported Formats

```text
.pdf  -> pypdf
.docx -> python-docx
.pptx -> python-pptx
```

The old binary `.doc` and `.ppt` formats are not supported. Text inside images
is also not extracted yet; that requires the separate OCR pipeline.

## Parser Boundary

`document_parser.py` contains a parser registry:

```text
file extension -> parser function
```

Each parser receives a file path and returns one plain-text string. The rest of
the application does not need to know whether that text came from a PDF page, a
Word paragraph, or a PowerPoint shape.

```text
Upload
  -> validate extension
  -> select parser
  -> extract plain text
  -> split into 1200-character chunks with 200-character overlap
  -> create 768-dimensional embeddings
  -> store document chunks in PostgreSQL
```

## Word Structure

A `.docx` document contains block-level elements. The parser walks paragraphs
and tables in document order:

- non-empty paragraph text becomes one text block
- cells in a table row are separated with tabs
- table rows are separated with line breaks
- blocks are separated with blank lines

This preserves enough structure for chunking and retrieval without storing
Word-specific XML in the knowledge base.

## PowerPoint Structure

A `.pptx` presentation contains slides, and each slide contains shapes. The
parser walks slides and shapes in order:

- each non-empty slide starts with `Slide N`
- text frames contribute their visible text
- table cells and rows use the same separators as Word tables

The slide labels help a retrieved chunk retain its presentation location.

## Frontend and Backend Validation

The file input uses `accept` to make the file picker show supported formats.
This is only user-interface guidance and can be bypassed.

FastAPI independently checks the filename extension before reading or storing
the upload. Unsupported files receive HTTP 400, so the backend remains the
source of truth.

## Automated Tests

`backend/tests/test_document_parsers.py` creates real temporary Word and
PowerPoint files. It verifies paragraph, slide, and table extraction order and
also confirms unsupported extensions are rejected. Temporary files disappear
when each test finishes.

Run the tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Upload one `.docx` and one `.pptx` file.
3. Confirm both records show `parsed`, a non-zero character count, chunks, and
   embedded chunks.
4. Click the chunk count and inspect the extracted content.
5. Ask a question whose answer exists only in one of the new files.
