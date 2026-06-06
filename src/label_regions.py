"""Label-region selection for completed application PDFs."""

from __future__ import annotations

import fitz

from src.form_mapping import FORM_REGIONS

MAX_LABEL_SCAN_PAGES = 12


def page_one_label_rect(page: fitz.Page) -> fitz.Rect:
    return FORM_REGIONS["label_area"].to_rect(page.rect)


def label_regions(document: fitz.Document) -> list[tuple[int, fitz.Rect, str]]:
    """Return page regions likely to contain affixed or supplemental labels."""
    if document.page_count == 0:
        return []

    regions: list[tuple[int, fitz.Rect, str]] = [(0, page_one_label_rect(document[0]), "page-one-label-area")]
    for page_index in range(1, min(document.page_count, MAX_LABEL_SCAN_PAGES)):
        page = document[page_index]
        text = page.get_text("text")
        if looks_like_non_label_page(text):
            continue
        regions.append((page_index, page.rect, "supplemental-label-page"))
    return regions


def looks_like_non_label_page(text: str) -> bool:
    normalized = " ".join(text.upper().split())
    non_label_hits = sum(
        phrase in normalized
        for phrase in (
            "INSTRUCTIONS FOR COMPLETING",
            "GENERAL INSTRUCTIONS",
            "PAPERWORK REDUCTION ACT",
            "THIS CERTIFICATE DOES NOT RELIEVE",
            "FORMULAS ONLINE",
            "FORMULA APPROVAL",
            "TTB FORMULA ID",
            "FORMULA ID",
            "YIELD SUMMARY",
            "ALCOHOL CONTENT OF FINISHED PRODUCT",
            "ALCOHOL FROM FLAVORS",
            "ALCOHOL FROM BASE",
            "METHOD OF MANUFACTURE",
            "DETAILED QUANTITATIVE LIST OF INGREDIENTS",
            "INGREDIENTS LIST",
            "FINAL ALCOHOL CONTENT",
        )
    )
    return non_label_hits >= 1
