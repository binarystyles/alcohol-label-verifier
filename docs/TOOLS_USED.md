# Tools Used

This project is implemented as a local, deterministic Streamlit application. It does not use cloud AI APIs, remote ML endpoints, runtime network calls, or live Formulas Online lookups.

## Application Runtime

| Tool | Use |
| --- | --- |
| Python 3.11 | Core application runtime. |
| Streamlit | Web UI, file upload workflow, result display, and CSV download controls. |
| pandas | Summary, detailed field-result, and extracted-application CSV exports. |
| pydantic | Installed structured-data dependency; current result models use Python dataclasses. |
| Python standard library (`hashlib`, `io`, `zipfile`, `dataclasses`) | In-memory upload handling, ZIP expansion, file hashing, and result models. |

## PDF And Image Processing

| Tool | Use |
| --- | --- |
| PyMuPDF (`pymupdf`, imported as `fitz`) | Opens PDFs, renders page regions, reads text layers, fills/generates sample PDFs, and converts scanned image inputs into in-memory PDF pages. |
| pypdf | Reads PDF AcroForm field values from completed applications. |
| PyMuPDF checkbox rendering | Reads visible checkbox marks for current source-form Item 3 Domestic/Imported and Item 5 product type when widgets are flattened or scanned. |
| Pillow | Image loading, scanned-image conversion, sample label artwork generation, photo-like/metallic/dense/stylized artwork fixtures, and raster label manipulation. |
| OpenCV headless | OCR image preprocessing variants, Otsu/adaptive thresholding, and sharpness scoring for low-quality/rotated label detection. |
| NumPy | Image-array operations for preprocessing, nonwhite-pixel ratio, and sharpness calculations. |

## OCR And Matching

| Tool | Use |
| --- | --- |
| Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-eng`) | Local OCR engine for scanned PDFs, scanned images, and raster label artwork, including colored, photo-like, metallic, dense-illustration, stylized-font, ornate, low-contrast, tiny-warning, glare/artifact, distorted-text, embossed, and reversed-text label variants. Installed through `packages.txt` and the Dockerfile. |
| pytesseract | Python wrapper used to call local Tesseract and collect text/confidence data. |
| RapidFuzz | Fuzzy matching for brand, class/type, bottler/producer, Item 15, and other tolerant text comparisons. |

## Testing And Quality Checks

| Tool | Use |
| --- | --- |
| pytest | Unit and workflow tests. |
| Streamlit testing (`streamlit.testing.v1`) | Streamlit UI regression tests. |
| Docker | Deployment packaging and OCR-available verification with Tesseract installed. |
| Git | Version control for source, docs, and deterministic sample artifacts. |

## Sample And Artifact Generation

| Tool | Use |
| --- | --- |
| PyMuPDF | Fills the tracked `docs/source/f510031.pdf` form template and writes synthetic completed application PDFs. |
| Pillow | Builds raster color-artwork labels, ornate overprint-style labels, photo-like label backgrounds, metallic-foil labels, dense illustration labels, stylized-font labels, low-quality/tiny-warning labels, curved/distorted labels, embossed labels, glare/artifact labels, rotated labels, and scanned-image fixtures. |
| zipfile | Creates the sample batch ZIP and expands uploaded ZIP files in memory. |
| openpyxl | Installed spreadsheet dependency available for future workbook export; current app outputs CSV only. |
| reportlab | Included as a PDF-generation dependency, though current sample generation is handled with PyMuPDF. |

## Reference Inputs

| Reference | Use |
| --- | --- |
| `docs/source/f510031.pdf` | Local copy of the current TTB F 5100.31 template used for deterministic sample generation and form-region mapping. |
| TTB F 5100.31 instructions | Defines the application fields and Item 9 formula-reference behavior used in `docs/FORM_MAPPING.md`. |
| TTB formula guidance and example formula pages | Informs local parsing of Formula ID/source documents included inside uploaded application packages, especially `Yield Summary` rows for final, finished-product, target, or bottling alcohol content, ABV, Alc/Vol, and proof values. |
