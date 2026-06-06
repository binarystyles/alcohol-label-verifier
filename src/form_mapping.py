"""Prototype normalized coordinates for TTB F 5100.31 page-one extraction.

Coordinates are expressed as x0, y0, x1, y1 fractions of page width and height.
They are intentionally easy to tune because filled forms and scans vary.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass(frozen=True)
class NormalizedRegion:
    x0: float
    y0: float
    x1: float
    y1: float
    description: str = ""

    def to_rect(self, page_rect: fitz.Rect) -> fitz.Rect:
        width = page_rect.width
        height = page_rect.height
        return fitz.Rect(
            page_rect.x0 + self.x0 * width,
            page_rect.y0 + self.y0 * height,
            page_rect.x0 + self.x1 * width,
            page_rect.y0 + self.y1 * height,
        )


FORM_REGIONS: dict[str, NormalizedRegion] = {
    "serial_number": NormalizedRegion(0.03, 0.15, 0.22, 0.20, "Item 4 serial number"),
    "product_type": NormalizedRegion(0.23, 0.145, 0.48, 0.205, "Item 5 product type"),
    "brand_name": NormalizedRegion(0.03, 0.205, 0.47, 0.235, "Item 6 brand name"),
    "fanciful_name": NormalizedRegion(0.03, 0.23, 0.47, 0.26, "Item 7 fanciful name"),
    "applicant_name_address": NormalizedRegion(0.41, 0.11, 0.96, 0.21, "Item 8 applicant"),
    "mailing_address": NormalizedRegion(0.48, 0.205, 0.96, 0.26, "Item 8a mailing"),
    "formula": NormalizedRegion(0.03, 0.255, 0.47, 0.285, "Item 9 formula"),
    "grape_varietals": NormalizedRegion(0.48, 0.255, 0.72, 0.285, "Item 10 grape varietals"),
    "wine_appellation": NormalizedRegion(0.73, 0.255, 0.96, 0.285, "Item 11 appellation"),
    "phone": NormalizedRegion(0.03, 0.29, 0.33, 0.33, "Item 12 phone"),
    "email": NormalizedRegion(0.34, 0.29, 0.96, 0.33, "Item 13 email"),
    "application_type": NormalizedRegion(0.03, 0.33, 0.96, 0.37, "Item 14 application type"),
    "item_15": NormalizedRegion(0.03, 0.37, 0.96, 0.43, "Item 15 container and translation info"),
    "label_area": NormalizedRegion(0.03, 0.685, 0.97, 0.975, "Lower page-one affixed label area"),
}


APPLICATION_FORM_FIELDS = tuple(key for key in FORM_REGIONS if key != "label_area")

