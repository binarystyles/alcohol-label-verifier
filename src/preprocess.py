"""Image preprocessing used before local OCR."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def prepare_for_ocr(image: Image.Image) -> Image.Image:
    """Return a high-contrast grayscale image suitable for Tesseract."""
    gray = image.convert("L")
    scale = 2 if min(gray.size) < 1000 else 1
    if scale > 1:
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    gray = ImageEnhance.Contrast(gray).enhance(1.8)
    gray = gray.filter(ImageFilter.SHARPEN)

    array = np.array(gray)
    array = cv2.GaussianBlur(array, (3, 3), 0)
    thresholded = cv2.adaptiveThreshold(
        array,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    )
    return Image.fromarray(thresholded)


def prepare_ocr_variants(image: Image.Image) -> list[tuple[str, Image.Image]]:
    """Return conservative OCR preprocessing variants for labels with artwork."""
    gray = image.convert("L")
    scale = 2 if min(gray.size) < 1000 else 1
    if scale > 1:
        gray = gray.resize((gray.width * scale, gray.height * scale), Image.Resampling.LANCZOS)
    contrast = ImageEnhance.Contrast(gray).enhance(2.0).filter(ImageFilter.SHARPEN)
    blurred = cv2.GaussianBlur(np.array(contrast), (3, 3), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return [
        ("adaptive", prepare_for_ocr(image)),
        ("grayscale", gray),
        ("contrast", contrast),
        ("otsu", Image.fromarray(otsu)),
    ]


def nonwhite_ratio(image: Image.Image, threshold: int = 245) -> float:
    gray = image.convert("L")
    array = np.array(gray)
    return float(np.mean(array < threshold))


def sharpness_score(image: Image.Image) -> float:
    """Estimate rendered image sharpness using variance of the Laplacian."""
    gray = image.convert("L")
    array = np.array(gray)
    return float(cv2.Laplacian(array, cv2.CV_64F).var())
