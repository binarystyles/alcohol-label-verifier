from __future__ import annotations

from src.constants import GOVERNMENT_WARNING, STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.models import ApplicationFields, LabelExtraction
from src.verifier import (
    verify_alcohol_content,
    verify_application,
    verify_brand,
    verify_bottler_producer,
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


def test_assignment_brand_case_example_passes() -> None:
    result = verify_brand("Stone's Throw", "STONE'S THROW Straight Bourbon Whiskey")
    assert result.status == STATUS_PASS


def test_brand_diacritic_and_curly_apostrophe_variations_pass() -> None:
    assert verify_brand("Caf\u00e9 Azul", "CAFE AZUL\nDISTILLED SPIRITS").status == STATUS_PASS
    assert verify_brand("Distiller\u2019s Cut", "DISTILLERS CUT\nDISTILLED SPIRITS").status == STATUS_PASS


def test_brand_ampersand_and_variation_passes() -> None:
    result = verify_brand("SMITH & SONS", "SMITH AND SONS Bourbon Whiskey")
    assert result.status == STATUS_PASS


def test_brand_company_abbreviation_passes() -> None:
    result = verify_brand("ACME DISTILLING CO.", "ACME DISTILLING COMPANY Vodka")
    assert result.status == STATUS_PASS


def test_brand_common_word_abbreviations_pass() -> None:
    assert verify_brand("SAINT GEORGE GIN", "ST. GEORGE GIN\nDISTILLED SPIRITS").status == STATUS_PASS
    assert verify_brand("MT. HOOD VODKA", "MOUNT HOOD VODKA\nDISTILLED SPIRITS").status == STATUS_PASS


def test_brand_number_symbol_variations_pass() -> None:
    assert verify_brand("OLD TOM NO. 5", "OLD TOM #5\nDISTILLED SPIRITS").status == STATUS_PASS
    assert verify_brand("OLD TOM NUMBER 5", "OLD TOM 5\nDISTILLED SPIRITS").status == STATUS_PASS


def test_brand_ocr_character_confusion_needs_review_not_fail() -> None:
    result = verify_brand("OLD TOM GIN", "0LD T0M GIN Botanical Reserve\nDISTILLED SPIRITS\n45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "OCR-like character substitutions" in result.reason


def test_brand_ocr_review_fallback_does_not_pass_materially_different_brand() -> None:
    result = verify_brand("OLD TOM GIN", "0LD T0M V0DKA\nDISTILLED SPIRITS\n45% Alc./Vol.")
    assert result.status == STATUS_FAIL
    assert "materially different" in result.reason


def test_brand_containing_proof_word_is_not_treated_as_alcohol_statement() -> None:
    result = verify_brand("PROOF RANGE BOURBON", "PROOF RANGE BOURBON\nDISTILLED SPIRITS\n90 Proof")
    assert result.status == STATUS_PASS


def test_brand_word_order_mismatch_fails() -> None:
    result = verify_brand("OLD TOM GIN", "TOM OLD GIN\nDISTILLED SPIRITS\n45% Alc./Vol.\n750 mL")
    assert result.status == STATUS_FAIL
    assert "materially different" in result.reason


def test_brand_in_bottler_line_only_does_not_pass() -> None:
    result = verify_brand(
        "OLD TOM GIN",
        "MOUNTAIN FORK VODKA\nDISTILLED SPIRITS\n45% Alc./Vol.\n750 mL\nBottled by Old Tom Gin",
    )
    assert result.status == STATUS_FAIL
    assert "non-brand context" in result.reason


def test_bottler_producer_requires_responsible_party_context() -> None:
    result = verify_bottler_producer("OLD TOM GIN", "OLD TOM GIN\nDISTILLED SPIRITS\n45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "outside responsible-party" in result.reason


def test_bottler_producer_accepts_combined_responsible_party_statement() -> None:
    result = verify_bottler_producer("Example Distilling Co.", "Produced and bottled by Example Distilling Co.")
    assert result.status == STATUS_PASS


def test_bottler_producer_accepts_comma_or_slash_responsible_party_actions() -> None:
    assert (
        verify_bottler_producer(
            "Example Distilling Co.",
            "Distilled, bottled and packaged by Example Distilling Co.",
        ).status
        == STATUS_PASS
    )
    assert verify_bottler_producer("Example Distilling Co.", "Produced/Bottled by Example Distilling Co.").status == STATUS_PASS


def test_bottler_producer_accepts_additional_valid_function_words() -> None:
    for text in (
        "Filled by Example Distilling Co.",
        "Made by Example Distilling Co.",
        "Prepared by Example Distilling Co.",
        "Manufactured by Example Distilling Co.",
        "Mfg. by Example Distilling Co.",
        "Mfr. by Example Distilling Co.",
        "Brewed, filled and packaged by Example Distilling Co.",
    ):
        assert verify_bottler_producer("Example Distilling Co.", text).status == STATUS_PASS


def test_bottler_producer_distributed_by_alone_needs_review() -> None:
    result = verify_bottler_producer("Example Distilling Co.", "Distributed by Example Distilling Co.")
    assert result.status == STATUS_REVIEW
    assert "outside responsible-party" in result.reason


def test_bottler_producer_accepts_distribution_inside_valid_action_list() -> None:
    result = verify_bottler_producer(
        "Example Imports LLC",
        "Imported, bottled and distributed by Example Imports LLC",
    )
    assert result.status == STATUS_PASS


def test_bottler_producer_accepts_punctuation_after_by_or_for() -> None:
    assert verify_bottler_producer("Example Distilling Co.", "Bottled by: Example Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Imports LLC", "Imported by: Example Imports LLC").status == STATUS_PASS
    assert verify_bottler_producer("Example Distilling Co.", "Produced for: Example Distilling Co.").status == STATUS_PASS
    assert (
        verify_bottler_producer(
            "Example Distilling Co.",
            "Distilled, bottled and packaged by: Example Distilling Co.",
        ).status
        == STATUS_PASS
    )


def test_bottler_producer_conflicting_same_role_needs_review() -> None:
    result = verify_bottler_producer(
        "Example Distilling Co.",
        "Bottled by Example Distilling Co.\nBottled by Canyon Creek Spirits",
    )
    assert result.status == STATUS_REVIEW
    assert result.found == "Canyon Creek Spirits"
    assert "conflicting responsible-party" in result.reason


def test_bottler_producer_conflicting_role_inside_action_list_needs_review() -> None:
    result = verify_bottler_producer(
        "Example Distilling Co.",
        "Distilled, bottled and packaged by Example Distilling Co.\nPackaged by Canyon Creek Spirits",
    )
    assert result.status == STATUS_REVIEW
    assert result.found == "Canyon Creek Spirits"


def test_bottler_producer_separate_importer_role_does_not_conflict() -> None:
    result = verify_bottler_producer(
        "Highland Forge Distilling Co.",
        "Bottled by Highland Forge Distilling Co.\nImported by Example Imports LLC",
    )
    assert result.status == STATUS_PASS


def test_bottler_producer_company_abbreviation_passes() -> None:
    assert verify_bottler_producer("Acme Distilling Co.", "Bottled by Acme Distilling Company").status == STATUS_PASS
    assert verify_bottler_producer("Acme Distilling Company", "Bottled by Acme Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Imports LLC", "Imported by Example Imports L.L.C.").status == STATUS_PASS
    assert verify_bottler_producer("Acme Distilling Inc.", "Bottled by Acme Distilling Incorporated").status == STATUS_PASS
    assert verify_bottler_producer("North Coast Ltd.", "Produced by North Coast Limited").status == STATUS_PASS
    assert verify_bottler_producer("Copper Ridge Corp.", "Distilled by Copper Ridge Corporation").status == STATUS_PASS
    assert verify_bottler_producer("Example Imports LLC", "Imported by Example Imports Limited").status == STATUS_REVIEW


def test_bottler_producer_accepts_distilled_by_statement() -> None:
    assert verify_bottler_producer("Example Distilling Co.", "Distilled by Example Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Distilling Co.", "Distilled and bottled by Example Distilling Co.").status == STATUS_PASS


def test_bottler_producer_accepts_blended_by_statement() -> None:
    assert verify_bottler_producer("Example Distilling Co.", "Blended by Example Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Distilling Co.", "Distilled and blended by Example Distilling Co.").status == STATUS_PASS


def test_bottler_producer_accepts_bottled_for_statement() -> None:
    assert verify_bottler_producer("Example Distilling Co.", "Bottled for Example Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Distilling Co.", "Produced for Example Distilling Co.").status == STATUS_PASS
    assert verify_bottler_producer("Example Distilling Co.", "For sale in Oregon only").status == STATUS_REVIEW


def test_bottler_producer_accepts_responsible_party_modifiers() -> None:
    assert (
        verify_bottler_producer("Example Distilling Co.", "Bottled exclusively for Example Distilling Co.").status
        == STATUS_PASS
    )
    assert (
        verify_bottler_producer("Example Distilling Co.", "Produced specially by Example Distilling Co.").status
        == STATUS_PASS
    )
    assert verify_bottler_producer("Example Imports LLC", "Imported solely by Example Imports LLC").status == STATUS_PASS
    assert (
        verify_bottler_producer(
            "Example Distilling Co.",
            "Distilled and bottled exclusively for Example Distilling Co.",
        ).status
        == STATUS_PASS
    )


def test_bottler_producer_modifier_conflicting_same_role_needs_review() -> None:
    result = verify_bottler_producer(
        "Example Distilling Co.",
        "Bottled exclusively for Example Distilling Co.\nBottled by Canyon Creek Spirits",
    )
    assert result.status == STATUS_REVIEW
    assert result.found == "Canyon Creek Spirits"


def test_bottler_producer_accepts_packed_by_statement() -> None:
    assert verify_bottler_producer("Example Winery", "Packed by Example Winery").status == STATUS_PASS
    assert verify_bottler_producer("Example Winery", "Packed and bottled by Example Winery").status == STATUS_PASS


def test_bottler_producer_accepts_canned_by_statement() -> None:
    assert verify_bottler_producer("Harbor Light Brewing Co.", "Canned by Harbor Light Brewing Co.").status == STATUS_PASS
    assert (
        verify_bottler_producer("Harbor Light Brewing Co.", "Brewed and canned by Harbor Light Brewing Co.").status
        == STATUS_PASS
    )


def test_government_warning_strict_title_case_behavior() -> None:
    result = verify_government_warning("Government Warning: Drinking may cause health problems.", 0.95)
    assert result.status == STATUS_FAIL
    assert "all caps" in result.reason


def test_government_warning_mixed_or_lowercase_heading_fails_even_with_exact_statement() -> None:
    for heading in ("GOVERNMENT Warning", "Government WARNING", "government warning"):
        text = GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", heading)
        result = verify_government_warning(text, 0.95)
        assert result.status == STATUS_FAIL
        assert "all caps" in result.reason


def test_government_warning_all_caps_heading_can_span_whitespace() -> None:
    text = GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "GOVERNMENT\nWARNING")
    result = verify_government_warning(text, 0.95)
    assert result.status == STATUS_PASS


def test_government_warning_noncanonical_heading_punctuation_fails() -> None:
    text = GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "GOVERNMENT-WARNING")
    result = verify_government_warning(text, 0.95)
    assert result.status == STATUS_FAIL
    assert "punctuation" in result.reason

    colon_text = GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "GOVERNMENT: WARNING")
    colon_result = verify_government_warning(colon_text, 0.95)
    assert colon_result.status == STATUS_FAIL
    assert "punctuation" in colon_result.reason


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


def test_government_warning_damaged_heading_needs_review_when_statement_is_close() -> None:
    ocr_text = GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "G0VERNMENT WARNlNG")
    result = verify_government_warning(ocr_text, 0.88)
    assert result.status == STATUS_REVIEW
    assert "heading or OCR text is not exact" in result.reason


def test_abv_mismatch_fails() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN 40% Alc./Vol.")
    assert result.status == STATUS_FAIL


def test_abv_match_accepts_percent_alc_by_vol_wording() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN 45% Alc. by Vol.")
    assert result.status == STATUS_PASS


def test_abv_match_accepts_alcohol_by_vol_abbreviation() -> None:
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN Alcohol 45% by Vol.").status == STATUS_PASS


def test_abv_match_accepts_alcohol_colon_by_volume_wording() -> None:
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN Alcohol: 45% by Volume").status == STATUS_PASS


def test_abv_match_accepts_compact_percent_vol_wording() -> None:
    assert verify_alcohol_content("13.5% ABV", "SUNSET HOLLOW 13.5% vol").status == STATUS_PASS
    assert verify_alcohol_content("13.5% ABV", "SUNSET HOLLOW 13,5% vol").status == STATUS_PASS
    assert verify_alcohol_content("13.5% ABV", "SUNSET HOLLOW Alc 13.5% Vol.").status == STATUS_PASS
    assert verify_alcohol_content("13.5% ABV", "SUNSET HOLLOW Alc 13,5% Vol.").status == STATUS_PASS


def test_abv_match_accepts_percent_by_volume_shorthand() -> None:
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45% by volume").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45 percent by volume").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45% Alcohol Vol.").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45% Alcohol Volume").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45% Alcohol/Vol.").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN Alcohol/Vol. 45%").status == STATUS_PASS


def test_proof_match_accepts_degrees_wording() -> None:
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 90 degrees proof").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 90\u00b0 proof").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 90 Proof 45% Alc./Vol.").status == STATUS_PASS
    assert verify_alcohol_content("45% ABV", "OLD TOM GIN 45 proof").status == STATUS_FAIL


def test_conflicting_alcohol_values_need_review() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN 45% Alc./Vol. Back label says 40% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "conflicting alcohol-content" in result.reason


def test_non_alcohol_percentage_does_not_create_abv_mismatch() -> None:
    result = verify_alcohol_content("40% ABV", "CASA VERDE TEQUILA 100% Agave Product of Mexico")
    assert result.status == STATUS_REVIEW
    assert "not clearly found" in result.reason


def test_non_alcohol_percent_by_volume_does_not_create_abv_mismatch() -> None:
    result = verify_alcohol_content("45% ABV", "OLD TOM GIN Natural flavoring 49% by volume")
    assert result.status == STATUS_REVIEW
    assert "not clearly found" in result.reason


def test_non_alcohol_percent_by_volume_does_not_conflict_with_real_abv() -> None:
    result = verify_alcohol_content(
        "45% ABV",
        "OLD TOM GIN Natural flavoring 49% by volume\n45% Alc./Vol.",
    )
    assert result.status == STATUS_PASS


def test_formula_alcohol_content_matches_label() -> None:
    result = verify_formula_alcohol_content("F-1001", "45% ABV", "formula-approval", "OLD TOM GIN 45% Alc./Vol.")
    assert result.status == STATUS_PASS
    assert result.field == "formula"


def test_formula_alcohol_content_range_matches_label() -> None:
    result = verify_formula_alcohol_content("F-1001", "25-30% ABV", "formula-approval", "Label says 27% Alc./Vol.")
    assert result.status == STATUS_PASS


def test_alcohol_content_decimal_comma_range_matches_high_end_label() -> None:
    result = verify_alcohol_content("12,5-13,5% ABV", "SUNSET HOLLOW 13.5% vol")
    assert result.status == STATUS_PASS
    assert result.expected == "12.5-13.5% ABV"


def test_expected_proof_range_converts_to_abv_before_label_comparison() -> None:
    result = verify_alcohol_content("80-90 Proof", "PROOF RANGE BOURBON 90 Proof")
    assert result.status == STATUS_PASS
    assert result.expected == "40-45% ABV"
    assert result.found == "45% ABV"


def test_expected_proof_prefix_range_converts_to_abv_before_label_comparison() -> None:
    result = verify_alcohol_content("Proof 80-90", "PROOF RANGE BOURBON 45% Alc./Vol.")
    assert result.status == STATUS_PASS
    assert result.expected == "40-45% ABV"


def test_expected_repeated_unit_proof_range_converts_to_abv_before_label_comparison() -> None:
    result = verify_alcohol_content("80 Proof - 90 Proof", "RANGE HOUSE BOURBON 90 Proof")
    assert result.status == STATUS_PASS
    assert result.expected == "40-45% ABV"
    assert result.found == "45% ABV"


def test_expected_repeated_unit_degree_proof_range_converts_to_abv() -> None:
    result = verify_alcohol_content("80\u00b0 Proof - 90\u00b0 Proof", "RANGE HOUSE BOURBON 90 Proof")
    assert result.status == STATUS_PASS
    assert result.expected == "40-45% ABV"


def test_expected_repeated_unit_abv_range_preserves_low_high_bounds() -> None:
    result = verify_alcohol_content("12.5%-13.5% ABV", "RANGE ESTATE 13.5% vol")
    assert result.status == STATUS_PASS
    assert result.expected == "12.5-13.5% ABV"


def test_formula_alcohol_content_decimal_comma_range_matches_high_end_label() -> None:
    result = verify_formula_alcohol_content("F-1001", "12,5-13,5% ABV", "formula-approval", "Label says 13.5% vol.")
    assert result.status == STATUS_PASS
    assert result.expected.startswith("12.5-13.5% ABV")


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


def test_formula_alcohol_content_conflicting_label_values_need_review() -> None:
    result = verify_formula_alcohol_content(
        "F-1001",
        "45% ABV",
        "formula-approval",
        "OLD TOM GIN 45% Alc./Vol. Back label says 40% Alc./Vol.",
    )
    assert result.status == STATUS_REVIEW
    assert "conflicting alcohol-content" in result.reason


def test_supplied_fanciful_name_missing_needs_review() -> None:
    fields = ApplicationFields(
        serial_number="APP-FANCIFUL",
        product_type="DISTILLED SPIRITS",
        brand_name="OLD TOM GIN",
        fanciful_name="Botanical Reserve",
        formula="F-1001",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
        raw_sources={"alcohol_content": "formula-approval"},
    )
    label = LabelExtraction(
        text=f"OLD TOM GIN DISTILLED SPIRITS Gin 45% Alc./Vol. 750 mL {GOVERNMENT_WARNING}",
        confidence=0.97,
    )

    result = verify_application(
        filename="fanciful.pdf",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    fanciful = next(field for field in result.field_results if field.field == "fanciful_name")
    assert result.overall_status == STATUS_REVIEW
    assert fanciful.status == STATUS_REVIEW


def test_no_formula_required_passes_formula_check() -> None:
    result = verify_formula_alcohol_content("NO FORMULA REQUIRED", "", "", "VALLEY TABLE WINE 13% Alc./Vol.")
    assert result.status == STATUS_PASS
    assert "no formula is required" in result.reason


def test_formula_not_required_wording_passes_formula_check() -> None:
    for formula in ("FORMULA NOT REQUIRED", "Not Required", "Not Applicable - No Formula Required"):
        result = verify_formula_alcohol_content(formula, "", "", "VALLEY TABLE WINE 13% Alc./Vol.")
        assert result.status == STATUS_PASS
        assert "no formula is required" in result.reason


def test_ambiguous_formula_na_still_needs_review() -> None:
    result = verify_formula_alcohol_content("N/A", "", "", "VALLEY TABLE WINE 13% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "No matching approved formula document" in result.reason


def test_matched_formula_without_final_alcohol_needs_review() -> None:
    result = verify_formula_alcohol_content("F-2800", "", "formula-approval", "OLD TOM GIN 45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "did not contain extractable final alcohol content" in result.reason


def test_unapproved_formula_document_needs_review() -> None:
    result = verify_formula_alcohol_content(
        "F-12700",
        "",
        "formula-approval-unapproved:REJECTED",
        "OLD TOM GIN 45% Alc./Vol.",
    )
    assert result.status == STATUS_REVIEW
    assert result.found == "REJECTED"
    assert "not approved" in result.reason


def test_product_type_mismatch_fails() -> None:
    result = verify_product_type("DISTILLED SPIRITS", "OLD TOM GIN MALT BEVERAGES 45% Alc./Vol.")
    assert result.status == STATUS_FAIL
    assert "different product type" in result.reason


def test_conflicting_explicit_product_type_statements_need_review() -> None:
    result = verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nMALT BEVERAGES\nWINE\n5.5% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert result.found == "WINE"
    assert "conflicting product-type" in result.reason


def test_product_type_descriptor_does_not_override_explicit_product_type() -> None:
    result = verify_product_type("DISTILLED SPIRITS", "CELLAR CASK WHISKEY Wine Cask Finish DISTILLED SPIRITS")
    assert result.status == STATUS_PASS


def test_wine_descriptor_does_not_override_distilled_spirits_class_type() -> None:
    assert (
        verify_product_type(
            "DISTILLED SPIRITS",
            "OLD TOM GIN\nWine Barrel Finished\nClass/Type: Gin\n45% Alc./Vol.",
        ).status
        == STATUS_PASS
    )
    assert (
        verify_product_type(
            "DISTILLED SPIRITS",
            "OLD TOM GIN\nMade with wine botanicals\nClass/Type: Gin\n45% Alc./Vol.",
        ).status
        == STATUS_PASS
    )


def test_distilled_spirits_specialty_class_can_satisfy_product_type() -> None:
    label = "SPARK RIDGE\nCranberry Lime\nClass/Type: Vodka Cocktail\n7% Alc./Vol."
    result = verify_product_type("DISTILLED SPIRITS", label)
    assert result.status == STATUS_PASS
    assert result.reason == "Product type matches."


def test_explicit_wine_product_type_still_fails_distilled_spirits_application() -> None:
    result = verify_product_type("DISTILLED SPIRITS", "OLD TOM GIN\nWINE\nClass/Type: Gin\n45% Alc./Vol.")
    assert result.status == STATUS_FAIL
    assert result.found == "WINE"


def test_product_type_first_label_line_passes_when_explicit() -> None:
    result = verify_product_type("DISTILLED SPIRITS", "DISTILLED SPIRITS\nOLD TOM GIN\nClass/Type: Gin\n45% Alc./Vol.")
    assert result.status == STATUS_PASS


def test_wine_product_type_passes_from_cider_and_perry_terms() -> None:
    assert verify_product_type("WINE", "ORCHARD RIDGE\nClass/Type: Hard Cider").status == STATUS_PASS
    assert verify_product_type("WINE", "PERRY\nClass/Type: Perry").status == STATUS_PASS
    assert verify_product_type("DISTILLED SPIRITS", "ORCHARD BRANDY\nClass/Type: Cider Brandy").status == STATUS_PASS


def test_wine_product_type_passes_from_cfr_wine_class_terms() -> None:
    assert verify_product_type("WINE", "SAKE\nMOON RICE\n15% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "MOON RICE\nClass/Type: Sake\n15% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "VERMOUTH\nVALLEY AROMATIC\n16% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "VALLEY VERMOUTH\nClass/Type: Vermouth\n16% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "CELLAR SHERRY\nClass/Type: Sherry\n18% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "OLD HARBOR PORT\nClass/Type: Port\n19% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "BRIGHT STAR\nClass/Type: Champagne\n12% Alc./Vol.").status == STATUS_PASS


def test_wine_product_type_passes_from_mead_and_sangria_terms() -> None:
    assert verify_product_type("WINE", "MEAD\nHONEY MOON\n12% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "HONEY MOON\nClass/Type: Mead\n12% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "HONEY WINE\nHONEY MOON\n12% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SANGRIA\nSUNSET PUNCH\n12% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SUNSET PUNCH\nClass/Type: Sangria\n12% Alc./Vol.").status == STATUS_PASS


def test_wine_product_type_passes_from_varietal_type_designations() -> None:
    assert verify_product_type("WINE", "CHARDONNAY\nSUNSET HOLLOW\n13.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SUNSET HOLLOW\nChardonnay\n13.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SUNSET HOLLOW\nCabernet Sauvignon\n13.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SUNSET HOLLOW\nRed Blend\n13.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("WINE", "SUNSET HOLLOW\nRose\n13.5% Alc./Vol.").status == STATUS_PASS


def test_wine_varietal_brand_or_descriptor_context_stays_conservative() -> None:
    assert verify_product_type("WINE", "CHARDONNAY HILL ESTATE\n13.5% Alc./Vol.").status == STATUS_REVIEW
    assert (
        verify_product_type(
            "DISTILLED SPIRITS",
            "OLD TOM GIN\nChardonnay Cask Finished\nClass/Type: Gin\n45% Alc./Vol.",
        ).status
        == STATUS_PASS
    )


def test_distilled_spirits_product_type_passes_from_class_type_context() -> None:
    assert verify_product_type("DISTILLED SPIRITS", "OLD TOM GIN\nClass/Type: Gin\n45% Alc./Vol.").status == STATUS_PASS
    assert (
        verify_product_type("DISTILLED SPIRITS", "RIVER BEND BOURBON\nStraight Bourbon Whiskey\n90 Proof").status
        == STATUS_PASS
    )


def test_malt_product_type_first_label_line_passes_when_explicit() -> None:
    assert verify_product_type("MALT BEVERAGES", "BEER\nSUNNY FARMS\n5.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "LAGER BEER\nSUNNY FARMS\n5.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "INDIA PALE ALE\nSUNNY FARMS\n5.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "MALT LIQUOR\nSUNNY FARMS\n5.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nClass/Type: IPA\n6.5% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nPilsner\n5.0% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nHARD SELTZER\n5.0% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nSPIKED SELTZER\n5.0% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARBOR LIGHT\nMALT-BASED SELTZER\n5.0% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "HARD SELTZER\nHARBOR LIGHT\n5.0% Alc./Vol.").status == STATUS_PASS
    assert verify_product_type("MALT BEVERAGES", "FLAVORED MALT BEVERAGE\nHARBOR TEA\n5.0% Alc./Vol.").status == STATUS_PASS
    assert (
        verify_product_type("MALT BEVERAGES", "PRODUCT TYPE: SPIKED SELTZER\nHARBOR LIGHT\n5.0% Alc./Vol.").status
        == STATUS_PASS
    )


def test_wine_brand_with_spirit_word_does_not_fail_product_type() -> None:
    result = verify_product_type("WINE", "SPIRIT HILL WINE\nWINE\nClass/Type: Red Wine\n13% Alc./Vol.")
    assert result.status == STATUS_PASS


def test_product_type_word_in_brand_only_needs_review() -> None:
    result = verify_product_type("WINE", "SPIRIT HILL ESTATE RED\nEstate Red\n13% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "not clearly found" in result.reason


def test_class_type_in_brand_line_only_needs_review() -> None:
    result = verify_class_type("Gin", "OLD TOM GIN\nDISTILLED SPIRITS\n45% Alc./Vol.\n750 mL")
    assert result.status == STATUS_REVIEW
    assert "non-class context" in result.reason


def test_conflicting_class_type_statements_need_review() -> None:
    result = verify_class_type("Gin", "OLD TOM GIN\nClass/Type: Gin\nClass/Type: Vodka\n45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert result.found == "Vodka"
    assert "conflicting class/type" in result.reason


def test_class_type_does_not_match_inside_larger_word() -> None:
    result = verify_class_type("Gin", "Class/Type: Ginger Liqueur\n45% Alc./Vol.")
    assert result.status == STATUS_REVIEW
    assert "not clearly found" in result.reason


def test_class_type_keeps_product_type_words_after_explicit_marker() -> None:
    assert (
        verify_class_type("Distilled Spirits Specialty", "Class/Type: Distilled Spirits Specialty").status
        == STATUS_PASS
    )
    assert (
        verify_class_type(
            "Distilled Spirits Specialty",
            "OLD TOM GIN Class/Type: Distilled Spirits Specialty 45% Alc./Vol.",
        ).status
        == STATUS_PASS
    )
    assert verify_class_type("Ale with natural flavors", "Class/Type: Ale with natural flavors").status == STATUS_PASS


def test_imported_country_of_origin_passes_when_present() -> None:
    result = verify_country_of_origin("Mexico", True, "CASA VERDE TEQUILA Product of Mexico")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_allows_the_before_country() -> None:
    result = verify_country_of_origin("United States", True, "Product of the United States")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_allows_produce_of_wording() -> None:
    result = verify_country_of_origin("France", True, "CHATEAU LUMIERE Produce of France")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_allows_imported_by_from_wording() -> None:
    result = verify_country_of_origin("France", True, "Imported by Example Imports LLC from France")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_allows_distilled_and_brewed_in_wording() -> None:
    assert verify_country_of_origin("Mexico", True, "Distilled in Mexico").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Distilled in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Distilled and bottled in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Distilled, matured and bottled in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Distilled and aged in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Blended in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Blended and bottled in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Blended, matured and bottled in Scotland").status == STATUS_PASS
    assert verify_country_of_origin("Belgium", True, "Brewed in Belgium").status == STATUS_PASS
    assert verify_country_of_origin("Belgium", True, "Brewed and bottled in Belgium").status == STATUS_PASS
    assert verify_country_of_origin("Italy", True, "Made and bottled in Italy").status == STATUS_PASS


def test_imported_country_of_origin_allows_produced_and_bottled_in_wording() -> None:
    result = verify_country_of_origin("France", True, "Produced and bottled in France")
    assert result.status == STATUS_PASS


def test_imported_country_of_origin_allows_us_abbreviations() -> None:
    assert verify_country_of_origin("United States", True, "Product of USA").status == STATUS_PASS
    assert verify_country_of_origin("United States", True, "Product of U.S.A.").status == STATUS_PASS
    assert verify_country_of_origin("United States", True, "Made in U.S.").status == STATUS_PASS


def test_imported_country_of_origin_allows_uk_abbreviations() -> None:
    assert verify_country_of_origin("United Kingdom", True, "Product of UK").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Product of U.K.").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Product of Great Britain").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Product of Scotland").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Product of England").status == STATUS_PASS


def test_imported_country_of_origin_allows_protected_whisky_origin_terms() -> None:
    assert verify_country_of_origin("United Kingdom", True, "HIGHLAND FORGE Scotch Whisky").status == STATUS_PASS
    assert verify_country_of_origin("Ireland", True, "OLD HARBOR Irish Whiskey").status == STATUS_PASS
    assert verify_country_of_origin("Canada", True, "MAPLE RIDGE Canadian Whisky").status == STATUS_PASS


def test_imported_country_of_origin_allows_the_netherlands_variants() -> None:
    assert verify_country_of_origin("The Netherlands", True, "Product of Netherlands").status == STATUS_PASS
    assert verify_country_of_origin("Netherlands", True, "Product of the Netherlands").status == STATUS_PASS


def test_imported_country_of_origin_allows_republic_of_ireland_variants() -> None:
    assert verify_country_of_origin("Ireland", True, "Product of Republic of Ireland").status == STATUS_PASS
    assert verify_country_of_origin("Republic of Ireland", True, "Product of Ireland").status == STATUS_PASS


def test_imported_country_of_origin_conflict_needs_review() -> None:
    result = verify_country_of_origin("Mexico", True, "Product of Mexico\nImported from France")
    assert result.status == STATUS_REVIEW
    assert result.found == "France"
    assert "conflicting country-of-origin" in result.reason


def test_imported_country_origin_aliases_do_not_create_false_conflict() -> None:
    assert (
        verify_country_of_origin("United Kingdom", True, "Product of Scotland\nImported from UK").status
        == STATUS_PASS
    )
    assert verify_country_of_origin("Ireland", True, "Product of Republic of Ireland").status == STATUS_PASS
    assert verify_country_of_origin("The Netherlands", True, "Product of Netherlands").status == STATUS_PASS


def test_imported_country_of_origin_needs_review_when_missing_from_label() -> None:
    result = verify_country_of_origin("Mexico", True, "CASA VERDE TEQUILA Imported by Borderland Imports LLC")
    assert result.status == STATUS_REVIEW


def test_domestic_application_with_foreign_origin_statement_needs_review() -> None:
    result = verify_country_of_origin("", False, "OLD TOM GIN Product of Mexico")
    assert result.status == STATUS_REVIEW
    assert result.found == "Mexico"
    assert "marked domestic" in result.reason


def test_domestic_application_with_imported_from_statement_needs_review() -> None:
    result = verify_country_of_origin("", False, "OLD TOM GIN Imported from France")
    assert result.status == STATUS_REVIEW
    assert result.found == "France"


def test_domestic_application_with_protected_foreign_origin_term_needs_review() -> None:
    result = verify_country_of_origin("", False, "HIGHLAND FORGE Scotch Whisky")
    assert result.status == STATUS_REVIEW
    assert result.found == "United Kingdom"


def test_domestic_application_with_us_origin_statement_still_passes() -> None:
    result = verify_country_of_origin("", False, "OLD TOM GIN Product of USA")
    assert result.status == STATUS_PASS


def test_imported_country_name_in_importer_name_is_not_enough() -> None:
    result = verify_country_of_origin("Mexico", True, "CASA VERDE TEQUILA Imported by Mexico Trading LLC")
    assert result.status == STATUS_REVIEW


def test_imported_country_adjective_alone_is_not_enough() -> None:
    result = verify_country_of_origin("France", True, "French Wine")
    assert result.status == STATUS_REVIEW
    assert verify_country_of_origin("Italy", True, "Italian Wine").status == STATUS_REVIEW


def test_imported_country_product_of_origin_wording_passes() -> None:
    assert verify_country_of_origin("France", True, "Wine of France").status == STATUS_PASS
    assert verify_country_of_origin("United Kingdom", True, "Whisky of Scotland").status == STATUS_PASS


def test_imported_country_unhandled_origin_shorthand_needs_review() -> None:
    assert verify_country_of_origin("France", True, "Vinted in France").status == STATUS_REVIEW
    assert verify_country_of_origin("United Kingdom", True, "Aged in Scotland").status == STATUS_REVIEW
    assert verify_country_of_origin("Mexico", True, "Bottled in Mexico").status == STATUS_REVIEW


def test_net_contents_match_passes_with_liters() -> None:
    result = verify_net_contents("750 mL", "Net Contents .75 L")
    assert result.status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 0,75 L").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents e750 mL").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 750 M.L.").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 750 M L").status == STATUS_PASS


def test_net_contents_match_passes_with_comma_thousands() -> None:
    assert verify_net_contents("1000 mL", "Net Contents 1,000 mL").status == STATUS_PASS


def test_net_contents_match_passes_with_centiliters() -> None:
    assert verify_net_contents("750 mL", "Net Contents 75 cL").status == STATUS_PASS
    assert verify_net_contents("75 cL", "Net Contents 750 mL").status == STATUS_PASS


def test_net_contents_match_passes_with_pints() -> None:
    assert verify_net_contents("16 fl oz", "Net Contents 1 Pint").status == STATUS_PASS
    assert verify_net_contents("8 fl oz", "Net Contents 1/2 Pint").status == STATUS_PASS
    assert verify_net_contents("500 mL", "Net Contents 1 Pint 0.9 FL OZ").status == STATUS_PASS


def test_net_contents_match_passes_with_plain_ounces() -> None:
    assert verify_net_contents("12 fl oz", "Net Contents 12 OZ").status == STATUS_PASS
    assert verify_net_contents("12 fl oz", "Net Contents 12 F L OZ").status == STATUS_PASS
    assert verify_net_contents("12 fl oz", "Serving size 12 OZ").status == STATUS_REVIEW
    assert verify_net_contents("8 fl oz", "Serving size 1/2 Pint").status == STATUS_REVIEW


def test_net_contents_match_passes_with_rounded_dual_unit_equivalents() -> None:
    assert verify_net_contents("750 mL", "Net Contents 750 mL / 25.4 FL OZ").status == STATUS_PASS
    assert verify_net_contents("1 L", "Net Contents 1 L / 33.8 FL OZ").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 750 mL / 24 FL OZ").status == STATUS_REVIEW


def test_net_contents_match_passes_with_multipack_statement() -> None:
    assert verify_net_contents("200 mL", "Net Contents 4 x 50 mL").status == STATUS_PASS
    assert verify_net_contents("200 mL", "Net Contents 4-50 mL").status == STATUS_PASS
    assert verify_net_contents("200 mL", "Net Contents 4 - 50 mL").status == STATUS_PASS
    assert verify_net_contents("200 mL", "Net Contents 4-pack 50 mL").status == STATUS_PASS
    assert verify_net_contents("48 fl oz", "Net Contents 4-pack of 12 fl oz cans").status == STATUS_PASS
    assert verify_net_contents("48 fl oz", "Net Contents 4/12 fl oz cans").status == STATUS_PASS
    assert verify_net_contents("2130 mL", "Net Contents 6/355 mL bottles").status == STATUS_PASS
    assert verify_net_contents("200 mL", "Net Contents 50 mL x 4").status == STATUS_PASS
    assert verify_net_contents("200 mL", "Net Contents 200 mL (4 x 50 mL)").status == STATUS_PASS


def test_net_contents_match_passes_with_written_number_words() -> None:
    assert verify_net_contents("750 mL", "Net Contents Seven Hundred Fifty Milliliters").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 750 millilitres").status == STATUS_PASS
    assert verify_net_contents("750 mL", "Net Contents 750 mls").status == STATUS_PASS
    assert verify_net_contents("1 L", "Net Contents one liter").status == STATUS_PASS
    assert verify_net_contents("1 L", "Serving size one liter").status == STATUS_REVIEW


def test_conflicting_net_contents_need_review() -> None:
    result = verify_net_contents("750 mL", "Net Contents 750 mL Back label says 1 L")
    assert result.status == STATUS_REVIEW
    assert "conflicting net-contents" in result.reason


def test_serving_size_volume_does_not_create_net_contents_mismatch() -> None:
    result = verify_net_contents("750 mL", "OLD TOM GIN Serving size 50 mL")
    assert result.status == STATUS_REVIEW
    assert "not clearly found" in result.reason


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
            "OLD TOM GIN\nDISTILLED SPIRITS\nClass/Type: Gin\n45% Alc./Vol.\n750 mL\n"
            f"Bottled by Example Distilling Co.\n{GOVERNMENT_WARNING}"
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
