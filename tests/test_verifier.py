from __future__ import annotations

from src.constants import GOVERNMENT_WARNING, STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.models import ApplicationFields, LabelExtraction
from src.verifier import (
    verify_alcohol_content,
    verify_application,
    verify_brand,
    verify_class_type,
    verify_government_warning,
    verify_net_contents,
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


def test_abv_mismatch_fails() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN 40% Alc./Vol.")
    assert result.status == STATUS_FAIL


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
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        bottler_producer="Example Distilling Co.",
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
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
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

