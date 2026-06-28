# Day 14 - Safe Web Page Import

## Goal

Import a public web page into the same knowledge pipeline used by uploaded
files while keeping the source URL and applying basic server-side request
forgery protections.

## Request Flow

```text
Browser URL input
  -> POST /documents/import-url
  -> validate scheme and resolved addresses
  -> download HTML with limits
  -> save an HTML snapshot
  -> remove page chrome and extract useful text
  -> chunk, embed, and store in PostgreSQL
  -> use with search, RAG, flashcards, and quizzes
```

## Why Save an HTML Snapshot

The imported HTML is written to `backend/storage/uploads` before parsing. A
later `Reprocess` action uses this saved snapshot instead of silently fetching
a newer version of the page. That makes processing reproducible even if the
live page changes or disappears.

The stored upload directory remains excluded from Git. PostgreSQL stores the
metadata, extracted text, chunks, embeddings, and source URL.

## Database Source Metadata

The `documents` table now has:

- `source_type`: `upload` or `url`
- `source_url`: the final URL after redirects, or `null` for uploaded files

FastAPI adds these columns to an existing development database during startup,
so previous document rows remain available and default to `upload`.

## HTML Extraction

BeautifulSoup turns HTML into a navigable DOM tree. Before extracting text,
the parser removes elements that usually add noise:

```text
script, style, noscript, svg, nav, footer, header, form, aside
```

It then prefers `main` or `article` content and extracts headings, paragraphs,
list items, quotes, preformatted text, and tables. Table cells are separated by
tabs and rows by line breaks.

Raw HTML is not embedded because markup, menus, scripts, and repeated layout
text waste vector space and reduce retrieval quality.

## SSRF Protection

The backend, not the browser, downloads the URL. Without validation, a user
could ask it to request internal services such as `http://127.0.0.1:8000`.

This version:

- allows only HTTP and HTTPS
- rejects URLs containing credentials
- resolves the hostname and accepts only global IP addresses
- validates every redirect destination again
- limits redirects to 5
- limits the response to 2 MB
- uses a 15-second timeout
- accepts only HTML content types

This is appropriate for the local learning project. A public production
service should additionally use an egress proxy or connect to a pinned,
validated address to defend against advanced DNS rebinding attacks.

## Current Limits

- JavaScript-rendered pages may have little useful text in their initial HTML.
- Login-protected pages are not supported.
- Importing a page does not crawl links to other pages.
- Reprocess uses the saved snapshot; it does not refresh the source URL.

## Automated Checks

`backend/tests/test_web_parser.py` uses `httpx.MockTransport`, so tests do not
depend on the public internet. The tests cover content cleanup, blocked local
addresses, successful HTML download, and a public URL redirecting to a private
address.

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Enter a public article URL under `Import a public web page`.
3. Confirm the result shows a title, source URL, character count, chunks, and
   embedded chunks.
4. Open the chunk preview and verify menus and scripts are absent.
5. Ask a question whose answer appears in the imported page.
6. Refresh the browser and confirm the document and source link remain.
