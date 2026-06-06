"""Field-by-field verification logic."""

from __future__ import annotations

from src.constants import (
    BRAND_PASS_THRESHOLD,
    BRAND_REVIEW_THRESHOLD,
    CLASS_TYPE_PASS_THRESHOLD,
    CLASS_TYPE_REVIEW_THRESHOLD,
    CRITICAL_FIELDS,
    GOVERNMENT_WARNING,
    LOW_CONFIDENCE_THRESHOLD,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_REVIEW,
    TEXT_FIELD_PASS_THRESHOLD,
)
from src.models import ApplicationFields, ApplicationResult, FieldResult, LabelExtraction
from src.normalize import (
    contains_title_case_warning,
    extract_abv_values,
    extract_net_contents_values,
    extract_product_type,
    fuzzy_score,
    government_warning_matches,
    normalize_abv,
    normalize_for_match,
    normalize_net_contents,
    normalize_text,
    snippet_around,
)


def verify_application(
    *,
    filename: str,
    fields: ApplicationFields,
    label: LabelExtraction,
    application_ocr_text: str,
    processing_time_seconds: float,
    extraction_warnings: list[str] | None = None,
    extraction_errors: list[str] | None = None,
) -> ApplicationResult:
    warnings = list(extraction_warnings or []) + list(label.warnings)
    errors = list(extraction_errors or [])
    results = build_field_results(fields, label)

    if label.missing_label_area:
        warnings.append("Label area is missing or blank.")
    if label.unreadable:
        warnings.append("Label text is unreadable or low confidence.")

    critical_fail = any(result.status == STATUS_FAIL and result.field in CRITICAL_FIELDS for result in results)
    any_fail = any(result.status == STATUS_FAIL for result in results)
    any_review = any(result.status == STATUS_REVIEW for result in results)

    if errors:
        overall_status = STATUS_REVIEW
    elif critical_fail:
        overall_status = STATUS_FAIL
    elif any_review or label.confidence < LOW_CONFIDENCE_THRESHOLD or warnings:
        overall_status = STATUS_REVIEW
    elif any_fail:
        overall_status = STATUS_REVIEW
    else:
        overall_status = STATUS_PASS

    confidence_values = [result.confidence for result in results]
    confidence = min(confidence_values + [label.confidence or 1.0]) if confidence_values else label.confidence
    confidence = max(0.0, min(1.0, confidence))

    return ApplicationResult(
        filename=filename,
        application_id=fields.serial_number or filename,
        serial_number=fields.serial_number,
        brand_name=fields.brand_name,
        product_type=fields.product_type,
        overall_status=overall_status,
        confidence=round(confidence, 3),
        processing_time_seconds=processing_time_seconds,
        short_summary=_short_summary(overall_status, results, warnings, errors),
        extracted_application_fields=fields.to_dict(),
        label_ocr_text=label.text,
        application_ocr_text=application_ocr_text,
        field_results=results,
        warnings=_dedupe(warnings),
        errors=_dedupe(errors),
    )


def build_field_results(fields: ApplicationFields, label: LabelExtraction) -> list[FieldResult]:
    label_text = label.text
    if (label.missing_label_area or label.unreadable) and not label_text.strip():
        reason = "Label area is missing or unreadable, so this field needs human review."
        return [
            _label_unavailable_result("brand_name", fields.brand_name, reason),
            _label_unavailable_result("fanciful_name", fields.fanciful_name, reason, optional=True),
            _label_unavailable_result("product_type", fields.product_type, reason),
            _label_unavailable_result("class_type", fields.class_type, reason),
            _label_unavailable_result("formula", fields.formula, reason),
            _label_unavailable_result("alcohol_content", fields.alcohol_content, reason),
            _label_unavailable_result("net_contents", fields.net_contents, reason),
            _label_unavailable_result("bottler_producer", fields.bottler_producer, reason, optional=True),
            _label_unavailable_country(fields.country_of_origin, fields.imported, reason),
            _result("government_warning", GOVERNMENT_WARNING, "", "", STATUS_REVIEW, label.confidence, "OCR confidence around the warning is too low to judge."),
            _label_unavailable_result("item_15", fields.item_15, reason, optional=True),
        ]
    return [
        verify_brand(fields.brand_name, label_text),
        verify_optional_fuzzy("fanciful_name", fields.fanciful_name, label_text),
        verify_product_type(fields.product_type, label_text),
        verify_class_type(fields.class_type, label_text),
        verify_formula_alcohol_content(fields.formula, label_text),
        verify_alcohol_content(fields.alcohol_content, label_text),
        verify_net_contents(fields.net_contents, label_text),
        verify_optional_fuzzy("bottler_producer", fields.bottler_producer, label_text, missing_status=STATUS_REVIEW),
        verify_country_of_origin(fields.country_of_origin, fields.imported, label_text),
        verify_government_warning(label_text, label.confidence),
        verify_item_15(fields.item_15, label_text),
    ]


def verify_brand(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _expected_missing("brand_name")
    score = fuzzy_score(expected, label_text)
    if score >= BRAND_PASS_THRESHOLD:
        return _result("brand_name", expected, expected, snippet_around(label_text, expected), STATUS_PASS, score / 100, "Brand name matches with harmless formatting variation allowed.")
    if score >= BRAND_REVIEW_THRESHOLD:
        return _result("brand_name", expected, "", snippet_around(label_text), STATUS_REVIEW, score / 100, "Brand name is similar but should be checked by a reviewer.")
    return _result("brand_name", expected, "", snippet_around(label_text), STATUS_FAIL, score / 100, "Required brand name appears materially different or missing.")


def verify_optional_fuzzy(
    field: str,
    expected: str,
    label_text: str,
    *,
    missing_status: str = STATUS_PASS,
) -> FieldResult:
    if not expected:
        return _result(field, "", "", "", STATUS_PASS, 1.0, "No expected value supplied; this optional field was not penalized.")
    score = fuzzy_score(expected, label_text)
    if score >= TEXT_FIELD_PASS_THRESHOLD:
        return _result(field, expected, expected, snippet_around(label_text, expected), STATUS_PASS, score / 100, "Expected text appears on the label.")
    return _result(field, expected, "", snippet_around(label_text), missing_status, score / 100, "Expected optional supplied text was not clearly found on the label.")


def verify_product_type(expected: str, label_text: str) -> FieldResult:
    expected_type = extract_product_type(expected)
    if not expected_type:
        return _expected_missing("product_type")
    found = extract_product_type(label_text)
    if found == expected_type:
        return _result("product_type", expected_type, found, snippet_around(label_text, found), STATUS_PASS, 0.95, "Product type matches.")
    if found:
        return _result("product_type", expected_type, found, snippet_around(label_text, found), STATUS_REVIEW, 0.7, "A different product type may appear on the label.")
    return _result("product_type", expected_type, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Product type was not clearly found on the label.")


def verify_class_type(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _expected_missing("class_type")
    score = fuzzy_score(expected, label_text)
    if score >= CLASS_TYPE_PASS_THRESHOLD:
        return _result("class_type", expected, expected, snippet_around(label_text, expected), STATUS_PASS, score / 100, "Class/type designation matches.")
    if score >= CLASS_TYPE_REVIEW_THRESHOLD:
        return _result("class_type", expected, "", snippet_around(label_text), STATUS_REVIEW, score / 100, "Class/type is similar but should be checked.")
    return _result("class_type", expected, "", snippet_around(label_text), STATUS_REVIEW, score / 100, "Class/type was not clearly found on the label.")


def verify_alcohol_content(expected: str, label_text: str) -> FieldResult:
    expected_abv = normalize_abv(expected)
    if expected_abv is None:
        return _expected_missing("alcohol_content")
    found_values = extract_abv_values(label_text)
    if not found_values:
        return _result("alcohol_content", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Alcohol content was not clearly found on the label.")
    closest = min(found_values, key=lambda value: abs(value - expected_abv))
    if abs(closest - expected_abv) <= 0.3:
        return _result("alcohol_content", f"{expected_abv:g}% ABV", f"{closest:g}% ABV", snippet_around(label_text, str(closest)), STATUS_PASS, 0.95, "Alcohol content matches after normalizing proof/ABV formats.")
    return _result("alcohol_content", f"{expected_abv:g}% ABV", f"{closest:g}% ABV", snippet_around(label_text), STATUS_FAIL, 0.95, "Material alcohol-content mismatch.")


def verify_formula_alcohol_content(formula: str, label_text: str) -> FieldResult:
    if not formula:
        return _result("formula", "", "", "", STATUS_REVIEW, 0.0, "Required Item 9 formula value could not be extracted.")
    expected_values = extract_abv_values(formula)
    if not expected_values:
        return _result(
            "formula",
            formula,
            "",
            "",
            STATUS_REVIEW,
            0.0,
            "Item 9 formula did not contain extractable alcohol content or proof.",
        )
    expected_abv = expected_values[0]
    found_values = extract_abv_values(label_text)
    if not found_values:
        return _result(
            "formula",
            f"{expected_abv:g}% ABV from Item 9",
            "",
            snippet_around(label_text),
            STATUS_REVIEW,
            0.45,
            "Alcohol content from Item 9 was not clearly found on the label.",
        )
    closest = min(found_values, key=lambda value: abs(value - expected_abv))
    if abs(closest - expected_abv) <= 0.3:
        return _result(
            "formula",
            f"{expected_abv:g}% ABV from Item 9",
            f"{closest:g}% ABV",
            snippet_around(label_text, str(closest)),
            STATUS_PASS,
            0.95,
            "Item 9 alcohol content matches the label after normalizing proof/ABV formats.",
        )
    return _result(
        "formula",
        f"{expected_abv:g}% ABV from Item 9",
        f"{closest:g}% ABV",
        snippet_around(label_text),
        STATUS_FAIL,
        0.95,
        "Item 9 alcohol content materially differs from the label.",
    )


def verify_net_contents(expected: str, label_text: str) -> FieldResult:
    expected_ml = normalize_net_contents(expected)
    if expected_ml is None:
        return _expected_missing("net_contents")
    found_values = extract_net_contents_values(label_text)
    if not found_values:
        return _result("net_contents", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Net contents were not clearly found on the label.")
    closest = min(found_values, key=lambda value: abs(value - expected_ml))
    if abs(closest - expected_ml) <= 1.0:
        return _result("net_contents", f"{expected_ml:g} mL", f"{closest:g} mL", snippet_around(label_text, str(int(closest))), STATUS_PASS, 0.95, "Net contents match after unit normalization.")
    return _result("net_contents", f"{expected_ml:g} mL", f"{closest:g} mL", snippet_around(label_text), STATUS_FAIL, 0.95, "Material net-contents mismatch.")


def verify_country_of_origin(expected: str, imported: bool, label_text: str) -> FieldResult:
    if not expected and not imported:
        return _result("country_of_origin", "", "", "", STATUS_PASS, 1.0, "Country of origin was not required for this application.")
    if not expected:
        return _expected_missing("country_of_origin")
    normalized_expected = normalize_for_match(expected)
    normalized_label = normalize_for_match(label_text)
    if normalized_expected and normalized_expected in normalized_label:
        return _result("country_of_origin", expected, expected, snippet_around(label_text, expected), STATUS_PASS, 0.95, "Country of origin appears on the label.")
    return _result("country_of_origin", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.6, "Country of origin was expected but not clearly found.")


def verify_government_warning(label_text: str, label_confidence: float) -> FieldResult:
    if label_confidence < 0.4 and not label_text.strip():
        return _result("government_warning", GOVERNMENT_WARNING, "", "", STATUS_REVIEW, label_confidence, "OCR confidence around the warning is too low to judge.")
    if contains_title_case_warning(label_text):
        return _result("government_warning", GOVERNMENT_WARNING, "Government Warning", snippet_around(label_text, "Government Warning"), STATUS_FAIL, 0.95, "Government warning heading is not all caps.")
    if government_warning_matches(label_text):
        return _result("government_warning", GOVERNMENT_WARNING, GOVERNMENT_WARNING, snippet_around(label_text, "GOVERNMENT WARNING"), STATUS_PASS, min(0.98, max(label_confidence, 0.9)), "Government warning text and all-caps heading match the canonical statement.")
    if "GOVERNMENT WARNING" in normalize_text(label_text):
        return _result("government_warning", GOVERNMENT_WARNING, "", snippet_around(label_text, "GOVERNMENT WARNING"), STATUS_FAIL, 0.9, "Government warning appears reworded, truncated, or materially altered.")
    return _result("government_warning", GOVERNMENT_WARNING, "", snippet_around(label_text), STATUS_FAIL, 0.9, "Government warning is missing.")


def verify_item_15(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _result("item_15", "", "", "", STATUS_PASS, 1.0, "No Item 15 information supplied; this optional field was not penalized.")
    score = fuzzy_score(expected, label_text)
    if score >= TEXT_FIELD_PASS_THRESHOLD:
        return _result("item_15", expected, expected, snippet_around(label_text, expected), STATUS_PASS, score / 100, "Item 15 container or translation information appears on the label/container text.")
    return _result("item_15", expected, "", snippet_around(label_text), STATUS_REVIEW, score / 100, "Item 15 information was supplied but not clearly found.")


def _expected_missing(field: str) -> FieldResult:
    return _result(field, "", "", "", STATUS_REVIEW, 0.0, "Expected application value could not be extracted.")


def _label_unavailable_result(field: str, expected: str, reason: str, optional: bool = False) -> FieldResult:
    if not expected:
        if optional:
            return _result(field, "", "", "", STATUS_PASS, 1.0, "No expected value supplied; this optional field was not penalized.")
        return _expected_missing(field)
    return _result(field, expected, "", "", STATUS_REVIEW, 0.0, reason)


def _label_unavailable_country(expected: str, imported: bool, reason: str) -> FieldResult:
    if not expected and not imported:
        return _result("country_of_origin", "", "", "", STATUS_PASS, 1.0, "Country of origin was not required for this application.")
    if not expected:
        return _expected_missing("country_of_origin")
    return _result("country_of_origin", expected, "", "", STATUS_REVIEW, 0.0, reason)


def _result(field: str, expected: str, found: str, evidence: str, status: str, confidence: float, reason: str) -> FieldResult:
    return FieldResult(
        field=field,
        expected=expected,
        found=found,
        evidence_snippet=evidence,
        status=status,
        confidence=round(max(0.0, min(1.0, confidence)), 3),
        reason=reason,
    )


def _short_summary(status: str, results: list[FieldResult], warnings: list[str], errors: list[str]) -> str:
    if errors:
        return "Application could not be processed cleanly; reviewer should inspect the PDF."
    failed = [result.field for result in results if result.status == STATUS_FAIL]
    review = [result.field for result in results if result.status == STATUS_REVIEW]
    if status == STATUS_FAIL:
        return "Failed critical checks: " + ", ".join(failed[:4])
    if status == STATUS_REVIEW:
        reasons = review[:4] or warnings[:2] or ["review recommended"]
        return "Needs review: " + ", ".join(reasons)
    return "All required checks passed with adequate confidence."


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
