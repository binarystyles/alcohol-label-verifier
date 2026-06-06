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

## Pipeline

1. Read uploaded file bytes in memory.
2. Compute a SHA-256 hash for Streamlit session caching.
3. Convert scanned images to an in-memory PDF page so the same region pipeline applies.
4. Try `pypdf` AcroForm extraction for PDFs.
5. If expected values remain missing, render/extract defined page-one form regions.
6. Parse an explicit `APPLICATION DATA SUMMARY` block when present in the package.
7. Extract label text only from the lower page-one label area and likely supplemental label pages.
8. Compare expected application values to label evidence.
9. Return one application result plus field-level results.

The extractor never uses label OCR as the source of expected application values. If an expected value cannot be extracted from application fields, form regions, AcroForm values, or an explicit application-data summary, that field becomes Needs Review.

## Status Logic

Fail is reserved for critical checks with extractable expected values:

- Government warning missing or materially altered on a readable label.
- Required brand materially mismatched.
- Material ABV mismatch.
- Material net contents mismatch.

Needs Review is used for uncertainty:

- Missing or unreadable label area.
- Low OCR confidence.
- Unreadable PDF.
- Missing expected application value.
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
