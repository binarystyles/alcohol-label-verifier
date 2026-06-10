from __future__ import annotations

from pathlib import Path

import fitz

from src.extractors import (
    clean_region_value,
    extract_acroform_fields,
    extract_application,
    extract_formula_identifier,
    extract_imported_status_from_widgets,
    extract_label,
    extract_product_type_from_widgets,
    parse_application_summary,
    parse_formula_approval_fields,
)
from src.form_mapping import FORM_REGIONS
from src.ocr import OCRText


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


def test_formula_identifier_extraction() -> None:
    assert extract_formula_identifier("F-1001") == "F-1001"
    assert extract_formula_identifier("TTB Formula ID: F-1001") == "F-1001"
    assert extract_formula_identifier("TTB Formula ID No.: F-1001") == "F-1001"
    assert extract_formula_identifier("TTB Formula ID: F 1001") == "F 1001"
    assert extract_formula_identifier("TTB Formula ID: F/1001") == "F/1001"
    assert extract_formula_identifier("TTB Formula ID: F.1001") == "F.1001"
    assert extract_formula_identifier("Formula #: F-1001") == "F-1001"
    assert extract_formula_identifier("Approved Formula #: F-1001") == "F-1001"
    assert extract_formula_identifier("TTB ID Number: DS 3400") == "DS 3400"
    assert extract_formula_identifier("TTB Formula ID: 123456") == "123456"
    assert extract_formula_identifier("Formula Number: 24-001") == "24-001"
    assert extract_formula_identifier("Lab Number: 12345") == "12345"
    assert extract_formula_identifier("Pre-import Approval No.: PIA-1001") == "PIA-1001"
    assert extract_formula_identifier("Pre-import approval reference: PIA 1001") == "PIA 1001"
    assert extract_formula_identifier("123456") == "123456"
    assert extract_formula_identifier("45% ABV") == ""


def test_formula_approval_parser_matches_id_and_final_alcohol_content() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-1001
    Class/Type: Gin
    Final Alcohol Content: 90 proof
    """
    fields = parse_formula_approval_fields(text, "F-1001")
    assert fields["alcohol_content"] == "45% ABV"
    assert fields["class_type"] == "Gin"


def test_formula_approval_parser_matches_separator_variants() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-1001
    Class/Type: Gin
    Alcohol Content of Finished Product: Low 45 High 45 Unit % by Volume
    """
    assert parse_formula_approval_fields(text, "F 1001")["alcohol_content"] == "45% ABV"
    assert parse_formula_approval_fields(text, "F/1001")["alcohol_content"] == "45% ABV"
    assert parse_formula_approval_fields(text, "F.1001")["alcohol_content"] == "45% ABV"


def test_formula_approval_parser_matches_formula_symbol_and_id_number_labels() -> None:
    for label in ("Formula #: F-10500", "Approved Formula #: F-10500", "Formula ID No.: F-10500"):
        text = f"""
        FORMULAS ONLINE ENTRY
        {label}
        Class/Type: Gin
        Yield Summary
        Alcohol Content of Finished Product: Low 45 High 45 Unit % by Volume
        """
        fields = parse_formula_approval_fields(text, "F-10500")
        assert fields["alcohol_content"] == "45% ABV"
        assert fields["class_type"] == "Gin"


def test_formula_approval_parser_matches_pre_import_approval_reference() -> None:
    text = """
    PRE-IMPORT APPROVAL LETTER

    Pre-import Approval No.: PIA-1001
    Status: Approved
    Brand Name: OLD TOM GIN
    Class/Type: Gin

    Yield Summary
    Alcohol Content of Finished Product: 45% ABV
    """
    fields = parse_formula_approval_fields(text, "PIA-1001")
    assert fields["alcohol_content"] == "45% ABV"
    assert fields["class_type"] == "Gin"


def test_formula_approval_parser_rejects_nonapproved_status() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-12700
    Status: Rejected
    Class/Type: Gin
    Yield Summary
    Alcohol Content of Finished Product: 45% ABV
    """
    fields = parse_formula_approval_fields(text, "F-12700")
    assert fields == {"alcohol_content": "", "_formula_approval_status": "REJECTED"}


def test_formula_approval_parser_matches_numeric_formula_identifiers() -> None:
    for label, expected in (
        ("TTB Formula ID: 123456", "123456"),
        ("Formula Number: 24-001", "24-001"),
        ("Lab Number: 12345", "12345"),
    ):
        text = f"""
        FORMULAS ONLINE ENTRY
        {label}
        Class/Type: Gin
        Yield Summary
        Alcohol Content of Finished Product: Low 45 High 45 Unit % by Volume
        """
        fields = parse_formula_approval_fields(text, expected)
        assert fields["alcohol_content"] == "45% ABV"
        assert fields["class_type"] == "Gin"


def test_formula_approval_parser_uses_finished_product_row_before_ingredient_abv() -> None:
    text = """
    Formulas Online
    TTB Formula ID: F-2002
    Ingredients List
    Vodka 98.0 - 99.0 Percentage ABV: 45% - 45%
    Yield Summary
    Alcohol Content of Finished Product: Low 25 High 30 Unit % by Volume
    Method of Manufacture
    """
    fields = parse_formula_approval_fields(text, "F-2002")
    assert fields["alcohol_content"] == "25-30% ABV"


def test_formula_approval_parser_handles_ttb_distilled_spirits_range() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: DS-2002
    Product Information Class: DISTILLED SPIRITS SPECIALTY
    Yield Summary
    Total Yield: 5.0 Gallons
    Alcohol Content of Finished Product: 25 30 % by Volume
    Ingredients List
    Corn 10.0 - 12.0 lb.
    Method of Manufacture
    """
    fields = parse_formula_approval_fields(text, "DS-2002")
    assert fields["alcohol_content"] == "25-30% ABV"


def test_formula_approval_parser_handles_ttb_wine_multiline_range() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: W-1001
    Product Information Class: OTHER THAN STANDARD WINE
    Yield Summary
    Alcohol Content of Finished Product:
    Low High Unit
    12.75 13.55 % by Volume
    Ingredients List
    Grape juice 950.0 - 975.0 gal.
    """
    fields = parse_formula_approval_fields(text, "W-1001")
    assert fields["alcohol_content"] == "12.75-13.55% ABV"


def test_formula_approval_parser_handles_decimal_comma_final_alcohol() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: W-9800
    Yield Summary
    Alcohol Content of Finished Product: Low 12,5 High 13,5 Unit % by Volume
    Ingredients List
    Grape juice 950.0 - 975.0 gal.
    """
    fields = parse_formula_approval_fields(text, "W-9800")
    assert fields["alcohol_content"] == "12.5-13.5% ABV"


def test_formula_approval_parser_handles_ttb_malt_rows_without_using_flavor_or_base_alcohol() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: MB-1001
    Product Information Class: MALT BEVERAGE SPECIALTY
    Yield Summary
    Alcohol Content of Finished Product: 5.5 5.8 % by Volume
    Alcohol From Flavors: 0.99 0.99 % by Volume
    Alcohol From Base: 4.51 4.81 % by Volume
    Ingredients List
    Malted barley 23.0 - 28.0 kg
    """
    fields = parse_formula_approval_fields(text, "MB-1001")
    assert fields["alcohol_content"] == "5.5-5.8% ABV"


def test_formula_approval_parser_converts_proof_before_later_percent_rows() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: DS-9001
    Yield Summary
    Final Alcohol Content: 90 Proof
    Alcohol From Base: 45 45 % by Volume
    Ingredients List
    Finished alcohol
    """
    fields = parse_formula_approval_fields(text, "DS-9001")
    assert fields["alcohol_content"] == "45% ABV"


def test_formula_approval_parser_converts_low_proof_to_abv() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: L-4001
    Yield Summary
    Final Alcohol Content: 40 Proof
    Ingredients List
    Finished alcohol, sugar, and natural flavors
    """
    fields = parse_formula_approval_fields(text, "L-4001")
    assert fields["alcohol_content"] == "20% ABV"


def test_formula_approval_parser_accepts_finished_alcohol_content_wording() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: F-8200
    Yield Summary
    Finished Alcohol Content: 45% ABV
    Ingredients List
    Finished alcohol, botanicals, and water
    """
    fields = parse_formula_approval_fields(text, "F-8200")
    assert fields["alcohol_content"] == "45% ABV"


def test_formula_approval_parser_accepts_final_product_alcohol_content_wording() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: F-8300
    Yield Summary
    Final Product Alcohol Content: 40 Proof
    Ingredients List
    Finished alcohol, botanicals, and water
    """
    fields = parse_formula_approval_fields(text, "F-8300")
    assert fields["alcohol_content"] == "20% ABV"


def test_formula_approval_parser_ignores_generic_alcohol_content_wording() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: F-8400
    Ingredients List
    Neutral spirits
    Alcohol Content: 95% ABV
    Method of Manufacture
    Blend and bottle.
    """
    fields = parse_formula_approval_fields(text, "F-8400")
    assert fields == {"alcohol_content": ""}


def test_formula_approval_parser_accepts_ttb_id_number_reference() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB ID Number: DS-3400
    Status: Approved
    Yield Summary
    Alcohol Content of Finished Product: Low 46 High 46 Unit % by Volume
    """
    fields = parse_formula_approval_fields(text, "DS-3400")
    assert fields["alcohol_content"] == "46% ABV"


def test_formula_approval_parser_handles_ocr_values_before_finished_product_label() -> None:
    text = """
    Formulas Online Entry
    TTB Formula ID: MB-2002
    Yield Summary
    3 5.5 5.8 % by Volume Alcohol Content of Finished Product
    0.99 0.99 % by Volume Alcohol From Flavors
    """
    fields = parse_formula_approval_fields(text, "MB-2002")
    assert fields["alcohol_content"] == "5.5-5.8% ABV"


def test_formula_approval_parser_marks_matching_document_without_final_alcohol() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-2800
    Status: Approved
    Ingredients List
    Finished alcohol, botanicals, and water.
    Method of Manufacture
    Blend, filter, and bottle.
    """
    fields = parse_formula_approval_fields(text, "F-2800")
    assert fields == {"alcohol_content": ""}


def test_formula_approval_parser_does_not_match_prefix_formula_id() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-29001
    Status: Approved
    Final Alcohol Content: 45% ABV
    """
    fields = parse_formula_approval_fields(text, "F-2900")
    assert fields == {}


def test_formula_approval_parser_uses_matching_document_only() -> None:
    text = """
    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-4000
    Status: Approved
    Class/Type: Vodka
    Alcohol Content of Finished Product: Low 40 High 40 Unit % by Volume

    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-9600
    Status: Approved
    Class/Type: Gin
    Alcohol Content of Finished Product: Low 45 High 45 Unit % by Volume

    FORMULAS ONLINE APPROVAL DETERMINATION
    TTB Formula ID: F-5000
    Status: Approved
    Class/Type: Rum
    Alcohol Content of Finished Product: Low 50 High 50 Unit % by Volume
    """

    target_fields = parse_formula_approval_fields(text, "F-9600")
    preceding_fields = parse_formula_approval_fields(text, "F-4000")
    following_fields = parse_formula_approval_fields(text, "F-5000")

    assert target_fields["alcohol_content"] == "45% ABV"
    assert target_fields["class_type"] == "Gin"
    assert preceding_fields["alcohol_content"] == "40% ABV"
    assert following_fields["alcohol_content"] == "50% ABV"


def test_application_derives_alcohol_content_from_matching_formula_approval() -> None:
    document = fitz.open()
    page = document.new_page(width=612, height=1008)
    page.insert_textbox(
        fitz.Rect(36, 36, 500, 220),
        """
        APPLICATION DATA SUMMARY
        Serial Number: APP-FORMULA
        Product Type: DISTILLED SPIRITS
        Brand Name: Formula Sample
        Formula: F-1001
        END APPLICATION DATA SUMMARY
        """,
        fontsize=10,
        fontname="helv",
    )
    formula_page = document.new_page(width=612, height=792)
    formula_page.insert_textbox(
        fitz.Rect(36, 36, 500, 220),
        """
        FORMULAS ONLINE APPROVAL DETERMINATION
        TTB Formula ID: F-1001
        Final Alcohol Content: 90 proof
        """,
        fontsize=10,
        fontname="helv",
    )
    try:
        pdf_bytes = document.write()
    finally:
        document.close()

    extraction = extract_application(pdf_bytes)

    assert extraction.fields.formula == "F-1001"
    assert extraction.fields.alcohol_content == "45% ABV"
    assert extraction.fields.raw_sources["alcohol_content"] == "formula-approval"


def test_acroform_extraction_falls_back_to_summary_for_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    pdf_bytes = sample_bytes["APP-001_old_tom_pass.pdf"]
    acroform_fields = extract_acroform_fields(pdf_bytes)
    assert acroform_fields["brand_name"] == "OLD TOM GIN"
    assert acroform_fields["serial_number"] == "1"
    extraction = extract_application(pdf_bytes)
    assert extraction.fields.serial_number == "APP-001"
    assert extraction.fields.brand_name == "OLD TOM GIN"
    assert extraction.fields.formula == "F-1001"
    assert extraction.fields.alcohol_content == "45% ABV"
    assert extraction.fields.raw_sources["alcohol_content"] == "formula-approval"


def test_region_based_application_extraction_from_generated_pdf(sample_bytes: dict[str, bytes]) -> None:
    extraction = extract_application(sample_bytes["APP-002_stones_throw_variation.pdf"])
    assert extraction.fields.brand_name == "STONE'S THROW"
    assert extraction.fields.product_type == "DISTILLED SPIRITS"


def test_product_type_checkbox_widget_extraction(sample_bytes: dict[str, bytes]) -> None:
    cases = {
        "APP-001_old_tom_pass.pdf": "DISTILLED SPIRITS",
        "APP-017_wine_artwork_pass.pdf": "WINE",
        "APP-018_malt_artwork_pass.pdf": "MALT BEVERAGES",
    }

    for filename, expected in cases.items():
        document = fitz.open(stream=sample_bytes[filename], filetype="pdf")
        try:
            assert extract_product_type_from_widgets(document[0]) == expected
        finally:
            document.close()


def test_imported_checkbox_widget_extraction(sample_bytes: dict[str, bytes]) -> None:
    document = fitz.open(stream=sample_bytes["APP-024_import_country_artwork_pass.pdf"], filetype="pdf")
    try:
        assert extract_imported_status_from_widgets(document[0]) is True
    finally:
        document.close()

    domestic_document = fitz.open(stream=sample_bytes["APP-001_old_tom_pass.pdf"], filetype="pdf")
    try:
        assert extract_imported_status_from_widgets(domestic_document[0]) is False
    finally:
        domestic_document.close()


def test_checkbox_mark_extraction_from_flattened_source_form() -> None:
    source = Path("docs/source/f510031.pdf")
    assert source.exists()
    document = fitz.open(source)
    page = document[0]
    for widget in page.widgets() or []:
        if widget.field_type_string != "CheckBox":
            continue
        states = widget.button_states() or {}
        option_text = " ".join(value for values in states.values() if values for value in values)
        if "Import" in option_text or "Spirits" in option_text:
            widget.field_value = next(value for values in states.values() if values for value in values if value != "Off")
        else:
            widget.field_value = "Off"
        widget.update()

    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    flattened = fitz.open()
    flattened_page = flattened.new_page(width=page.rect.width, height=page.rect.height)
    flattened_page.insert_image(flattened_page.rect, pixmap=pixmap)
    try:
        assert extract_product_type_from_widgets(flattened_page) == "DISTILLED SPIRITS"
        assert extract_imported_status_from_widgets(flattened_page) is True
    finally:
        document.close()
        flattened.close()


def test_generated_pdf_application_fields_do_not_keep_form_boilerplate(sample_bytes: dict[str, bytes]) -> None:
    extraction = extract_application(sample_bytes["APP-001_old_tom_pass.pdf"])
    assert extraction.fields.mailing_address == ""
    assert extraction.fields.grape_varietals == ""
    assert extraction.fields.wine_appellation == ""
    assert extraction.fields.phone == "202-555-0100"
    assert extraction.fields.email == "labels@example.test"
    assert extraction.fields.application_type == "Certificate of Label Approval"
    assert extraction.fields.item_15 == ""
    assert extraction.fields.raw_sources["imported"] == "application-summary"
    assert "TYPE OF A" not in extraction.fields.to_dict().get("grape_varietals", "")


def test_region_cleaning_preserves_values_after_printed_field_labels() -> None:
    assert clean_region_value("serial_number", "4. SERIAL NUMBER APP-SCAN") == "APP-SCAN"
    assert clean_region_value("brand_name", "6. BRAND NAME SCANNED SAMPLE") == "SCANNED SAMPLE"
    assert clean_region_value("brand_name", "6. BRAND WAME SCANNED SAMPLE") == "SCANNED SAMPLE"
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
    assert "FORMULAS ONLINE" not in label.text


def test_label_extraction_finds_supplemental_label_after_attached_instructions() -> None:
    document = fitz.open()
    first_page = document.new_page(width=612, height=792)
    label_rect = FORM_REGIONS["label_area"].to_rect(first_page.rect)
    first_page.draw_rect(label_rect, color=(1, 1, 1), fill=(1, 1, 1))

    for _ in range(5):
        page = document.new_page(width=612, height=792)
        page.insert_textbox(
            fitz.Rect(36, 36, 560, 740),
            "GENERAL INSTRUCTIONS\nPAPERWORK REDUCTION ACT\nThis certificate does not relieve you from liability.",
            fontsize=12,
            fontname="helv",
        )

    label_page = document.new_page(width=612, height=792)
    label_page.insert_textbox(
        fitz.Rect(72, 72, 540, 360),
        "OLD TOM GIN\n45% Alc./Vol.\nGOVERNMENT WARNING",
        fontsize=18,
        fontname="helv",
    )
    try:
        pdf_bytes = document.write()
    finally:
        document.close()

    label = extract_label(pdf_bytes)

    assert not label.missing_label_area
    assert "OLD TOM GIN" in label.text
    assert "PAPERWORK REDUCTION ACT" not in label.text


def test_generated_supplemental_label_sample_skips_instruction_pages(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-093_supplemental_label_after_instructions_pass.pdf"])

    assert not label.missing_label_area
    assert "OLD TOM GIN" in label.text
    assert "supplemental-label-page" in label.text
    assert "PAPERWORK REDUCTION ACT" not in label.text
    assert "Local Tesseract OCR is not installed" not in " ".join(label.warnings)


def test_generated_long_attachment_sample_scans_later_label_page(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-094_long_attachment_before_label_pass.pdf"])

    assert not label.missing_label_area
    assert "supplemental-label-page p.15" in label.text
    assert "OLD TOM GIN" in label.text
    assert "PAPERWORK REDUCTION ACT" not in label.text


def test_label_extraction_skips_ocr_text_that_looks_like_instructions(monkeypatch) -> None:
    document = fitz.open()
    for _ in range(3):
        document.new_page(width=612, height=792)
    try:
        pdf_bytes = document.write()
    finally:
        document.close()

    def fake_extract_region_text(page: fitz.Page, rect: fitz.Rect) -> OCRText:
        if page.number == 1:
            return OCRText(
                text="GENERAL INSTRUCTIONS PAPERWORK REDUCTION ACT",
                confidence=0.91,
                source="tesseract",
                nonwhite_ratio=0.4,
            )
        if page.number == 2:
            return OCRText(
                text="OLD TOM GIN 45% Alc./Vol. GOVERNMENT WARNING",
                confidence=0.9,
                source="tesseract",
                nonwhite_ratio=0.3,
            )
        return OCRText(text="", confidence=0.0, source="pdf-text", nonwhite_ratio=0.0)

    monkeypatch.setattr("src.extractors.extract_region_text", fake_extract_region_text)

    label = extract_label(pdf_bytes)

    assert "OLD TOM GIN" in label.text
    assert "PAPERWORK REDUCTION ACT" not in label.text


def test_unreadable_attachment_page_does_not_downgrade_later_readable_label(monkeypatch) -> None:
    document = fitz.open()
    for _ in range(3):
        document.new_page(width=612, height=792)
    try:
        pdf_bytes = document.write()
    finally:
        document.close()

    def fake_extract_region_text(page: fitz.Page, rect: fitz.Rect) -> OCRText:
        if page.number == 1:
            return OCRText(
                text="",
                confidence=0.0,
                source="tesseract",
                warning="Local OCR could not read this page.",
                nonwhite_ratio=0.5,
                sharpness=0.0,
            )
        if page.number == 2:
            return OCRText(
                text="OLD TOM GIN 45% Alc./Vol. GOVERNMENT WARNING",
                confidence=0.93,
                source="tesseract",
                nonwhite_ratio=0.3,
                sharpness=500.0,
            )
        return OCRText(text="", confidence=0.0, source="pdf-text", nonwhite_ratio=0.0)

    monkeypatch.setattr("src.extractors.extract_region_text", fake_extract_region_text)

    label = extract_label(pdf_bytes)

    assert label.text.startswith("[supplemental-label-page p.3]")
    assert "OLD TOM GIN" in label.text
    assert not label.unreadable
    assert label.warnings == []


def test_label_extraction_marks_low_sharpness_ocr_as_unreadable(monkeypatch) -> None:
    document = fitz.open()
    document.new_page(width=612, height=792)
    try:
        pdf_bytes = document.write()
    finally:
        document.close()

    def fake_extract_region_text(page: fitz.Page, rect: fitz.Rect) -> OCRText:
        return OCRText(
            text="OLD TOM GIN Botanical Reserve DISTILLED SPIRITS 45% ABV",
            confidence=0.9,
            source="tesseract",
            nonwhite_ratio=0.5,
            sharpness=100.0,
        )

    monkeypatch.setattr("src.extractors.extract_region_text", fake_extract_region_text)

    label = extract_label(pdf_bytes)

    assert label.unreadable
    assert label.confidence == 0.9
    assert any("rotated, blurry, or low quality" in warning for warning in label.warnings)


def test_missing_label_area_behavior(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-006_missing_label_area.pdf"])
    assert label.missing_label_area
    assert label.text == ""


def test_unreadable_ocr_behavior(sample_bytes: dict[str, bytes]) -> None:
    label = extract_label(sample_bytes["APP-005_low_quality_rotated.pdf"])
    assert label.unreadable or label.confidence < 0.55
