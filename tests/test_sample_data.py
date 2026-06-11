from __future__ import annotations

from pathlib import Path

import fitz

from src.batch import process_batch
from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.form_mapping import FORM_REGIONS
from src.ocr import tesseract_available
from src.sample_data import sample_specs


def test_generated_sample_data_loads_correctly(sample_paths: list[Path]) -> None:
    assert len(sample_paths) == len(sample_specs())
    assert len(sample_paths) >= 20
    assert Path("samples/sample_batch.zip").exists()
    assert Path("samples/expected_outcomes.md").exists()
    assert all(path.exists() and path.stat().st_size > 0 for path in sample_paths)


def test_generated_sample_outcomes(sample_paths: list[Path]) -> None:
    results = process_batch([(path.name, path.read_bytes()) for path in sample_paths], cache={})
    actual = {result.filename: result.overall_status for result in results}
    expected = {spec.filename: _expected_status(spec) for spec in sample_specs()}
    assert actual == expected


def test_expected_status_set_is_complete() -> None:
    statuses = {spec.expected_status for spec in sample_specs()}
    assert statuses == {STATUS_PASS, STATUS_FAIL, STATUS_REVIEW}


def test_sample_corpus_includes_color_artwork_ocr_cases() -> None:
    specs = sample_specs()
    artwork_specs = [spec for spec in specs if spec.artwork_label]
    assert len(artwork_specs) >= 30
    assert any(spec.expected_status == STATUS_PASS for spec in artwork_specs)
    assert any(spec.expected_status == STATUS_FAIL for spec in artwork_specs)
    assert any(spec.expected_status == STATUS_REVIEW for spec in artwork_specs)
    artwork_styles = {spec.artwork_style for spec in artwork_specs}
    assert {
        "geometric",
        "busy",
        "dark",
        "warning-panel",
        "busy-low-contrast",
        "crest",
        "texture",
        "photo",
        "photo-low-contrast",
        "ornate",
        "micro-warning",
        "metallic-foil",
        "dense-illustration",
        "stylized",
        "curved-distorted",
        "embossed",
        "glare",
    } <= artwork_styles


def test_sample_corpus_includes_required_field_and_formula_edge_cases() -> None:
    specs = {spec.filename: spec for spec in sample_specs()}
    assert "APP-023_no_formula_required_pass.pdf" in specs
    assert "APP-026_missing_expected_brand_review.pdf" in specs
    assert "APP-027_product_type_mismatch_fail.pdf" in specs
    assert "APP-028_formula_document_missing_final_alcohol_review.pdf" in specs
    assert "APP-029_formula_id_prefix_mismatch_review.pdf" in specs
    assert "APP-030_wine_cask_spirits_pass.pdf" in specs
    assert "APP-031_tequila_agave_missing_abv_review.pdf" in specs
    assert "APP-032_low_proof_liqueur_pass.pdf" in specs
    assert "APP-033_serving_size_missing_net_contents_review.pdf" in specs
    assert "APP-034_formula_ttb_id_number_pass.pdf" in specs
    assert "APP-035_alc_by_vol_order_pass.pdf" in specs
    assert "APP-036_missing_fanciful_name_review.pdf" in specs
    assert "APP-037_proof_before_value_pass.pdf" in specs
    assert "APP-038_alcohol_by_volume_order_pass.pdf" in specs
    assert "APP-039_brand_only_in_bottler_line_fail.pdf" in specs
    assert "APP-040_class_type_only_in_brand_review.pdf" in specs
    assert "APP-041_bottler_only_in_brand_review.pdf" in specs
    assert "APP-042_produced_and_bottled_by_pass.pdf" in specs
    assert "APP-043_ocr_damaged_warning_heading_review.pdf" in specs
    assert "APP-044_conflicting_abv_values_review.pdf" in specs
    assert "APP-045_conflicting_net_contents_review.pdf" in specs
    assert "APP-046_brand_word_order_mismatch_fail.pdf" in specs
    assert "APP-047_wine_brand_contains_spirit_pass.pdf" in specs
    assert "APP-048_class_type_substring_review.pdf" in specs
    assert "APP-049_product_type_brand_word_review.pdf" in specs
    assert "APP-050_product_type_first_line_pass.pdf" in specs
    assert "APP-051_us_origin_abbreviation_pass.pdf" in specs
    assert "APP-052_centiliter_net_contents_pass.pdf" in specs
    assert "APP-053_percent_alc_by_vol_pass.pdf" in specs
    assert "APP-054_stones_throw_case_pass.pdf" in specs
    assert "APP-055_produce_of_origin_pass.pdf" in specs
    assert "APP-056_pint_net_contents_pass.pdf" in specs
    assert "APP-057_plain_ounce_net_contents_pass.pdf" in specs
    assert "APP-058_distilled_by_responsible_party_pass.pdf" in specs
    assert "APP-059_beer_product_type_first_line_pass.pdf" in specs
    assert "APP-060_blended_by_responsible_party_pass.pdf" in specs
    assert "APP-061_bottled_for_responsible_party_pass.pdf" in specs
    assert "APP-062_fractional_pint_net_contents_pass.pdf" in specs
    assert "APP-063_written_net_contents_pass.pdf" in specs
    assert "APP-064_alcohol_by_vol_abbreviation_pass.pdf" in specs
    assert "APP-065_degrees_proof_pass.pdf" in specs
    assert "APP-066_class_type_implies_distilled_spirits_pass.pdf" in specs
    assert "APP-067_dual_unit_net_contents_pass.pdf" in specs
    assert "APP-068_imported_by_from_origin_pass.pdf" in specs
    assert "APP-069_alcohol_colon_by_volume_pass.pdf" in specs
    assert "APP-070_comma_thousands_net_contents_pass.pdf" in specs
    assert "APP-071_hard_cider_wine_product_type_pass.pdf" in specs
    assert "APP-072_uk_origin_abbreviation_pass.pdf" in specs
    assert "APP-073_compact_percent_vol_pass.pdf" in specs
    assert "APP-074_ampersand_brand_pass.pdf" in specs
    assert "APP-075_company_abbreviation_pass.pdf" in specs
    assert "APP-076_saint_abbreviation_brand_pass.pdf" in specs
    assert "APP-077_percent_by_volume_pass.pdf" in specs
    assert "APP-078_decimal_comma_litre_pass.pdf" in specs
    assert "APP-079_british_millilitres_pass.pdf" in specs
    assert "APP-080_scotland_origin_pass.pdf" in specs
    assert "APP-081_republic_ireland_origin_pass.pdf" in specs
    assert "APP-082_finished_alcohol_formula_pass.pdf" in specs
    assert "APP-083_final_product_alcohol_formula_pass.pdf" in specs
    assert "APP-084_distilled_in_origin_pass.pdf" in specs
    assert "APP-085_brewed_in_origin_pass.pdf" in specs
    assert "APP-086_packed_by_responsible_party_pass.pdf" in specs
    assert "APP-087_blended_in_origin_pass.pdf" in specs
    assert "APP-088_distilled_and_bottled_in_origin_pass.pdf" in specs
    assert "APP-089_distilled_matured_bottled_origin_pass.pdf" in specs
    assert "APP-090_ipa_class_type_malt_pass.pdf" in specs
    assert "APP-091_canned_by_responsible_party_pass.pdf" in specs
    assert "APP-092_formula_id_separator_variant_pass.pdf" in specs
    assert "APP-093_supplemental_label_after_instructions_pass.pdf" in specs
    assert "APP-094_long_attachment_before_label_pass.pdf" in specs
    assert "APP-095_wine_of_origin_pass.pdf" in specs
    assert "APP-096_multiple_formula_documents_pass.pdf" in specs
    assert "APP-097_diacritic_brand_pass.pdf" in specs
    assert "APP-098_decimal_comma_abv_pass.pdf" in specs
    assert "APP-099_decimal_comma_abv_range_pass.pdf" in specs
    assert "APP-100_expected_proof_range_pass.pdf" in specs
    assert "APP-101_repeated_unit_proof_range_pass.pdf" in specs
    assert "APP-102_hard_seltzer_malt_pass.pdf" in specs
    assert "APP-103_hard_seltzer_first_line_pass.pdf" in specs
    assert "APP-104_bottler_legal_suffix_pass.pdf" in specs
    assert "APP-105_formula_symbol_label_pass.pdf" in specs
    assert "APP-106_estimated_net_contents_mark_pass.pdf" in specs
    assert "APP-107_dotted_net_contents_unit_pass.pdf" in specs
    assert "APP-108_mixed_case_warning_heading_fail.pdf" in specs
    assert "APP-109_wine_descriptor_spirits_class_pass.pdf" in specs
    assert "APP-110_numeric_formula_id_pass.pdf" in specs
    assert "APP-111_busy_artwork_pass.pdf" in specs
    assert "APP-112_dark_reverse_artwork_pass.pdf" in specs
    assert "APP-113_colored_warning_panel_pass.pdf" in specs
    assert "APP-114_busy_low_contrast_artwork_review.pdf" in specs
    assert "APP-120_formula_not_required_pass.pdf" in specs
    assert "APP-121_import_country_conflict_review.pdf" in specs
    assert "APP-122_product_type_conflict_review.pdf" in specs
    assert "APP-123_class_type_conflict_review.pdf" in specs
    assert "APP-124_bottler_conflict_review.pdf" in specs
    assert "APP-125_comma_responsible_party_pass.pdf" in specs
    assert "APP-126_pre_import_approval_pass.pdf" in specs
    assert "APP-127_rejected_formula_review.pdf" in specs
    assert "APP-128_dotted_abv_crest_artwork_pass.pdf" in specs
    assert "APP-129_vv_textured_artwork_pass.pdf" in specs
    assert "APP-130_spaced_abv_dark_artwork_pass.pdf" in specs
    assert "APP-131_formula_alc_vol_heading_pass.pdf" in specs
    assert "APP-132_scotch_whisky_origin_pass.pdf" in specs
    assert "APP-133_photo_artwork_pass.pdf" in specs
    assert "APP-134_photo_low_contrast_artwork_review.pdf" in specs
    assert "APP-135_ambiguous_product_type_checkboxes_review.pdf" in specs
    assert "APP-136_ambiguous_import_checkboxes_review.pdf" in specs
    assert "APP-150_chardonnay_varietal_wine_pass.pdf" in specs
    assert "APP-151_bottled_exclusively_for_pass.pdf" in specs
    assert "APP-152_distilled_spirits_specialty_class_pass.pdf" in specs
    assert "APP-155_vodka_cocktail_class_product_type_pass.pdf" in specs
    assert "APP-156_bottled_in_origin_review.pdf" in specs
    assert "APP-157_hyphenated_warning_heading_fail.pdf" in specs
    assert "APP-158_multipack_net_contents_pass.pdf" in specs
    assert "APP-159_formula_target_abv_pass.pdf" in specs
    assert "APP-160_mfg_made_bottled_origin_pass.pdf" in specs
    assert "APP-161_formula_bottling_proof_pass.pdf" in specs
    assert "APP-162_dash_multipack_net_contents_pass.pdf" in specs
    assert "APP-163_colon_warning_heading_fail.pdf" in specs
    assert "APP-164_hyphen_pack_net_contents_pass.pdf" in specs
    assert "APP-165_slash_multipack_net_contents_pass.pdf" in specs
    assert "APP-166_imported_bottled_distributed_by_pass.pdf" in specs
    assert "APP-167_colon_bottled_by_pass.pdf" in specs
    assert "APP-168_percent_alcohol_volume_pass.pdf" in specs
    assert "APP-169_slash_alcohol_volume_pass.pdf" in specs
    assert "APP-170_brewed_canned_origin_pass.pdf" in specs
    assert "APP-171_class_type_first_liqueur_pass.pdf" in specs
    assert "APP-172_wine_varietal_appellation_missing_review.pdf" in specs
    assert "APP-173_word_count_multipack_net_contents_pass.pdf" in specs
    assert "APP-174_first_line_sparkling_hard_seltzer_pass.pdf" in specs
    assert "APP-175_first_line_imperial_stout_pass.pdf" in specs
    assert "APP-176_first_line_straight_rye_whiskey_pass.pdf" in specs
    assert "APP-177_imported_into_from_origin_pass.pdf" in specs
    assert "APP-178_under_authority_responsible_party_review.pdf" in specs
    assert "APP-179_bottled_for_by_actual_bottler_pass.pdf" in specs
    assert "APP-180_oneline_bottled_for_by_actual_bottler_pass.pdf" in specs
    assert "APP-181_oneline_bottled_for_brand_owner_review.pdf" in specs
    assert "APP-182_formula_final_abv_heading_pass.pdf" in specs
    assert "APP-183_formula_as_bottled_heading_pass.pdf" in specs
    assert "APP-184_ornate_artwork_pass.pdf" in specs
    assert "APP-185_tiny_warning_artwork_review.pdf" in specs
    assert "APP-186_champagne_of_france_origin_pass.pdf" in specs
    assert "APP-187_mezcal_of_mexico_origin_pass.pdf" in specs
    assert "APP-188_modified_hard_cider_first_line_pass.pdf" in specs
    assert "APP-189_barleywine_ale_malt_pass.pdf" in specs
    assert "APP-190_tequila_barrel_aged_beer_pass.pdf" in specs
    assert "APP-191_split_front_back_panels_pass.pdf" in specs
    assert "APP-192_split_panel_conflicting_abv_review.pdf" in specs
    assert "APP-193_metallic_foil_artwork_pass.pdf" in specs
    assert "APP-194_dense_illustration_artwork_review.pdf" in specs
    assert "APP-195_stylized_font_artwork_pass.pdf" in specs
    assert "APP-196_curved_distorted_text_review.pdf" in specs
    assert "APP-197_embossed_low_contrast_review.pdf" in specs
    assert "APP-198_partial_glare_scan_review.pdf" in specs
    assert specs["APP-023_no_formula_required_pass.pdf"].include_formula_approval is False
    assert specs["APP-120_formula_not_required_pass.pdf"].include_formula_approval is False
    assert specs["APP-120_formula_not_required_pass.pdf"].fields["formula"] == "FORMULA NOT REQUIRED"
    assert specs["APP-120_formula_not_required_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-121_import_country_conflict_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-122_product_type_conflict_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-123_class_type_conflict_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-124_bottler_conflict_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-125_comma_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-126_pre_import_approval_pass.pdf"].formula_approval_header == "PRE-IMPORT APPROVAL LETTER"
    assert specs["APP-126_pre_import_approval_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-127_rejected_formula_review.pdf"].formula_approval_status == "Rejected"
    assert specs["APP-127_rejected_formula_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-128_dotted_abv_crest_artwork_pass.pdf"].artwork_style == "crest"
    assert specs["APP-128_dotted_abv_crest_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-129_vv_textured_artwork_pass.pdf"].artwork_style == "texture"
    assert specs["APP-129_vv_textured_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-130_spaced_abv_dark_artwork_pass.pdf"].artwork_style == "dark"
    assert specs["APP-130_spaced_abv_dark_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-131_formula_alc_vol_heading_pass.pdf"].formula_approval_alcohol_label == "Finished Product Alc/Vol"
    assert specs["APP-131_formula_alc_vol_heading_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-132_scotch_whisky_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert "SCOTCH WHISKY" in specs["APP-132_scotch_whisky_origin_pass.pdf"].label_lines
    assert specs["APP-132_scotch_whisky_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-133_photo_artwork_pass.pdf"].artwork_style == "photo"
    assert specs["APP-133_photo_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-134_photo_low_contrast_artwork_review.pdf"].artwork_style == "photo-low-contrast"
    assert specs["APP-134_photo_low_contrast_artwork_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-135_ambiguous_product_type_checkboxes_review.pdf"].fields["product_type"] == ""
    assert specs["APP-135_ambiguous_product_type_checkboxes_review.pdf"].source_product_type_checks == (
        "WINE",
        "DISTILLED SPIRITS",
    )
    assert specs["APP-135_ambiguous_product_type_checkboxes_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-136_ambiguous_import_checkboxes_review.pdf"].source_import_checks == (False, True)
    assert specs["APP-136_ambiguous_import_checkboxes_review.pdf"].fields["country_of_origin"] == "Mexico"
    assert specs["APP-136_ambiguous_import_checkboxes_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-137_formula_of_the_finished_product_pass.pdf"].formula_approval_alcohol_label == "Alcohol Content of the Finished Product"
    assert specs["APP-137_formula_of_the_finished_product_pass.pdf"].expected_status == STATUS_PASS
    assert "Natural flavoring 49% by volume" in specs["APP-138_flavoring_percent_with_abv_pass.pdf"].label_lines
    assert specs["APP-138_flavoring_percent_with_abv_pass.pdf"].expected_status == STATUS_PASS
    assert "45% Alc./Vol." not in specs["APP-139_flavoring_percent_missing_abv_review.pdf"].label_lines
    assert specs["APP-139_flavoring_percent_missing_abv_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-140_formula_row_number_pass.pdf"].formula_approval_alcohol_row_number == "3"
    assert specs["APP-140_formula_row_number_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-141_domestic_foreign_origin_review.pdf"].fields["imported"] is False
    assert specs["APP-141_domestic_foreign_origin_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-142_domestic_imported_from_origin_review.pdf"].fields["imported"] is False
    assert specs["APP-142_domestic_imported_from_origin_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-143_dual_proof_abv_statement_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-144_lager_beer_first_line_pass.pdf"].fields["product_type"] == "MALT BEVERAGES"
    assert specs["APP-144_lager_beer_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-145_brand_number_symbol_pass.pdf"].fields["brand_name"] == "OLD TOM NO. 5"
    assert specs["APP-145_brand_number_symbol_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-146_finished_product_proof_formula_pass.pdf"].formula_approval_alcohol_label == "Finished Product Proof"
    assert specs["APP-146_finished_product_proof_formula_pass.pdf"].formula_approval_unit == "Proof"
    assert specs["APP-146_finished_product_proof_formula_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-147_mead_wine_class_pass.pdf"].fields["class_type"] == "Mead"
    assert specs["APP-147_mead_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-148_flavored_malt_beverage_first_line_pass.pdf"].label_lines[0] == "FLAVORED MALT BEVERAGE"
    assert specs["APP-148_flavored_malt_beverage_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-149_superseded_formula_review.pdf"].formula_approval_status == "Approved - Superseded"
    assert specs["APP-149_superseded_formula_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-150_chardonnay_varietal_wine_pass.pdf"].fields["product_type"] == "WINE"
    assert specs["APP-150_chardonnay_varietal_wine_pass.pdf"].fields["class_type"] == "Chardonnay"
    assert "Chardonnay" in specs["APP-150_chardonnay_varietal_wine_pass.pdf"].label_lines
    assert "California" in specs["APP-150_chardonnay_varietal_wine_pass.pdf"].label_lines
    assert specs["APP-150_chardonnay_varietal_wine_pass.pdf"].expected_status == STATUS_PASS
    assert "Bottled exclusively for Example Distilling Co." in specs["APP-151_bottled_exclusively_for_pass.pdf"].label_lines
    assert specs["APP-151_bottled_exclusively_for_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-152_distilled_spirits_specialty_class_pass.pdf"].fields["class_type"] == "Distilled Spirits Specialty"
    assert "Class/Type: Distilled Spirits Specialty" in specs["APP-152_distilled_spirits_specialty_class_pass.pdf"].label_lines
    assert specs["APP-152_distilled_spirits_specialty_class_pass.pdf"].expected_status == STATUS_PASS
    assert "Distributed by Example Distilling Co." in specs["APP-154_distributed_by_only_review.pdf"].label_lines
    assert specs["APP-154_distributed_by_only_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-155_vodka_cocktail_class_product_type_pass.pdf"].fields["class_type"] == "Vodka Cocktail"
    assert "DISTILLED SPIRITS" not in specs["APP-155_vodka_cocktail_class_product_type_pass.pdf"].label_lines
    assert "Class/Type: Vodka Cocktail" in specs["APP-155_vodka_cocktail_class_product_type_pass.pdf"].label_lines
    assert specs["APP-155_vodka_cocktail_class_product_type_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-156_bottled_in_origin_review.pdf"].fields["country_of_origin"] == "Mexico"
    assert "Bottled in Mexico" in specs["APP-156_bottled_in_origin_review.pdf"].label_lines
    assert specs["APP-156_bottled_in_origin_review.pdf"].expected_status == STATUS_REVIEW
    assert "GOVERNMENT-WARNING" in specs["APP-157_hyphenated_warning_heading_fail.pdf"].label_lines[-1]
    assert specs["APP-157_hyphenated_warning_heading_fail.pdf"].expected_status == STATUS_FAIL
    assert specs["APP-158_multipack_net_contents_pass.pdf"].fields["net_contents"] == "200 mL"
    assert "Net Contents 4 x 50 mL" in specs["APP-158_multipack_net_contents_pass.pdf"].label_lines
    assert specs["APP-158_multipack_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-159_formula_target_abv_pass.pdf"].formula_approval_alcohol_label == "Target ABV"
    assert specs["APP-159_formula_target_abv_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-160_mfg_made_bottled_origin_pass.pdf"].fields["country_of_origin"] == "Italy"
    assert "Made and bottled in Italy" in specs["APP-160_mfg_made_bottled_origin_pass.pdf"].label_lines
    assert "Mfg. by Example Distilling Co." in specs["APP-160_mfg_made_bottled_origin_pass.pdf"].label_lines
    assert specs["APP-160_mfg_made_bottled_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-161_formula_bottling_proof_pass.pdf"].formula_approval_alcohol_label == "Bottling Proof"
    assert specs["APP-161_formula_bottling_proof_pass.pdf"].formula_approval_unit == "Proof"
    assert specs["APP-161_formula_bottling_proof_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-162_dash_multipack_net_contents_pass.pdf"].fields["net_contents"] == "200 mL"
    assert "Net Contents 4-50 mL" in specs["APP-162_dash_multipack_net_contents_pass.pdf"].label_lines
    assert specs["APP-162_dash_multipack_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert "GOVERNMENT: WARNING" in specs["APP-163_colon_warning_heading_fail.pdf"].label_lines[-1]
    assert specs["APP-163_colon_warning_heading_fail.pdf"].expected_status == STATUS_FAIL
    assert specs["APP-164_hyphen_pack_net_contents_pass.pdf"].fields["net_contents"] == "48 fl oz"
    assert "Net Contents 4-pack of 12 fl oz cans" in specs["APP-164_hyphen_pack_net_contents_pass.pdf"].label_lines
    assert specs["APP-164_hyphen_pack_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-165_slash_multipack_net_contents_pass.pdf"].fields["net_contents"] == "48 fl oz"
    assert "Net Contents 4/12 fl oz cans" in specs["APP-165_slash_multipack_net_contents_pass.pdf"].label_lines
    assert specs["APP-165_slash_multipack_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-166_imported_bottled_distributed_by_pass.pdf"].fields["country_of_origin"] == "Mexico"
    assert "Imported, bottled and distributed by Example Imports LLC" in specs["APP-166_imported_bottled_distributed_by_pass.pdf"].label_lines
    assert specs["APP-166_imported_bottled_distributed_by_pass.pdf"].expected_status == STATUS_PASS
    assert "Bottled by: Example Distilling Co." in specs["APP-167_colon_bottled_by_pass.pdf"].label_lines
    assert specs["APP-167_colon_bottled_by_pass.pdf"].expected_status == STATUS_PASS
    assert "45% Alcohol Vol." in specs["APP-168_percent_alcohol_volume_pass.pdf"].label_lines
    assert specs["APP-168_percent_alcohol_volume_pass.pdf"].expected_status == STATUS_PASS
    assert "45% Alcohol/Vol." in specs["APP-169_slash_alcohol_volume_pass.pdf"].label_lines
    assert specs["APP-169_slash_alcohol_volume_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-170_brewed_canned_origin_pass.pdf"].fields["country_of_origin"] == "Belgium"
    assert "Brewed and canned in Belgium" in specs["APP-170_brewed_canned_origin_pass.pdf"].label_lines
    assert specs["APP-170_brewed_canned_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-171_class_type_first_liqueur_pass.pdf"].fields["class_type"] == "Liqueur"
    assert specs["APP-171_class_type_first_liqueur_pass.pdf"].label_lines[0] == "Class/Type: Liqueur"
    assert "DISTILLED SPIRITS" not in specs["APP-171_class_type_first_liqueur_pass.pdf"].label_lines
    assert specs["APP-171_class_type_first_liqueur_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-172_wine_varietal_appellation_missing_review.pdf"].fields["grape_varietals"] == "Cabernet Sauvignon; Merlot"
    assert specs["APP-172_wine_varietal_appellation_missing_review.pdf"].fields["wine_appellation"] == "California"
    assert "Cabernet Sauvignon" in specs["APP-172_wine_varietal_appellation_missing_review.pdf"].label_lines
    assert "Merlot" not in specs["APP-172_wine_varietal_appellation_missing_review.pdf"].label_lines
    assert "California" not in specs["APP-172_wine_varietal_appellation_missing_review.pdf"].label_lines
    assert specs["APP-172_wine_varietal_appellation_missing_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-173_word_count_multipack_net_contents_pass.pdf"].fields["net_contents"] == "72 fl oz"
    assert "Net Contents six 12 fl oz cans" in specs["APP-173_word_count_multipack_net_contents_pass.pdf"].label_lines
    assert specs["APP-173_word_count_multipack_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-174_first_line_sparkling_hard_seltzer_pass.pdf"].label_lines[0] == "SPARKLING HARD SELTZER"
    assert specs["APP-174_first_line_sparkling_hard_seltzer_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-175_first_line_imperial_stout_pass.pdf"].label_lines[0] == "IMPERIAL STOUT"
    assert specs["APP-175_first_line_imperial_stout_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-176_first_line_straight_rye_whiskey_pass.pdf"].label_lines[0] == "STRAIGHT RYE WHISKEY"
    assert specs["APP-176_first_line_straight_rye_whiskey_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-177_imported_into_from_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert "Imported into the United States from France by Example Imports LLC" in specs["APP-177_imported_into_from_origin_pass.pdf"].label_lines
    assert specs["APP-177_imported_into_from_origin_pass.pdf"].expected_status == STATUS_PASS
    assert "Bottled under the authority of Example Distilling Co." in specs["APP-178_under_authority_responsible_party_review.pdf"].label_lines
    assert specs["APP-178_under_authority_responsible_party_review.pdf"].expected_status == STATUS_REVIEW
    assert "Bottled for Old Tom Brands" in specs["APP-179_bottled_for_by_actual_bottler_pass.pdf"].label_lines
    assert "Bottled by Example Distilling Co." in specs["APP-179_bottled_for_by_actual_bottler_pass.pdf"].label_lines
    assert specs["APP-179_bottled_for_by_actual_bottler_pass.pdf"].expected_status == STATUS_PASS
    assert "Bottled for Old Tom Brands by Example Distilling Co." in specs["APP-180_oneline_bottled_for_by_actual_bottler_pass.pdf"].label_lines
    assert specs["APP-180_oneline_bottled_for_by_actual_bottler_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-181_oneline_bottled_for_brand_owner_review.pdf"].fields["bottler_producer"] == "Old Tom Brands"
    assert "Bottled for Old Tom Brands by Example Distilling Co." in specs["APP-181_oneline_bottled_for_brand_owner_review.pdf"].label_lines
    assert specs["APP-181_oneline_bottled_for_brand_owner_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-182_formula_final_abv_heading_pass.pdf"].formula_approval_alcohol_label == "Final ABV"
    assert specs["APP-182_formula_final_abv_heading_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-183_formula_as_bottled_heading_pass.pdf"].formula_approval_alcohol_label == "Alcohol Content as Bottled"
    assert specs["APP-183_formula_as_bottled_heading_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-027_product_type_mismatch_fail.pdf"].expected_status == STATUS_FAIL
    assert specs["APP-029_formula_id_prefix_mismatch_review.pdf"].formula_approval_id == "F-29001"
    assert specs["APP-030_wine_cask_spirits_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-031_tequila_agave_missing_abv_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-032_low_proof_liqueur_pass.pdf"].formula_approval_unit == "Proof"
    assert specs["APP-033_serving_size_missing_net_contents_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-034_formula_ttb_id_number_pass.pdf"].formula_approval_identifier_label == "TTB ID Number"
    assert specs["APP-036_missing_fanciful_name_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-039_brand_only_in_bottler_line_fail.pdf"].expected_status == STATUS_FAIL
    assert specs["APP-040_class_type_only_in_brand_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-041_bottler_only_in_brand_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-042_produced_and_bottled_by_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-043_ocr_damaged_warning_heading_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-044_conflicting_abv_values_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-045_conflicting_net_contents_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-046_brand_word_order_mismatch_fail.pdf"].expected_status == STATUS_FAIL
    assert specs["APP-047_wine_brand_contains_spirit_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-048_class_type_substring_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-049_product_type_brand_word_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-050_product_type_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-051_us_origin_abbreviation_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-052_centiliter_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-053_percent_alc_by_vol_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-054_stones_throw_case_pass.pdf"].fields["brand_name"] == "Stone's Throw"
    assert specs["APP-054_stones_throw_case_pass.pdf"].label_lines[0] == "STONE'S THROW"
    assert specs["APP-054_stones_throw_case_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-055_produce_of_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert specs["APP-055_produce_of_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-056_pint_net_contents_pass.pdf"].fields["net_contents"] == "500 mL"
    assert specs["APP-056_pint_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-057_plain_ounce_net_contents_pass.pdf"].fields["net_contents"] == "12 fl oz"
    assert specs["APP-057_plain_ounce_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-058_distilled_by_responsible_party_pass.pdf"].fields["bottler_producer"] == "Example Distilling Co."
    assert specs["APP-058_distilled_by_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-059_beer_product_type_first_line_pass.pdf"].fields["brand_name"] == "SUNNY FARMS"
    assert specs["APP-059_beer_product_type_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-060_blended_by_responsible_party_pass.pdf"].fields["bottler_producer"] == "Example Distilling Co."
    assert specs["APP-060_blended_by_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-061_bottled_for_responsible_party_pass.pdf"].fields["bottler_producer"] == "Example Distilling Co."
    assert specs["APP-061_bottled_for_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-062_fractional_pint_net_contents_pass.pdf"].fields["net_contents"] == "8 fl oz"
    assert specs["APP-062_fractional_pint_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-063_written_net_contents_pass.pdf"].fields["net_contents"] == "750 mL"
    assert specs["APP-063_written_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-064_alcohol_by_vol_abbreviation_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-065_degrees_proof_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-066_class_type_implies_distilled_spirits_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-067_dual_unit_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-068_imported_by_from_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert specs["APP-068_imported_by_from_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-069_alcohol_colon_by_volume_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-070_comma_thousands_net_contents_pass.pdf"].fields["net_contents"] == "1000 mL"
    assert specs["APP-070_comma_thousands_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-071_hard_cider_wine_product_type_pass.pdf"].fields["product_type"] == "WINE"
    assert specs["APP-071_hard_cider_wine_product_type_pass.pdf"].fields["class_type"] == "Hard Cider"
    assert specs["APP-071_hard_cider_wine_product_type_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-072_uk_origin_abbreviation_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-072_uk_origin_abbreviation_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-073_compact_percent_vol_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-074_ampersand_brand_pass.pdf"].fields["brand_name"] == "SMITH & SONS"
    assert specs["APP-074_ampersand_brand_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-075_company_abbreviation_pass.pdf"].fields["brand_name"] == "ACME DISTILLING CO."
    assert specs["APP-075_company_abbreviation_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-076_saint_abbreviation_brand_pass.pdf"].fields["brand_name"] == "SAINT GEORGE GIN"
    assert specs["APP-076_saint_abbreviation_brand_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-077_percent_by_volume_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-078_decimal_comma_litre_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-079_british_millilitres_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-080_scotland_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-080_scotland_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-081_republic_ireland_origin_pass.pdf"].fields["country_of_origin"] == "Ireland"
    assert specs["APP-081_republic_ireland_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-082_finished_alcohol_formula_pass.pdf"].formula_approval_alcohol_label == "Finished Alcohol Content"
    assert specs["APP-082_finished_alcohol_formula_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-083_final_product_alcohol_formula_pass.pdf"].formula_approval_alcohol_label == "Final Product Alcohol Content"
    assert specs["APP-083_final_product_alcohol_formula_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-084_distilled_in_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-084_distilled_in_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-085_brewed_in_origin_pass.pdf"].fields["country_of_origin"] == "Belgium"
    assert specs["APP-085_brewed_in_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-086_packed_by_responsible_party_pass.pdf"].fields["bottler_producer"] == "Sunset Hollow Winery"
    assert specs["APP-086_packed_by_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-087_blended_in_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-087_blended_in_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-088_distilled_and_bottled_in_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-088_distilled_and_bottled_in_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-089_distilled_matured_bottled_origin_pass.pdf"].fields["country_of_origin"] == "United Kingdom"
    assert specs["APP-089_distilled_matured_bottled_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-090_ipa_class_type_malt_pass.pdf"].fields["class_type"] == "IPA"
    assert specs["APP-090_ipa_class_type_malt_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-091_canned_by_responsible_party_pass.pdf"].fields["bottler_producer"] == "Harbor Light Brewing Co."
    assert specs["APP-091_canned_by_responsible_party_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-092_formula_id_separator_variant_pass.pdf"].fields["formula"] == "F 9200"
    assert specs["APP-092_formula_id_separator_variant_pass.pdf"].formula_approval_id == "F-9200"
    assert specs["APP-092_formula_id_separator_variant_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-093_supplemental_label_after_instructions_pass.pdf"].blank_label is True
    assert specs["APP-093_supplemental_label_after_instructions_pass.pdf"].instruction_pages_before_supplemental_label == 3
    assert specs["APP-093_supplemental_label_after_instructions_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-094_long_attachment_before_label_pass.pdf"].blank_label is True
    assert specs["APP-094_long_attachment_before_label_pass.pdf"].instruction_pages_before_supplemental_label == 13
    assert specs["APP-094_long_attachment_before_label_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-095_wine_of_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert specs["APP-095_wine_of_origin_pass.pdf"].include_formula_approval is False
    assert specs["APP-095_wine_of_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-096_multiple_formula_documents_pass.pdf"].extra_formula_approvals_before
    assert specs["APP-096_multiple_formula_documents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-097_diacritic_brand_pass.pdf"].fields["brand_name"] == "Caf\u00e9 Azul"
    assert specs["APP-097_diacritic_brand_pass.pdf"].label_lines[0] == "CAFE AZUL"
    assert specs["APP-097_diacritic_brand_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-098_decimal_comma_abv_pass.pdf"].fields["alcohol_content"] == "13.5% ABV"
    assert "13,5% vol" in specs["APP-098_decimal_comma_abv_pass.pdf"].label_lines
    assert specs["APP-098_decimal_comma_abv_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-099_decimal_comma_abv_range_pass.pdf"].fields["alcohol_content"] == "12,5-13,5% ABV"
    assert "13.5% vol" in specs["APP-099_decimal_comma_abv_range_pass.pdf"].label_lines
    assert specs["APP-099_decimal_comma_abv_range_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-100_expected_proof_range_pass.pdf"].fields["alcohol_content"] == "80-90 Proof"
    assert "90 Proof" in specs["APP-100_expected_proof_range_pass.pdf"].label_lines
    assert specs["APP-100_expected_proof_range_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-101_repeated_unit_proof_range_pass.pdf"].fields["alcohol_content"] == "80 Proof - 90 Proof"
    assert "90 Proof" in specs["APP-101_repeated_unit_proof_range_pass.pdf"].label_lines
    assert specs["APP-101_repeated_unit_proof_range_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-102_hard_seltzer_malt_pass.pdf"].fields["product_type"] == "MALT BEVERAGES"
    assert "HARD SELTZER" in specs["APP-102_hard_seltzer_malt_pass.pdf"].label_lines
    assert specs["APP-102_hard_seltzer_malt_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-103_hard_seltzer_first_line_pass.pdf"].label_lines[0] == "HARD SELTZER"
    assert specs["APP-103_hard_seltzer_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-104_bottler_legal_suffix_pass.pdf"].fields["bottler_producer"] == "North Coast Ltd."
    assert "Bottled by North Coast Limited" in specs["APP-104_bottler_legal_suffix_pass.pdf"].label_lines
    assert specs["APP-104_bottler_legal_suffix_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-105_formula_symbol_label_pass.pdf"].formula_approval_identifier_label == "Formula #"
    assert specs["APP-105_formula_symbol_label_pass.pdf"].expected_status == STATUS_PASS
    assert "Net Contents e750 mL" in specs["APP-106_estimated_net_contents_mark_pass.pdf"].label_lines
    assert specs["APP-106_estimated_net_contents_mark_pass.pdf"].expected_status == STATUS_PASS
    assert "Net Contents 750 M.L." in specs["APP-107_dotted_net_contents_unit_pass.pdf"].label_lines
    assert specs["APP-107_dotted_net_contents_unit_pass.pdf"].expected_status == STATUS_PASS
    assert "GOVERNMENT Warning" in specs["APP-108_mixed_case_warning_heading_fail.pdf"].label_lines[-1]
    assert specs["APP-108_mixed_case_warning_heading_fail.pdf"].expected_status == STATUS_FAIL
    assert "Wine Barrel Finished" in specs["APP-109_wine_descriptor_spirits_class_pass.pdf"].label_lines
    assert specs["APP-109_wine_descriptor_spirits_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-110_numeric_formula_id_pass.pdf"].fields["formula"] == "123456"
    assert specs["APP-110_numeric_formula_id_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-111_busy_artwork_pass.pdf"].artwork_style == "busy"
    assert specs["APP-111_busy_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-112_dark_reverse_artwork_pass.pdf"].artwork_style == "dark"
    assert specs["APP-112_dark_reverse_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-113_colored_warning_panel_pass.pdf"].artwork_style == "warning-panel"
    assert specs["APP-113_colored_warning_panel_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-114_busy_low_contrast_artwork_review.pdf"].artwork_style == "busy-low-contrast"
    assert specs["APP-114_busy_low_contrast_artwork_review.pdf"].expected_status == STATUS_REVIEW
    assert "45% A.B.V." in specs["APP-128_dotted_abv_crest_artwork_pass.pdf"].label_lines
    assert "5.5% v/v" in specs["APP-129_vv_textured_artwork_pass.pdf"].label_lines
    assert "A B V 50%" in specs["APP-130_spaced_abv_dark_artwork_pass.pdf"].label_lines
    assert specs["APP-133_photo_artwork_pass.pdf"].artwork_style == "photo"
    assert specs["APP-134_photo_low_contrast_artwork_review.pdf"].artwork_style == "photo-low-contrast"
    assert specs["APP-184_ornate_artwork_pass.pdf"].artwork_style == "ornate"
    assert specs["APP-184_ornate_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-185_tiny_warning_artwork_review.pdf"].artwork_style == "micro-warning"
    assert specs["APP-185_tiny_warning_artwork_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-186_champagne_of_france_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert "Champagne of France" in specs["APP-186_champagne_of_france_origin_pass.pdf"].label_lines
    assert specs["APP-186_champagne_of_france_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-187_mezcal_of_mexico_origin_pass.pdf"].fields["country_of_origin"] == "Mexico"
    assert "Mezcal of Mexico" in specs["APP-187_mezcal_of_mexico_origin_pass.pdf"].label_lines
    assert specs["APP-187_mezcal_of_mexico_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-188_modified_hard_cider_first_line_pass.pdf"].fields["class_type"] == "Hard Cider"
    assert "APPLE HARD CIDER" in specs["APP-188_modified_hard_cider_first_line_pass.pdf"].label_lines
    assert specs["APP-188_modified_hard_cider_first_line_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-189_barleywine_ale_malt_pass.pdf"].fields["class_type"] == "Barleywine Ale"
    assert "BARLEYWINE ALE" in specs["APP-189_barleywine_ale_malt_pass.pdf"].label_lines
    assert specs["APP-189_barleywine_ale_malt_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-190_tequila_barrel_aged_beer_pass.pdf"].fields["class_type"] == "Barrel Aged Beer"
    assert "TEQUILA BARREL AGED BEER" in specs["APP-190_tequila_barrel_aged_beer_pass.pdf"].label_lines
    assert specs["APP-190_tequila_barrel_aged_beer_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-191_split_front_back_panels_pass.pdf"].split_panel_label is True
    assert specs["APP-191_split_front_back_panels_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-192_split_panel_conflicting_abv_review.pdf"].split_panel_label is True
    assert "Alcohol: 40% by Volume" in specs["APP-192_split_panel_conflicting_abv_review.pdf"].label_lines
    assert specs["APP-192_split_panel_conflicting_abv_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-193_metallic_foil_artwork_pass.pdf"].artwork_style == "metallic-foil"
    assert specs["APP-193_metallic_foil_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-194_dense_illustration_artwork_review.pdf"].artwork_style == "dense-illustration"
    assert specs["APP-194_dense_illustration_artwork_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-195_stylized_font_artwork_pass.pdf"].artwork_style == "stylized"
    assert specs["APP-195_stylized_font_artwork_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-196_curved_distorted_text_review.pdf"].artwork_style == "curved-distorted"
    assert specs["APP-196_curved_distorted_text_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-197_embossed_low_contrast_review.pdf"].artwork_style == "embossed"
    assert specs["APP-197_embossed_low_contrast_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-198_partial_glare_scan_review.pdf"].artwork_style == "glare"
    assert specs["APP-198_partial_glare_scan_review.pdf"].expected_status == STATUS_REVIEW
    assert specs["APP-115_sake_wine_class_pass.pdf"].fields["class_type"] == "Sake"
    assert specs["APP-115_sake_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-116_vermouth_wine_class_pass.pdf"].fields["class_type"] == "Vermouth"
    assert specs["APP-116_vermouth_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-117_sherry_wine_class_pass.pdf"].fields["class_type"] == "Sherry"
    assert specs["APP-117_sherry_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-118_champagne_wine_class_pass.pdf"].fields["class_type"] == "Champagne"
    assert specs["APP-118_champagne_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-119_port_wine_class_pass.pdf"].fields["class_type"] == "Port"
    assert specs["APP-119_port_wine_class_pass.pdf"].expected_status == STATUS_PASS
    assert "0LD T0M GIN" in specs["APP-153_ocr_character_confusion_brand_review.pdf"].label_lines
    assert specs["APP-153_ocr_character_confusion_brand_review.pdf"].expected_status == STATUS_REVIEW


def test_sample_generator_uses_real_source_form_when_available(sample_paths: list[Path]) -> None:
    source_form = Path("docs/source/f510031.pdf")
    if not source_form.exists():
        return

    document = fitz.open(sample_paths[0])
    try:
        text = document[0].get_text("text")
    finally:
        document.close()

    assert "DEPARTMENT OF THE TREASURY" in text
    assert "ALCOHOL AND TOBACCO TAX AND TRADE BUREAU" in text
    assert "APPLICATION DATA SUMMARY" in text


def test_sample_form_mapping_keeps_product_and_applicant_regions_separate() -> None:
    assert FORM_REGIONS["product_type"].x1 <= FORM_REGIONS["applicant_name_address"].x0


def _expected_status(spec) -> str:
    if tesseract_available():
        return spec.expected_status
    return spec.expected_status_without_ocr or spec.expected_status
