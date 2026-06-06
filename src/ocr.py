"""Local OCR helpers with PDF text-layer fast paths."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO

import fitz
import pytesseract
from PIL import Image

from src.preprocess import nonwhite_ratio, prepare_for_ocr, sharpness_score


@dataclass
class OCRText:
    text: str
    confidence: float
    source: str
    warning: str = ""
    nonwhite_ratio: float = 0.0
    sharpness: float = 0.0


@lru_cache(maxsize=1)
def tesseract_available() -> bool:
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def page_region_to_image(page: fitz.Page, rect: fitz.Rect, dpi: int = 200) -> Image.Image:
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png")))


def ocr_image(image: Image.Image) -> OCRText:
    ratio = nonwhite_ratio(image)
    sharpness = sharpness_score(image)
    if not tesseract_available():
        return OCRText(
            text="",
            confidence=0.0,
            source="ocr-unavailable",
            warning="Local Tesseract OCR is not installed or is not on PATH.",
            nonwhite_ratio=ratio,
            sharpness=sharpness,
        )

    prepared = prepare_for_ocr(image)
    try:
        data = pytesseract.image_to_data(prepared, output_type=pytesseract.Output.DICT, lang="eng")
    except Exception as exc:
        return OCRText(
            text="",
            confidence=0.0,
            source="ocr-error",
            warning=f"Local OCR failed: {exc}",
            nonwhite_ratio=ratio,
            sharpness=sharpness,
        )

    words: list[str] = []
    confidences: list[float] = []
    for text, confidence in zip(data.get("text", []), data.get("conf", [])):
        text = (text or "").strip()
        if not text:
            continue
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            confidence_value = -1
        words.append(text)
        if confidence_value >= 0:
            confidences.append(confidence_value / 100.0)

    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return OCRText(
        text=" ".join(words).strip(),
        confidence=round(mean_confidence, 3),
        source="tesseract",
        nonwhite_ratio=ratio,
        sharpness=sharpness,
    )


def extract_region_text(page: fitz.Page, rect: fitz.Rect, prefer_text_layer: bool = True) -> OCRText:
    text = ""
    if prefer_text_layer:
        text = page.get_text("text", clip=rect).strip()
    image = page_region_to_image(page, rect)
    ratio = nonwhite_ratio(image)
    sharpness = sharpness_score(image)
    if text:
        return OCRText(text=text, confidence=0.97, source="pdf-text", nonwhite_ratio=ratio, sharpness=sharpness)

    result = ocr_image(image)
    result.nonwhite_ratio = ratio
    result.sharpness = sharpness
    return result
