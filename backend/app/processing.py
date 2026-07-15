from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .chunker import chunk_text
from .database import SessionLocal
from .document_parser import UnsupportedDocumentTypeError, parse_document
from .embeddings import create_embedding
from .models import (
    Document,
    DocumentChunk,
    DocumentMindMap,
    DocumentSummary,
    Flashcard,
    ProcessingJob,
    QuizAttempt,
    QuizQuestion,
    QuizResponse,
)


TERMINAL_JOB_STATUSES = {"completed", "failed"}


def calculate_job_percent(current: int, total: int, status: str) -> int:
    if status == "completed":
        return 100
    if total <= 0:
        return 0
    return max(0, min(99, round((current / total) * 100)))


def update_job(
    db: Session,
    job: ProcessingJob | None,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    progress_current: int | None = None,
    progress_total: int | None = None,
    error: str | None = None,
) -> None:
    if job is None:
        return

    if status is not None:
        job.status = status
        if status == "running" and job.started_at is None:
            job.started_at = datetime.utcnow()
        if status in TERMINAL_JOB_STATUSES:
            job.completed_at = datetime.utcnow()
    if stage is not None:
        job.stage = stage
    if message is not None:
        job.message = message
    if progress_current is not None:
        job.progress_current = progress_current
    if progress_total is not None:
        job.progress_total = max(1, progress_total)
    if error is not None:
        job.error = error

    db.add(job)
    db.commit()
    db.refresh(job)


def clear_document_artifacts(document: Document, db: Session) -> None:
    attempt_ids = [
        attempt_id
        for (attempt_id,) in db.query(QuizAttempt.id)
        .filter(QuizAttempt.document_id == document.id)
        .all()
    ]
    if attempt_ids:
        db.query(QuizResponse).filter(QuizResponse.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
    db.query(QuizAttempt).filter(QuizAttempt.document_id == document.id).delete()
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
    db.query(DocumentMindMap).filter(DocumentMindMap.document_id == document.id).delete()
    db.query(DocumentSummary).filter(DocumentSummary.document_id == document.id).delete()
    db.query(Flashcard).filter(Flashcard.document_id == document.id).delete()
    db.query(QuizQuestion).filter(QuizQuestion.document_id == document.id).delete()


def process_document(document: Document, db: Session, job: ProcessingJob | None = None) -> None:
    update_job(
        db,
        job,
        status="running",
        stage="resetting",
        message="Clearing old generated data.",
        progress_current=0,
        progress_total=4,
    )
    clear_document_artifacts(document, db)

    document.parse_status = "processing"
    document.parse_error = None
    document.extracted_text = None
    document.text_char_count = 0
    document.page_count = 0
    document.ocr_used = False
    document.ocr_page_count = 0
    document.ocr_error = None
    db.add(document)
    db.commit()
    db.refresh(document)

    update_job(
        db,
        job,
        stage="extracting",
        message="Extracting readable text from the document.",
        progress_current=1,
    )

    storage_path = Path(document.storage_path)
    try:
        parse_result = parse_document(storage_path, document.original_filename)
        document.extracted_text = parse_result.text
        document.text_char_count = len(document.extracted_text)
        document.page_count = parse_result.page_count
        document.ocr_used = parse_result.ocr_used
        document.ocr_page_count = parse_result.ocr_page_count
        document.ocr_error = parse_result.ocr_error
        document.parse_status = "parsed" if document.extracted_text else "empty"
    except UnsupportedDocumentTypeError as error:
        document.parse_status = "unsupported"
        document.parse_error = str(error)
    except Exception as error:
        document.parse_status = "failed"
        document.parse_error = str(error)

    db.add(document)
    db.commit()
    db.refresh(document)

    if document.parse_status != "parsed" or not document.extracted_text:
        final_status = "failed" if document.parse_status in {"failed", "unsupported"} else "completed"
        update_job(
            db,
            job,
            status=final_status,
            stage=document.parse_status,
            message=document.parse_error or f"Document processing ended as {document.parse_status}.",
            progress_current=4,
            progress_total=4,
            error=document.parse_error if final_status == "failed" else None,
        )
        return

    update_job(
        db,
        job,
        stage="chunking",
        message="Splitting extracted text into searchable chunks.",
        progress_current=2,
        progress_total=4,
    )
    chunks = chunk_text(document.extracted_text)
    if not chunks:
        update_job(
            db,
            job,
            status="completed",
            stage="empty",
            message="No chunks were created from the extracted text.",
            progress_current=4,
            progress_total=4,
        )
        return

    update_job(
        db,
        job,
        stage="embedding",
        message=f"Generating embeddings for {len(chunks)} chunks.",
        progress_current=0,
        progress_total=len(chunks),
    )
    chunk_records = []
    embedded_count = 0
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
        update_job(
            db,
            job,
            stage="embedding",
            message=f"Generated embeddings for {index + 1} of {len(chunks)} chunks.",
            progress_current=index + 1,
            progress_total=len(chunks),
        )

    db.add_all(chunk_records)
    db.commit()

    update_job(
        db,
        job,
        status="completed",
        stage="completed",
        message=f"Document processed: {len(chunks)} chunks, {embedded_count} embedded.",
        progress_current=len(chunks),
        progress_total=len(chunks),
    )


def run_document_processing_job(document_id: int, job_id: int) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        job = db.get(ProcessingJob, job_id)
        if document is None or job is None:
            return

        try:
            process_document(document, db, job)
        except Exception as error:
            if document.parse_status == "processing":
                document.parse_status = "failed"
                document.parse_error = str(error)
                db.add(document)
                db.commit()
            update_job(
                db,
                job,
                status="failed",
                stage="failed",
                message="Processing job failed.",
                error=str(error),
            )
    finally:
        db.close()


def mark_interrupted_jobs(db: Session) -> int:
    interrupted_jobs = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.status.in_(["queued", "running"]))
        .all()
    )
    for job in interrupted_jobs:
        job.status = "failed"
        job.stage = "interrupted"
        job.message = "The backend restarted before this job finished."
        job.error = "Interrupted by backend restart."
        job.completed_at = datetime.utcnow()

    if interrupted_jobs:
        db.commit()

    return len(interrupted_jobs)
