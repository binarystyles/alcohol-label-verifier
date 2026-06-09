"""Application file and ZIP intake helpers."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import hashlib
import time
import zipfile

import fitz
from PIL import Image, ImageOps, ImageSequence

from src.extractors import extract_application, extract_label
from src.models import ApplicationResult
from src.verifier import verify_application


SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
SUPPORTED_APPLICATION_EXTENSIONS = (".pdf", *SUPPORTED_IMAGE_EXTENSIONS)
SUPPORTED_UPLOAD_TYPES = ["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expand_named_files(named_files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    expanded: list[tuple[str, bytes]] = []
    for filename, data in named_files:
        lower = filename.lower()
        if is_supported_application_file(filename):
            expanded.append((filename, data))
        elif lower.endswith(".zip"):
            try:
                extracted = extract_application_files_from_zip(data, prefix=filename)
            except zipfile.BadZipFile:
                expanded.append((filename, data))
            else:
                expanded.extend(extracted or [(filename, data)])
    return expanded


def is_supported_application_file(filename: str) -> bool:
    return filename.lower().endswith(SUPPORTED_APPLICATION_EXTENSIONS)


def extract_application_files_from_zip(zip_bytes: bytes, prefix: str = "archive.zip") -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            if info.is_dir() or not is_supported_application_file(info.filename):
                continue
            with archive.open(info) as handle:
                files.append((f"{prefix}/{info.filename}", handle.read()))
    return files


def extract_pdfs_from_zip(zip_bytes: bytes, prefix: str = "archive.zip") -> list[tuple[str, bytes]]:
    """Backward-compatible PDF-only ZIP helper used by older callers/tests."""
    return [
        (filename, data)
        for filename, data in extract_application_files_from_zip(zip_bytes, prefix=prefix)
        if filename.lower().endswith(".pdf")
    ]


def image_bytes_to_pdf_bytes(image_bytes: bytes) -> bytes:
    """Convert one scanned image file into an in-memory PDF package."""
    with Image.open(BytesIO(image_bytes)) as image:
        frames = []
        for frame in ImageSequence.Iterator(image):
            oriented = ImageOps.exif_transpose(frame)
            frames.append(oriented.convert("RGB").copy())

    if not frames:
        raise ValueError("Image did not contain any readable pages.")

    document = fitz.open()
    try:
        for frame in frames:
            page_width = 612
            page_height = max(1, page_width * frame.height / frame.width)
            page = document.new_page(width=page_width, height=page_height)
            image_buffer = BytesIO()
            frame.save(image_buffer, format="PNG")
            page.insert_image(page.rect, stream=image_buffer.getvalue())
        return document.tobytes(garbage=4, deflate=True)
    finally:
        document.close()


def normalize_application_file_to_pdf(filename: str, file_bytes: bytes) -> bytes:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return file_bytes
    if lower.endswith(SUPPORTED_IMAGE_EXTENSIONS):
        return image_bytes_to_pdf_bytes(file_bytes)
    if lower.endswith(".zip"):
        try:
            extracted = extract_application_files_from_zip(file_bytes, prefix=filename)
        except zipfile.BadZipFile as exc:
            raise ValueError(
                "ZIP archive could not be opened. Upload a valid ZIP containing completed application PDFs or scanned image files."
            ) from exc
        if not extracted:
            raise ValueError(
                "ZIP archive did not contain any completed application PDFs or scanned image files."
            )
        raise ValueError("ZIP archive was not expanded before processing.")
    raise ValueError("Unsupported file type. Use a completed application PDF or scanned image file.")


def process_application_file(filename: str, file_bytes: bytes) -> ApplicationResult:
    start = time.perf_counter()
    try:
        pdf_bytes = normalize_application_file_to_pdf(filename, file_bytes)
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


def process_application_file_cached(filename: str, file_bytes: bytes, cache: dict[str, ApplicationResult] | None = None) -> ApplicationResult:
    if cache is None:
        return process_application_file(filename, file_bytes)
    key = sha256_bytes(file_bytes)
    if key not in cache:
        cache[key] = process_application_file(filename, file_bytes)
    result = deepcopy(cache[key])
    result.filename = filename
    return result


def process_pdf(filename: str, pdf_bytes: bytes) -> ApplicationResult:
    """Backward-compatible alias for processing a completed application PDF."""
    return process_application_file(filename, pdf_bytes)


def process_pdf_cached(filename: str, pdf_bytes: bytes, cache: dict[str, ApplicationResult] | None = None) -> ApplicationResult:
    """Backward-compatible alias for cached PDF processing."""
    return process_application_file_cached(filename, pdf_bytes, cache=cache)
