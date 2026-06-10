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
| `APP-069_alcohol_colon_by_volume_pass.pdf` | Pass | Pass | Label states alcohol content with colon wording, Alcohol: 45% by Volume. |
| `APP-070_comma_thousands_net_contents_pass.pdf` | Pass | Pass | Label states net contents with a comma thousands separator, 1,000 mL. |
| `APP-071_hard_cider_wine_product_type_pass.pdf` | Pass | Pass | Wine product type is supported by hard-cider label and class/type wording. |
| `APP-072_uk_origin_abbreviation_pass.pdf` | Pass | Pass | Imported wine origin uses U.K. abbreviation for application country United Kingdom. |
| `APP-073_compact_percent_vol_pass.pdf` | Pass | Pass | Label states alcohol content with compact percent-vol wording. |
| `APP-074_ampersand_brand_pass.pdf` | Pass | Pass | Brand ampersand in the application matches AND on the label as a harmless text variation. |
| `APP-075_company_abbreviation_pass.pdf` | Pass | Pass | Brand and bottler Co. abbreviations match Company on the label as harmless legal-suffix variations. |
| `APP-076_saint_abbreviation_brand_pass.pdf` | Pass | Pass | Brand Saint abbreviation in the label matches Saint in the application as a harmless word variation. |
| `APP-077_percent_by_volume_pass.pdf` | Pass | Pass | Label states alcohol content with percent-by-volume shorthand. |
| `APP-078_decimal_comma_litre_pass.pdf` | Pass | Pass | Label states net contents as decimal-comma litres. |
| `APP-079_british_millilitres_pass.pdf` | Pass | Pass | Label states net contents with British millilitres spelling. |
| `APP-080_scotland_origin_pass.pdf` | Pass | Pass | Imported origin names Scotland while the application country is United Kingdom. |
| `APP-081_republic_ireland_origin_pass.pdf` | Pass | Pass | Imported origin names Republic of Ireland while the application country is Ireland. |
| `APP-082_finished_alcohol_formula_pass.pdf` | Pass | Pass | Formula support states final ABV as Finished Alcohol Content. |
| `APP-083_final_product_alcohol_formula_pass.pdf` | Pass | Pass | Formula support states final proof as Final Product Alcohol Content. |
| `APP-084_distilled_in_origin_pass.pdf` | Pass | Pass | Imported spirits origin is stated as Distilled in Scotland for a United Kingdom application country. |
| `APP-085_brewed_in_origin_pass.pdf` | Pass | Pass | Imported malt beverage origin is stated as Brewed in Belgium. |
| `APP-086_packed_by_responsible_party_pass.pdf` | Pass | Pass | Wine label uses Packed by as responsible-party wording. |
| `APP-087_blended_in_origin_pass.pdf` | Pass | Pass | Imported spirits origin is stated as Blended in Scotland for a United Kingdom application country. |
| `APP-088_distilled_and_bottled_in_origin_pass.pdf` | Pass | Pass | Imported spirits origin is stated as Distilled and bottled in Scotland for a United Kingdom application country. |
| `APP-089_distilled_matured_bottled_origin_pass.pdf` | Pass | Pass | Imported spirits origin is stated as Distilled, matured and bottled in Scotland for a United Kingdom application country. |
| `APP-090_ipa_class_type_malt_pass.pdf` | Pass | Pass | Malt beverage product type is inferred from IPA class/type shorthand. |
| `APP-091_canned_by_responsible_party_pass.pdf` | Pass | Pass | Malt beverage label uses Brewed and canned by as responsible-party wording. |
| `APP-092_formula_id_separator_variant_pass.pdf` | Pass | Pass | Application Formula ID uses a space while the submitted formula approval uses a hyphenated ID. |
| `APP-093_supplemental_label_after_instructions_pass.pdf` | Pass | Pass | Page-one label area is blank, attached instructions are skipped, and a later supplemental label page is verified. |
| `APP-094_long_attachment_before_label_pass.pdf` | Pass | Pass | Supplemental label appears after more than twelve attached instruction pages and still verifies. |
| `APP-095_wine_of_origin_pass.pdf` | Pass | Pass | Imported wine states origin as Wine of France, a product-style country-of-origin statement. |
| `APP-096_multiple_formula_documents_pass.pdf` | Pass | Pass | Package includes an unrelated approved formula before the matching Formula ID; only the matching formula document is used. |
| `APP-097_diacritic_brand_pass.pdf` | Pass | Pass | Application brand contains a diacritic that is absent from label text and still matches after normalization. |
| `APP-098_decimal_comma_abv_pass.pdf` | Pass | Pass | Imported wine label uses decimal-comma alcohol content wording and still matches expected ABV. |
| `APP-099_decimal_comma_abv_range_pass.pdf` | Pass | Pass | Application alcohol-content range uses decimal commas and still matches the high-end label ABV. |
| `APP-100_expected_proof_range_pass.pdf` | Pass | Pass | Application alcohol-content range is stated in proof and is converted to ABV before label comparison. |
| `APP-101_repeated_unit_proof_range_pass.pdf` | Pass | Pass | Application alcohol-content proof range repeats the proof unit on both sides and still matches the label. |
| `APP-102_hard_seltzer_malt_pass.pdf` | Pass | Pass | Malt beverage hard seltzer label uses hard-seltzer wording instead of beer-style terms. |
| `APP-103_hard_seltzer_first_line_pass.pdf` | Pass | Pass | Malt beverage hard seltzer label states product type as the first line before the brand. |
| `APP-104_bottler_legal_suffix_pass.pdf` | Pass | Pass | Responsible-party legal suffix Ltd. in the application matches Limited on the label. |
| `APP-105_formula_symbol_label_pass.pdf` | Pass | Pass | Formula support identifies the approval as Formula # instead of Formula ID. |
| `APP-106_estimated_net_contents_mark_pass.pdf` | Pass | Pass | Label prefixes net contents with a compact estimated quantity mark, e750 mL. |
| `APP-107_dotted_net_contents_unit_pass.pdf` | Pass | Pass | Label states net contents with dotted metric unit styling, 750 M.L. |
| `APP-108_mixed_case_warning_heading_fail.pdf` | Fail | Fail | Government warning statement is exact, but the heading is mixed case instead of all caps. |
| `APP-109_wine_descriptor_spirits_class_pass.pdf` | Pass | Pass | Distilled spirits class/type should control when wine appears only as a finish descriptor. |
| `APP-110_numeric_formula_id_pass.pdf` | Pass | Pass | Item 9 and formula support use a numeric TTB Formula ID instead of a letter-prefixed ID. |
| `APP-111_busy_artwork_pass.pdf` | Pass | Needs Review | Busy color artwork with decorative shapes should still pass when required text remains readable. |
| `APP-112_dark_reverse_artwork_pass.pdf` | Pass | Needs Review | Dark color artwork with reversed/light text should pass when OCR can read the label. |
| `APP-113_colored_warning_panel_pass.pdf` | Pass | Needs Review | Color-artwork wine label keeps the government warning inside a colored panel and should still pass. |
| `APP-114_busy_low_contrast_artwork_review.pdf` | Needs Review | Needs Review | Busy low-contrast artwork should not be failed as missing fields; it should require review for OCR quality. |
| `APP-115_sake_wine_class_pass.pdf` | Pass | Pass | Sake is a wine-from-other-agricultural-products class under 27 CFR 4.21, so a wine application can pass without the literal word WINE on the label. |
| `APP-116_vermouth_wine_class_pass.pdf` | Pass | Pass | Vermouth is a type of aperitif wine under 27 CFR 4.21 and should satisfy wine product-type verification. |
| `APP-117_sherry_wine_class_pass.pdf` | Pass | Pass | Sherry is a dessert wine type under 27 CFR 4.21 and should satisfy wine product-type verification. |
| `APP-118_champagne_wine_class_pass.pdf` | Pass | Pass | Champagne is a sparkling grape wine type under 27 CFR 4.21 and should satisfy wine product-type verification. |
| `APP-119_port_wine_class_pass.pdf` | Pass | Pass | Port is a dessert wine type under 27 CFR 4.21 and should satisfy wine product-type verification without confusing Porter malt-beverage labels. |
| `APP-120_formula_not_required_pass.pdf` | Pass | Pass | Item 9 uses FORMULA NOT REQUIRED wording rather than NO FORMULA REQUIRED; no formula approval page should be required. |
| `APP-121_import_country_conflict_review.pdf` | Needs Review | Needs Review | Imported label contains both the expected country and a conflicting origin statement, so country of origin requires review. |
| `APP-122_product_type_conflict_review.pdf` | Needs Review | Needs Review | Label contains both expected and conflicting explicit product-type statements, so product type requires review. |
| `APP-123_class_type_conflict_review.pdf` | Needs Review | Needs Review | Label contains expected and conflicting Class/Type statements, so class/type requires review. |
| `APP-124_bottler_conflict_review.pdf` | Needs Review | Needs Review | Label contains expected and conflicting Bottled by statements, so responsible-party text requires review. |
| `APP-125_comma_responsible_party_pass.pdf` | Pass | Pass | Label uses comma-separated responsible-party actions before By and should still match the application entity. |
| `APP-126_pre_import_approval_pass.pdf` | Pass | Pass | Item 9 references a pre-import approval letter in the same PDF package, and the approved alcohol content matches the label. |
| `APP-127_rejected_formula_review.pdf` | Needs Review | Needs Review | Matching formula support has Status: Rejected, so final alcohol content cannot be used as approved expected evidence. |
| `APP-128_dotted_abv_crest_artwork_pass.pdf` | Pass | Needs Review | Color crest-style artwork uses dotted A.B.V. alcohol-content wording and should still verify. |
| `APP-129_vv_textured_artwork_pass.pdf` | Pass | Needs Review | Textured color artwork uses v/v alcohol-content wording and should still verify. |
| `APP-130_spaced_abv_dark_artwork_pass.pdf` | Pass | Needs Review | Dark color artwork uses OCR-spaced A B V alcohol-content wording and should still verify. |
| `APP-131_formula_alc_vol_heading_pass.pdf` | Pass | Pass | Formula support states final alcohol with the abbreviated heading Finished Product Alc/Vol. |
| `APP-132_scotch_whisky_origin_pass.pdf` | Pass | Pass | Imported spirits origin is satisfied by the protected Scotch Whisky designation without a separate Product of statement. |
| `APP-133_photo_artwork_pass.pdf` | Pass | Needs Review | Photo-like color artwork with scenic background and readable panels should still verify. |
| `APP-134_photo_low_contrast_artwork_review.pdf` | Needs Review | Needs Review | Photo-like low-contrast artwork should require review for OCR quality instead of failing as missing text. |
| `APP-135_ambiguous_product_type_checkboxes_review.pdf` | Needs Review | Needs Review | Application has multiple Item 5 product-type checkboxes selected, so expected product type is ambiguous and must not be guessed from the label. |
| `APP-136_ambiguous_import_checkboxes_review.pdf` | Needs Review | Needs Review | Application has both Domestic and Imported Item 3 checkboxes selected, so source of product is ambiguous even though country evidence is present. |
| `APP-137_formula_of_the_finished_product_pass.pdf` | Pass | Pass | Formula support states final alcohol with the official-style Alcohol Content of the Finished Product wording. |
| `APP-138_flavoring_percent_with_abv_pass.pdf` | Pass | Pass | Non-alcohol flavoring percent-by-volume text must not conflict with the real label ABV statement. |
| `APP-139_flavoring_percent_missing_abv_review.pdf` | Needs Review | Needs Review | Non-alcohol flavoring percent-by-volume text alone should not be treated as an ABV mismatch; missing actual ABV requires review. |
| `APP-140_formula_row_number_pass.pdf` | Pass | Pass | Formula support has an OCR-style row number before the low/high final-alcohol values and should still verify. |
| `APP-141_domestic_foreign_origin_review.pdf` | Needs Review | Needs Review | Application is domestic/no imported origin, but the label contains foreign origin wording and should require review. |
| `APP-142_domestic_imported_from_origin_review.pdf` | Needs Review | Needs Review | Application is domestic/no imported origin, but the label contains imported-from origin wording and should require review. |
| `APP-143_dual_proof_abv_statement_pass.pdf` | Pass | Pass | Label states proof immediately before ABV; the parser must not reread the ABV number as Proof 45. |
| `APP-144_lager_beer_first_line_pass.pdf` | Pass | Pass | Malt beverage label states LAGER BEER before the brand; this should be treated as an explicit product-type statement. |
| `APP-145_brand_number_symbol_pass.pdf` | Pass | Pass | Brand number marker in the application uses No. while the label uses #; this should pass as harmless formatting variation. |
| `APP-146_finished_product_proof_formula_pass.pdf` | Pass | Pass | Matching formula support states Finished Product Proof rather than Alcohol Content of Finished Product; proof must convert to ABV for label comparison. |
| `APP-147_mead_wine_class_pass.pdf` | Pass | Pass | Wine application uses Mead as the label class/type rather than the word WINE; this should still satisfy product type. |
| `APP-148_flavored_malt_beverage_first_line_pass.pdf` | Pass | Pass | Malt application states FLAVORED MALT BEVERAGE before the brand; this should be treated as explicit product-type evidence. |
| `APP-149_superseded_formula_review.pdf` | Needs Review | Needs Review | Matching formula support says Status: Approved - Superseded, so it should not be used as current approved expected evidence. |
| `APP-150_chardonnay_varietal_wine_pass.pdf` | Pass | Pass | Wine label uses the grape varietal Chardonnay as the type designation without a separate WINE statement, which should still satisfy product type. |
| `APP-151_bottled_exclusively_for_pass.pdf` | Pass | Pass | Responsible-party wording may include a modifier such as Bottled exclusively for before the expected entity. |
| `APP-152_distilled_spirits_specialty_class_pass.pdf` | Pass | Pass | Explicit Class/Type values may contain product-type words such as Distilled Spirits Specialty and should still verify. |
| `APP-153_ocr_character_confusion_brand_review.pdf` | Needs Review | Needs Review | OCR-style zero/letter substitutions in required brand text should be treated as a similar-but-not-certain Needs Review case. |
| `APP-154_distributed_by_only_review.pdf` | Needs Review | Needs Review | Distribution-only wording should not satisfy the expected bottler/producer responsible-party statement. |
| `APP-155_vodka_cocktail_class_product_type_pass.pdf` | Pass | Pass | Distilled spirits specialty/cocktail class-type text can satisfy product type without a separate DISTILLED SPIRITS line. |
| `APP-156_bottled_in_origin_review.pdf` | Needs Review | Needs Review | Imported country of origin should need review when the label has only bottling-location wording, not clear origin wording. |
| `APP-157_hyphenated_warning_heading_fail.pdf` | Fail | Fail | Readable labels with hyphenated government-warning headings should fail strict canonical-heading validation. |
| `APP-158_multipack_net_contents_pass.pdf` | Pass | Pass | Multipack net-contents wording such as 4 x 50 mL should normalize to the total package volume. |
| `APP-159_formula_target_abv_pass.pdf` | Pass | Pass | Formula support states final alcohol with Target ABV shorthand and should verify against the label. |
| `APP-160_mfg_made_bottled_origin_pass.pdf` | Pass | Pass | Imported origin can be stated as Made and bottled in Italy, and abbreviated Mfg. by wording should satisfy responsible-party evidence. |
| `APP-161_formula_bottling_proof_pass.pdf` | Pass | Pass | Formula support states final packaged strength as Bottling Proof and should verify against the label proof statement. |
| `APP-162_dash_multipack_net_contents_pass.pdf` | Pass | Pass | Dash-separated multipack net-contents wording such as 4-50 mL should normalize to the total package volume. |
| `APP-163_colon_warning_heading_fail.pdf` | Fail | Fail | Readable government warning heading with colon punctuation between GOVERNMENT and WARNING should fail strict canonical-heading validation. |
| `APP-164_hyphen_pack_net_contents_pass.pdf` | Pass | Pass | Hyphenated pack net-contents wording such as 4-pack of 12 fl oz cans should normalize to total package volume. |
| `APP-165_slash_multipack_net_contents_pass.pdf` | Pass | Pass | Slash-separated multipack net-contents wording such as 4/12 fl oz cans should normalize to total package volume rather than a fractional ounce. |
| `APP-166_imported_bottled_distributed_by_pass.pdf` | Pass | Pass | Responsible-party wording can include distribution when it is combined with valid imported/bottled actions. |
| `APP-167_colon_bottled_by_pass.pdf` | Pass | Pass | Colon punctuation after Bottled by should still satisfy responsible-party evidence. |
| `APP-168_percent_alcohol_volume_pass.pdf` | Pass | Pass | Percent Alcohol Vol. wording should normalize as ABV. |
| `APP-169_slash_alcohol_volume_pass.pdf` | Pass | Pass | Slash-separated Alcohol/Vol. wording should normalize as ABV. |
| `APP-170_brewed_canned_origin_pass.pdf` | Pass | Pass | Imported malt beverage origin can be stated as Brewed and canned in Belgium. |
| `APP-171_class_type_first_liqueur_pass.pdf` | Pass | Pass | A first-line Class/Type statement can satisfy distilled spirits product type when no separate DISTILLED SPIRITS line appears. |
| `APP-172_wine_varietal_appellation_missing_review.pdf` | Needs Review | Needs Review | Application supplies grape varietal and appellation values, but the label is missing Merlot and California, so wine-only fields need review. |

These PDFs are synthetic completed applications. When `docs/source/f510031.pdf` is available locally, the generator fills the real TTB form template. Otherwise it falls back to a controlled TTB-like one-page layout.
