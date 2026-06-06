"""Label-region selection for completed application PDFs."""

from __future__ import annotations

import fitz

from src.form_mapping import FORM_REGIONS


def page_one_label_rect(page: fitz.Page) -> fitz.Rect:
    return FORM_REGIONS["label_area"].to_rect(page.rect)


def label_regions(document: fitz.Document) -> list[tuple[int, fitz.Rect, str]]:
    """Return page regions likely to contain affixed or supplemental labels."""
    if document.page_count == 0:
        return []

    regions: list[tuple[int, fitz.Rect, str]] = [(0, page_one_label_rect(document[0]), "page-one-label-area")]
    for page_index in range(1, min(document.page_count, 6)):
        page = document[page_index]
        text = page.get_text("text")
        if _looks_like_instruction_page(text):
            continue
        regions.append((page_index, page.rect, "supplemental-label-page"))
    return regions


def _looks_like_instruction_page(text: str) -> bool:
    normalized = " ".join(text.upper().split())
    instruction_hits = sum(
        phrase in normalized
        for phrase in (
            "INSTRUCTIONS FOR COMPLETING",
            "GENERAL INSTRUCTIONS",
            "PAPERWORK REDUCTION ACT",
            "THIS CERTIFICATE DOES NOT RELIEVE",
        )
    )
    return instruction_hits >= 1

