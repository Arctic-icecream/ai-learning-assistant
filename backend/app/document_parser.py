from collections.abc import Callable
from pathlib import Path

from .docx_parser import extract_docx_text
from .pdf_parser import extract_pdf_text
from .pptx_parser import extract_pptx_text
from .web_parser import extract_html_file_text


Parser = Callable[[Path], str]

PARSERS: dict[str, Parser] = {
    ".pdf": extract_pdf_text,
    ".docx": extract_docx_text,
    ".pptx": extract_pptx_text,
    ".html": extract_html_file_text,
}

SUPPORTED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".docx", ".pptx"})


class UnsupportedDocumentTypeError(ValueError):
    pass


def extract_document_text(path: Path, original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    parser = PARSERS.get(extension)
    if parser is None:
        supported = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise UnsupportedDocumentTypeError(
            f"Unsupported document type '{extension or 'unknown'}'. Supported: {supported}"
        )

    return parser(path)
