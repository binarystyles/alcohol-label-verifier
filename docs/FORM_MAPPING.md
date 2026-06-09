# Form Mapping

The prototype uses normalized page coordinates in `src/form_mapping.py` so regions scale with page size. These regions are tuned around TTB F 5100.31 page one and are intended to be easy to adjust. Scanned application image files are converted to an in-memory PDF page first, then the same normalized regions are applied.

Sources reviewed: the TTB Forms page lists current TTB F 5100.31 as `Application for and Certification/Exemption of Label/Bottle Approval (04/2023)`, and the linked form PDF includes the page-one fields and instructions used for this mapping. TTB's formula approval basics guidance states that the Formula ID is needed before applying for label approval and that final alcohol content is part of the formula application information. TTB's distilled spirits, wine, and malt beverage example formula pages show Formulas Online entries with a Yield Summary section and an `Alcohol Content of Finished Product` row.

| TTB item | Extracted field | Verification use |
| --- | --- | --- |
| Item 4 | `serial_number` | Application identifier and result table reference. |
| Item 5 | `product_type` | Compared to label evidence for Wine, Distilled Spirits, or Malt Beverages. A readable, different product type is a critical mismatch. Explicit `DISTILLED SPIRITS` and `MALT BEVERAGE(S)` phrases are prioritized over incidental descriptors such as `Wine Cask Finish`. |
| Item 6 | `brand_name` | Required critical check against label brand text. |
| Item 7 | `fanciful_name` | Optional check when supplied. |
| Item 8 | `applicant_name_address` | Application context and possible bottler/producer support. |
| Item 8a | `mailing_address` | Extracted for reviewer context. |
| Item 9 | `formula` | Formula ID/reference, such as a TTB Formula ID, TTB ID number, lab number, pre-import approval reference, or no-formula-required note. When a Formula ID is present, the extractor looks for an exact normalized matching formula approval/source document inside the same uploaded PDF package and derives expected `alcohol_content` from that matched document's `Alcohol Content of Finished Product` or final-alcohol-content field. Prefix-sharing IDs, such as `F-2900` and `F-29001`, are not treated as matches. Low/high ranges are preserved for label comparison. Malt beverage rows for `Alcohol From Flavors` and `Alcohol From Base` are ignored as the expected label ABV source. Missing matching formula support, or matched support with no extractable final alcohol content, becomes Needs Review. A readable approved-formula alcohol mismatch becomes Fail. |
| Item 10 | `grape_varietals` | Extracted for reviewer context for wine applications. |
| Item 11 | `wine_appellation` | Extracted for reviewer context and possible label comparison. |
| Item 12 | `phone` | Extracted for reviewer context. |
| Item 13 | `email` | Extracted for reviewer context. |
| Item 14 | `application_type` | Extracted for reviewer context. |
| Item 15 | `item_15` | Checked against label/container text when supplied; missing evidence becomes Needs Review. |
| Lower page-one label area | label OCR text | Evidence source for all label checks. |

The current TTB F 5100.31 instructions place brand, fanciful name, product type, formula/pre-COLA reference, wine-only grape varietals, wine appellation, contact details, application type, and Item 15 container text in page-one form fields. TTB's formula approval basics guidance describes formulas as recipes with detailed ingredients and manufacturing steps, and identifies final alcohol content as formula application information. TTB's example formulas show that the final-product alcohol content may be a low/high range in the Formulas Online Yield Summary. In this prototype, Formula ID lookup is local to the uploaded PDF package and requires an exact normalized ID match: the app does not call Formulas Online or any remote TTB service.

The blank TTB F 5100.31 form does not always expose class/type, alcohol content, net contents, bottler/producer, country of origin, or imported status as simple fields. For this reason, the extractor also looks for an explicit application-data summary block inside the completed PDF. That block is treated as application/package metadata, not label evidence.

Net contents checks ignore serving-size, recipe, calorie, and per-serving volumes so unrelated label text does not create a false mismatch. Imported country checks require origin-style label wording, such as `Product of Mexico`, `Produced in Mexico`, `Made in Mexico`, `Imported from Mexico`, or `Country of Origin Mexico`; a country name appearing only in an importer company name is not enough for a Pass. `United States` may also match common origin abbreviations such as `USA`, `U.S.A.`, and `U.S.` when they appear in origin-style wording.

When `docs/source/f510031.pdf` is available locally, the sample generator fills the real TTB form template and adds an invisible application-data summary text layer for expected values that are not first-page fields. If the source form is absent, it falls back to a controlled TTB-like one-page layout.
