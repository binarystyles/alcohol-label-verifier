# Alcohol Label Verification

Live demo URL: https://alcohol-label-verifier-ttb.streamlit.app/

## Summary

Alcohol Label Verification is a local-first Streamlit prototype for batch review of completed TTB alcohol label application files. Compliance agents select one or many completed application PDFs or scanned application images, click **Verify Applications**, and receive Pass, Needs Review, or Fail recommendations with downloadable CSV outputs.

Each PDF or scanned application image is treated as a self-contained verification package. Users do not upload labels separately. Users do not create CSV input files. CSVs are generated only as outputs for reviewer convenience.

## Problem Context

Agents compare application data against label artwork for brand name, product type, class/type designation, alcohol content, net contents, bottler or producer, country of origin when applicable, Item 15 information when supplied, and the required government warning. The prototype is designed for a simple batch-first workflow because large submitters may send hundreds of applications at once.

The prior pilot target was missed because processing took 30 to 40 seconds per label. This implementation avoids cloud calls and minimizes OCR by checking AcroForms and PDF text layers before rendering only needed regions.

## Primary Workflow

1. Open the app.
2. Select completed TTB application PDFs, scanned application images, or upload a ZIP containing either.
3. Click **Verify Applications**.
4. Review the summary table.
5. Open details only for applications that need attention.
6. Download summary, field-results, or extracted-application-data CSVs.

There is no manual-entry mode and no separate single-application page. Batch mode handles one file and many files the same way.

## Key Features

- Batch PDF, scanned image, and ZIP intake.
- One-button verification workflow.
- Top-page light/dark mode toggle.
- Session-only intake-type plus file-hash caching.
- Best-effort AcroForm extraction with checkbox, region, and summary fallback.
- Separate application extraction and label evidence extraction.
- Local Tesseract OCR fallback for raster label areas.
- Ordered brand matching for harmless case, punctuation, apostrophe, ampersand, legal suffix variants such as `Co.`/`Company`, `Inc.`/`Incorporated`, `Corp.`/`Corporation`, `Ltd.`/`Limited`, and `L.L.C.`/`LLC`, and common `St.`/`Saint` or `Mt.`/`Mount` variations such as `STONE'S THROW`, `Stone's Throw`, `STONES THROW`, `SMITH & SONS` / `SMITH AND SONS`, `ACME DISTILLING CO.` / `ACME DISTILLING COMPANY`, and `SAINT GEORGE` / `ST. GEORGE`, without treating reordered brand words or distinct legal suffixes as equivalent.
- Strict government warning validation.
- CSV exports for summary, field-level checks, and extracted application data.
- Synthetic completed application PDFs for demo and tests.

## Architecture

The pipeline is implemented in small modules under `src/`:

- `pdf_intake.py`: file hashing, ZIP expansion, scanned image normalization, and PDF processing.
- `extractors.py`: AcroForm, source-form checkbox, form-region, summary, and label extraction.
- `form_mapping.py`: normalized TTB F 5100.31 coordinate heuristics.
- `ocr.py` and `preprocess.py`: local OCR and image cleanup.
- `normalize.py`: deterministic value parsing and fuzzy normalization.
- `verifier.py`: field checks and overall status logic.
- `batch.py`: batch processing and CSV dataframes.
- `sample_data.py`: synthetic completed application PDF generation.

## Local Setup

Install Python 3.11 and Tesseract OCR, then run:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/create_sample_applications.py
python -m pytest -q
streamlit run app.py
```

On Windows, make sure `tesseract.exe` is on `PATH`. The app still works for text-layer PDFs without Tesseract, but scanned images and raster label OCR require it.

## Docker Setup

```bash
docker build -t alcohol-label-verifier .
docker run --rm -it -p 8501:8501 alcohol-label-verifier
```

Then open `http://localhost:8501`.

To run it in the background instead:

```bash
docker run --rm -d --name alcohol-label-verifier -p 8501:8501 alcohol-label-verifier
docker logs -f alcohol-label-verifier
```

## Streamlit Community Cloud Deployment

1. Push this repository to GitHub.
2. Create a new Streamlit Community Cloud app from the repository.
3. Set the main file path to `app.py`.
4. Keep `requirements.txt` and `packages.txt` in the repo so Tesseract and Python dependencies install.
5. Deploy and replace the live demo placeholder above with the app URL.

## Testing With Sample PDFs

Generate the samples:

```bash
python scripts/create_sample_applications.py
```

Open the app, select PDFs from `samples/applications` or upload `samples/sample_batch.zip`, then click **Verify Applications**. The expected outcomes are documented in `samples/expected_outcomes.md`.

The sample generator uses the public TTB F 5100.31 template at `docs/source/f510031.pdf` when present, so generated samples resemble the current agency form with completed fields and affixed label artwork. If that template is absent, the generator falls back to a controlled one-page layout for tests.

The generated set currently includes 155 samples covering passing applications, readable critical mismatches, missing labels, low-quality OCR review cases, Formula ID support, numeric Formula ID support, Formula `#` support-document labels, TTB ID Number formula references, pre-import approval letter references, explicit non-approved and non-current formula support statuses such as rejected or approved-superseded, exact Formula ID matching with separator variants such as `F 9200` / `F-9200`, multiple submitted formula documents where only the matching Formula ID is used, no-formula-required applications including `FORMULA NOT REQUIRED` wording, final-alcohol ranges, final-alcohol table rows with OCR-style row numbers, matched formula documents without final alcohol content, formula wording variants such as `Finished Alcohol Content`, `Final Product Alcohol Content`, `Final Alcohol by Volume`, `Alcohol Content Finished Product`, `Alcohol Content of the Finished Product`, `Alcohol by Volume of Finished Product`, `Finished Product Alcohol`, `Finished Product ABV`, `Finished Product Alc/Vol`, and `Finished Product Proof`, proof/ABV normalization including low-proof formula support, expected proof ranges such as `80-90 Proof` and `80 Proof - 90 Proof`, adjacent dual proof/ABV label statements such as `90 Proof 45% Alc./Vol.`, `Proof 90`, `90 degrees proof`, `Alc. 45% by Vol.`, `45% Alc. by Vol.`, `45% by volume`, `Alcohol 45% by Volume`, `Alcohol: 45% by Volume`, `13.5% vol`, decimal-comma `13,5% vol`, decimal-comma ABV ranges such as `12,5-13,5% ABV`, `Alcohol 45% by Vol.`, dotted/spaced ABV abbreviations such as `45% A.B.V.` and `A B V 50%`, and `v/v` wording, non-alcohol percentages such as `100% Agave`, non-alcohol ingredient percent-by-volume statements such as `Natural flavoring 49% by volume`, conflicting alcohol-content statements, net contents normalization including cL/centiliter labels, dotted and OCR-split metric units such as `750 M.L.` and `750 M L`, plain `12 OZ`, compact estimated quantity marks such as `e750 mL`, comma thousands such as `1,000 mL`, decimal-comma litres such as `0,75 L`, British spellings such as `750 millilitres`, fractional `1/2 Pint`, spelled-out `Seven Hundred Fifty Milliliters`, rounded dual-unit `750 mL / 25.4 FL OZ`, and compound `1 Pint 0.9 FL OZ` labels, conflicting net-contents statements, serving-size volume false-positive prevention, imported-country pass/review cases including U.S./USA, U.K./UK, Scotland/United Kingdom, Republic of Ireland/Ireland, `Scotch Whisky`, `Irish Whiskey`, `Canadian Whisky`, `Distilled in Scotland`, `Distilled and bottled in Scotland`, `Distilled, matured and bottled in Scotland`, `Blended in Scotland`, `Brewed in Belgium`, The Netherlands variants, `Produce of France`, `Wine of France`, `Imported by ... from France` wording, conflicting origin statements, and domestic/no-imported-origin applications whose labels contain foreign origin wording, missing required application values, ambiguous multiple Item 5 product-type checkboxes, ambiguous multiple Item 3 Domestic/Imported checkboxes, supplied fanciful-name review, supplemental label pages after attached instruction pages, supplemental labels after long attachment sections, assignment-style brand capitalization tolerance such as application `Stone's Throw` matching label `STONE'S THROW`, brand ampersand/`AND`, `No.`/`#` number marker variations, legal suffix variants such as `Co.`/`Company`, `Inc.`/`Incorporated`, `Corp.`/`Corporation`, `Ltd.`/`Limited`, and `L.L.C.`/`LLC`, `St.`/`Saint`, curly apostrophe, diacritic variations, and OCR-like character-substitution review for required brand text, brand text appearing only in bottler/importer context, reordered brand words, distinct legal suffixes that should not be treated as equivalent, incidental product-type words inside brand names, product-type words appearing only in primary brand text, explicit product-type text before brand text including `BEER`, `LAGER BEER`, `MALT LIQUOR`, `FLAVORED MALT BEVERAGE`, `IPA`, `Pilsner`, first-line `HARD SELTZER`, and `HARD CIDER`, conflicting explicit product-type statements, distilled-spirits product-type support from clear class/type statements such as `Gin`, `Vodka Cocktail`, and distilled-spirits specialty/cocktail labels without a separate product-type line, wine product-type support from hard-cider/perry terms, 27 CFR wine class/type terms such as `Sake`, `Vermouth`, `Sherry`, `Port`, `Champagne`, `Mead`, and `Sangria`, and common grape-varietal type designations such as `Chardonnay`, class/type word-fragment false-positive prevention, explicit class/type values that include product-type words such as `Distilled Spirits Specialty`, conflicting class/type statements, class/type text appearing only inside the brand line, bottler/producer text appearing only outside responsible-party context, responsible-party wording such as `Distilled by`, `Blended by`, `Bottled for`, `Bottled exclusively for`, `Filled by`, `Made by`, `Prepared by`, `Canned by`, `Packed by`, `Produced and bottled by`, and comma/slash-separated action lists such as `Distilled, bottled and packaged by` or `Produced/Bottled by`, distribution-only responsible-party review, conflicting same-role responsible-party statements, mixed/lowercase government warning headings, OCR-damaged government warning headings, product-type mismatch failures, product-type descriptors such as wine-cask-finished spirits, descriptor-only wine wording such as `Wine Barrel Finished` on distilled spirits, Item 15 review, and color-artwork labels including crest-style artwork, textured artwork, busy artwork, dark/reversed text, colored warning panels, noisy low-contrast artwork, and photo-like scenic artwork with readable and low-contrast OCR-quality outcomes. See `samples/expected_outcomes.md` for the full sample list and expected Pass / Needs Review / Fail outcomes.

## Application File Intake

For each completed application file, the app:

1. Reads bytes in memory.
2. Computes SHA-256 for session caching.
3. Converts scanned image files to an in-memory single-application PDF representation.
4. Tries `pypdf` AcroForm extraction for PDFs.
5. Reads source-form checkbox widgets and visible checkbox marks for Item 3 Domestic/Imported and Item 5 product type when available.
6. Extracts mapped form regions from page one when needed.
7. Parses an explicit application-data summary block when present.
8. Extracts label evidence from the lower page-one affixed label area and likely supplemental label pages.
9. Compares application values to label evidence.

Label OCR text is never used to invent expected application values.

## TTB F 5100.31 Field Mapping

The prototype maps Item 4 through Item 15 and the lower page-one label area with normalized coordinates in `src/form_mapping.py`. The mapping is based on the current TTB Forms page entry for TTB F 5100.31 (04/2023), the instructions embedded in that form, and TTB's formula approval basics guidance. Item 9 is treated as a Formula ID/reference. The app searches the same uploaded application package for an exact normalized matching formula approval/source document and uses that document's final alcohol content as the expected value for label comparison. Formula labels such as `TTB Formula ID`, numeric Formula IDs, `Formula Number`, `Formula #`, `TTB ID Number`, `Lab Number`, and `Pre-import Approval No.` are recognized. Separator-only Formula ID differences such as `F 9200`, `F/9200`, and `F-9200` are normalized, but prefix-sharing Formula IDs are not treated as matches. Missing matching formula approval content, matched content with no final alcohol value, or a matched document with an explicit non-approved or non-current status becomes Needs Review, while a readable approved-formula alcohol mismatch becomes Fail. The app does not call Formulas Online or any TTB network service at runtime. See `docs/FORM_MAPPING.md` for the full mapping. Coordinates are heuristics and should be tuned with real completed application samples.

## Approach

The app uses deterministic rules plus fuzzy matching rather than cloud LLM APIs. That choice keeps the proof of concept local, explainable, lower latency, and easier to deploy in privacy-sensitive environments. See `docs/APPROACH.md`.

## Tools Used

See `docs/TOOLS_USED.md` for the canonical implementation, OCR, testing, deployment, sample-generation, and reference-input tool inventory.

## Security And Privacy

Uploaded files are processed in memory during the Streamlit session. The app does not permanently store uploads, does not call cloud AI APIs, and does not make runtime network calls. The public TTB blank form at `docs/source/f510031.pdf` is tracked because deterministic sample generation depends on it. Other raw source/reference files under `docs/source/` remain ignored.

## Performance Notes

Clean text-layer PDFs process quickly because the app avoids OCR when PDF text is available. Scanned PDFs, scanned image files, and raster labels require local OCR and may take longer. Session caching avoids reprocessing unchanged files during Streamlit reruns.

## Error Handling

Unreadable PDFs, malformed ZIP archives, ZIPs with no supported application files, missing label areas, low OCR confidence, low-confidence form OCR, missing expected values, and close-but-not-exact OCR reads of the government warning produce plain-English Needs Review reasons. Critical mismatches on readable evidence produce Fail.

## Known Limitations And Tradeoffs

- Form coordinates are prototype heuristics.
- Real completed PDFs may have different layout, scan quality, or supplemental page structure.
- OCR confidence is an approximation.
- Low-quality raster labels may need human review.
- Visual validation of bold type, exact type size, characters per inch, and contrasting background is not fully implemented.
- The app does not integrate with COLA and does not grant approval.

## Future Improvements

- Tune form mappings against a larger real-world PDF set.
- Add optional reviewer-adjustable coordinate profiles.
- Add better supplemental-label page classification.
- Add visual quality scoring for warning size, contrast, and legibility.
- Add multiprocessing for very large batches after memory profiling.
- Add persistent audit exports if approved by policy.

## Testing

```bash
python scripts/create_sample_applications.py
python -m pytest -q
```
