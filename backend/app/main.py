from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .chunker import chunk_text
from .database import Base, engine, get_db
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


@app.on_event("startup")
def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_document_parse_columns()


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
    if document.parse_status == "parsed" and document.extracted_text:
        chunks = chunk_text(document.extracted_text)
        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    char_count=len(chunk),
                )
                for index, chunk in enumerate(chunks)
            ]
        )
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
        }
        for chunk in chunks
    ]
