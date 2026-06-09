# Approach

## Architecture

The app is a standalone Streamlit workflow that treats each completed application PDF or scanned application image as a self-contained verification package. Users upload one or many files, or a ZIP containing supported files. The batch processor expands ZIP files in memory, hashes each file for session-only caching, normalizes scanned image files to an in-memory PDF representation, extracts application data, extracts label-area text, runs deterministic checks, and produces summary and detailed CSV outputs.

The main modules are:

- `src/pdf_intake.py`: PDF/image/ZIP expansion, hashing, per-file processing, and cache entry points.
- `src/extractors.py`: AcroForm extraction, page-one region extraction, application summary parsing, and label-area extraction.
- `src/form_mapping.py`: normalized prototype coordinates for TTB F 5100.31 page-one fields.
- `src/ocr.py` and `src/preprocess.py`: PDF crop rendering, image preprocessing, and local Tesseract OCR fallback.
- `src/normalize.py`: text, brand, ABV/proof, net contents, product type, and warning normalization.
- `src/verifier.py`: field checks and overall Pass / Needs Review / Fail aggregation.
- `src/batch.py`: batch orchestration and CSV-ready dataframes.
- `src/sample_data.py`: deterministic sample application package generation, including color-artwork labels.

See `docs/TOOLS_USED.md` for the implementation, OCR, test, and deployment toolchain.

## Pipeline

1. Read uploaded file bytes in memory.
2. Compute a SHA-256 hash for Streamlit session caching.
3. Convert scanned images to an in-memory PDF page so the same region pipeline applies.
4. Try `pypdf` AcroForm extraction for PDFs.
5. If expected values remain missing, render/extract defined page-one form regions.
6. Parse an explicit `APPLICATION DATA SUMMARY` block when present in the package.
7. Use Item 9 as a Formula ID/reference and look for an exact normalized matching formula approval/source document inside the same uploaded package.
8. Derive expected alcohol content from the matched formula approval document when available.
9. Extract label text only from the lower page-one label area and likely supplemental label pages, skipping formula approval/source documents.
10. Compare expected application values to label evidence.
11. Return one application result plus field-level results.

The extractor never uses label OCR as the source of expected application values. If an expected value cannot be extracted from application fields, form regions, AcroForm values, an explicit application-data summary, or a matched formula approval document, that field becomes Needs Review.

## Status Logic

Fail is reserved for critical checks with extractable expected values:

- Government warning missing or materially altered on a readable label.
- Required brand materially mismatched. Brand matching is limited to primary label text so a brand name appearing only in producer, importer, warning, or other non-brand context does not create a false pass.
- Product type materially mismatched. Explicit `DISTILLED SPIRITS` and `MALT BEVERAGE(S)` phrases are prioritized over incidental descriptors such as `Wine Cask Finish`.
- Material ABV mismatch. Proof values from labels and formula support are converted to ABV, including low-proof values such as `40 Proof` = `20% ABV` and label wording such as `Proof 90`. Common label wording such as `Alc. 45% by Vol.` and `Alcohol 45% by Volume` is normalized to ABV. Non-alcohol percentages such as `100% Agave` are ignored for ABV/proof matching and become Needs Review if no actual alcohol statement is found.
- Material net contents mismatch. Serving-size, recipe, calorie, or per-serving volumes are ignored so they do not create false net-contents mismatches.

Needs Review is used for uncertainty:

- Missing or unreadable label area.
- Malformed ZIP archive or ZIP with no supported completed application files.
- Low OCR confidence.
- Low-confidence form OCR for an expected application value.
- Unreadable PDF.
- Missing expected application value.
- Supplied optional application value, such as a fanciful name, is not clearly found on the label.
- Class/type text appears only in brand, producer, warning, or other non-class context.
- Bottler/producer text appears only in brand or other non-responsible-party context instead of wording such as `Bottled by`, `Imported by`, or `Produced and bottled by`.
- Label contains both matching and conflicting alcohol-content or net-contents values.
- Missing matching formula approval content for an Item 9 Formula ID.
- Matching formula approval/source document found but no final alcohol content is extractable.
- Formula support document has a similar but nonmatching prefix-sharing Formula ID.
- Imported country of origin is missing or the country name appears only in unrelated text, such as an importer company name, rather than in origin wording like `Product of`.
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
- Only mapped page-one regions and candidate label areas are rendered.
- Results are cached by PDF hash during the Streamlit session.

On clean text-layer PDFs and generated samples, processing is typically well under the 5-second target per application. Scanned images, scanned PDFs, and rotated raster labels depend on local Tesseract speed and image quality.
