from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .chunker import chunk_text
from .database import Base, engine, get_db
from .embeddings import create_embedding
from .llm import generate_answer
from .models import Document, DocumentChunk
from .pdf_parser import extract_pdf_text

app = FastAPI(title="AI Learning Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


@app.on_event("startup")
def create_tables() -> None:
    ensure_vector_extension()
    Base.metadata.create_all(bind=engine)
    ensure_document_parse_columns()
    ensure_chunk_embedding_columns()


def ensure_vector_extension() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def ensure_document_parse_columns() -> None:
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS extracted_text TEXT")
        )
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS text_char_count INTEGER NOT NULL DEFAULT 0"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS parse_status VARCHAR(50) NOT NULL DEFAULT 'pending'"
            )
        )
        connection.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS parse_error TEXT")
        )


def ensure_chunk_embedding_columns() -> None:
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(768)")
        )
        connection.execute(
            text(
                "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(50) NOT NULL DEFAULT 'pending'"
            )
        )
        connection.execute(
            text("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_error TEXT")
        )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "it's alive! we are good to go!"}


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    file_bytes = await file.read()
    original_filename = Path(file.filename or "unknown").name
    stored_filename = f"{uuid4().hex}_{original_filename}"
    storage_path = UPLOAD_DIR / stored_filename
    storage_path.write_bytes(file_bytes)
    content_type = file.content_type or "application/octet-stream"

    parse_status = "skipped"
    parse_error = None
    extracted_text = None
    text_char_count = 0

    if content_type == "application/pdf" or original_filename.lower().endswith(".pdf"):
        try:
            extracted_text = extract_pdf_text(storage_path)
            text_char_count = len(extracted_text)
            parse_status = "parsed" if extracted_text else "empty"
        except Exception as error:
            parse_status = "failed"
            parse_error = str(error)

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=len(file_bytes),
        storage_path=str(storage_path),
        extracted_text=extracted_text,
        text_char_count=text_char_count,
        parse_status=parse_status,
        parse_error=parse_error,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    chunks = []
    embedded_count = 0
    if document.parse_status == "parsed" and document.extracted_text:
        chunks = chunk_text(document.extracted_text)
        chunk_records = []
        for index, chunk in enumerate(chunks):
            chunk_record = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                char_count=len(chunk),
            )

            try:
                chunk_record.embedding = create_embedding(chunk)
                chunk_record.embedding_status = "embedded"
                embedded_count += 1
            except Exception as error:
                chunk_record.embedding_status = "failed"
                chunk_record.embedding_error = str(error)

            chunk_records.append(chunk_record)

        db.add_all(chunk_records)
        db.commit()

    return {
        "id": document.id,
        "filename": document.original_filename,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "storage_path": document.storage_path,
        "parse_status": document.parse_status,
        "text_char_count": document.text_char_count,
        "parse_error": document.parse_error,
        "chunk_count": len(chunks),
        "embedded_count": embedded_count,
    }


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()

    return [
        {
            "id": document.id,
            "filename": document.original_filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
            "parse_status": document.parse_status,
            "text_char_count": document.text_char_count,
            "parse_error": document.parse_error,
            "chunk_count": db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .count(),
            "embedded_count": db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == document.id,
                DocumentChunk.embedding_status == "embedded",
            )
            .count(),
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]


@app.get("/documents/{document_id}/chunks")
def list_document_chunks(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    return [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "char_count": chunk.char_count,
            "embedding_status": chunk.embedding_status,
            "embedding_error": chunk.embedding_error,
        }
        for chunk in chunks
    ]


def semantic_search(
    query: str, top_k: int, db: Session
) -> list[dict[str, object]]:
    query_embedding = create_embedding(query)
    query_vector = vector_literal(query_embedding)

    rows = db.execute(
        text(
            """
            SELECT
                dc.id,
                dc.document_id,
                d.original_filename,
                dc.chunk_index,
                dc.content,
                dc.char_count,
                dc.embedding <=> (:query_vector)::vector AS distance
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> (:query_vector)::vector
            LIMIT :top_k
            """
        ),
        {"query_vector": query_vector, "top_k": top_k},
    ).mappings()

    return [
        {
            "chunk_id": row["id"],
            "document_id": row["document_id"],
            "filename": row["original_filename"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "char_count": row["char_count"],
            "distance": float(row["distance"]),
        }
        for row in rows
    ]


@app.post("/search")
def search_documents(
    request: SearchRequest, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    return semantic_search(request.query, request.top_k, db)


@app.post("/answer")
def answer_question(
    request: AnswerRequest, db: Session = Depends(get_db)
) -> dict[str, object]:
    results = semantic_search(request.query, request.top_k, db)
    context = "\n\n".join(
        f"Source {index + 1}: {result['filename']}, chunk {int(result['chunk_index']) + 1}\n{result['content']}"
        for index, result in enumerate(results)
    )
    answer = generate_answer(request.query, context)

    return {
        "answer": answer,
        "sources": results,
    }
