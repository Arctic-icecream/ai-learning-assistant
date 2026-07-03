# Day 17 - Selective Local PDF OCR

## Goal

Make scanned and image-based PDF pages searchable without slowing down normal
text PDFs or sending document images to a cloud OCR service.

## Pipeline

```text
PDF page
  -> pypdf native text extraction
  -> at least 80 characters: keep native text
  -> fewer than 80 characters:
       render page to a 200 DPI RGB image with PyMuPDF
       run local RapidOCR with ONNX Runtime
       keep recognized lines with confidence >= 0.50
       use OCR text when it is longer than native text
  -> merge pages in reading order
  -> chunks -> embeddings -> knowledge features
```

Only low-text pages enter OCR. A 100-page digital textbook should therefore
remain close to its previous parsing speed, while a mixed PDF can OCR scanned
pages and preserve native text on the others.

## Why Two PDF Libraries

`pypdf` reads the PDF text layer. It is the fast first choice when characters
already exist in the document.

PyMuPDF renders a complete page into pixels with `Page.get_pixmap()`. OCR needs
those pixels because a scanned page contains an image rather than selectable
characters.

References:

- https://pymupdf.readthedocs.io/en/latest/recipes-images.html
- https://rapidai.github.io/RapidOCRDocs/main/install_usage/rapidocr/usage/

## OCR Engine

The project uses:

```text
rapidocr 3.9.1
onnxruntime 1.27.0
PyMuPDF 1.28.0
```

RapidOCR 3.9 uses PP-OCRv6 small models for detection and recognition. The
models are bundled with the installed Python package. ONNX Runtime performs CPU
inference locally.

`ocr.py` initializes the engine lazily behind a thread lock. Uploading Word,
PowerPoint, web pages, or normal text PDFs does not initialize the OCR model.

## Limits

- native text threshold: 80 characters per page
- render resolution: 200 DPI
- maximum OCR pages per PDF: 30
- minimum accepted line confidence: 0.50

The page limit bounds processing time and memory use. If more low-text pages
exist, the document records an OCR warning rather than silently pretending the
whole PDF was processed.

Images are passed to OCR in memory. Rendered page PNG files are not written to
the upload directory or committed to Git.

## Database Metadata

The `documents` table now stores:

- `page_count`: PDF page count
- `ocr_used`: whether any page entered OCR
- `ocr_page_count`: number of pages sent through OCR
- `ocr_error`: page errors or page-limit warnings

Existing databases receive these columns during FastAPI startup with safe
defaults. Existing uploaded PDFs can use OCR by clicking `Reprocess`.

## Frontend

PDF upload results show page count and OCR page count. Stored document rows show
either the normal page count or a compact value such as `OCR 4/10`.

This makes the processing route observable: a successful upload alone is not
enough evidence that a scanned page was recognized.

## Testing

`backend/tests/test_pdf_ocr.py` creates real temporary PDFs with PyMuPDF. It
checks that only image pages enter OCR, page limits create warnings, and weak
recognition lines are removed.

The automated tests replace the expensive model call with a deterministic fake
OCR function. A separate local smoke check loaded all three ONNX models and
recognized an in-memory image at approximately 0.968 confidence.

The official `rapidocr check` command loaded the bundled models successfully
but could not download its remote sample image under the current network
policy. The local-image smoke test avoids that network dependency.

## Manual Check

1. Start the stack with `start-dev.cmd`.
2. Upload a scanned PDF with visible text but no selectable text layer.
3. Confirm `OCR pages` is greater than zero.
4. Open its chunk preview and inspect the recognized content.
5. Ask a question answered by the scanned page.
6. Reprocess an older scanned PDF to apply the new OCR pipeline.

OCR can introduce spacing, punctuation, or character errors. Confidence
filtering removes weak lines but does not make OCR equivalent to the source.
