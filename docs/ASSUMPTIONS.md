# Assumptions

- This is a standalone proof of concept with no COLA integration.
- Each completed application PDF or scanned application image is self-contained and includes both application data and label artwork.
- Users do not upload separate label images.
- Users do not create CSV input files. CSVs are outputs for reviewer convenience.
- ZIP uploads may contain unsupported non-application files; those entries are ignored. A malformed ZIP, or a ZIP with no supported completed application PDFs/images, is reported as Needs Review with a clear reason instead of crashing the app.
- Uploaded files are processed from memory or temporary library buffers and are not permanently stored by the app.
- No cloud AI APIs, remote ML endpoints, or runtime network calls are used.
- Tesseract is installed locally in deployment environments through `packages.txt` or the Dockerfile, especially for scanned images and raster-only PDFs.
- Filled TTB F 5100.31 files may vary by producer, scanner, page size, and whether they contain AcroForm values, PDF text, or only raster imagery.
- The normalized form coordinates in `src/form_mapping.py` are prototype heuristics and may need tuning against real agency PDF samples.
- Item 9 on current TTB F 5100.31 is treated as a Formula ID/reference. The app looks for an exact normalized matching approved formula/source document inside the same uploaded application package and derives expected alcohol content from that matched document, not from label OCR and not from a runtime network lookup. Separator-only Formula ID differences are normalized, but prefix-sharing Formula IDs are not considered matches.
- Expected values such as class/type, ABV, net contents, bottler/producer, and country of origin may not be explicit on every blank form. The app supports an application-data summary block inside the same PDF for those application/package values.
- Net contents and imported country checks are context-aware. Serving-size volumes are not treated as net contents, and a country name must appear in origin wording rather than only in unrelated importer or brand text.
- If an expected application value cannot be extracted, the field is marked Needs Review instead of being inferred from the label.
- If an expected application value comes only from low-confidence form OCR, mismatches are marked Needs Review instead of Fail because the source value itself may be wrong.
- OCR can be unreliable for low-resolution, rotated, distorted, or low-contrast labels. A government warning must match strictly to Pass, including a readable all-caps `GOVERNMENT WARNING` heading, but OCR-imperfect warning text that is close to the canonical statement is routed to Needs Review rather than treated as a confirmed material alteration.
- Reliable visual detection of bold type, exact type size, characters per inch, and contrasting background is documented as a limitation unless implemented separately.
