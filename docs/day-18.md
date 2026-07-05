# Day 18 - Document Deletion and Storage Management

## Goal

Make stored learning data visible and allow one document to be deleted without
resetting the entire development database.

## APIs

```text
GET    /storage/stats
DELETE /documents/{document_id}
```

The storage endpoint reports document and artifact counts, tracked file bytes,
actual upload-directory bytes, and files not referenced by PostgreSQL.

## Cascade Deletion

`documents` is the root record. Related tables use PostgreSQL foreign keys with
`ON DELETE CASCADE`:

```text
document
  -> chunks and embeddings
  -> summaries -> mind maps
  -> flashcards
  -> quiz questions -> quiz responses
  -> quiz attempts -> quiz responses
```

Deleting the document row lets PostgreSQL remove this related data inside the
same database transaction. The application does not issue separate delete
requests for every table.

## Database and File Transactions

PostgreSQL can roll back database changes, but it cannot restore a file deleted
by Windows. The delete endpoint therefore uses a compensating workflow:

```text
validate file path
  -> rename upload to a hidden .deleting file
  -> delete document row and commit database transaction
  -> permanently remove the staged file
```

If the database commit fails, the staged file is renamed back to its original
path. If final file cleanup fails after a successful database commit, the API
returns success with a cleanup warning. Storage statistics then count the
remaining staged file as an orphan.

Renaming occurs inside the same upload directory and filesystem, where it is
normally an atomic operation.

## Path Safety

Before staging, the resolved file path must be inside
`backend/storage/uploads`. A database value pointing elsewhere is rejected.
This prevents a damaged or malicious record from deleting unrelated files.

Missing upload files do not block database cleanup. The response reports that
the file was already missing.

## Storage Statistics

The dashboard shows:

- document count
- tracked file size from database records
- actual upload-directory size
- embedded chunks versus total chunks
- summaries, mind maps, flashcards, and quiz attempts
- orphan file count

Tracked and actual bytes can differ when a file is missing, an old upload has no
database row, or a final cleanup operation failed.

## Frontend Deletion Flow

Each document has a trash icon with an accessible label and tooltip. Clicking
it opens a confirmation dialog listing the related learning artifacts that will
be removed.

After success, React reloads the document list and storage statistics. If the
deleted document was visible in a chunk, summary, mind-map, flashcard, or quiz
panel, those states are cleared so the page cannot display stale data.

## Tests

`backend/tests/test_document_storage.py` uses temporary directories and checks:

- staging and permanent cleanup
- restoration after a simulated database failure
- missing-file handling
- rejection of paths outside the upload directory

Temporary files disappear after each test. Existing uploaded learning files
are not deleted by the test suite.

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Note the current document count and disk usage.
3. Upload a small disposable test document.
4. Generate at least one derived artifact such as a summary.
5. Click the document's trash icon and inspect the confirmation dialog.
6. Confirm deletion.
7. Verify the document, file, and related artifacts disappear and statistics
   decrease.

Use a disposable test document for this check. Deletion is permanent after the
database transaction and file cleanup complete.
