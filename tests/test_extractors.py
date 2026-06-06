from __future__ import annotations

from pathlib import Path

from src.extractors import (
    clean_region_value,
    extract_acroform_fields,
    extract_application,
    extract_label,
    parse_application_summary,
)


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
    acroform_fields = extract_acroform_fields(pdf_bytes)
    assert acroform_fields["brand_name"] == "OLD TOM GIN"
    assert acroform_fields["serial_number"] == "1"
    extraction = extract_application(pdf_bytes)
    assert extraction.fields.serial_number == "APP-001"
    assert extraction.fields.brand_name == "OLD TOM GIN"
    assert extraction.fields.alcohol_content == "45% ABV"


def test_region_based_application_extraction_from_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    extraction = extract_application(sample_bytes["APP-002_stones_throw_variation.pdf"])
    assert extraction.fields.brand_name == "STONE'S THROW"
    assert extraction.fields.product_type == "DISTILLED SPIRITS"


def test_generated_pdf_application_fields_do_not_keep_form_boilerplate(sample_bytes: dict[str, bytes]) -> None:
    extraction = extract_application(sample_bytes["APP-001_old_tom_pass.pdf"])
    assert extraction.fields.mailing_address == ""
    assert extraction.fields.grape_varietals == ""
    assert extraction.fields.wine_appellation == ""
    assert extraction.fields.phone == "202-555-0100"
    assert extraction.fields.email == "labels@example.test"
    assert extraction.fields.application_type == "Certificate of Label Approval"
    assert extraction.fields.item_15 == ""
    assert "TYPE OF A" not in extraction.fields.to_dict().get("grape_varietals", "")


def test_region_cleaning_preserves_values_after_printed_field_labels() -> None:
    assert clean_region_value("serial_number", "4. SERIAL NUMBER APP-SCAN") == "APP-SCAN"
    assert clean_region_value("brand_name", "6. BRAND NAME SCANNED SAMPLE") == "SCANNED SAMPLE"
    assert clean_region_value("phone", "EMAIL A\n202 555 0100") == "202-555-0100"
    assert clean_region_value("email", 'DDRESS\n"For sale in only"\nlabels@example.test') == "labels@example.test"
    assert clean_region_value("item_15", "Item 15 container and translation info") == ""
    assert clean_region_value("item_15", "O\nSO, S O\nS\nO S O") == ""
    assert (
        clean_region_value("application_type", "CERTIFIC\nATE OF LABEL APPROVAL\nTTB ID")
        == "Certificate of Label Approval"
    )


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
