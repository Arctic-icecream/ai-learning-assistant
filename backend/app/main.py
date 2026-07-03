from pathlib import Path
import csv
import io
import json
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from .chunker import chunk_text
from .database import Base, engine, get_db
from .document_parser import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    UnsupportedDocumentTypeError,
    parse_document,
)
from .embeddings import create_embedding
from .llm import (
    CHAT_MODEL,
    generate_answer,
    generate_document_summary,
    generate_flashcards,
    generate_mind_map,
    generate_quiz_questions,
)
from .models import (
    Document,
    DocumentChunk,
    DocumentMindMap,
    DocumentSummary,
    Flashcard,
    QuizAttempt,
    QuizQuestion,
    QuizResponse,
)
from .web_parser import WebImportError, fetch_web_page

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


class FlashcardGenerateRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=20)


class QuizGenerateRequest(BaseModel):
    count: int = Field(default=8, ge=1, le=20)


class QuizAnswerRequest(BaseModel):
    question_id: int
    answer: str = ""


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerRequest] = Field(min_length=1)


class WebImportRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class SummaryGenerateRequest(BaseModel):
    mode: Literal["brief", "detailed"] = "brief"


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"


def document_response(document: Document, db: Session) -> dict[str, object]:
    chunk_count = (
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count()
    )
    embedded_count = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id,
            DocumentChunk.embedding_status == "embedded",
        )
        .count()
    )

    return {
        "id": document.id,
        "filename": document.original_filename,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "storage_path": document.storage_path,
        "source_type": document.source_type,
        "source_url": document.source_url,
        "parse_status": document.parse_status,
        "text_char_count": document.text_char_count,
        "parse_error": document.parse_error,
        "page_count": document.page_count,
        "ocr_used": document.ocr_used,
        "ocr_page_count": document.ocr_page_count,
        "ocr_error": document.ocr_error,
        "chunk_count": chunk_count,
        "embedded_count": embedded_count,
        "created_at": document.created_at.isoformat(),
    }


def process_document(document: Document, db: Session) -> None:
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

    document.parse_status = "skipped"
    document.parse_error = None
    document.extracted_text = None
    document.text_char_count = 0
    document.page_count = 0
    document.ocr_used = False
    document.ocr_page_count = 0
    document.ocr_error = None

    storage_path = Path(document.storage_path)
    try:
        parse_result = parse_document(
            storage_path, document.original_filename
        )
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
        return

    chunk_records = []
    for index, chunk in enumerate(chunk_text(document.extracted_text)):
        chunk_record = DocumentChunk(
            document_id=document.id,
            chunk_index=index,
            content=chunk,
            char_count=len(chunk),
        )

        try:
            chunk_record.embedding = create_embedding(chunk)
            chunk_record.embedding_status = "embedded"
        except Exception as error:
            chunk_record.embedding_status = "failed"
            chunk_record.embedding_error = str(error)

        chunk_records.append(chunk_record)

    db.add_all(chunk_records)
    db.commit()


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
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS page_count INTEGER NOT NULL DEFAULT 0"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_used BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_page_count INTEGER NOT NULL DEFAULT 0"
            )
        )
        connection.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS ocr_error TEXT")
        )
        connection.execute(
            text(
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_type VARCHAR(20) NOT NULL DEFAULT 'upload'"
            )
        )
        connection.execute(
            text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT")
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
    original_filename = Path(file.filename or "unknown").name
    extension = Path(original_filename).suffix.lower()
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type. Supported: {supported}",
        )

    file_bytes = await file.read()
    stored_filename = f"{uuid4().hex}_{original_filename}"
    storage_path = UPLOAD_DIR / stored_filename
    storage_path.write_bytes(file_bytes)
    content_type = file.content_type or "application/octet-stream"

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        size_bytes=len(file_bytes),
        storage_path=str(storage_path),
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    process_document(document, db)

    return document_response(document, db)


@app.post("/documents/import-url")
def import_web_page(
    request: WebImportRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        web_page = fetch_web_page(request.url)
    except WebImportError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    safe_title = "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in web_page.title
    ).strip("_")[:80]
    original_filename = f"{safe_title or 'web-page'}.html"
    stored_filename = f"{uuid4().hex}_{original_filename}"
    storage_path = UPLOAD_DIR / stored_filename
    html_bytes = web_page.html.encode("utf-8")
    storage_path.write_bytes(html_bytes)

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type="text/html",
        size_bytes=len(html_bytes),
        storage_path=str(storage_path),
        source_type="url",
        source_url=web_page.url,
    )

    db.add(document)
    db.commit()
    db.refresh(document)
    process_document(document, db)

    return document_response(document, db)


@app.post("/documents/{document_id}/reprocess")
def reprocess_document(
    document_id: int, db: Session = Depends(get_db)
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if not Path(document.storage_path).exists():
        raise HTTPException(status_code=404, detail="Stored file not found")

    process_document(document, db)
    db.refresh(document)

    return document_response(document, db)


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    documents = db.query(Document).order_by(Document.created_at.desc()).all()

    return [
        document_response(document, db)
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


def flashcard_response(card: Flashcard) -> dict[str, object]:
    return {
        "id": card.id,
        "document_id": card.document_id,
        "question": card.question,
        "answer": card.answer,
        "source_chunk_index": card.source_chunk_index,
        "created_at": card.created_at.isoformat(),
    }


def quiz_question_response(question: QuizQuestion) -> dict[str, object]:
    choices: list[str] = []
    if question.choices:
        try:
            parsed_choices = json.loads(question.choices)
            if isinstance(parsed_choices, list):
                choices = [str(choice) for choice in parsed_choices]
        except json.JSONDecodeError:
            choices = []

    return {
        "id": question.id,
        "document_id": question.document_id,
        "question_type": question.question_type,
        "question": question.question,
        "choices": choices,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "created_at": question.created_at.isoformat(),
    }


def summary_response(summary: DocumentSummary) -> dict[str, object]:
    return {
        "id": summary.id,
        "document_id": summary.document_id,
        "mode": summary.mode,
        "content": summary.content,
        "model_name": summary.model_name,
        "source_chunk_count": summary.source_chunk_count,
        "model_call_count": summary.model_call_count,
        "created_at": summary.created_at.isoformat(),
    }


def mind_map_response(mind_map: DocumentMindMap) -> dict[str, object]:
    return {
        "id": mind_map.id,
        "document_id": mind_map.document_id,
        "summary_id": mind_map.summary_id,
        "tree": mind_map.tree,
        "model_name": mind_map.model_name,
        "node_count": mind_map.node_count,
        "created_at": mind_map.created_at.isoformat(),
    }


@app.get("/documents/{document_id}/mind-maps")
def list_document_mind_maps(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    mind_maps = (
        db.query(DocumentMindMap)
        .filter(DocumentMindMap.document_id == document_id)
        .order_by(DocumentMindMap.created_at.desc())
        .all()
    )
    return [mind_map_response(mind_map) for mind_map in mind_maps]


@app.post("/documents/{document_id}/mind-maps/generate")
def generate_document_mind_map(
    document_id: int, db: Session = Depends(get_db)
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    summary = (
        db.query(DocumentSummary)
        .filter(
            DocumentSummary.document_id == document_id,
            DocumentSummary.mode == "detailed",
        )
        .order_by(DocumentSummary.created_at.desc())
        .first()
    )
    if summary is None:
        summary = (
            db.query(DocumentSummary)
            .filter(DocumentSummary.document_id == document_id)
            .order_by(DocumentSummary.created_at.desc())
            .first()
        )
    if summary is None:
        raise HTTPException(
            status_code=400,
            detail="Generate a document summary before creating a mind map",
        )

    tree, node_count = generate_mind_map(summary.content)
    mind_map = DocumentMindMap(
        document_id=document_id,
        summary_id=summary.id,
        tree=tree,
        model_name=CHAT_MODEL,
        node_count=node_count,
    )
    db.add(mind_map)
    db.commit()
    db.refresh(mind_map)

    return mind_map_response(mind_map)


@app.get("/documents/{document_id}/summaries")
def list_document_summaries(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    summaries = (
        db.query(DocumentSummary)
        .filter(DocumentSummary.document_id == document_id)
        .order_by(DocumentSummary.created_at.desc())
        .all()
    )
    return [summary_response(summary) for summary in summaries]


@app.post("/documents/{document_id}/summaries/generate")
def generate_summary(
    document_id: int,
    request: SummaryGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no chunks")

    content, model_call_count = generate_document_summary(
        [chunk.content for chunk in chunks], request.mode
    )
    summary = DocumentSummary(
        document_id=document_id,
        mode=request.mode,
        content=content,
        model_name=CHAT_MODEL,
        source_chunk_count=len(chunks),
        model_call_count=model_call_count,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)

    return summary_response(summary)


def normalize_quiz_answer(answer: str) -> str:
    return " ".join(answer.strip().casefold().split())


def quiz_attempt_response(attempt: QuizAttempt, responses: list[QuizResponse]) -> dict[str, object]:
    return {
        "id": attempt.id,
        "document_id": attempt.document_id,
        "total_questions": attempt.total_questions,
        "scored_questions": attempt.scored_questions,
        "correct_answers": attempt.correct_answers,
        "created_at": attempt.created_at.isoformat(),
        "responses": [
            {
                "question_id": response.quiz_question_id,
                "submitted_answer": response.submitted_answer,
                "is_correct": response.is_correct,
            }
            for response in responses
        ],
    }


def quiz_attempts_for_document(document_id: int, db: Session) -> list[dict[str, object]]:
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.document_id == document_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(10)
        .all()
    )
    if not attempts:
        return []

    attempt_ids = [attempt.id for attempt in attempts]
    responses = (
        db.query(QuizResponse)
        .filter(QuizResponse.attempt_id.in_(attempt_ids))
        .order_by(QuizResponse.id.asc())
        .all()
    )
    responses_by_attempt = {attempt.id: [] for attempt in attempts}
    for response in responses:
        responses_by_attempt[response.attempt_id].append(response)

    return [
        quiz_attempt_response(attempt, responses_by_attempt[attempt.id])
        for attempt in attempts
    ]


@app.get("/documents/{document_id}/flashcards")
def list_flashcards(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    cards = (
        db.query(Flashcard)
        .filter(Flashcard.document_id == document_id)
        .order_by(Flashcard.id.asc())
        .all()
    )

    return [flashcard_response(card) for card in cards]


@app.get("/documents/{document_id}/flashcards/export")
def export_flashcards(
    document_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    cards = (
        db.query(Flashcard)
        .filter(Flashcard.document_id == document_id)
        .order_by(Flashcard.id.asc())
        .all()
    )
    if not cards:
        raise HTTPException(status_code=400, detail="Document has no flashcards")

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Question", "Answer"])
    for card in cards:
        writer.writerow([card.question, card.answer])

    safe_name = "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in Path(document.original_filename).stem
    )
    filename = f"{safe_name or 'flashcards'}-anki.csv"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/documents/{document_id}/flashcards/generate")
def generate_document_flashcards(
    document_id: int,
    request: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(8)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no chunks")

    context = "\n\n".join(
        f"Chunk {chunk.chunk_index + 1}:\n{chunk.content}" for chunk in chunks
    )
    generated_cards = generate_flashcards(context, request.count)

    db.query(Flashcard).filter(Flashcard.document_id == document_id).delete()
    card_records = [
        Flashcard(
            document_id=document_id,
            question=card["question"],
            answer=card["answer"],
            source_chunk_index=None,
        )
        for card in generated_cards
    ]
    db.add_all(card_records)
    db.commit()

    for card in card_records:
        db.refresh(card)

    return [flashcard_response(card) for card in card_records]


@app.get("/documents/{document_id}/quiz")
def list_quiz_questions(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.document_id == document_id)
        .order_by(QuizQuestion.id.asc())
        .all()
    )

    return [quiz_question_response(question) for question in questions]


@app.post("/documents/{document_id}/quiz/generate")
def generate_document_quiz(
    document_id: int,
    request: QuizGenerateRequest,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
        .limit(8)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no chunks")

    context = "\n\n".join(
        f"Chunk {chunk.chunk_index + 1}:\n{chunk.content}" for chunk in chunks
    )
    generated_questions = generate_quiz_questions(context, request.count)

    attempt_ids = [
        attempt_id
        for (attempt_id,) in db.query(QuizAttempt.id)
        .filter(QuizAttempt.document_id == document_id)
        .all()
    ]
    if attempt_ids:
        db.query(QuizResponse).filter(QuizResponse.attempt_id.in_(attempt_ids)).delete(
            synchronize_session=False
        )
    db.query(QuizAttempt).filter(QuizAttempt.document_id == document_id).delete()
    db.query(QuizQuestion).filter(QuizQuestion.document_id == document_id).delete()
    question_records = [
        QuizQuestion(
            document_id=document_id,
            question_type=str(question["question_type"]),
            question=str(question["question"]),
            choices=json.dumps(question["choices"], ensure_ascii=False),
            correct_answer=str(question["correct_answer"]),
            explanation=str(question["explanation"]),
        )
        for question in generated_questions
    ]
    db.add_all(question_records)
    db.commit()

    for question in question_records:
        db.refresh(question)

    return [quiz_question_response(question) for question in question_records]


@app.get("/documents/{document_id}/quiz/attempts")
def list_quiz_attempts(
    document_id: int, db: Session = Depends(get_db)
) -> list[dict[str, object]]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return quiz_attempts_for_document(document_id, db)


@app.post("/documents/{document_id}/quiz/submit")
def submit_quiz(
    document_id: int,
    request: QuizSubmitRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.document_id == document_id)
        .order_by(QuizQuestion.id.asc())
        .all()
    )
    if not questions:
        raise HTTPException(status_code=400, detail="Document has no quiz questions")

    answers_by_question = {answer.question_id: answer.answer for answer in request.answers}
    question_ids = {question.id for question in questions}
    unknown_question_ids = set(answers_by_question) - question_ids
    if unknown_question_ids:
        raise HTTPException(status_code=400, detail="Quiz submission contains an invalid question")

    attempt = QuizAttempt(
        document_id=document_id,
        total_questions=len(questions),
        scored_questions=0,
        correct_answers=0,
    )
    db.add(attempt)
    db.flush()

    response_records = []
    for question in questions:
        submitted_answer = answers_by_question.get(question.id, "").strip()
        is_objective_question = question.question_type in {
            "multiple_choice",
            "true_false",
        }
        is_correct = (
            normalize_quiz_answer(submitted_answer)
            == normalize_quiz_answer(question.correct_answer)
            if is_objective_question and submitted_answer
            else None
        )
        if is_objective_question:
            attempt.scored_questions += 1
            if is_correct:
                attempt.correct_answers += 1

        response_records.append(
            QuizResponse(
                attempt_id=attempt.id,
                quiz_question_id=question.id,
                submitted_answer=submitted_answer,
                is_correct=is_correct,
            )
        )

    db.add_all(response_records)
    db.commit()
    db.refresh(attempt)

    return quiz_attempt_response(attempt, response_records)


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
