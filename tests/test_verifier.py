from __future__ import annotations

from src.constants import GOVERNMENT_WARNING, STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.models import ApplicationFields, LabelExtraction
from src.verifier import (
    verify_alcohol_content,
    verify_application,
    verify_brand,
    verify_class_type,
    verify_government_warning,
    verify_formula_alcohol_content,
    verify_net_contents,
    verify_product_type,
    verify_country_of_origin,
)


def test_brand_variation_passes() -> None:
    result = verify_brand("STONE'S THROW", "STONES THROW Straight Bourbon Whiskey")
    assert result.status == STATUS_PASS


def test_government_warning_strict_title_case_behavior() -> None:
    result = verify_government_warning("Government Warning: Drinking may cause health problems.", 0.95)
    assert result.status == STATUS_FAIL
    assert "all caps" in result.reason


def test_government_warning_missing_fails_when_label_is_readable() -> None:
    result = verify_government_warning("OLD TOM GIN 45% Alc./Vol. 750 mL", 0.95)
    assert result.status == STATUS_FAIL


def test_government_warning_low_confidence_needs_review_instead_of_missing_fail() -> None:
    result = verify_government_warning("OLD TOM GIN garbled rotated text", 0.32)
    assert result.status == STATUS_REVIEW
    assert "rotated, blurry, or unreadable" in result.reason


def test_government_warning_ocr_imperfect_canonical_text_needs_review() -> None:
    ocr_text = (
        "GOVERNMENT WARNING: (1) Aecording tothe Surgeon General women should notdrink "
        "alcoholic beverages during pregnancy because of the riskof birth defects. "
        "(2) Consumption of aleaholic beverages impairs your ability to drive a car or "
        "operate machinery, and may cause health problems."
    )
    result = verify_government_warning(ocr_text, 0.83)
    assert result.status == STATUS_REVIEW
    assert "close to canonical" in result.reason


def test_abv_mismatch_fails() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN 40% Alc./Vol.")
    assert result.status == STATUS_FAIL


def test_formula_alcohol_content_matches_label() -> None:
    result = verify_formula_alcohol_content("F-1001", "45% ABV", "formula-approval", "OLD TOM GIN 45% Alc./Vol.")
    assert result.status == STATUS_PASS
    assert result.field == "formula"


def test_formula_alcohol_content_range_matches_label() -> None:
    result = verify_formula_alcohol_content("F-1001", "25-30% ABV", "formula-approval", "Label says 27% Alc./Vol.")
    assert result.status == STATUS_PASS


def test_formula_alcohol_content_range_mismatch_fails() -> None:
    result = verify_formula_alcohol_content("F-1001", "25-30% ABV", "formula-approval", "Label says 35% Alc./Vol.")
    assert result.status == STATUS_FAIL


def test_formula_approval_missing_needs_review() -> None:
    result = verify_formula_alcohol_content("F-1001", "45% ABV", "application-summary", "OLD TOM GIN 45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "approved formula document" in result.reason


def test_formula_alcohol_content_mismatch_fails() -> None:
    result = verify_formula_alcohol_content("F-1001", "45% ABV", "formula-approval", "OLD TOM GIN 40% Alc./Vol.")
    assert result.status == STATUS_FAIL


def test_no_formula_required_passes_formula_check() -> None:
    result = verify_formula_alcohol_content("NO FORMULA REQUIRED", "", "", "VALLEY TABLE WINE 13% Alc./Vol.")
    assert result.status == STATUS_PASS
    assert "no formula is required" in result.reason


def test_matched_formula_without_final_alcohol_needs_review() -> None:
    result = verify_formula_alcohol_content("F-2800", "", "formula-approval", "OLD TOM GIN 45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "did not contain extractable final alcohol content" in result.reason


def test_product_type_mismatch_fails() -> None:
    result = verify_product_type("DISTILLED SPIRITS", "OLD TOM GIN MALT BEVERAGES 45% Alc./Vol.")
    assert result.status == STATUS_FAIL
    assert "different product type" in result.reason


def test_imported_country_of_origin_passes_when_present() -> None:
    result = verify_country_of_origin("Mexico", True, "CASA VERDE TEQUILA Product of Mexico")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_needs_review_when_missing_from_label() -> None:
    result = verify_country_of_origin("Mexico", True, "CASA VERDE TEQUILA Imported by Borderland Imports LLC")
    assert result.status == STATUS_REVIEW


def test_net_contents_match_passes_with_liters() -> None:
    result = verify_net_contents("750 mL", "Net Contents .75 L")
    assert result.status == STATUS_PASS


def test_expected_value_missing_behavior() -> None:
    result = verify_class_type("", "Gin 45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert result.reason == "Expected application value could not be extracted."


def test_overall_status_aggregation_pass() -> None:
    fields = ApplicationFields(
        serial_number="APP-X",
        product_type="DISTILLED SPIRITS",
        brand_name="OLD TOM GIN",
        formula="F-1001",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        bottler_producer="Example Distilling Co.",
        raw_sources={"alcohol_content": "formula-approval"},
    )
    label = LabelExtraction(
        text=(
            "OLD TOM GIN DISTILLED SPIRITS Gin 45% Alc./Vol. 750 mL "
            "Bottled by Example Distilling Co. "
            f"{GOVERNMENT_WARNING}"
        ),
        confidence=0.97,
    )
    result = verify_application(
        filename="x.pdf",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    assert result.overall_status == STATUS_PASS


def test_overall_status_aggregation_fail() -> None:
    fields = ApplicationFields(
        serial_number="APP-X",
        product_type="DISTILLED SPIRITS",
        brand_name="OLD TOM GIN",
        formula="F-1001",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        raw_sources={"alcohol_content": "formula-approval"},
    )
    label = LabelExtraction(
        text=f"OLD TOM GIN DISTILLED SPIRITS Gin 40% Alc./Vol. 750 mL {GOVERNMENT_WARNING}",
        confidence=0.97,
    )
    result = verify_application(
        filename="x.pdf",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    assert result.overall_status == STATUS_FAIL


def test_low_confidence_label_text_does_not_fail_government_warning() -> None:
    fields = ApplicationFields(
        serial_number="APP-LOW",
        product_type="DISTILLED SPIRITS",
        brand_name="OLD TOM GIN",
        formula="F-1001",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        raw_sources={"alcohol_content": "formula-approval"},
    )
    label = LabelExtraction(
        text="OLD TOM GIN blurry rotated OCR text",
        confidence=0.32,
        unreadable=True,
    )

    result = verify_application(
        filename="low.pdf",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    warning = next(field for field in result.field_results if field.field == "government_warning")
    assert result.overall_status == STATUS_REVIEW
    assert warning.status == STATUS_REVIEW
    assert "rotated, blurry, or unreadable" in warning.reason


def test_low_confidence_application_ocr_does_not_drive_brand_fail() -> None:
    fields = ApplicationFields(
        serial_number="APP-SCAN",
        product_type="DISTILLED SPIRITS",
        brand_name="SCANNED SAMPLE",
        formula="NO FORMULA REQUIRED",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        raw_sources={"brand_name": "form-region"},
        raw_confidences={"brand_name": 0.62},
    )
    label = LabelExtraction(
        text=f"SGANNED SAMPLE DISTILLED SPIRITS Gin 45% Alc./Vol. 750 mL {GOVERNMENT_WARNING}",
        confidence=0.91,
    )

    result = verify_application(
        filename="scan.png",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    brand = next(field for field in result.field_results if field.field == "brand_name")
    assert result.overall_status == STATUS_REVIEW
    assert brand.status == STATUS_REVIEW
    assert "low-confidence form OCR" in brand.reason
