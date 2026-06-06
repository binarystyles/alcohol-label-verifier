# Expected Sample Outcomes

| File | Expected status | Purpose |
| --- | --- | --- |
| `APP-001_old_tom_pass.pdf` | Pass | Fully passing label with matching application summary and affixed label text. |
| `APP-002_stones_throw_variation.pdf` | Pass | Brand punctuation/case variation should not fail. |
| `APP-003_wrong_abv.pdf` | Fail | Application expects 45% ABV but label shows 40% ABV. |
| `APP-004_bad_warning.pdf` | Fail | Warning heading is title case and the statement is materially altered. |
| `APP-005_low_quality_rotated.pdf` | Needs Review | Rasterized low-quality rotated label should require human review if OCR is uncertain. |
| `APP-006_missing_label_area.pdf` | Needs Review | Application data is present but the affixed label area is blank. |

These PDFs are synthetic completed applications. They use the TTB F 5100.31 visual base when `docs/source/f510031.pdf` is present; otherwise the generator creates a simplified form with the same field concepts.
