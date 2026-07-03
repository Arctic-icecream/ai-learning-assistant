from dataclasses import dataclass
from io import BytesIO
from threading import Lock
from typing import Any

import numpy as np
from PIL import Image
from rapidocr import RapidOCR


OCR_MIN_CONFIDENCE = 0.50


@dataclass(frozen=True)
class OCRResult:
    text: str
    line_count: int
    average_confidence: float


_engine: RapidOCR | None = None
_engine_lock = Lock()


def get_ocr_engine() -> RapidOCR:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = RapidOCR()
    return _engine


def recognize_png(
    image_bytes: bytes,
    engine: Any | None = None,
    min_confidence: float = OCR_MIN_CONFIDENCE,
) -> OCRResult:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    result = (engine or get_ocr_engine())(np.asarray(image))
    texts = tuple(result.txts or ())
    scores = tuple(result.scores or ())

    accepted = [
        (str(text).strip(), float(score))
        for text, score in zip(texts, scores)
        if str(text).strip() and float(score) >= min_confidence
    ]
    if not accepted:
        return OCRResult(text="", line_count=0, average_confidence=0.0)

    return OCRResult(
        text="\n".join(text for text, _ in accepted),
        line_count=len(accepted),
        average_confidence=sum(score for _, score in accepted) / len(accepted),
    )
