from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .docx_parser import extract_docx_text
from .pdf_parser import extract_pdf_text
from .pptx_parser import extract_pptx_text
from .web_parser import extract_html_file_text


Parser = Callable[[Path], str]

PARSERS: dict[str, Parser] = {
    ".docx": extract_docx_text,
    ".pptx": extract_pptx_text,
    ".html": extract_html_file_text,
}

SUPPORTED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".docx", ".pptx"})


class UnsupportedDocumentTypeError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentParseResult:
    text: str
    page_count: int = 0
    ocr_used: bool = False
    ocr_page_count: int = 0
    ocr_error: str | None = None


def parse_document(path: Path, original_filename: str) -> DocumentParseResult:
    extension = Path(original_filename).suffix.lower()
    if extension == ".pdf":
        pdf_result = extract_pdf_text(path)
        return DocumentParseResult(
            text=pdf_result.text,
            page_count=pdf_result.page_count,
            ocr_used=pdf_result.ocr_used,
            ocr_page_count=pdf_result.ocr_page_count,
            ocr_error=pdf_result.ocr_error,
        )

    parser = PARSERS.get(extension)
    if parser is None:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type '{extension or 'unknown'}'. Supported: {supported}"
        )

    return DocumentParseResult(text=parser(path))


def extract_document_text(path: Path, original_filename: str) -> str:
    return parse_document(path, original_filename).text
