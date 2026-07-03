from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pymupdf
from PIL import Image, ImageDraw

from backend.app.ocr import OCRResult, recognize_png
from backend.app.pdf_parser import extract_pdf_text


def make_png(text: str) -> bytes:
    image = Image.new("RGB", (1000, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 260), text, fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def create_mixed_pdf(path: Path) -> None:
    document = pymupdf.open()
    text_page = document.new_page()
    text_page.insert_text(
        (72, 100),
        "AODV is a reactive routing protocol that discovers routes only when they are needed. "
        "This sentence is intentionally long enough to avoid OCR fallback.",
    )
    image_page = document.new_page()
    image_page.insert_image(image_page.rect, stream=make_png("SCANNED NETWORK NOTES"))
    document.save(path)
    document.close()


class FakeEngineResult:
    txts = ("High confidence line", "Low confidence noise", "Another line")
    scores = (0.95, 0.20, 0.75)


class FakeEngine:
    def __call__(self, image: object) -> FakeEngineResult:
        return FakeEngineResult()


class PDFOCRTests(unittest.TestCase):
    def test_ocr_runs_only_for_low_text_pages(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "mixed.pdf"
            create_mixed_pdf(path)
            calls = []

            def fake_ocr(image_bytes: bytes) -> OCRResult:
                calls.append(len(image_bytes))
                return OCRResult(
                    text="AODV scanned explanation",
                    line_count=1,
                    average_confidence=0.98,
                )

            result = extract_pdf_text(path, ocr_function=fake_ocr)

            self.assertEqual(len(calls), 1)
            self.assertEqual(result.page_count, 2)
            self.assertTrue(result.ocr_used)
            self.assertEqual(result.ocr_page_count, 1)
            self.assertIn("reactive routing protocol", result.text)
            self.assertIn("AODV scanned explanation", result.text)

    def test_ocr_page_limit_is_reported(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "empty-pages.pdf"
            document = pymupdf.open()
            for _ in range(3):
                document.new_page()
            document.save(path)
            document.close()

            result = extract_pdf_text(
                path,
                ocr_function=lambda _: OCRResult("Recognized", 1, 0.9),
                max_ocr_pages=2,
            )

            self.assertEqual(result.ocr_page_count, 2)
            self.assertIn("1 low-text page(s) were skipped", result.ocr_error or "")

    def test_confidence_filter_removes_weak_lines(self) -> None:
        result = recognize_png(make_png("TEST"), engine=FakeEngine())

        self.assertEqual(result.line_count, 2)
        self.assertIn("High confidence line", result.text)
        self.assertIn("Another line", result.text)
        self.assertNotIn("Low confidence noise", result.text)
        self.assertAlmostEqual(result.average_confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
