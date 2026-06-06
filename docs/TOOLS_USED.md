# Tools Used

This project is implemented as a local, deterministic Streamlit application. It does not use cloud AI APIs, remote ML endpoints, or runtime network calls.

## Application Runtime

| Tool | Use |
| --- | --- |
| Python 3.11 | Core application runtime. |
| Streamlit | Web UI, file upload workflow, result display, and CSV download controls. |
| pandas | Summary, detailed field-result, and extracted-application CSV exports. |
| pydantic | Installed structured-data dependency; current result models use Python dataclasses. |

## PDF And Image Processing

| Tool | Use |
| --- | --- |
| PyMuPDF (`pymupdf`, imported as `fitz`) | Opens PDFs, renders page regions, reads text layers, fills/generates sample PDFs, and converts scanned image inputs into in-memory PDF pages. |
| pypdf | Reads PDF AcroForm field values from completed applications. |
| Pillow | Image loading, scanned-image conversion, sample label artwork generation, and raster label manipulation. |
| OpenCV headless | OCR image preprocessing and sharpness scoring for low-quality/rotated label detection. |
| NumPy | Image-array operations for preprocessing, nonwhite-pixel ratio, and sharpness calculations. |

## OCR And Matching

| Tool | Use |
| --- | --- |
| Tesseract OCR (`tesseract-ocr`, `tesseract-ocr-eng`) | Local OCR engine for scanned PDFs, scanned images, and raster label artwork. Installed through `packages.txt` and the Dockerfile. |
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
| Pillow | Builds raster color-artwork labels, low-quality labels, and scanned-image fixtures. |
| zipfile | Creates the sample batch ZIP and expands uploaded ZIP files in memory. |
| openpyxl | Installed spreadsheet dependency available for future workbook export; current app outputs CSV only. |
| reportlab | Included as a PDF-generation dependency, though current sample generation is handled with PyMuPDF. |

## Reference Inputs

| Reference | Use |
| --- | --- |
| `docs/source/f510031.pdf` | Local copy of the current TTB F 5100.31 template used for deterministic sample generation and form-region mapping. |
| TTB F 5100.31 instructions | Defines the application fields and Item 9 formula-reference behavior used in `docs/FORM_MAPPING.md`. |
| TTB formula guidance and example formula pages | Informs local parsing of Formula ID/source documents, especially `Yield Summary` and `Alcohol Content of Finished Product` rows. |
