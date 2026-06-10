# Approach

## Architecture

The app is a standalone Streamlit workflow that treats each completed application PDF or scanned application image as a self-contained verification package. Users upload one or many files, or a ZIP containing supported files. The batch processor expands ZIP files in memory, caches each file by intake type plus hash for the current session, normalizes scanned image files to an in-memory PDF representation, extracts application data, extracts label-area text, runs deterministic checks, and produces summary and detailed CSV outputs.

The main modules are:

- `src/pdf_intake.py`: PDF/image/ZIP expansion, hashing, per-file processing, and cache entry points.
- `src/extractors.py`: AcroForm extraction, source-form checkbox extraction, page-one region extraction, application summary parsing, and label-area extraction.
- `src/form_mapping.py`: normalized prototype coordinates for TTB F 5100.31 page-one fields.
- `src/ocr.py` and `src/preprocess.py`: PDF crop rendering, multiple local image-preprocessing variants, and local Tesseract OCR fallback.
- `src/normalize.py`: text, brand, ABV/proof, net contents, product type, and warning normalization.
- `src/verifier.py`: field checks and overall Pass / Needs Review / Fail aggregation.
- `src/batch.py`: batch orchestration and CSV-ready dataframes.
- `src/sample_data.py`: deterministic sample application package generation, including color-artwork labels.

See `docs/TOOLS_USED.md` for the implementation, OCR, test, and deployment toolchain.

## Pipeline

1. Read uploaded file bytes in memory.
2. Compute an intake-type plus SHA-256 key for Streamlit session caching.
3. Convert scanned images to an in-memory PDF page so the same region pipeline applies.
4. Try `pypdf` AcroForm extraction for PDFs.
5. Read current source-form checkbox widgets, or visible checkbox marks on flattened/scanned source-form pages, for Item 3 Domestic/Imported and Item 5 product type.
6. If expected values remain missing, render/extract defined page-one form regions.
7. Parse an explicit `APPLICATION DATA SUMMARY` block when present in the package.
8. Use Item 9 as a Formula ID/reference and look for an exact normalized matching formula approval/source document or pre-import approval letter inside the same uploaded package, ignoring unrelated approvals that may also be attached.
9. Derive expected alcohol content from the matched approval/source document when an approved final/finished-product alcohol, ABV, Alc/Vol, or proof heading is available.
10. Extract label text only from the lower page-one label area and likely supplemental label pages in the first 30 pages, skipping attached instruction pages and formula approval/source documents.
11. Compare expected application values to label evidence.
12. Return one application result plus field-level results.

The extractor never uses label OCR as the source of expected application values. If an expected value cannot be extracted from application fields, form regions, AcroForm values, an explicit application-data summary, or a matched formula approval document, that field becomes Needs Review.

## Status Logic

Fail is reserved for critical checks with extractable expected values:

- Government warning missing, materially altered, or shown with a readable non-all-caps heading on a readable label.
- Required brand materially mismatched. Brand matching is limited to primary label text and preserves word order. Harmless case, apostrophe, punctuation, curly apostrophe, diacritic, ampersand/`AND`, `No.`/`#` number marker variation, legal-suffix variants such as `Co.`/`Company`, `Inc.`/`Incorporated`, `Corp.`/`Corporation`, `Ltd.`/`Limited`, and `L.L.C.`/`LLC`, and common `St.`/`Saint` or `Mt.`/`Mount` variations pass, but a brand name appearing only in producer, importer, warning, or other non-brand context, with reordered brand words, or with a different explicit legal suffix does not create a false pass.
- Product type materially mismatched. Explicit `DISTILLED SPIRITS`, distilled-spirits class/type terms such as `Gin`, `Whiskey`, `Distilled Spirits Specialty`, or `Vodka Cocktail`, `MALT BEVERAGE(S)`, `FLAVORED MALT BEVERAGE`, beer-style terms such as `Beer`, `Lager Beer`, `India Pale Ale`, `IPA`, `Pilsner`, `Gose`, `Witbier`, `Hard Seltzer`, or `Spiked Seltzer`, `MALT LIQUOR`, hard-cider/perry terms, CFR wine class/type terms such as `Sake`, `Vermouth`, `Sherry`, `Port`, `Champagne`, `Mead`, and `Sangria`, common grape-varietal type designations such as `Chardonnay` or `Cabernet Sauvignon`, and wine statements in product/class label context are prioritized over incidental descriptors or brand words such as `Wine Cask Finish`, `Wine Barrel Finished`, `Made with wine botanicals`, or `Spirit` inside a wine brand, even when the explicit product-type statement appears before the brand.
- Material ABV mismatch. Proof values from labels, expected application data, and formula support are converted to ABV, including low-proof values such as `40 Proof` = `20% ABV`, expected proof ranges such as `80-90 Proof` or `80 Proof - 90 Proof`, and label wording such as `Proof 90` or `90 degrees proof`. Common label wording such as `Alc. 45% by Vol.`, `45% Alc. by Vol.`, `45% by volume`, `Alcohol 45% by Volume`, `Alcohol: 45% by Volume`, `13.5% vol`, repeated-unit ranges such as `12.5%-13.5% ABV`, decimal-comma `13,5% vol`, decimal-comma ranges such as `12,5-13,5% ABV`, and `Alcohol 45% by Vol.` is normalized to ABV. Non-alcohol percentages such as `100% Agave` and ingredient percent-by-volume text such as `Natural flavoring 49% by volume` are ignored for ABV/proof matching and become Needs Review if no actual alcohol statement is found.
- Material net contents mismatch. Milliliters, litres, British `millilitres`, decimal-comma litres such as `0,75 L`, centiliters, fluid ounces, plain ounces used as net contents, dotted or OCR-split metric units such as `750 M.L.` and `750 M L`, compact estimated quantity marks such as `e750 mL`, comma thousands such as `1,000 mL`, whole or fractional pints, spelled-out number words such as `Seven Hundred Fifty Milliliters`, rounded dual-unit statements such as `750 mL / 25.4 FL OZ`, compound pint/ounce statements, and multipack statements such as `4 x 50 mL` are normalized to milliliters. Serving-size, recipe, calorie, or per-serving volumes are ignored so they do not create false net-contents mismatches.

Needs Review is used for uncertainty:

- Missing or unreadable label area.
- Malformed ZIP archive or ZIP with no supported completed application files.
- Low OCR confidence.
- Low-confidence form OCR for an expected application value.
- Unreadable PDF.
- Missing expected application value.
- Source of product Domestic/Imported checkbox cannot be extracted with enough certainty.
- Mutually exclusive source/product checkboxes contain multiple selected values, so the application value is ambiguous.
- Supplied optional application value, such as a fanciful name, is not clearly found on the label.
- Expected text appears only as a fragment inside a larger word, such as `Gin` inside `Ginger`.
- Required brand text appears to match only after OCR-like character substitutions such as `0` for `O`; this is not a Pass because the readable label text still needs confirmation.
- Product-type words appear only in primary brand text, with no clear product/class label statement, or the label contains conflicting explicit product-type statements.
- Class/type text appears only in brand, producer, warning, or other non-class context, or the label contains conflicting explicit class/type statements. Explicit `Class/Type:` values are preserved even when the value contains product-type words, such as `Distilled Spirits Specialty`, and clear distilled-spirits specialty/cocktail class-type text may satisfy Item 5 without a separate `DISTILLED SPIRITS` line.
- Bottler/producer text appears only in brand or other non-responsible-party context instead of wording such as `Bottled by`, `Bottled for`, `Bottled exclusively for`, `Distilled by`, `Blended by`, `Imported solely by`, `Filled by`, `Made by`, `Prepared by`, `Canned by`, `Packed by`, `Produced specially by`, `Produced and bottled by`, or comma/slash-separated action lists such as `Distilled, bottled and packaged by` and `Produced/Bottled by`, or the label contains conflicting same-role responsible-party statements. Distribution-only wording is routed to Needs Review rather than treated as a bottler/producer match. Harmless legal suffix variants pass, but distinct suffixes such as `LLC` versus `Limited` are not treated as the same entity.
- Label contains both matching and conflicting alcohol-content or net-contents values.
- Missing matching formula approval or pre-import approval content for an Item 9 reference.
- Matching formula approval/source document or pre-import approval letter found but no final alcohol content is extractable.
- Matching formula approval/source document or pre-import approval letter has an explicit non-approved or non-current status.
- Formula support document has a similar but nonmatching prefix-sharing Formula ID.
- Imported country of origin is missing, conflicts with another origin-style country statement, or appears only in unrelated text such as an importer company name rather than in origin wording like `Product of`, `Produce of`, `Distilled in`, `Distilled and bottled in`, `Distilled, matured and bottled in`, `Blended in`, `Blended and bottled in`, `Brewed in`, `Brewed and bottled in`, `Made in`, `Imported from`, or `Imported by ... from`. Bottling-location-only wording such as `Bottled in Mexico` is routed to Needs Review because it does not clearly prove country of origin. Domestic/no-country-required applications pass when no origin is claimed, but non-U.S. origin-style label wording such as `Product of Mexico` is routed to Needs Review because it conflicts with the domestic source context. United States and United Kingdom origins can match common label abbreviations such as `USA`, `U.S.A.`, `U.S.`, `UK`, or `U.K.`; United Kingdom can also match constituent-origin wording such as `Product of Scotland`, `Distilled in Scotland`, `Distilled and bottled in Scotland`, `Distilled, matured and bottled in Scotland`, `Blended in Scotland`, or protected `Scotch Whisky` designation; Ireland can match `Republic of Ireland` or `Irish Whiskey`; Canada can match `Canadian Whisky`; and Netherlands can match `The Netherlands`.
- Government warning text is close to canonical, but the heading or OCR text is not exact enough for a strict pass.
- Optional supplied value not clearly found.
- Item 15 supplied but not clearly found.

Pass is only returned when all required checks pass with adequate confidence.

## Human In The Loop

The tool recommends review status; it does not approve applications. This is intentional because OCR can misread small text, raster quality varies, and some regulatory checks require visual judgment that is not reliable in this prototype.

## Speed Strategy

The app avoids full-document OCR unless necessary:

- Embedded PDF text is used first.
- AcroForms are checked before region OCR.
- Current source-form checkbox widgets and visible checkbox marks are checked before OCR is trusted for checkbox-only values.
- Only mapped page-one regions and candidate label areas are rendered.
- Unreadable scanned attachment pages do not downgrade the result when a later supplemental label page is readable.
- Label OCR tries conservative adaptive-threshold, grayscale, contrast, and Otsu-preprocessed variants, then keeps the strongest local Tesseract result. This improves colored artwork, crest-style/logo-like artwork, textured and photo-like backgrounds, dark/reversed text, and colored warning panels without making network calls.
- Results are cached by intake type plus file hash during the Streamlit session, so identical bytes uploaded as different file types still take the correct PDF/image/ZIP processing path.

On clean text-layer PDFs and generated samples, processing is typically well under the 5-second target per application. Scanned images, scanned PDFs, and rotated raster labels depend on local Tesseract speed and image quality.
