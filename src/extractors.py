"""PDF application and label extraction."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any

import fitz
from pypdf import PdfReader

from src.form_mapping import APPLICATION_FORM_FIELDS, FORM_REGIONS
from src.label_regions import label_regions
from src.models import ApplicationExtraction, ApplicationFields, LabelExtraction
from src.normalize import extract_product_type, normalize_text
from src.ocr import extract_region_text


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "serial_number": ("serial", "serial_number", "item4", "item_4"),
    "product_type": ("product_type", "type_of_product", "item5", "item_5"),
    "brand_name": ("brand", "brand_name", "item6", "item_6"),
    "fanciful_name": ("fanciful", "fanciful_name", "item7", "item_7"),
    "applicant_name_address": ("applicant", "name_address", "item8", "item_8"),
    "mailing_address": ("mailing", "item8a", "item_8a"),
    "formula": ("formula", "item9", "item_9"),
    "grape_varietals": ("grape", "varietal", "item10", "item_10"),
    "wine_appellation": ("appellation", "item11", "item_11"),
    "phone": ("phone", "item12", "item_12"),
    "email": ("email", "item13", "item_13"),
    "application_type": ("application_type", "type_of_application", "item14", "item_14"),
    "item_15": ("item15", "item_15", "container", "foreign_language", "embossed"),
    "class_type": ("class_type", "class", "designation"),
    "alcohol_content": ("alcohol_content", "abv", "alcohol", "proof"),
    "net_contents": ("net_contents", "net_content", "contents"),
    "bottler_producer": ("bottler", "producer", "importer"),
    "country_of_origin": ("country", "origin"),
    "imported": ("imported", "import"),
}

SUMMARY_KEYS: dict[str, str] = {
    "serial number": "serial_number",
    "serial_number": "serial_number",
    "application id": "serial_number",
    "product type": "product_type",
    "product_type": "product_type",
    "brand name": "brand_name",
    "brand_name": "brand_name",
    "fanciful name": "fanciful_name",
    "fanciful_name": "fanciful_name",
    "applicant": "applicant_name_address",
    "applicant name address": "applicant_name_address",
    "mailing address": "mailing_address",
    "formula": "formula",
    "grape varietals": "grape_varietals",
    "wine appellation": "wine_appellation",
    "phone": "phone",
    "email": "email",
    "application type": "application_type",
    "item 15": "item_15",
    "item_15": "item_15",
    "class type": "class_type",
    "class/type": "class_type",
    "class_type": "class_type",
    "alcohol content": "alcohol_content",
    "alcohol_content": "alcohol_content",
    "abv": "alcohol_content",
    "net contents": "net_contents",
    "net_contents": "net_contents",
    "bottler producer": "bottler_producer",
    "bottler/producer": "bottler_producer",
    "bottler_producer": "bottler_producer",
    "country of origin": "country_of_origin",
    "country_of_origin": "country_of_origin",
    "imported": "imported",
}


def extract_application(pdf_bytes: bytes) -> ApplicationExtraction:
    warnings: list[str] = []
    errors: list[str] = []
    fields = ApplicationFields()
    application_text_parts: list[str] = []

    try:
        acro_fields = extract_acroform_fields(pdf_bytes)
        _merge_fields(fields, acro_fields, "acroform")
    except Exception as exc:
        warnings.append(f"AcroForm extraction could not be used: {exc}")

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return ApplicationExtraction(fields=fields, application_ocr_text="", errors=[f"PDF could not be opened: {exc}"])

    full_text = "\n".join(page.get_text("text") for page in document)
    summary_fields = parse_application_summary(full_text)

    if document.page_count:
        page = document[0]
        for field_name in APPLICATION_FORM_FIELDS:
            if getattr(fields, field_name):
                continue
            region = FORM_REGIONS[field_name].to_rect(page.rect)
            extracted = extract_region_text(page, region)
            if extracted.text:
                application_text_parts.append(f"{field_name}: {extracted.text}")
                cleaned = clean_region_value(field_name, extracted.text)
                if field_name == "product_type":
                    cleaned = extract_product_type(cleaned) or extract_product_type(extracted.text)
                if cleaned:
                    setattr(fields, field_name, cleaned)
                    fields.raw_sources[field_name] = "form-region"
            elif extracted.warning:
                warnings.append(extracted.warning)

    _merge_fields(fields, summary_fields, "application-summary")
    application_text_parts.append(_strip_label_area_from_page_one(document))
    if summary_fields:
        application_text_parts.append(_summary_text(summary_fields))
    else:
        warnings.append("No application-data summary block was found.")

    if not any((fields.serial_number, fields.brand_name, fields.product_type)):
        warnings.append("Application fields could not be extracted with enough certainty.")

    return ApplicationExtraction(
        fields=fields,
        application_ocr_text="\n\n".join(part for part in application_text_parts if part.strip()),
        warnings=_dedupe(warnings),
        errors=errors,
    )


def extract_label(pdf_bytes: bytes) -> LabelExtraction:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return LabelExtraction(text="", confidence=0.0, unreadable=True, warnings=[f"PDF could not be opened: {exc}"])

    texts: list[str] = []
    confidences: list[float] = []
    warnings: list[str] = []
    saw_visual_content = False
    saw_readable_content = False

    for page_index, rect, label in label_regions(document):
        page = document[page_index]
        extracted = extract_region_text(page, rect)
        if extracted.nonwhite_ratio > 0.01 or extracted.text.strip():
            saw_visual_content = True
        if extracted.text.strip():
            saw_readable_content = True
            texts.append(f"[{label} p.{page_index + 1}]\n{extracted.text.strip()}")
            confidences.append(extracted.confidence)
        elif extracted.warning:
            warnings.append(extracted.warning)

    if not saw_visual_content:
        return LabelExtraction(
            text="",
            confidence=0.0,
            missing_label_area=True,
            unreadable=False,
            warnings=["No readable affixed label area was found in the completed application file."],
        )

    if saw_visual_content and not saw_readable_content:
        warnings.append("Label artwork was present, but text could not be read with adequate confidence.")
        return LabelExtraction(
            text="",
            confidence=0.0,
            missing_label_area=False,
            unreadable=True,
            warnings=_dedupe(warnings),
        )

    confidence = min(confidences) if confidences else 0.0
    return LabelExtraction(
        text="\n\n".join(texts),
        confidence=round(confidence, 3),
        missing_label_area=False,
        unreadable=confidence < 0.4,
        warnings=_dedupe(warnings),
    )


def extract_acroform_fields(pdf_bytes: bytes) -> dict[str, Any]:
    reader = PdfReader(BytesIO(pdf_bytes))
    raw_fields = reader.get_fields() or {}
    mapped: dict[str, Any] = {}
    for raw_name, field in raw_fields.items():
        value = _field_value(field)
        if value in ("", None):
            continue
        target = _target_field_name(raw_name)
        if target:
            mapped[target] = str(value).strip()
    return mapped


def parse_application_summary(text: str) -> dict[str, Any]:
    match = re.search(
        r"APPLICATION DATA SUMMARY(?P<body>.*?)END APPLICATION DATA SUMMARY",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return {}

    fields: dict[str, Any] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = re.sub(r"[^a-z0-9_/ ]+", "", key.lower()).strip()
        target = SUMMARY_KEYS.get(normalized_key)
        if not target:
            continue
        value = value.strip()
        if target == "imported":
            fields[target] = value.lower() in {"yes", "true", "y", "1", "imported"}
        else:
            fields[target] = value
    return fields


def clean_region_value(field_name: str, text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept: list[str] = []
    for line in lines:
        upper = normalize_text(line)
        if _is_form_label_line(upper):
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip(" :-")
    if field_name == "item_15" and "PART II" in normalize_text(cleaned):
        return ""
    if field_name == "product_type":
        return extract_product_type(cleaned)
    return cleaned


def _field_value(field: Any) -> Any:
    if isinstance(field, dict):
        value = field.get("/V") or field.get("V") or field.get("/DV") or field.get("DV")
        if isinstance(value, list):
            return " ".join(str(item) for item in value if item)
        return value
    return field


def _target_field_name(raw_name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", raw_name.lower())
    for target, aliases in FIELD_ALIASES.items():
        if key == target or any(alias in key for alias in aliases):
            return target
    return ""


def _merge_fields(fields: ApplicationFields, values: dict[str, Any], source: str) -> None:
    for key, value in values.items():
        if not hasattr(fields, key):
            continue
        if key == "imported":
            if value:
                fields.imported = bool(value)
                fields.raw_sources[key] = source
            continue
        value = str(value).strip()
        existing_source = fields.raw_sources.get(key, "")
        may_override_noisy_region = source == "application-summary" and existing_source == "form-region"
        if value and (not getattr(fields, key) or may_override_noisy_region):
            setattr(fields, key, value)
            fields.raw_sources[key] = source


def _strip_label_area_from_page_one(document: fitz.Document) -> str:
    if document.page_count == 0:
        return ""
    page = document[0]
    label_rect = FORM_REGIONS["label_area"].to_rect(page.rect)
    app_rect = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, label_rect.y0)
    return page.get_text("text", clip=app_rect).strip()


def _summary_text(fields: dict[str, Any]) -> str:
    lines = ["APPLICATION DATA SUMMARY"]
    for key, value in fields.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _is_form_label_line(upper_line: str) -> bool:
    label_phrases = (
        "SERIAL NUMBER",
        "TYPE OF PRODUCT",
        "BRAND NAME",
        "FANCIFUL NAME",
        "NAME AND ADDRESS",
        "MAILING ADDRESS",
        "FORMULA",
        "GRAPE VARIETAL",
        "WINE APPELLATION",
        "PHONE NUMBER",
        "EMAIL ADDRESS",
        "TYPE OF APPLICATION",
        "SHOW ANY INFORMATION",
        "AFFIXED BELOW",
        "ONLY IF IT DOES NOT APPEAR",
        "TRANSLATIONS OF FOREIGN",
        "REQUIRED",
        "IF ANY",
    )
    if any(phrase in upper_line for phrase in label_phrases):
        return True
    if re.fullmatch(r"\d+[A-Z]?\.?", upper_line):
        return True
    return False


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
