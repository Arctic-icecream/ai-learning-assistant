from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Document

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

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(file_bytes),
        storage_path=str(storage_path),
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "id": document.id,
        "filename": document.original_filename,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "storage_path": document.storage_path,
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
            "created_at": document.created_at.isoformat(),
        }
        for document in documents
    ]
