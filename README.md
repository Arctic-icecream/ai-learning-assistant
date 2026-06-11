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

One-click start on Windows:

```powershell
.\start-dev.cmd
```

One-click stop on Windows:

```powershell
.\stop-dev.cmd
```

Clear uploaded development test data:

```powershell
.\reset-dev-data.cmd
```

The start script opens Ollama and Docker Desktop if needed, launches
PostgreSQL with Docker Compose, then opens separate PowerShell windows for the
FastAPI backend and Next.js frontend.
The stop script shuts services down without deleting database data. The reset
script clears the `documents` table and removes uploaded test files.

If the frontend shows `Failed to fetch`, check that:

1. Ollama started successfully and has `nomic-embed-text`.
2. Docker Desktop started successfully.
3. `start-dev.cmd` started PostgreSQL successfully.
4. The backend window shows `Application startup complete`.
5. http://127.0.0.1:8000/health returns JSON.

API checks:

```powershell
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/documents
```

Database:

```powershell
docker compose up -d
```

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
