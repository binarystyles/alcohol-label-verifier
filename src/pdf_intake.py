"""PDF and ZIP intake helpers."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import hashlib
import time
import zipfile

from src.extractors import extract_application, extract_label
from src.models import ApplicationResult
from src.verifier import verify_application


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expand_named_files(named_files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    expanded: list[tuple[str, bytes]] = []
    for filename, data in named_files:
        lower = filename.lower()
        if lower.endswith(".pdf"):
            expanded.append((filename, data))
        elif lower.endswith(".zip"):
            expanded.extend(extract_pdfs_from_zip(data, prefix=filename))
    return expanded


def extract_pdfs_from_zip(zip_bytes: bytes, prefix: str = "archive.zip") -> list[tuple[str, bytes]]:
    pdfs: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".pdf"):
                continue
            with archive.open(info) as handle:
                pdfs.append((f"{prefix}/{info.filename}", handle.read()))
    return pdfs


def process_pdf(filename: str, pdf_bytes: bytes) -> ApplicationResult:
    start = time.perf_counter()
    try:
        application = extract_application(pdf_bytes)
        label = extract_label(pdf_bytes)
        elapsed = time.perf_counter() - start
        return verify_application(
            filename=filename,
            fields=application.fields,
            label=label,
            application_ocr_text=application.application_ocr_text,
            processing_time_seconds=elapsed,
            extraction_warnings=application.warnings,
            extraction_errors=application.errors,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start
        from src.constants import STATUS_REVIEW
        from src.models import ApplicationFields, LabelExtraction

        return verify_application(
            filename=filename,
            fields=ApplicationFields(),
            label=LabelExtraction(text="", confidence=0.0, unreadable=True, warnings=[]),
            application_ocr_text="",
            processing_time_seconds=elapsed,
            extraction_warnings=["The application could not be processed."],
            extraction_errors=[str(exc)],
        )


def process_pdf_cached(filename: str, pdf_bytes: bytes, cache: dict[str, ApplicationResult] | None = None) -> ApplicationResult:
    if cache is None:
        return process_pdf(filename, pdf_bytes)
    key = sha256_bytes(pdf_bytes)
    if key not in cache:
        cache[key] = process_pdf(filename, pdf_bytes)
    result = deepcopy(cache[key])
    result.filename = filename
    return result

