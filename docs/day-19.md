# Day 19 - Background Processing Jobs

Today we separated "upload accepted" from "document processing finished".

## Why

Before today, `/documents/upload` waited for parsing, OCR, chunking, and embedding before the browser got a response. Large PDFs could make the UI feel frozen.

Now the backend creates a `processing_jobs` row and returns immediately with HTTP `202 Accepted`. The document is processed in the background, and the frontend polls `/jobs/{job_id}` to show progress.

## What Changed

- `backend/app/models.py`
  - Added `ProcessingJob`.
  - This stores job status, stage, message, progress, and errors.

- `backend/app/processing.py`
  - Moved document processing out of `main.py`.
  - Handles reset, text extraction, OCR, chunking, embedding, and job progress updates.

- `backend/app/main.py`
  - Upload, web import, and reprocess now create background jobs.
  - Added `GET /jobs/{job_id}`.
  - On backend startup, unfinished jobs are marked failed as interrupted.

- `frontend/src/app/page.tsx`
  - Tracks active jobs.
  - Polls the backend every second while jobs are running.
  - Shows progress bars for upload, web import, and document reprocessing.

- `scripts/reset-dev-data.ps1`
  - Clears `processing_jobs` together with documents and generated artifacts.

## Key Idea

`202 Accepted` means: the backend accepted the request, but the work is not finished yet.

The frontend flow is now:

1. Upload the file.
2. Receive `{ document, job }`.
3. Poll `/jobs/{job_id}`.
4. Refresh documents when the job reaches `completed` or `failed`.

This is the first step toward a real production-style worker architecture. Later, a durable queue such as Redis + Celery can replace FastAPI background tasks.
