# Assumptions

- This is a standalone proof of concept with no COLA integration.
- Each completed application PDF or scanned application image is self-contained and includes both application data and label artwork.
- Users do not upload separate label images.
- Users do not create CSV input files. CSVs are outputs for reviewer convenience.
- Uploaded files are processed from memory or temporary library buffers and are not permanently stored by the app.
- No cloud AI APIs, remote ML endpoints, or runtime network calls are used.
- Tesseract is installed locally in deployment environments through `packages.txt` or the Dockerfile, especially for scanned images and raster-only PDFs.
- Filled TTB F 5100.31 files may vary by producer, scanner, page size, and whether they contain AcroForm values, PDF text, or only raster imagery.
- The normalized form coordinates in `src/form_mapping.py` are prototype heuristics and may need tuning against real agency PDF samples.
- Item 9 on current TTB F 5100.31 is treated as the formula/pre-COLA reference field, not as the general alcohol-content field.
- Expected values such as class/type, ABV, net contents, bottler/producer, and country of origin may not be explicit on every blank form. The app supports an application-data summary block inside the same PDF for those application/package values.
- If an expected application value cannot be extracted, the field is marked Needs Review instead of being inferred from the label.
- OCR can be unreliable for low-resolution, rotated, distorted, or low-contrast labels.
- Reliable visual detection of bold type, exact type size, characters per inch, and contrasting background is documented as a limitation unless implemented separately.
