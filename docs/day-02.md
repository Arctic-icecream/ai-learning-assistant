# Day 2 Notes

## Today's Goal

Connect the Next.js frontend to the FastAPI backend for the first time.

## Request Flow

```text
Browser
  -> Next.js page on http://localhost:3000
  -> fetch("http://127.0.0.1:8000/health")
  -> FastAPI /health route
  -> JSON response
  -> React state update
  -> UI re-renders
```

## Concepts

- API: a contract that lets one program talk to another program.
- GET request: an HTTP request used to read data.
- JSON: a data format commonly used between frontend and backend.
- `fetch`: the browser API used to make HTTP requests.
- CORS: browser security rules that control which websites can read API
  responses from another origin.
- `useState`: a React hook for storing UI state.
- `"use client"`: a Next.js directive that allows browser-side interactivity.

## States Used Today

- `idle`: no request has been made.
- `loading`: the request is currently running.
- `success`: the backend responded successfully.
- `error`: the frontend could not get a successful response.

## Git Habit

Today's work should be committed and pushed after verification so GitHub shows
daily progress.

