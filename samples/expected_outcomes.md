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

These PDFs are synthetic completed applications. When `docs/source/f510031.pdf` is available locally, the generator fills the real TTB form template. Otherwise it falls back to a controlled TTB-like one-page layout.
