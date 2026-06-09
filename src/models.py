"""Structured result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ApplicationFields:
    serial_number: str = ""
    product_type: str = ""
    brand_name: str = ""
    fanciful_name: str = ""
    applicant_name_address: str = ""
    mailing_address: str = ""
    formula: str = ""
    grape_varietals: str = ""
    wine_appellation: str = ""
    phone: str = ""
    email: str = ""
    application_type: str = ""
    item_15: str = ""
    class_type: str = ""
    alcohol_content: str = ""
    net_contents: str = ""
    bottler_producer: str = ""
    country_of_origin: str = ""
    imported: bool = False
    raw_sources: dict[str, str] = field(default_factory=dict)
    raw_confidences: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FieldResult:
    field: str
    expected: str
    found: str
    evidence_snippet: str
    status: str
    confidence: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationExtraction:
    fields: ApplicationFields
    application_ocr_text: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class LabelExtraction:
    text: str
    confidence: float
    missing_label_area: bool = False
    unreadable: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class ApplicationResult:
    filename: str
    application_id: str
    serial_number: str
    brand_name: str
    product_type: str
    overall_status: str
    confidence: float
    processing_time_seconds: float
    short_summary: str
    extracted_application_fields: dict[str, Any]
    label_ocr_text: str
    application_ocr_text: str
    field_results: list[FieldResult]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "application_id": self.application_id,
            "serial_number": self.serial_number,
            "brand_name": self.brand_name,
            "product_type": self.product_type,
            "overall_status": self.overall_status,
            "confidence": round(self.confidence, 3),
            "processing_time_seconds": round(self.processing_time_seconds, 3),
            "short_summary": self.short_summary,
            "warnings": "; ".join(self.warnings),
            "errors": "; ".join(self.errors),
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["field_results"] = [result.to_dict() for result in self.field_results]
        return data
