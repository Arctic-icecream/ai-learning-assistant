from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from pypdf import PdfReader

from .ocr import OCRResult, recognize_png


PDF_NATIVE_TEXT_THRESHOLD = 80
PDF_OCR_DPI = 200
PDF_MAX_OCR_PAGES = 30


@dataclass(frozen=True)
class PDFParseResult:
    text: str
    page_count: int
    ocr_used: bool
    ocr_page_count: int
    ocr_error: str | None


def extract_pdf_text(
    path: Path,
    ocr_function: Callable[[bytes], OCRResult] = recognize_png,
    native_text_threshold: int = PDF_NATIVE_TEXT_THRESHOLD,
    max_ocr_pages: int = PDF_MAX_OCR_PAGES,
) -> PDFParseResult:
    reader = PdfReader(path)
    native_page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    ocr_candidates = [
        index
        for index, text in enumerate(native_page_texts)
        if len(text) < native_text_threshold
    ]
    ocr_candidate_set = set(ocr_candidates[:max_ocr_pages])
    ocr_errors: list[str] = []
    ocr_page_count = 0

    if len(ocr_candidates) > max_ocr_pages:
        skipped_count = len(ocr_candidates) - max_ocr_pages
        ocr_errors.append(
            f"OCR page limit reached; {skipped_count} low-text page(s) were skipped"
        )

    page_texts: list[str] = []
    pdf_document = pymupdf.open(path) if ocr_candidate_set else None

    try:
        for page_index, native_text in enumerate(native_page_texts):
            page_text = native_text
            if page_index in ocr_candidate_set and pdf_document is not None:
                ocr_page_count += 1
                try:
                    pixmap = pdf_document[page_index].get_pixmap(
                        dpi=PDF_OCR_DPI,
                        colorspace=pymupdf.csRGB,
                        alpha=False,
                    )
                    ocr_result = ocr_function(pixmap.tobytes("png"))
                    if len(ocr_result.text) > len(page_text):
                        page_text = ocr_result.text
                except Exception as error:
                    ocr_errors.append(f"Page {page_index + 1}: {error}")

            if page_text:
                page_texts.append(f"Page {page_index + 1}\n{page_text}")
    finally:
        if pdf_document is not None:
            pdf_document.close()

    return PDFParseResult(
        text="\n\n".join(page_texts),
        page_count=len(native_page_texts),
        ocr_used=ocr_page_count > 0,
        ocr_page_count=ocr_page_count,
        ocr_error="; ".join(ocr_errors) if ocr_errors else None,
    )
