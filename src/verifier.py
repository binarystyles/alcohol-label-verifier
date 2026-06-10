"""Field-by-field verification logic."""

from __future__ import annotations

import re

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
    contains_noncanonical_warning_heading_punctuation,
    contains_title_case_warning,
    extract_abv_values,
    extract_net_contents_values,
    extract_product_type,
    fuzzy_score,
    government_warning_matches,
    government_warning_similarity,
    normalize_abv,
    normalize_for_match,
    normalize_name,
    normalize_net_contents,
    normalize_text,
    ordered_fuzzy_score,
    snippet_around,
    WINE_TYPE_DESIGNATION_PATTERN,
)

WARNING_OCR_REVIEW_THRESHOLD = 86.0
LOW_FORM_OCR_CONFIDENCE_THRESHOLD = 0.9


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
    if label.missing_label_area or label.unreadable or label.confidence < LOW_CONFIDENCE_THRESHOLD:
        if label.missing_label_area:
            reason = "Label area is missing or blank, so this field needs human review."
            warning_reason = "Label area is missing or blank, so the government warning cannot be judged."
        else:
            reason = "Label OCR is low confidence; the label appears rotated, blurry, or unreadable, so this field needs human review."
            warning_reason = "Label OCR is low confidence; the label appears rotated, blurry, or unreadable, so the government warning cannot be judged reliably."
        return [
            _label_unavailable_result("brand_name", fields.brand_name, reason),
            _label_unavailable_result("fanciful_name", fields.fanciful_name, reason, optional=True),
            _label_unavailable_result("product_type", fields.product_type, reason),
            _label_unavailable_result("class_type", fields.class_type, reason),
            _label_unavailable_result("formula", fields.formula, reason),
            _label_unavailable_result("grape_varietals", fields.grape_varietals, reason, optional=True),
            _label_unavailable_result("wine_appellation", fields.wine_appellation, reason, optional=True),
            _label_unavailable_result("alcohol_content", fields.alcohol_content, reason),
            _label_unavailable_result("net_contents", fields.net_contents, reason),
            _label_unavailable_result("bottler_producer", fields.bottler_producer, reason, optional=True),
            _label_unavailable_country(fields.country_of_origin, fields.imported, reason),
            _result("government_warning", GOVERNMENT_WARNING, "", "", STATUS_REVIEW, label.confidence, warning_reason),
            _label_unavailable_result("item_15", fields.item_15, reason, optional=True),
        ]
    results = [
        verify_brand(fields.brand_name, label_text),
        verify_optional_fuzzy("fanciful_name", fields.fanciful_name, label_text, missing_status=STATUS_REVIEW),
        verify_product_type(fields.product_type, label_text),
        verify_class_type(fields.class_type, label_text),
        verify_formula_alcohol_content(fields.formula, fields.alcohol_content, fields.raw_sources.get("alcohol_content", ""), label_text),
        verify_grape_varietals(fields.grape_varietals, label_text),
        verify_optional_fuzzy("wine_appellation", fields.wine_appellation, label_text, missing_status=STATUS_REVIEW),
        verify_alcohol_content(fields.alcohol_content, label_text),
        verify_net_contents(fields.net_contents, label_text),
        verify_bottler_producer(fields.bottler_producer, label_text),
        verify_country_of_origin(fields.country_of_origin, fields.imported, label_text),
        verify_government_warning(label_text, label.confidence),
        verify_item_15(fields.item_15, label_text),
    ]
    return [_downgrade_low_confidence_expected_result(result, fields) for result in results]


def verify_brand(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _expected_missing("brand_name")
    primary_text = _primary_brand_text(label_text)
    primary_score = ordered_fuzzy_score(expected, primary_text)
    full_score = ordered_fuzzy_score(expected, label_text)
    ocr_confusion_score = _ocr_confusion_review_score(expected, primary_text or label_text)
    if primary_score >= BRAND_PASS_THRESHOLD:
        return _result("brand_name", expected, expected, snippet_around(primary_text, expected), STATUS_PASS, primary_score / 100, "Brand name matches with harmless formatting variation allowed.")
    if primary_score >= BRAND_REVIEW_THRESHOLD:
        return _result("brand_name", expected, "", snippet_around(primary_text), STATUS_REVIEW, primary_score / 100, "Brand name is similar but should be checked by a reviewer.")
    if ocr_confusion_score >= BRAND_PASS_THRESHOLD:
        return _result(
            "brand_name",
            expected,
            "",
            snippet_around(primary_text or label_text),
            STATUS_REVIEW,
            min(0.85, ocr_confusion_score / 100),
            "Brand name appears to match except for OCR-like character substitutions; reviewer should confirm the label text.",
        )
    if full_score >= BRAND_PASS_THRESHOLD and primary_text:
        return _result("brand_name", expected, "", snippet_around(label_text, expected), STATUS_FAIL, full_score / 100, "Expected brand appears only in producer, importer, warning, or other non-brand context.")
    return _result("brand_name", expected, "", snippet_around(primary_text or label_text), STATUS_FAIL, max(primary_score, full_score) / 100, "Required brand name appears materially different or missing.")


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


def verify_grape_varietals(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _result("grape_varietals", "", "", "", STATUS_PASS, 1.0, "No expected value supplied; this optional field was not penalized.")
    varietals = _split_expected_list(expected)
    if not varietals:
        return _result("grape_varietals", expected, "", "", STATUS_PASS, 1.0, "No expected value supplied; this optional field was not penalized.")
    matched: list[str] = []
    scores: list[float] = []
    for varietal in varietals:
        score = fuzzy_score(varietal, label_text)
        scores.append(score)
        if score >= TEXT_FIELD_PASS_THRESHOLD:
            matched.append(varietal)
    if len(matched) == len(varietals):
        return _result(
            "grape_varietals",
            expected,
            "; ".join(matched),
            snippet_around(label_text, matched[0]),
            STATUS_PASS,
            min(scores) / 100,
            "Expected grape varietal text appears on the label.",
        )
    missing = [varietal for varietal in varietals if varietal not in matched]
    return _result(
        "grape_varietals",
        expected,
        "; ".join(matched),
        snippet_around(label_text),
        STATUS_REVIEW,
        max(scores, default=0.0) / 100,
        f"Expected grape varietal text was not clearly found on the label: {', '.join(missing)}.",
    )


def _split_expected_list(expected: str) -> list[str]:
    parts = re.split(r"\s*(?:;|,|/|\+|\bAND\b)\s*", expected, flags=re.IGNORECASE)
    return [part.strip(" .:-") for part in parts if part.strip(" .:-")]


def verify_bottler_producer(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _result("bottler_producer", "", "", "", STATUS_PASS, 1.0, "No expected value supplied; this optional field was not penalized.")
    conflicting_parties = _conflicting_responsible_party_values(expected, label_text)
    if conflicting_parties:
        return _result(
            "bottler_producer",
            expected,
            "; ".join(conflicting_parties),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting responsible-party statements; reviewer should confirm the intended bottler/producer/importer.",
        )
    party_text = _responsible_party_text(label_text)
    score = fuzzy_score(expected, party_text)
    if score >= TEXT_FIELD_PASS_THRESHOLD:
        return _result("bottler_producer", expected, expected, snippet_around(party_text, expected), STATUS_PASS, score / 100, "Expected bottler/producer appears in responsible-party label text.")
    full_score = fuzzy_score(expected, label_text)
    if full_score >= TEXT_FIELD_PASS_THRESHOLD:
        return _result(
            "bottler_producer",
            expected,
            "",
            snippet_around(label_text, expected),
            STATUS_REVIEW,
            full_score / 100,
            "Expected bottler/producer appears only outside responsible-party label text.",
        )
    return _result("bottler_producer", expected, "", snippet_around(party_text or label_text), STATUS_REVIEW, max(score, full_score) / 100, "Expected bottler/producer was not clearly found in responsible-party label text.")


def verify_product_type(expected: str, label_text: str) -> FieldResult:
    expected_type = extract_product_type(expected)
    if not expected_type:
        return _expected_missing("product_type")
    explicit_types = _explicit_product_type_statements(label_text)
    conflicting_types = sorted({product_type for product_type in explicit_types if product_type != expected_type})
    if expected_type in explicit_types and conflicting_types:
        return _result(
            "product_type",
            expected_type,
            ", ".join(conflicting_types),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting product-type statements; reviewer should confirm the intended product type.",
        )
    candidate_text = _product_type_candidate_text(label_text)
    found = extract_product_type(candidate_text)
    if found == expected_type:
        return _result("product_type", expected_type, found, snippet_around(candidate_text, found), STATUS_PASS, 0.95, "Product type matches.")
    if (
        expected_type == "DISTILLED SPIRITS"
        and found == "WINE"
        and _distilled_spirits_class_statement_present(candidate_text)
        and not _explicit_product_type_statement_present(candidate_text, "WINE")
    ):
        return _result(
            "product_type",
            expected_type,
            "DISTILLED SPIRITS",
            snippet_around(candidate_text),
            STATUS_PASS,
            0.9,
            "Distilled spirits product type is supported by class/type text; wine wording appears only as a descriptor.",
        )
    if found:
        return _result("product_type", expected_type, found, snippet_around(candidate_text, found), STATUS_FAIL, 0.9, "Label shows a different product type than the completed application.")
    return _result("product_type", expected_type, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Product type was not clearly found on the label.")


def verify_class_type(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _expected_missing("class_type")
    class_values = _explicit_class_type_values(label_text)
    matching_class_values = [value for value in class_values if fuzzy_score(expected, value) >= CLASS_TYPE_PASS_THRESHOLD]
    conflicting_class_values = [
        value for value in class_values if fuzzy_score(expected, value) < CLASS_TYPE_REVIEW_THRESHOLD
    ]
    if matching_class_values and conflicting_class_values:
        return _result(
            "class_type",
            expected,
            "; ".join(conflicting_class_values),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting class/type statements; reviewer should confirm the intended class/type.",
        )
    class_text = _class_type_candidate_text(label_text)
    score = fuzzy_score(expected, class_text)
    if score >= CLASS_TYPE_PASS_THRESHOLD:
        return _result("class_type", expected, expected, snippet_around(class_text, expected), STATUS_PASS, score / 100, "Class/type designation matches.")
    if score >= CLASS_TYPE_REVIEW_THRESHOLD:
        return _result("class_type", expected, "", snippet_around(class_text), STATUS_REVIEW, score / 100, "Class/type is similar but should be checked.")
    full_score = fuzzy_score(expected, label_text)
    if full_score >= CLASS_TYPE_PASS_THRESHOLD and class_text:
        return _result("class_type", expected, "", snippet_around(label_text, expected), STATUS_REVIEW, full_score / 100, "Class/type appears only in brand, producer, warning, or other non-class context.")
    return _result("class_type", expected, "", snippet_around(class_text or label_text), STATUS_REVIEW, max(score, full_score) / 100, "Class/type was not clearly found on the label.")


def verify_alcohol_content(expected: str, label_text: str) -> FieldResult:
    expected_bounds = _expected_abv_bounds(expected)
    if expected_bounds is None:
        return _expected_missing("alcohol_content")
    found_values = extract_abv_values(label_text)
    if not found_values:
        return _result("alcohol_content", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Alcohol content was not clearly found on the label.")
    low, high = expected_bounds
    closest = min(found_values, key=lambda value: _distance_from_range(value, low, high))
    expected_display = _abv_display(low, high)
    matching_values = _values_inside_range(found_values, low, high, tolerance=0.3)
    conflicting_values = _values_outside_range(found_values, low, high, tolerance=0.3)
    if matching_values and conflicting_values:
        return _result(
            "alcohol_content",
            expected_display,
            _format_found_values(found_values, "% ABV"),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting alcohol-content values; reviewer should confirm the intended statement.",
        )
    if matching_values:
        return _result("alcohol_content", expected_display, f"{closest:g}% ABV", snippet_around(label_text, str(closest)), STATUS_PASS, 0.95, "Alcohol content matches after normalizing proof/ABV formats.")
    return _result("alcohol_content", expected_display, f"{closest:g}% ABV", snippet_around(label_text), STATUS_FAIL, 0.95, "Material alcohol-content mismatch.")


def verify_formula_alcohol_content(formula: str, approved_alcohol_content: str, alcohol_source: str, label_text: str) -> FieldResult:
    if not formula:
        return _result("formula", "", "", "", STATUS_REVIEW, 0.0, "Required Item 9 Formula ID could not be extracted.")
    if _is_no_formula_required_statement(formula):
        return _result("formula", formula, formula, "", STATUS_PASS, 1.0, "Item 9 states that no formula is required.")
    if alcohol_source.startswith("formula-approval-unapproved"):
        status = alcohol_source.split(":", 1)[1] if ":" in alcohol_source else "not approved"
        return _result(
            "formula",
            formula,
            status,
            "",
            STATUS_REVIEW,
            0.0,
            "The matching formula/pre-import approval document is not approved or is not current, so its final alcohol content cannot be used as expected label evidence.",
        )
    if alcohol_source != "formula-approval":
        return _result(
            "formula",
            formula,
            "",
            "",
            STATUS_REVIEW,
            0.0,
            "No matching approved formula document with final alcohol content was found for the Item 9 Formula ID.",
        )
    expected_bounds = _expected_abv_bounds(approved_alcohol_content)
    if expected_bounds is None:
        return _result(
            "formula",
            formula,
            "",
            "",
            STATUS_REVIEW,
            0.0,
            "The matched formula approval did not contain extractable final alcohol content.",
        )
    low, high = expected_bounds
    found_values = extract_abv_values(label_text)
    if not found_values:
        return _result(
            "formula",
            f"{_abv_display(low, high)} from approved formula {formula}",
            "",
            snippet_around(label_text),
            STATUS_REVIEW,
            0.45,
            "Alcohol content from the approved formula was not clearly found on the label.",
        )
    closest = min(found_values, key=lambda value: _distance_from_range(value, low, high))
    matching_values = _values_inside_range(found_values, low, high, tolerance=0.3)
    conflicting_values = _values_outside_range(found_values, low, high, tolerance=0.3)
    if matching_values and conflicting_values:
        return _result(
            "formula",
            f"{_abv_display(low, high)} from approved formula {formula}",
            _format_found_values(found_values, "% ABV"),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting alcohol-content values; reviewer should confirm the value that corresponds to the approved formula.",
        )
    if matching_values:
        return _result(
            "formula",
            f"{_abv_display(low, high)} from approved formula {formula}",
            f"{closest:g}% ABV",
            snippet_around(label_text, str(closest)),
            STATUS_PASS,
            0.95,
            "Approved formula alcohol content matches the label after normalizing proof/ABV formats.",
        )
    return _result(
        "formula",
        f"{_abv_display(low, high)} from approved formula {formula}",
        f"{closest:g}% ABV",
        snippet_around(label_text),
        STATUS_FAIL,
        0.95,
        "Approved formula alcohol content materially differs from the label.",
    )


def _is_no_formula_required_statement(formula: str) -> bool:
    normalized = normalize_text(formula)
    if "NO FORMULA REQUIRED" in normalized or "FORMULA NOT REQUIRED" in normalized:
        return True
    return normalized in {"NOT REQUIRED", "NOT APPLICABLE - NO FORMULA REQUIRED"}


def verify_net_contents(expected: str, label_text: str) -> FieldResult:
    expected_ml = normalize_net_contents(expected)
    if expected_ml is None:
        return _expected_missing("net_contents")
    found_values = extract_net_contents_values(label_text)
    if not found_values:
        return _result("net_contents", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.45, "Net contents were not clearly found on the label.")
    closest = min(found_values, key=lambda value: abs(value - expected_ml))
    tolerance = _net_contents_tolerance(expected_ml)
    matching_values = [value for value in found_values if abs(value - expected_ml) <= tolerance]
    conflicting_values = [value for value in found_values if abs(value - expected_ml) > tolerance]
    if matching_values and conflicting_values:
        return _result(
            "net_contents",
            f"{expected_ml:g} mL",
            _format_found_values(found_values, " mL"),
            snippet_around(label_text),
            STATUS_REVIEW,
            0.75,
            "Label contains conflicting net-contents values; reviewer should confirm the intended statement.",
        )
    if matching_values:
        return _result("net_contents", f"{expected_ml:g} mL", f"{closest:g} mL", snippet_around(label_text, str(int(closest))), STATUS_PASS, 0.95, "Net contents match after unit normalization.")
    return _result("net_contents", f"{expected_ml:g} mL", f"{closest:g} mL", snippet_around(label_text), STATUS_FAIL, 0.95, "Material net-contents mismatch.")


def _net_contents_tolerance(expected_ml: float) -> float:
    return max(1.0, expected_ml * 0.003)


def verify_country_of_origin(expected: str, imported: bool, label_text: str) -> FieldResult:
    if not expected and not imported:
        origin_countries = [
            country
            for country in _country_origin_statements_in_label(label_text)
            if normalize_for_match(country) != "UNITED STATES"
        ]
        if origin_countries:
            return _result(
                "country_of_origin",
                "",
                ", ".join(origin_countries),
                snippet_around(label_text),
                STATUS_REVIEW,
                0.75,
                "Application is marked domestic/no imported origin, but the label contains origin-style country wording; reviewer should confirm source of product.",
            )
        return _result("country_of_origin", "", "", "", STATUS_PASS, 1.0, "Country of origin was not required for this application.")
    if not expected:
        return _expected_missing("country_of_origin")
    if _country_origin_statement_present(expected, label_text):
        conflicting_countries = _conflicting_country_origin_statements(expected, label_text)
        if conflicting_countries:
            return _result(
                "country_of_origin",
                expected,
                ", ".join(conflicting_countries),
                snippet_around(label_text),
                STATUS_REVIEW,
                0.75,
                "Label contains conflicting country-of-origin statements; reviewer should confirm the intended origin.",
            )
        return _result("country_of_origin", expected, expected, snippet_around(label_text, expected), STATUS_PASS, 0.95, "Country of origin appears on the label.")
    return _result("country_of_origin", expected, "", snippet_around(label_text), STATUS_REVIEW, 0.6, "Country of origin was expected but not clearly found.")


def verify_government_warning(label_text: str, label_confidence: float) -> FieldResult:
    if label_confidence < LOW_CONFIDENCE_THRESHOLD:
        return _result(
            "government_warning",
            GOVERNMENT_WARNING,
            "",
            snippet_around(label_text),
            STATUS_REVIEW,
            label_confidence,
            "Label OCR is low confidence; the label appears rotated, blurry, or unreadable, so the government warning cannot be judged reliably.",
        )
    if contains_title_case_warning(label_text):
        return _result("government_warning", GOVERNMENT_WARNING, "Government Warning", snippet_around(label_text, "Government Warning"), STATUS_FAIL, 0.95, "Government warning heading is not all caps.")
    if contains_noncanonical_warning_heading_punctuation(label_text):
        return _result(
            "government_warning",
            GOVERNMENT_WARNING,
            "GOVERNMENT-WARNING",
            snippet_around(label_text),
            STATUS_FAIL,
            0.95,
            "Government warning heading punctuation is not canonical.",
        )
    if government_warning_matches(label_text):
        return _result("government_warning", GOVERNMENT_WARNING, GOVERNMENT_WARNING, snippet_around(label_text, "GOVERNMENT WARNING"), STATUS_PASS, min(0.98, max(label_confidence, 0.9)), "Government warning text and all-caps heading match the canonical statement.")
    similarity = government_warning_similarity(label_text)
    if "GOVERNMENT WARNING" in normalize_text(label_text):
        if similarity >= WARNING_OCR_REVIEW_THRESHOLD:
            return _result(
                "government_warning",
                GOVERNMENT_WARNING,
                "GOVERNMENT WARNING",
                snippet_around(label_text, "GOVERNMENT WARNING"),
                STATUS_REVIEW,
                min(0.85, max(label_confidence, 0.6)),
                "Government warning heading is present and the statement is close to canonical, but OCR/text is not exact; reviewer should confirm the warning.",
            )
        return _result("government_warning", GOVERNMENT_WARNING, "", snippet_around(label_text, "GOVERNMENT WARNING"), STATUS_FAIL, 0.9, "Government warning appears reworded, truncated, or materially altered.")
    if similarity >= WARNING_OCR_REVIEW_THRESHOLD:
        return _result(
            "government_warning",
            GOVERNMENT_WARNING,
            "",
            snippet_around(label_text),
            STATUS_REVIEW,
            min(0.85, max(label_confidence, 0.6)),
            "Government warning text is close to canonical, but the heading or OCR text is not exact; reviewer should confirm the warning.",
        )
    return _result("government_warning", GOVERNMENT_WARNING, "", snippet_around(label_text), STATUS_FAIL, 0.9, "Government warning is missing.")


def verify_item_15(expected: str, label_text: str) -> FieldResult:
    if not expected:
        return _result("item_15", "", "", "", STATUS_PASS, 1.0, "No Item 15 information supplied; this optional field was not penalized.")
    score = fuzzy_score(expected, label_text)
    if score >= TEXT_FIELD_PASS_THRESHOLD:
        return _result("item_15", expected, expected, snippet_around(label_text, expected), STATUS_PASS, score / 100, "Item 15 container or translation information appears on the label/container text.")
    return _result("item_15", expected, "", snippet_around(label_text), STATUS_REVIEW, score / 100, "Item 15 information was supplied but not clearly found.")


def _primary_brand_text(label_text: str) -> str:
    candidates: list[str] = []
    for line in _label_lines(label_text):
        primary = _line_before_non_brand_context(line)
        if primary and not _is_obvious_non_brand_line(primary):
            candidates.append(primary)
    return "\n".join(candidates)


def _product_type_candidate_text(label_text: str) -> str:
    return "\n".join(
        line
        for index, line in enumerate(_label_lines(label_text))
        if (index > 0 or _is_explicit_product_type_line(line) or _is_explicit_class_type_line(line))
        and not _is_obvious_non_product_type_line(line)
    )


MODIFIED_CIDER_TYPE_PATTERN = (
    r"(?:APPLE|PEAR|DRY|SEMI[-\s]+DRY|SWEET|SEMI[-\s]+SWEET|SPARKLING|STILL|HOPPED|"
    r"BARREL[-\s]+AGED)\s+HARD\s+CIDER|HARD\s+(?:APPLE|PEAR)\s+CIDER|(?:APPLE|PEAR)\s+CIDER"
)
MODIFIED_BEER_TYPE_PATTERN = (
    r"(?:[A-Z0-9&']+\s+){0,3}(?:BARREL|CASK|OAK|WOOD)[-\s]+AGED\s+"
    r"(?:BEER|ALE|LAGER|STOUT|PORTER|IPA|PILSNER|PILS)|BARLEY\s*WINE(?:\s+ALE)?"
)


def _is_explicit_class_type_line(line: str) -> bool:
    normalized = normalize_text(line)
    return "CLASS/TYPE" in normalized or "CLASS TYPE" in normalized


def _is_explicit_product_type_line(line: str) -> bool:
    normalized = normalize_text(line)
    return bool(
        re.fullmatch(
            r"(?:PRODUCT\s+TYPE\s*:?\s*)?(?:DISTILLED\s+SPIRITS|MALT\s+BEVERAGES?|MALT\s+LIQUOR|BEER|ALE|LAGER|STOUT|PORTER|IPA|PILSNER|PILS|SAISON|GOSE|KOLSCH|KOELSCH|BOCK|DOPPELBOCK|WITBIER|HEFEWEIZEN|LAMBIC|CERVEZA|FMB|HARD\s+SELTZER|SPIKED\s+SELTZER|MALT[-\s]+BASED[-\s]+SELTZER|WINE|RED\s+WINE|WHITE\s+WINE|ROSE\s+WINE|SPARKLING\s+WINE|TABLE\s+WINE|DESSERT\s+WINE|HARD\s+CIDER|CIDER|PERRY|SAKE|VERMOUTH|SHERRY|ANGELICA|MADEIRA|MUSCATEL|PORT|CHAMPAGNE)",
            normalized,
        )
        or re.fullmatch(
            rf"(?:PRODUCT\s+TYPE\s*:?\s*)?(?:(?:LIGHT|LAGER|PILSNER|PILS|WHEAT)\s+BEER|"
            rf"(?:INDIA\s+PALE|PALE|BROWN|AMBER|BLONDE|RED|CREAM)\s+ALE|"
            rf"FLAVORED\s+MALT\s+BEVERAGE|{MODIFIED_BEER_TYPE_PATTERN}|MEAD|HONEY\s+WINE|SANGRIA|{MODIFIED_CIDER_TYPE_PATTERN}|"
            rf"{WINE_TYPE_DESIGNATION_PATTERN})",
            normalized,
        )
        or re.fullmatch(
            r"(?:PRODUCT\s+TYPE\s*:?\s*)?(?:(?:SPARKLING|FLAVORED|FLAVOURED|ALCOHOLIC)\s+HARD\s+SELTZER|(?:IMPERIAL|DOUBLE|TRIPLE|HAZY|SESSION|WEST\s+COAST|NEW\s+ENGLAND|DRY[-\s]+HOPPED|BARREL[-\s]+AGED)\s+(?:STOUT|PORTER|IPA|PILSNER|PILS|LAGER|ALE)|(?:STRAIGHT\s+)?(?:(?:RYE|BOURBON|MALT|WHEAT|CORN)\s+)?WHISKEY|(?:SINGLE\s+MALT\s+)?SCOTCH\s+WHISKY|(?:IRISH|CANADIAN|STRAIGHT|RYE|BOURBON|MALT|WHEAT|CORN)\s+WHISKY|GIN|VODKA|RUM|TEQUILA|MEZCAL|BRANDY|COGNAC|LIQUEUR|CORDIAL|SCHNAPPS|AQUAVIT|BOURBON)",
            normalized,
        )
    )


def _is_obvious_non_product_type_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized:
        return True
    return bool(
        re.search(
            r"\b(GOVERNMENT\s+WARNING|PRODUCT\s+OF|PRODUCED\s+IN|MADE\s+IN|COUNTRY\s+OF\s+ORIGIN|BOTTLED\s+BY|PRODUCED\s+BY|IMPORTED\s+BY|BREWED\s+BY|NET\s+CONTENTS?|SERVING\s+SIZE|ALC|ALCOHOL|PROOF)\b",
            normalized,
        )
    )


def _explicit_product_type_statement_present(label_text: str, product_type: str) -> bool:
    return any(_is_explicit_product_type_line(line) and extract_product_type(line) == product_type for line in _label_lines(label_text))


def _explicit_product_type_statements(label_text: str) -> list[str]:
    product_types: list[str] = []
    for line in _label_lines(label_text):
        if not _is_explicit_product_type_line(line):
            continue
        product_type = extract_product_type(line)
        if product_type:
            product_types.append(product_type)
    return product_types


def _distilled_spirits_class_statement_present(label_text: str) -> bool:
    for line in _label_lines(label_text):
        normalized = normalize_text(line)
        if "CLASS/TYPE" in normalized or "CLASS TYPE" in normalized:
            value = re.split(r"CLASS\s*/?\s*TYPE\s*:?", line, maxsplit=1, flags=re.IGNORECASE)[-1]
            if extract_product_type(value) == "DISTILLED SPIRITS":
                return True
            continue
        if _is_obvious_non_class_line(line):
            continue
        if extract_product_type(line) == "DISTILLED SPIRITS":
            return True
    return False


def _class_type_candidate_text(label_text: str) -> str:
    candidates: list[str] = []
    lines = _label_lines(label_text)
    for index, line in enumerate(lines):
        normalized_line = normalize_text(line)
        if "CLASS/TYPE" in normalized_line or "CLASS TYPE" in normalized_line:
            value = re.split(r"CLASS\s*/?\s*TYPE\s*:?", line, maxsplit=1, flags=re.IGNORECASE)[-1].strip(" :-")
            if value:
                candidates.append(value)
            continue
        if index == 0 and not _is_explicit_product_type_line(line):
            continue
        if _is_obvious_non_class_line(line):
            continue
        candidates.append(line)
    return "\n".join(candidates)


def _explicit_class_type_values(label_text: str) -> list[str]:
    values: list[str] = []
    for line in _label_lines(label_text):
        normalized_line = normalize_text(line)
        if "CLASS/TYPE" not in normalized_line and "CLASS TYPE" not in normalized_line:
            continue
        value = re.split(r"CLASS\s*/?\s*TYPE\s*:?", line, maxsplit=1, flags=re.IGNORECASE)[-1].strip(" :-")
        if value:
            values.append(value)
    return values


def _responsible_party_text(label_text: str) -> str:
    candidates: list[str] = []
    for line in _label_lines(label_text):
        if _responsible_party_entries(line):
            candidates.append(line)
    return "\n".join(candidates)


RESPONSIBLE_PARTY_ACTION_PATTERN = (
    r"(?:BOTTLED|PRODUCED|DISTILLED|BLENDED|IMPORTED|BREWED|VINTED|CELLARED|CANNED|PACKED|PACKAGED|FILLED|MADE|PREPARED|MANUFACTURED|MFG\.?|MFR\.?|DISTRIBUTED)"
)
RESPONSIBLE_PARTY_ACTION_ALIASES = {"MFG": "MANUFACTURED", "MFR": "MANUFACTURED"}
RESPONSIBLE_PARTY_REQUIRED_ACTIONS = {
    "BOTTLED",
    "PRODUCED",
    "DISTILLED",
    "BLENDED",
    "IMPORTED",
    "BREWED",
    "VINTED",
    "CELLARED",
    "CANNED",
    "PACKED",
    "PACKAGED",
    "FILLED",
    "MADE",
    "PREPARED",
    "MANUFACTURED",
}
RESPONSIBLE_PARTY_ACTION_LIST_PATTERN = (
    rf"{RESPONSIBLE_PARTY_ACTION_PATTERN}"
    rf"(?:(?:\s*(?:,|/|&)\s*|\s+AND\s+){RESPONSIBLE_PARTY_ACTION_PATTERN})*"
)
RESPONSIBLE_PARTY_MODIFIER_PATTERN = r"(?:(?:EXCLUSIVELY|SPECIALLY|SOLELY)\s+)?"
RESPONSIBLE_PARTY_CONTEXT_PATTERN = (
    rf"\b{RESPONSIBLE_PARTY_ACTION_LIST_PATTERN}\s+{RESPONSIBLE_PARTY_MODIFIER_PATTERN}(?:BY|FOR)\b"
)
RESPONSIBLE_PARTY_VALUE_PATTERN = re.compile(
    rf"\b(?P<actions>{RESPONSIBLE_PARTY_ACTION_LIST_PATTERN})\s+{RESPONSIBLE_PARTY_MODIFIER_PATTERN}(?P<role>BY|FOR)\s*(?::|-|\.)?\s+(?P<party>.+)",
    re.IGNORECASE,
)


def _responsible_party_entries(label_text: str) -> list[tuple[frozenset[str], str, str]]:
    entries: list[tuple[frozenset[str], str, str]] = []
    for line in _label_lines(label_text):
        match = RESPONSIBLE_PARTY_VALUE_PATTERN.search(line)
        if not match:
            continue
        actions = frozenset(
            RESPONSIBLE_PARTY_ACTION_ALIASES.get(action.rstrip("."), action.rstrip("."))
            for action in re.findall(RESPONSIBLE_PARTY_ACTION_PATTERN, normalize_text(match.group("actions")))
        )
        role = normalize_text(match.group("role"))
        party = match.group("party").strip(" .:-")
        if not actions.intersection(RESPONSIBLE_PARTY_REQUIRED_ACTIONS) or not party:
            continue
        for entry_role, entry_party in _split_chained_responsible_party(role, party):
            entries.append((actions, entry_role, entry_party))
    return entries


def _split_chained_responsible_party(role: str, party: str) -> list[tuple[str, str]]:
    opposite_role = "BY" if role == "FOR" else "FOR"
    pattern = re.compile(rf"\s+\b{opposite_role}\b\s*(?::|-|\.)?\s+", re.IGNORECASE)
    for match in pattern.finditer(party):
        first_party = party[: match.start()].strip(" .:-")
        second_party = party[match.end() :].strip(" .:-")
        if _looks_like_chained_responsible_party_split(first_party, second_party):
            return [(role, first_party), (opposite_role, second_party)]
    return [(role, party)]


def _looks_like_chained_responsible_party_split(first_party: str, second_party: str) -> bool:
    first_tokens = re.findall(r"[A-Za-z0-9]+", first_party)
    second_tokens = re.findall(r"[A-Za-z0-9]+", second_party)
    return len(first_tokens) >= 2 and len(second_tokens) >= 2


def _conflicting_responsible_party_values(expected: str, label_text: str) -> list[str]:
    entries = _responsible_party_entries(label_text)
    matching_entries = [
        (actions, role)
        for actions, role, party in entries
        if fuzzy_score(expected, party) >= TEXT_FIELD_PASS_THRESHOLD
    ]
    if not matching_entries:
        return []

    conflicts: list[str] = []
    for actions, role, party in entries:
        if fuzzy_score(expected, party) >= TEXT_FIELD_PASS_THRESHOLD:
            continue
        if any(
            _responsible_party_entries_conflict(actions, role, matched_actions, matched_role)
            for matched_actions, matched_role in matching_entries
        ):
            conflicts.append(party)
    return conflicts


def _responsible_party_entries_conflict(
    actions: frozenset[str],
    role: str,
    matched_actions: frozenset[str],
    matched_role: str,
) -> bool:
    if not actions.intersection(matched_actions):
        return False
    if role == matched_role:
        return True
    return matched_role == "FOR" and role == "BY"


def _label_lines(label_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in re.split(r"[\r\n]+", label_text or ""):
        line = raw_line.strip()
        if not line:
            continue
        if re.fullmatch(r"\[[^\]]+\]", line):
            continue
        lines.append(line)
    if len(lines) == 1:
        return _split_flat_label_line(lines[0])
    return lines


OCR_CONFUSION_TRANSLATION = str.maketrans({"0": "O", "1": "I", "5": "S"})


def _ocr_confusion_review_score(expected: str, actual: str) -> float:
    expected_tokens = _normalize_ocr_confusions(expected).split()
    actual_tokens = _normalize_ocr_confusions(actual).split()
    if _contains_ordered_token_sequence(expected_tokens, actual_tokens):
        return 100.0
    return ordered_fuzzy_score(_normalize_ocr_confusions(expected), _normalize_ocr_confusions(actual))


def _normalize_ocr_confusions(value: str) -> str:
    return normalize_name(normalize_text(value).translate(OCR_CONFUSION_TRANSLATION))


def _contains_ordered_token_sequence(expected_tokens: list[str], actual_tokens: list[str]) -> bool:
    if not expected_tokens or len(expected_tokens) > len(actual_tokens):
        return False
    width = len(expected_tokens)
    return any(actual_tokens[index : index + width] == expected_tokens for index in range(len(actual_tokens) - width + 1))


def _split_flat_label_line(line: str) -> list[str]:
    split_markers = (
        r"\bCLASS\s*/?\s*TYPE\s*:?",
        r"\b(?:DISTILLED\s+SPIRITS|MALT\s+BEVERAGES?)\b",
        RESPONSIBLE_PARTY_CONTEXT_PATTERN,
        r"\bGOVERNMENT\s+WARNING\b",
        r"\b(?:NET\s+CONTENTS?|SERVING\s+SIZE)\b",
        r"\b(?:ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+\d|PROOF\s*\d|\d{1,3}(?:\.\d+)?\s*(?:%|PERCENT|PROOF))\b",
    )
    pattern = "(" + "|".join(split_markers) + ")"
    pieces = re.split(pattern, line, flags=re.IGNORECASE)
    if len(pieces) == 1:
        return [line]
    lines: list[str] = []
    current = ""
    for piece in pieces:
        if not piece:
            continue
        if re.match(pattern, piece, flags=re.IGNORECASE):
            if current.strip() and _ends_with_class_type_marker(current):
                current += " " + piece
                continue
            if current.strip():
                lines.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        lines.append(current.strip())
    return lines


def _ends_with_class_type_marker(text: str) -> bool:
    return bool(re.search(r"\bCLASS\s*/?\s*TYPE\s*:?\s*$", text, flags=re.IGNORECASE))


def _line_before_non_brand_context(line: str) -> str:
    context_pattern = (
        RESPONSIBLE_PARTY_CONTEXT_PATTERN +
        r"|\bGOVERNMENT\s+WARNING\b"
        r"|\bCLASS\s*/?\s*TYPE\s*:?"
        r"|\b(?:DISTILLED\s+SPIRITS|MALT\s+BEVERAGES?)\b"
        r"|\b(?:NET\s+CONTENTS?|SERVING\s+SIZE)\b"
        r"|\b(?:ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+\d|PROOF\s*\d|\d{1,3}(?:\.\d+)?\s*(?:%|PERCENT|PROOF))\b"
    )
    parts = re.split(context_pattern, line, maxsplit=1, flags=re.IGNORECASE)
    return parts[0].strip(" :-")


def _is_obvious_non_brand_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized:
        return True
    return bool(
        re.search(
            RESPONSIBLE_PARTY_CONTEXT_PATTERN
            + r"|\b(CLASS\s*/?\s*TYPE|DISTILLED\s+SPIRITS|MALT\s+BEVERAGES?|GOVERNMENT\s+WARNING|PRODUCT\s+OF|PRODUCED\s+IN|MADE\s+IN|COUNTRY\s+OF\s+ORIGIN|NET\s+CONTENTS?|SERVING\s+SIZE|ALC|ALCOHOL\s+\d|PROOF\s*\d|\d{1,3}(?:\.\d+)?\s*(?:%|PERCENT|PROOF))\b",
            normalized,
        )
    )


def _is_obvious_non_class_line(line: str) -> bool:
    normalized = normalize_text(line)
    if not normalized:
        return True
    return bool(
        re.search(
            RESPONSIBLE_PARTY_CONTEXT_PATTERN
            + r"|\b(DISTILLED\s+SPIRITS|MALT\s+BEVERAGES?|GOVERNMENT\s+WARNING|PRODUCT\s+OF|PRODUCED\s+IN|MADE\s+IN|COUNTRY\s+OF\s+ORIGIN|NET\s+CONTENTS?|SERVING\s+SIZE|ALC|ALCOHOL|PROOF)\b",
            normalized,
        )
    )


def _is_responsible_party_line(line: str) -> bool:
    return bool(re.search(RESPONSIBLE_PARTY_CONTEXT_PATTERN, normalize_text(line)))


def _expected_missing(field: str) -> FieldResult:
    return _result(field, "", "", "", STATUS_REVIEW, 0.0, "Expected application value could not be extracted.")


def _downgrade_low_confidence_expected_result(result: FieldResult, fields: ApplicationFields) -> FieldResult:
    if result.status == STATUS_REVIEW:
        return result
    if fields.raw_sources.get(result.field) != "form-region":
        return result
    source_confidence = fields.raw_confidences.get(result.field, 1.0)
    if source_confidence >= LOW_FORM_OCR_CONFIDENCE_THRESHOLD:
        return result
    if result.status == STATUS_PASS:
        return _result(
            result.field,
            result.expected,
            result.found,
            result.evidence_snippet,
            STATUS_REVIEW,
            min(result.confidence, source_confidence),
            "Expected application value came from low-confidence form OCR; reviewer should confirm it before treating this as verified.",
        )
    return _result(
        result.field,
        result.expected,
        result.found,
        result.evidence_snippet,
        STATUS_REVIEW,
        min(result.confidence, source_confidence),
        "Expected application value came from low-confidence form OCR; reviewer should confirm it before treating this as a mismatch.",
    )


def _expected_abv_bounds(expected: str) -> tuple[float, float] | None:
    repeated_unit_proof_range_match = re.search(
        r"(?P<low>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:\u00b0|DEGREES?)?\s*PROOF\s*(?:-|TO|\u2013|\u2014|â€“|â€”)\s*(?P<high>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:\u00b0|DEGREES?)?\s*PROOF\b",
        expected,
        flags=re.IGNORECASE,
    )
    if repeated_unit_proof_range_match:
        low = float(repeated_unit_proof_range_match.group("low").replace(",", ".")) / 2.0
        high = float(repeated_unit_proof_range_match.group("high").replace(",", ".")) / 2.0
        if 0 < low <= 100 and 0 < high <= 100:
            return (min(low, high), max(low, high))

    repeated_unit_abv_range_match = re.search(
        r"(?P<low>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:%|PERCENT|PCT\.?)\s*(?:ABV|ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+BY\s+VOLUME|VOL(?:UME)?\.?)?\s*(?:-|TO|\u2013|\u2014|â€“|â€”)\s*(?P<high>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:%|PERCENT|PCT\.?)\s*(?:ABV|ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+BY\s+VOLUME|VOL(?:UME)?\.?)",
        expected,
        flags=re.IGNORECASE,
    )
    if repeated_unit_abv_range_match:
        low = float(repeated_unit_abv_range_match.group("low").replace(",", "."))
        high = float(repeated_unit_abv_range_match.group("high").replace(",", "."))
        if 0 < low <= 100 and 0 < high <= 100:
            return (min(low, high), max(low, high))

    proof_range_match = re.search(
        r"(?P<low>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:-|TO|\u2013|\u2014|â€“|â€”)\s*(?P<high>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:\u00b0|DEGREES?)?\s*PROOF\b",
        expected,
        flags=re.IGNORECASE,
    ) or re.search(
        r"\bPROOF\s*:?\s*(?P<low>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:-|TO|\u2013|\u2014|â€“|â€”)\s*(?P<high>\d{1,3}(?:[.,]\d{1,2})?)\b",
        expected,
        flags=re.IGNORECASE,
    )
    if proof_range_match:
        low = float(proof_range_match.group("low").replace(",", ".")) / 2.0
        high = float(proof_range_match.group("high").replace(",", ".")) / 2.0
        if 0 < low <= 100 and 0 < high <= 100:
            return (min(low, high), max(low, high))

    decimal_range_match = re.search(
        r"(?P<low>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:-|TO|\u2013|\u2014|â€“|â€”)\s*(?P<high>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:%|PERCENT)?\s*(?:ABV|ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+BY\s+VOLUME)?",
        expected,
        flags=re.IGNORECASE,
    )
    if decimal_range_match:
        low = float(decimal_range_match.group("low").replace(",", "."))
        high = float(decimal_range_match.group("high").replace(",", "."))
        if 0 < low <= 100 and 0 < high <= 100:
            return (min(low, high), max(low, high))

    range_match = re.search(
        r"(?P<low>\d{1,3}(?:\.\d+)?)\s*(?:-|TO|–|—)\s*(?P<high>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)?\s*(?:ABV|ALC\.?\s*/?\s*VOL\.?|ALCOHOL\s+BY\s+VOLUME)?",
        expected,
        flags=re.IGNORECASE,
    )
    if range_match:
        low = float(range_match.group("low"))
        high = float(range_match.group("high"))
        if 0 < low <= 100 and 0 < high <= 100:
            return (min(low, high), max(low, high))

    value = normalize_abv(expected)
    if value is None:
        return None
    return (value, value)


def _distance_from_range(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 0.0
    return min(abs(value - low), abs(value - high))


def _values_inside_range(values: list[float], low: float, high: float, *, tolerance: float) -> list[float]:
    return [value for value in values if low - tolerance <= value <= high + tolerance]


def _values_outside_range(values: list[float], low: float, high: float, *, tolerance: float) -> list[float]:
    return [value for value in values if value < low - tolerance or value > high + tolerance]


def _format_found_values(values: list[float], suffix: str) -> str:
    return ", ".join(f"{value:g}{suffix}" for value in values)


def _abv_display(low: float, high: float) -> str:
    if abs(low - high) <= 0.01:
        return f"{low:g}% ABV"
    return f"{low:g}-{high:g}% ABV"


def _country_origin_statement_present(expected: str, label_text: str) -> bool:
    normalized_country = normalize_for_match(expected)
    normalized_label = normalize_for_match(label_text)
    if not normalized_country or not normalized_label:
        return False
    patterns: list[str] = []
    for country_name in _country_origin_name_variants(normalized_country):
        country = re.escape(country_name)
        patterns.extend(
            (
                rf"\bPRODUCT\s+(?:OF|FROM)\s+(?:THE\s+)?{country}\b",
                rf"\bPRODUCE\s+(?:OF|FROM)\s+(?:THE\s+)?{country}\b",
                rf"\b(?:{COUNTRY_ORIGIN_PRODUCT_TERMS_PATTERN})\s+OF\s+(?:THE\s+)?{country}\b",
                rf"\bPRODUCED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bPRODUCED\s+AND\s+BOTTLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bPRODUCED(?:\s+AND)?\s+(?:BOTTLED|CANNED|PACKAGED|PACKED)(?:\s+AND\s+(?:BOTTLED|CANNED|PACKAGED|PACKED))*\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bDISTILLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bDISTILLED\s+AND\s+BOTTLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bDISTILLED(?:\s+AND)?\s+(?:AGED|MATURED)(?:\s+AND\s+BOTTLED)?\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBLENDED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBLENDED\s+AND\s+BOTTLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBLENDED(?:\s+AND)?\s+(?:AGED|MATURED)(?:\s+AND\s+BOTTLED)?\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBREWED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBREWED\s+AND\s+BOTTLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bBREWED(?:\s+AND)?\s+(?:BOTTLED|CANNED|PACKAGED|PACKED)(?:\s+AND\s+(?:BOTTLED|CANNED|PACKAGED|PACKED))*\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bMADE\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bMADE\s+AND\s+BOTTLED\s+IN\s+(?:THE\s+)?{country}\b",
                rf"\bIMPORTED\s+FROM\s+(?:THE\s+)?{country}\b",
                rf"\bIMPORTED\s+(?:INTO|TO)\b(?:\s+[A-Z0-9]+){{0,12}}\s+FROM\s+(?:THE\s+)?{country}\b",
                rf"\bIMPORTED\s+BY\b(?:\s+[A-Z0-9]+){{0,12}}\s+FROM\s+(?:THE\s+)?{country}\b",
                rf"\bCOUNTRY\s+OF\s+ORIGIN\s+(?:THE\s+)?{country}\b",
                rf"\bORIGIN\s+(?:THE\s+)?{country}\b",
                rf"\b{country}\s+ORIGIN\b",
            )
        )
        if country_name == "SCOTLAND":
            patterns.append(r"\bSCOTCH\s+WHISK(?:Y|EY)\b")
        elif country_name in {"IRELAND", "REPUBLIC OF IRELAND"}:
            patterns.append(r"\bIRISH\s+WHISK(?:Y|EY)\b")
        elif country_name == "CANADA":
            patterns.append(r"\bCANADIAN\s+WHISK(?:Y|EY)\b")
    return any(re.search(pattern, normalized_label) for pattern in patterns)


COUNTRY_ORIGIN_PRODUCT_TERMS_PATTERN = (
    r"WINE|BEER|ALE|LAGER|STOUT|PORTER|CIDER|PERRY|HARD\s+CIDER|HARD\s+SELTZER|"
    r"MALT\s+BEVERAGES?|FLAVORED\s+MALT\s+BEVERAGE|MALT\s+LIQUOR|"
    r"WHISKY|WHISKEY|BOURBON|SCOTCH|VODKA|GIN|RUM|TEQUILA|MEZCAL|BRANDY|COGNAC|"
    r"LIQUEUR|CORDIAL|SCHNAPPS|AQUAVIT|SAKE|VERMOUTH|SHERRY|PORT|CHAMPAGNE|"
    r"MEAD|SANGRIA"
)


COUNTRY_ORIGIN_CANONICAL_ALIASES: dict[str, tuple[str, ...]] = {
    "ARGENTINA": ("ARGENTINA",),
    "AUSTRALIA": ("AUSTRALIA",),
    "AUSTRIA": ("AUSTRIA",),
    "BARBADOS": ("BARBADOS",),
    "BELGIUM": ("BELGIUM",),
    "BRAZIL": ("BRAZIL",),
    "CANADA": ("CANADA",),
    "CHILE": ("CHILE",),
    "CHINA": ("CHINA",),
    "COLOMBIA": ("COLOMBIA",),
    "DENMARK": ("DENMARK",),
    "DOMINICAN REPUBLIC": ("DOMINICAN REPUBLIC",),
    "FRANCE": ("FRANCE",),
    "GERMANY": ("GERMANY",),
    "GREECE": ("GREECE",),
    "GUATEMALA": ("GUATEMALA",),
    "HUNGARY": ("HUNGARY",),
    "IRELAND": ("IRELAND", "REPUBLIC OF IRELAND"),
    "ITALY": ("ITALY",),
    "JAMAICA": ("JAMAICA",),
    "JAPAN": ("JAPAN",),
    "MEXICO": ("MEXICO",),
    "NETHERLANDS": ("NETHERLANDS", "THE NETHERLANDS"),
    "NEW ZEALAND": ("NEW ZEALAND",),
    "PERU": ("PERU",),
    "PORTUGAL": ("PORTUGAL",),
    "SOUTH AFRICA": ("SOUTH AFRICA",),
    "SPAIN": ("SPAIN",),
    "SWITZERLAND": ("SWITZERLAND",),
    "TRINIDAD AND TOBAGO": ("TRINIDAD AND TOBAGO",),
    "UNITED KINGDOM": (
        "UNITED KINGDOM",
        "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
        "GREAT BRITAIN",
        "BRITAIN",
        "UK",
        "U K",
        "ENGLAND",
        "SCOTLAND",
        "WALES",
        "NORTHERN IRELAND",
    ),
    "UNITED STATES": ("UNITED STATES", "UNITED STATES OF AMERICA", "USA", "U S A", "US", "U S"),
}


def _conflicting_country_origin_statements(expected: str, label_text: str) -> list[str]:
    expected_canonical = _canonical_country_origin(expected)
    conflicts: list[str] = []
    for country in _country_origin_statements_in_label(label_text):
        if normalize_for_match(country) == expected_canonical:
            continue
        conflicts.append(country)
    return conflicts


def _country_origin_statements_in_label(label_text: str) -> list[str]:
    countries: list[str] = []
    for country, aliases in COUNTRY_ORIGIN_CANONICAL_ALIASES.items():
        if any(_country_origin_statement_present(alias, label_text) for alias in aliases):
            countries.append(country.title())
    return countries


def _canonical_country_origin(country: str) -> str:
    normalized_country = normalize_for_match(country)
    for canonical, aliases in COUNTRY_ORIGIN_CANONICAL_ALIASES.items():
        if normalized_country in {normalize_for_match(alias) for alias in aliases}:
            return canonical
    return normalized_country


def _country_origin_name_variants(normalized_country: str) -> tuple[str, ...]:
    if normalized_country in {"UNITED STATES", "UNITED STATES OF AMERICA", "USA", "U S A", "US", "U S"}:
        return ("UNITED STATES", "UNITED STATES OF AMERICA", "USA", "U S A", "US", "U S")
    if normalized_country in {
        "UNITED KINGDOM",
        "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
        "GREAT BRITAIN",
        "BRITAIN",
        "UK",
        "U K",
    }:
        return (
            "UNITED KINGDOM",
            "UNITED KINGDOM OF GREAT BRITAIN AND NORTHERN IRELAND",
            "GREAT BRITAIN",
            "BRITAIN",
            "UK",
            "U K",
            "ENGLAND",
            "SCOTLAND",
            "WALES",
            "NORTHERN IRELAND",
        )
    if normalized_country in {"IRELAND", "REPUBLIC OF IRELAND"}:
        return ("IRELAND", "REPUBLIC OF IRELAND")
    if normalized_country in {"NETHERLANDS", "THE NETHERLANDS"}:
        return ("NETHERLANDS", "THE NETHERLANDS")
    return (normalized_country,)


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
        warning_summary = _review_warning_summary(warnings)
        if warning_summary:
            return f"Needs review: {warning_summary}"
        reasons = review[:4] or warnings[:2] or ["review recommended"]
        return "Needs review: " + ", ".join(reasons)
    return "All required checks passed with adequate confidence."


def _review_warning_summary(warnings: list[str]) -> str:
    for warning in warnings:
        normalized = warning.lower()
        if "label image appears rotated" in normalized or "label text is unreadable" in normalized:
            return "label OCR quality"
        if "label artwork was present" in normalized:
            return "label artwork text unreadable"
        if "no readable affixed label area" in normalized or "label area is missing" in normalized:
            return "missing or blank label area"
    return ""


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
