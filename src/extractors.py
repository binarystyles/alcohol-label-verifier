"""PDF application and label extraction."""

from __future__ import annotations

from io import BytesIO
import re
from typing import Any

import fitz
from pypdf import PdfReader

from src.form_mapping import APPLICATION_FORM_FIELDS, FORM_REGIONS
from src.label_regions import label_regions, looks_like_non_label_page
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

PHONE_PATTERN = re.compile(r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
FORMULA_FINAL_ALCOHOL_PATTERN = re.compile(
    r"(?:ALCOHOL\s+CONTENT\s+OF\s+FINISHED\s+PRODUCT|FINAL\s+ALCOHOL\s+CONTENT|FINISHED\s+ALCOHOL\s+CONTENT|FINISHED\s+PRODUCT\s+ALCOHOL\s+CONTENT|FINAL\s+PRODUCT\s+ALCOHOL\s+CONTENT|TARGET\s+ALCOHOL\s+CONTENT)",
    flags=re.IGNORECASE,
)
FORMULA_ID_VALUE_PATTERN = r"[A-Z]{1,8}\s*[-./]?\s*\d[A-Z0-9]*(?:\s*[-./]\s*[A-Z0-9]+)*"
FORMULA_ID_PATTERNS = (
    re.compile(rf"(?:TTB\s+)?FORMULA\s+ID\s*[:#]?\s*(?P<id>{FORMULA_ID_VALUE_PATTERN})", re.IGNORECASE),
    re.compile(rf"TTB\s+ID\s*(?:NO\.?|NUMBER)?\s*[:#]?\s*(?P<id>{FORMULA_ID_VALUE_PATTERN})", re.IGNORECASE),
    re.compile(rf"FORMULA\s*(?:NO\.?|NUMBER)\s*[:#]?\s*(?P<id>{FORMULA_ID_VALUE_PATTERN})", re.IGNORECASE),
    re.compile(rf"LAB\s*(?:NO\.?|NUMBER)\s*[:#]?\s*(?P<id>{FORMULA_ID_VALUE_PATTERN})", re.IGNORECASE),
)
LOW_LABEL_SHARPNESS_THRESHOLD = 250.0

FIELD_LABEL_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "serial_number": (re.compile(r"^\s*4\.?\s*SERIAL\s+NUMBER\s*[:\-]?\s*", re.IGNORECASE),),
    "product_type": (re.compile(r"^\s*5\.?\s*TYPE\s+OF\s+PRODUCT\s*[:\-]?\s*", re.IGNORECASE),),
    "brand_name": (re.compile(r"^\s*6\.?\s*BRAND\s+(?:NAME|WAME)\s*[:\-]?\s*", re.IGNORECASE),),
    "fanciful_name": (re.compile(r"^\s*7\.?\s*FANCIFUL\s+NAME\s*[:\-]?\s*", re.IGNORECASE),),
    "applicant_name_address": (
        re.compile(r"^\s*8\.?\s*NAME\s+AND\s+ADDRESS\s+OF\s+APPLICANT\s*[:\-]?\s*", re.IGNORECASE),
        re.compile(r"^\s*NAME\s+AND\s+ADDRESS\s*[:\-]?\s*", re.IGNORECASE),
    ),
    "mailing_address": (
        re.compile(r"^\s*8A\.?\s*MAILING\s+ADDRESS\s*[:\-]?\s*", re.IGNORECASE),
        re.compile(r"^\s*MAILING\s+ADDRESS\s*[:\-]?\s*", re.IGNORECASE),
    ),
    "formula": (re.compile(r"^\s*9\.?\s*FORMULA\s*[:\-]?\s*", re.IGNORECASE),),
    "grape_varietals": (re.compile(r"^\s*10\.?\s*GRAPE\s+VARIETALS?\s*[:\-]?\s*", re.IGNORECASE),),
    "wine_appellation": (re.compile(r"^\s*11\.?\s*WINE\s+APPELLATION\s*[:\-]?\s*", re.IGNORECASE),),
    "phone": (re.compile(r"^\s*12\.?\s*PHONE(?:\s+NUMBER)?\s*[:\-]?\s*", re.IGNORECASE),),
    "email": (re.compile(r"^\s*13\.?\s*EMAIL(?:\s+ADDRESS)?\s*[:\-]?\s*", re.IGNORECASE),),
    "application_type": (re.compile(r"^\s*14\.?\s*TYPE\s+OF\s+APPLICATION\s*[:\-]?\s*", re.IGNORECASE),),
}

APPLICATION_TYPE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("CERTIFICATEOFLABELAPPROVAL", "Certificate of Label Approval"),
    ("CERTIFICATEOFEXEMPTIONFROMLABELAPPROVAL", "Certificate of Exemption from Label Approval"),
    ("DISTINCTIVELIQUORBOTTLEAPPROVAL", "Distinctive Liquor Bottle Approval"),
    ("RESUBMISSIONAFTERREJECTION", "Resubmission After Rejection"),
)

FORM_BOILERPLATE_FRAGMENTS = (
    "AFFIXED BELOW",
    "ATE OF EXEMPTION",
    "ATE OF LABEL",
    "BOTTLE CAPACITY",
    "CERTIFIC",
    "CHECK APPLICABLE",
    "DISTINCTIVE LIQUOR",
    "EMAIL A",
    "EXEMPTION FROM LABEL",
    "FILL IN",
    "FOR SALE IN",
    "IF ANY",
    "LABEL APPROVAL",
    "ONLY IF IT DOES NOT APPEAR",
    "PPLICATION",
    "REJECTION",
    "REQUIRED",
    "RESUBMISSION",
    "SHOW ANY INFORMATION",
    "TOTAL BOTTLE",
    "TRANSLATIONS OF FOREIGN",
    "TTB ID",
    "TYPE OF A",
)


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

    package_text = _application_package_text(document)
    summary_fields = parse_application_summary(package_text)
    _merge_fields(fields, summary_fields, "application-summary")

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
                    fields.raw_confidences[field_name] = extracted.confidence
            elif extracted.warning:
                warnings.append(extracted.warning)
        _merge_formula_approval(fields, package_text)

    application_text_parts.append(package_text)
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
    saw_low_quality_label_image = False

    for page_index, rect, label in label_regions(document):
        page = document[page_index]
        extracted = extract_region_text(page, rect)
        if label == "supplemental-label-page" and extracted.text.strip() and looks_like_non_label_page(extracted.text):
            continue
        if extracted.nonwhite_ratio > 0.02 or extracted.text.strip():
            saw_visual_content = True
        if extracted.nonwhite_ratio > 0.02 and 0 < extracted.sharpness < LOW_LABEL_SHARPNESS_THRESHOLD:
            saw_low_quality_label_image = True
        if extracted.text.strip():
            saw_readable_content = True
            texts.append(f"[{label} p.{page_index + 1}]\n{extracted.text.strip()}")
            confidences.append(extracted.confidence)
        elif extracted.warning and extracted.nonwhite_ratio > 0.02:
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
    if saw_low_quality_label_image:
        warnings.append("Label image appears rotated, blurry, or low quality; OCR results require human review.")
    return LabelExtraction(
        text="\n\n".join(texts),
        confidence=round(confidence, 3),
        missing_label_area=False,
        unreadable=confidence < 0.4 or saw_low_quality_label_image,
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


def parse_formula_approval_fields(text: str, formula_id: str) -> dict[str, str]:
    normalized_id = _normalize_formula_id(formula_id)
    if not normalized_id:
        return {}

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    windows: list[str] = []
    for index, line in enumerate(lines):
        if _line_matches_formula_id(line, normalized_id):
            start = max(0, index - 18)
            end = min(len(lines), index + 40)
            windows.append("\n".join(lines[start:end]))

    matched_formula_document = False
    matched_class_type = ""
    for window in windows:
        normalized_window = normalize_text(window)
        if not _looks_like_formula_approval_text(normalized_window):
            continue
        matched_formula_document = True
        alcohol_content = _extract_formula_final_alcohol_content(window)
        class_type = _extract_labeled_value(window, ("class/type", "class type", "classification"))
        if class_type and not matched_class_type:
            matched_class_type = class_type
        if not alcohol_content:
            continue
        fields = {"alcohol_content": alcohol_content}
        if class_type:
            fields["class_type"] = class_type
        return fields
    if matched_formula_document:
        fields = {"alcohol_content": ""}
        if matched_class_type:
            fields["class_type"] = matched_class_type
        return fields
    return {}


def extract_formula_identifier(text: str) -> str:
    if not text:
        return ""
    labeled_identifier = _extract_labeled_formula_identifier(text)
    if labeled_identifier:
        return labeled_identifier

    first_part = re.split(r"[;\n]", text, maxsplit=1)[0]
    generic_match = re.search(rf"\b(?P<id>{FORMULA_ID_VALUE_PATTERN})\b", first_part, flags=re.IGNORECASE)
    return generic_match.group(0).strip().upper() if generic_match else ""


def _extract_labeled_formula_identifier(text: str) -> str:
    for pattern in FORMULA_ID_PATTERNS:
        labeled_match = pattern.search(text)
        if labeled_match:
            return labeled_match.group("id").strip().upper()
    return ""


def _line_matches_formula_id(line: str, normalized_id: str) -> bool:
    candidate = _extract_labeled_formula_identifier(line)
    return bool(candidate and _normalize_formula_id(candidate) == normalized_id)


def clean_region_value(field_name: str, text: str) -> str:
    if field_name == "application_type":
        application_type = _extract_application_type(text)
        if application_type:
            return application_type
    if field_name == "phone":
        match = PHONE_PATTERN.search(text)
        return _normalize_phone(match.group(0)) if match else ""
    if field_name == "email":
        match = EMAIL_PATTERN.search(text)
        return match.group(0).strip() if match else ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept: list[str] = []
    for line in lines:
        line = _strip_field_label_prefix(field_name, line)
        upper = normalize_text(line)
        if _is_form_label_line(upper) or _is_form_boilerplate_line(upper):
            continue
        kept.append(line)
    cleaned = "\n".join(kept).strip(" :-")
    if _is_blank_or_punctuation(cleaned):
        return ""
    if field_name == "item_15":
        if "PART II" in normalize_text(cleaned) or _looks_like_item_15_noise(cleaned):
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
                fields.raw_confidences[key] = 1.0
            continue
        value = str(value).strip()
        existing_source = fields.raw_sources.get(key, "")
        may_override_existing = source == "application-summary" and existing_source in {"acroform", "form-region"}
        if value and (not getattr(fields, key) or may_override_existing):
            setattr(fields, key, value)
            fields.raw_sources[key] = source
            fields.raw_confidences[key] = 1.0


def _merge_formula_approval(fields: ApplicationFields, package_text: str) -> None:
    formula_id = extract_formula_identifier(fields.formula)
    if not formula_id:
        return
    if fields.formula != formula_id:
        fields.formula = formula_id
        fields.raw_sources["formula"] = "formula-id"
    approval_fields = parse_formula_approval_fields(package_text, formula_id)
    for key, value in approval_fields.items():
        if key == "class_type" and fields.class_type:
            continue
        setattr(fields, key, value)
        fields.raw_sources[key] = "formula-approval"
        fields.raw_confidences[key] = 1.0


def _application_package_text(document: fitz.Document) -> str:
    parts: list[str] = []
    for page_index, page in enumerate(document):
        if page_index == 0:
            parts.append(_strip_label_area_from_page_one(document))
        else:
            parts.append(page.get_text("text").strip())
    return "\n\n".join(part for part in parts if part.strip())


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


def _looks_like_formula_approval_text(normalized_text: str) -> bool:
    return any(
        marker in normalized_text
        for marker in (
            "FORMULA APPROVAL",
            "FORMULAS ONLINE",
            "TTB FORMULA ID",
            "FORMULA ID",
            "FINAL ALCOHOL CONTENT",
            "ALCOHOL CONTENT OF FINISHED PRODUCT",
            "YIELD SUMMARY",
            "DETAILED QUANTITATIVE LIST OF INGREDIENTS",
            "INGREDIENTS LIST",
            "METHOD OF MANUFACTURE",
        )
    )


def _extract_formula_final_alcohol_content(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        normalized_line = normalize_text(line)
        if not _is_formula_final_alcohol_line(normalized_line):
            continue
        prefix_segment = _formula_alcohol_segment_before_label(line)
        prefix_values = _formula_alcohol_numbers(prefix_segment)
        if prefix_values:
            return _format_formula_abv_values(prefix_values[-2:], prefix_segment)
        snippet = " ".join(lines[index : index + 4])
        segment = _formula_alcohol_segment_after_label(snippet)
        values = _formula_alcohol_numbers(segment)[:2]
        if values:
            return _format_formula_abv_values(values, segment)

    return ""


def _is_formula_final_alcohol_line(normalized_line: str) -> bool:
    return any(
        marker in normalized_line
        for marker in (
            "ALCOHOL CONTENT OF FINISHED PRODUCT",
            "FINAL ALCOHOL CONTENT",
            "FINISHED ALCOHOL CONTENT",
            "FINISHED PRODUCT ALCOHOL CONTENT",
            "FINAL PRODUCT ALCOHOL CONTENT",
            "TARGET ALCOHOL CONTENT",
        )
    )


def _formula_alcohol_segment_after_label(snippet: str) -> str:
    marker = FORMULA_FINAL_ALCOHOL_PATTERN.search(snippet)
    if not marker:
        return ""

    tail = snippet[marker.end() : marker.end() + 180]
    return re.split(
        r"\b(?:ALCOHOL\s+FROM\s+FLAVORS?|ALCOHOL\s+FROM\s+BASE|INGREDIENTS?\s+LIST|METHOD\s+OF\s+MANUFACTURE|DETAILED\s+QUANTITATIVE)\b",
        tail,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]


def _formula_alcohol_segment_before_label(line: str) -> str:
    marker = FORMULA_FINAL_ALCOHOL_PATTERN.search(line)
    if not marker:
        return ""
    prefix = line[: marker.start()]
    if "TOTAL YIELD" in normalize_text(prefix):
        return ""
    return prefix


def _formula_alcohol_numbers(segment: str) -> list[float]:
    values = [float(match) for match in re.findall(r"\d{1,3}(?:\.\d+)?", segment)]
    return [value for value in values if 0 < value <= 200]


def _format_formula_abv_values(values: list[float], snippet: str) -> str:
    uses_proof = "PROOF" in normalize_text(snippet) and "%" not in snippet and "ABV" not in normalize_text(snippet)
    converted = [value / 2.0 if uses_proof else value for value in values]
    low = min(converted)
    high = max(converted)
    if abs(low - high) <= 0.01:
        return f"{low:g}% ABV"
    return f"{low:g}-{high:g}% ABV"


def _extract_labeled_value(text: str, labels: tuple[str, ...]) -> str:
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = re.sub(r"[^a-z0-9/ ]+", "", key.lower()).strip()
        if normalized_key in labels:
            return value.strip()
    return ""


def _normalize_formula_id(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalize_text(value))


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
        "ITEM 15 CONTAINER AND TRANSLATION INFO",
    )
    if any(phrase in upper_line for phrase in label_phrases):
        return True
    if re.fullmatch(r"\d+[A-Z]?\.?", upper_line):
        return True
    if re.fullmatch(r"ITEM \d+[A-Z]? .+", upper_line):
        return True
    return False


def _strip_field_label_prefix(field_name: str, line: str) -> str:
    stripped = line
    for pattern in FIELD_LABEL_PATTERNS.get(field_name, ()):
        stripped = pattern.sub("", stripped)
    return stripped.strip(" :-")


def _is_form_boilerplate_line(upper_line: str) -> bool:
    if not upper_line:
        return True
    if any(fragment in upper_line for fragment in FORM_BOILERPLATE_FRAGMENTS):
        return True
    if re.fullmatch(r"[A-D]\.?", upper_line):
        return True
    return False


def _extract_application_type(text: str) -> str:
    compact = re.sub(r"[^A-Z]", "", normalize_text(text))
    for marker, display in APPLICATION_TYPE_OPTIONS:
        if marker in compact:
            return display
    return ""


def _normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return value.strip()


def _is_blank_or_punctuation(value: str) -> bool:
    return not re.sub(r"[\W_]+", "", value)


def _looks_like_item_15_noise(value: str) -> bool:
    tokens = re.findall(r"[A-Z0-9]+", normalize_text(value))
    meaningful_tokens = [token for token in tokens if len(token) > 2]
    return not meaningful_tokens and len(tokens) >= 3


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
