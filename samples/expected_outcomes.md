# Expected Sample Outcomes

| File | Expected with OCR | Expected without OCR | Purpose |
| --- | --- | --- | --- |
| `APP-001_old_tom_pass.pdf` | Pass | Pass | Fully passing label with matching approved formula alcohol content, application summary, and affixed label text. |
| `APP-002_stones_throw_variation.pdf` | Pass | Pass | Brand punctuation/case variation should not fail. |
| `APP-003_wrong_abv.pdf` | Fail | Fail | Approved formula expects 45% ABV but label shows 40% ABV. |
| `APP-004_bad_warning.pdf` | Fail | Fail | Warning heading is title case and the statement is materially altered. |
| `APP-005_low_quality_rotated.pdf` | Needs Review | Needs Review | Rasterized low-quality rotated label should require human review if OCR is uncertain. |
| `APP-006_missing_label_area.pdf` | Needs Review | Needs Review | Application data is present but the affixed label area is blank. |
| `APP-007_artwork_vodka_pass.pdf` | Pass | Needs Review | High-contrast raster label with color artwork should pass when OCR is available. |
| `APP-008_artwork_brand_mismatch_fail.pdf` | Fail | Needs Review | Color-artwork label has a materially different brand name. |
| `APP-009_artwork_wrong_net_contents_fail.pdf` | Fail | Needs Review | Color-artwork label shows a different net contents value. |
| `APP-010_artwork_title_case_warning_fail.pdf` | Fail | Needs Review | Color-artwork label has a title-case and altered government warning. |
| `APP-011_artwork_missing_warning_fail.pdf` | Fail | Needs Review | Color-artwork label omits the required government warning. |
| `APP-012_artwork_low_contrast_review.pdf` | Needs Review | Needs Review | Color-artwork label is intentionally low contrast and should require review. |
| `APP-013_missing_formula_support_review.pdf` | Needs Review | Needs Review | Item 9 has a Formula ID but the package lacks the matching formula approval page. |
| `APP-014_formula_range_pass.pdf` | Pass | Pass | Approved formula final alcohol range covers the label ABV. |
| `APP-015_formula_range_fail.pdf` | Fail | Fail | Approved formula final alcohol range does not cover the label ABV. |
| `APP-016_bourbon_proof_artwork_pass.pdf` | Pass | Needs Review | Color-artwork bourbon label uses proof rather than percent ABV. |
| `APP-017_wine_artwork_pass.pdf` | Pass | Needs Review | Color-artwork wine label exercises wine product type and appellation context. |
| `APP-018_malt_artwork_pass.pdf` | Pass | Needs Review | Color-artwork malt beverage label exercises malt product type and fl oz normalization. |
| `APP-019_import_country_missing_review.pdf` | Needs Review | Needs Review | Imported product has no extracted country of origin. |
| `APP-020_item15_missing_review.pdf` | Needs Review | Needs Review | Item 15 container text is supplied in the application but not found on the label. |
| `APP-021_apostrophe_artwork_pass.pdf` | Pass | Needs Review | Color-artwork label confirms apostrophe-insensitive brand matching. |
| `APP-022_artwork_wrong_bottler_review.pdf` | Needs Review | Needs Review | Color-artwork label has a bottler/producer difference that should be reviewed. |
| `APP-023_no_formula_required_pass.pdf` | Pass | Pass | Item 9 states no formula is required and the label still matches application alcohol content. |
| `APP-024_import_country_artwork_pass.pdf` | Pass | Needs Review | Imported color-artwork label includes the expected country of origin. |
| `APP-025_import_country_missing_on_label_review.pdf` | Needs Review | Needs Review | Imported application has an expected country of origin that is not clearly on the label. |
| `APP-026_missing_expected_brand_review.pdf` | Needs Review | Needs Review | Required brand value is missing from the application extraction and must not be invented from label OCR. |
| `APP-027_product_type_mismatch_fail.pdf` | Fail | Fail | Readable label shows a different product type than the completed application. |
| `APP-028_formula_document_missing_final_alcohol_review.pdf` | Needs Review | Needs Review | Matching formula approval document is present but lacks extractable final alcohol content. |
| `APP-029_formula_id_prefix_mismatch_review.pdf` | Needs Review | Needs Review | Formula approval page has a longer prefix-sharing ID and must not satisfy the Item 9 Formula ID. |
| `APP-030_wine_cask_spirits_pass.pdf` | Pass | Needs Review | Distilled spirits label mentions wine as a cask-finish descriptor without changing product type. |
| `APP-031_tequila_agave_missing_abv_review.pdf` | Needs Review | Needs Review | Label has a non-alcohol percentage but no readable ABV/proof statement. |
| `APP-032_low_proof_liqueur_pass.pdf` | Pass | Pass | Approved formula gives final alcohol as 40 proof, which should normalize to 20% ABV. |
| `APP-033_serving_size_missing_net_contents_review.pdf` | Needs Review | Needs Review | Label has a serving-size volume but no clear net contents statement, so net contents need review rather than a false mismatch. |
| `APP-034_formula_ttb_id_number_pass.pdf` | Pass | Pass | Formula support uses a TTB ID Number label instead of a TTB Formula ID label. |
| `APP-035_alc_by_vol_order_pass.pdf` | Pass | Pass | Label states alcohol content as Alc. value by Vol., which should normalize as ABV. |
| `APP-036_missing_fanciful_name_review.pdf` | Needs Review | Needs Review | Application supplies a fanciful name, but the label does not clearly show it. |
| `APP-037_proof_before_value_pass.pdf` | Pass | Pass | Label states proof before the value, which should normalize to ABV. |
| `APP-038_alcohol_by_volume_order_pass.pdf` | Pass | Pass | Label states alcohol value before by-volume wording, which should normalize as ABV. |
| `APP-039_brand_only_in_bottler_line_fail.pdf` | Fail | Fail | Expected brand appears only in the bottler line while the primary brand is materially different. |
| `APP-040_class_type_only_in_brand_review.pdf` | Needs Review | Needs Review | Class/type value appears only inside the brand name and is not clearly stated as class/type. |
| `APP-041_bottler_only_in_brand_review.pdf` | Needs Review | Needs Review | Expected bottler/producer appears as brand text only, with no responsible-party statement. |
| `APP-042_produced_and_bottled_by_pass.pdf` | Pass | Pass | Responsible-party statement uses combined produced-and-bottled wording. |
| `APP-043_ocr_damaged_warning_heading_review.pdf` | Needs Review | Needs Review | Warning statement is close to canonical, but the all-caps heading has OCR-like character damage. |
| `APP-044_conflicting_abv_values_review.pdf` | Needs Review | Needs Review | Label contains both matching and conflicting alcohol-content values. |
| `APP-045_conflicting_net_contents_review.pdf` | Needs Review | Needs Review | Label contains both matching and conflicting net-contents values. |
| `APP-046_brand_word_order_mismatch_fail.pdf` | Fail | Fail | Brand tokens are reordered, which should not pass as a harmless brand variation. |
| `APP-047_wine_brand_contains_spirit_pass.pdf` | Pass | Pass | Wine brand contains the word Spirit, but explicit wine label text controls product-type matching. |
| `APP-048_class_type_substring_review.pdf` | Needs Review | Needs Review | Expected class/type Gin appears only as a word fragment inside Ginger and must not pass. |
| `APP-049_product_type_brand_word_review.pdf` | Needs Review | Needs Review | Product-type word appears only in the brand while explicit wine/class wording is missing. |
| `APP-050_product_type_first_line_pass.pdf` | Pass | Pass | Explicit product type appears before the brand and should still verify. |
| `APP-051_us_origin_abbreviation_pass.pdf` | Pass | Pass | Imported origin uses U.S.A. abbreviation for application country United States. |
| `APP-052_centiliter_net_contents_pass.pdf` | Pass | Pass | Label states net contents in centiliters, equivalent to the application 750 mL value. |
| `APP-053_percent_alc_by_vol_pass.pdf` | Pass | Pass | Label states alcohol content with the common percent Alc. by Vol. wording. |
| `APP-054_stones_throw_case_pass.pdf` | Pass | Pass | Assignment example: application brand Stone's Throw matches label brand STONE'S THROW despite capitalization. |
| `APP-055_produce_of_origin_pass.pdf` | Pass | Pass | Imported wine uses common Produce of France origin wording. |
| `APP-056_pint_net_contents_pass.pdf` | Pass | Pass | Label states net contents as a compound pint and fluid-ounce amount equivalent to 500 mL. |
| `APP-057_plain_ounce_net_contents_pass.pdf` | Pass | Pass | Label states net contents as plain 12 OZ, equivalent to the application 12 fl oz value. |
| `APP-058_distilled_by_responsible_party_pass.pdf` | Pass | Pass | Distilled spirits label uses Distilled by as responsible-party wording. |
| `APP-059_beer_product_type_first_line_pass.pdf` | Pass | Pass | Malt beverage label puts BEER before a brand that does not itself contain beer-style product words. |
| `APP-060_blended_by_responsible_party_pass.pdf` | Pass | Pass | Distilled spirits label uses Blended by as responsible-party wording. |
| `APP-061_bottled_for_responsible_party_pass.pdf` | Pass | Pass | Distilled spirits label uses Bottled for as responsible-party wording. |
| `APP-062_fractional_pint_net_contents_pass.pdf` | Pass | Pass | Label states net contents as fractional 1/2 Pint, equivalent to the application 8 fl oz value. |
| `APP-063_written_net_contents_pass.pdf` | Pass | Pass | Label spells out net contents as Seven Hundred Fifty Milliliters, equivalent to the application 750 mL value. |
| `APP-064_alcohol_by_vol_abbreviation_pass.pdf` | Pass | Pass | Label states alcohol content as Alcohol 45% by Vol., which should normalize as ABV. |
| `APP-065_degrees_proof_pass.pdf` | Pass | Pass | Label states proof with degrees wording, which should normalize to 45% ABV. |
| `APP-066_class_type_implies_distilled_spirits_pass.pdf` | Pass | Pass | Distilled spirits product type is supported by a clear Gin class/type statement even without the literal DISTILLED SPIRITS phrase. |
| `APP-067_dual_unit_net_contents_pass.pdf` | Pass | Pass | Label states both metric and rounded U.S. customary net contents for the same 750 mL package. |
| `APP-068_imported_by_from_origin_pass.pdf` | Pass | Pass | Imported wine origin is stated as Imported by Example Imports LLC from France. |

These PDFs are synthetic completed applications. When `docs/source/f510031.pdf` is available locally, the generator fills the real TTB form template. Otherwise it falls back to a controlled TTB-like one-page layout.
