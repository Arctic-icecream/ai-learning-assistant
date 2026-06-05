# AI Learning Assistant

An AI-powered learning assistant built step by step with:

- Frontend: Next.js + React
- Backend: Python FastAPI
- Database: PostgreSQL
- Vector search: pgvector
- AI: OpenAI API first, local models later

## Day 1 Goal

Set up the project structure, Git workflow, and minimal frontend/backend skeletons.

## Run Locally

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open:

- Frontend: http://localhost:3000
- Backend health check: http://127.0.0.1:8000/health

## Planned MVP

1. Upload a PDF.
2. Extract text from the PDF.
3. Split the text into chunks.
4. Store chunks and embeddings.
5. Ask questions using RAG.
6. Generate summaries, mind maps, Anki cards, and exam questions.
