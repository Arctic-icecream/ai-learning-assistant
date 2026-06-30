# Day 15 - Hierarchical Document Summaries

## Goal

Generate and save grounded brief or detailed summaries for documents of
different lengths using the local Ollama chat model.

## Why Hierarchical Summarization

A long document can contain more text than a model should receive in one
prompt. Sending only the first chunks loses later chapters, while sending every
chunk at once can exceed the context window and make important details harder
to retain.

The application uses hierarchical Map-Reduce summarization:

```text
document chunks
  -> Map: summarize each group of 6 chunks
  -> Reduce: merge groups of up to 8 note sets
  -> repeat Reduce when needed
  -> write the final brief or detailed summary
```

Documents with 6 or fewer chunks go directly to the final summary prompt and
use one model call.

For example, 13 chunks become three Map batches: 6, 6, and 1. Those three note
sets fit in one final prompt, so the total is four local model calls.

## Grounding Rules

Every summarization prompt tells the model to:

- use only the supplied document text or intermediate notes
- preserve definitions, relationships, examples, and qualifications
- avoid adding outside facts
- write in the same language as the source

These instructions reduce hallucination, but generated summaries should still
be treated as study aids rather than authoritative replacements for the source.

## Summary Modes

`brief` produces:

- a short overview
- 5 to 8 key points
- a review checklist

`detailed` produces:

- an overview
- titled main-concept sections
- definitions, relationships, examples, and qualifications
- a review checklist

Both are returned as Markdown and rendered safely with `react-markdown`.

## Database

The new `document_summaries` table stores every generated version:

- `document_id`: source document
- `mode`: `brief` or `detailed`
- `content`: generated Markdown
- `model_name`: local model used
- `source_chunk_count`: number of document chunks processed
- `model_call_count`: total Map, Reduce, and final calls
- `created_at`: generation time

Generating another summary creates a history entry instead of overwriting the
previous result. Reprocessing a document deletes its summaries because they no
longer describe the current extracted text.

## API

```text
GET  /documents/{document_id}/summaries
POST /documents/{document_id}/summaries/generate
```

Generate request:

```json
{
  "mode": "brief"
}
```

Pydantic restricts the mode to `brief` or `detailed`, so invalid values are
rejected before the endpoint executes.

## Frontend State

The summary panel stores:

- the selected document
- the current mode
- generation status
- summary history

The segmented control changes mode. `Generate Summary` sends the selected mode
to FastAPI, and the returned database record is inserted at the beginning of
the visible history.

## Tests

`backend/tests/test_summary_generation.py` mocks the Ollama HTTP call. It checks
batch order, one-call short summaries, four-call summarization for 13 chunks,
and invalid mode rejection without requiring the model to run.

Run all backend tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Click `Summaries` on a parsed document.
3. Select `Brief` and generate a summary.
4. Select `Detailed` and generate another summary.
5. Confirm both versions show their mode, chunk count, model call count, and
   creation time.
6. Refresh the browser, reopen `Summaries`, and confirm the history remains.
