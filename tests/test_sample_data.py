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
    assert len(artwork_specs) >= 10
    assert any(spec.expected_status == STATUS_PASS for spec in artwork_specs)
    assert any(spec.expected_status == STATUS_FAIL for spec in artwork_specs)
    assert any(spec.expected_status == STATUS_REVIEW for spec in artwork_specs)


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
    assert specs["APP-023_no_formula_required_pass.pdf"].include_formula_approval is False
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
    assert specs["APP-054_stones_throw_case_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-055_produce_of_origin_pass.pdf"].fields["country_of_origin"] == "France"
    assert specs["APP-055_produce_of_origin_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-056_pint_net_contents_pass.pdf"].fields["net_contents"] == "500 mL"
    assert specs["APP-056_pint_net_contents_pass.pdf"].expected_status == STATUS_PASS
    assert specs["APP-057_plain_ounce_net_contents_pass.pdf"].fields["net_contents"] == "12 fl oz"
    assert specs["APP-057_plain_ounce_net_contents_pass.pdf"].expected_status == STATUS_PASS


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
