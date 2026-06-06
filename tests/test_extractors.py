from __future__ import annotations

from pathlib import Path

from src.extractors import extract_acroform_fields, extract_application, extract_label, parse_application_summary


def test_application_summary_parser_maps_expected_fields() -> None:
    text = """
    APPLICATION DATA SUMMARY
    Serial Number: APP-X
    Product Type: WINE
    Brand Name: Sample Brand
    Class/Type: Red Wine
    Alcohol Content: 13.5% ABV
    Net Contents: 750 mL
    Imported: yes
    END APPLICATION DATA SUMMARY
    """
    fields = parse_application_summary(text)
    assert fields["serial_number"] == "APP-X"
    assert fields["product_type"] == "WINE"
    assert fields["class_type"] == "Red Wine"
    assert fields["imported"] is True


def test_acroform_extraction_falls_back_to_summary_for_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    pdf_bytes = sample_bytes["APP-001_old_tom_pass.pdf"]
    assert extract_acroform_fields(pdf_bytes) == {}
    extraction = extract_application(pdf_bytes)
    assert extraction.fields.serial_number == "APP-001"
    assert extraction.fields.brand_name == "OLD TOM GIN"
    assert extraction.fields.alcohol_content == "45% ABV"


def test_region_based_application_extraction_from_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    extraction = extract_application(sample_bytes["APP-002_stones_throw_variation.pdf"])
    assert extraction.fields.brand_name == "STONE'S THROW"
    assert extraction.fields.product_type == "DISTILLED SPIRITS"


def test_label_area_extraction_from_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-001_old_tom_pass.pdf"])
    assert not label.missing_label_area
    assert "OLD TOM GIN" in label.text
    assert "GOVERNMENT WARNING" in label.text


def test_missing_label_area_behavior(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-006_missing_label_area.pdf"])
    assert label.missing_label_area
    assert label.text == ""


def test_unreadable_ocr_behavior(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-005_low_quality_rotated.pdf"])
    assert label.unreadable or label.confidence < 0.55

