# Day 3 Notes

## Today's Goal

Upload a file from the Next.js frontend, receive it in the FastAPI backend,
save the file on disk, and store document metadata in PostgreSQL.

## Request Flow

```text
Browser file input
  -> FormData
  -> POST /documents/upload
  -> FastAPI UploadFile
  -> Save file to backend/storage/uploads
  -> Insert metadata into PostgreSQL documents table
  -> Return document id and metadata as JSON
  -> React displays the upload result
```

## Why Not Store the Whole PDF in PostgreSQL?

For this project, PostgreSQL stores metadata and relationships. The uploaded
file itself is saved on disk for local development. In production, this would
usually become object storage such as S3 or MinIO.

## Concepts

- POST: an HTTP method used when the client sends data to the server.
- `multipart/form-data`: the request format browsers use for file uploads.
- `FormData`: a browser API for building multipart requests.
- `UploadFile`: FastAPI's file upload type.
- SQLAlchemy model: a Python class that describes a database table.
- Database session: the unit used to add, commit, and query database records.
- Docker Compose: a way to run supporting services such as PostgreSQL.

## Documents Table

The first version of the `documents` table stores:

- original filename
- stored filename
- content type
- file size
- storage path
- creation time

