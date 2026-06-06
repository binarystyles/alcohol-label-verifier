# Form Mapping

The prototype uses normalized page coordinates in `src/form_mapping.py` so regions scale with page size. These regions are tuned around TTB F 5100.31 page one and are intended to be easy to adjust. Scanned application image files are converted to an in-memory PDF page first, then the same normalized regions are applied.

| TTB item | Extracted field | Verification use |
| --- | --- | --- |
| Item 4 | `serial_number` | Application identifier and result table reference. |
| Item 5 | `product_type` | Compared to label evidence for Wine, Distilled Spirits, or Malt Beverages. |
| Item 6 | `brand_name` | Required critical check against label brand text. |
| Item 7 | `fanciful_name` | Optional check when supplied. |
| Item 8 | `applicant_name_address` | Application context and possible bottler/producer support. |
| Item 8a | `mailing_address` | Extracted for reviewer context. |
| Item 9 | `formula` | Extracted for reviewer context. |
| Item 10 | `grape_varietals` | Extracted for reviewer context for wine applications. |
| Item 11 | `wine_appellation` | Extracted for reviewer context and possible label comparison. |
| Item 12 | `phone` | Extracted for reviewer context. |
| Item 13 | `email` | Extracted for reviewer context. |
| Item 14 | `application_type` | Extracted for reviewer context. |
| Item 15 | `item_15` | Checked against label/container text when supplied; missing evidence becomes Needs Review. |
| Lower page-one label area | label OCR text | Evidence source for all label checks. |

The blank TTB F 5100.31 form does not always expose class/type, alcohol content, net contents, bottler/producer, country of origin, or imported status as simple fields. For this reason, the extractor also looks for an explicit application-data summary block inside the completed PDF. That block is treated as application/package metadata, not label evidence.

When `docs/source/f510031.pdf` is available locally, the sample generator fills the real TTB form template and adds an invisible application-data summary text layer for expected values that are not first-page fields. If the source form is absent, it falls back to a controlled TTB-like one-page layout.
