from __future__ import annotations

from pathlib import Path
from io import BytesIO
import zipfile

import fitz
from PIL import Image, ImageDraw

from src.constants import STATUS_PASS, STATUS_REVIEW
from src.pdf_intake import (
    expand_named_files,
    extract_application_files_from_zip,
    extract_pdfs_from_zip,
    image_bytes_to_pdf_bytes,
    process_application_file,
    process_pdf,
    sha256_bytes,
)


def test_sha256_is_stable(sample_bytes: dict[str, bytes]) -> None:
    data = sample_bytes["APP-001_old_tom_pass.pdf"]
    assert sha256_bytes(data) == sha256_bytes(data)


def test_process_one_pdf(sample_bytes: dict[str, bytes]) -> None:
    result = process_pdf("APP-001_old_tom_pass.pdf", sample_bytes["APP-001_old_tom_pass.pdf"])
    assert result.overall_status == STATUS_PASS


def test_zip_batch_expansion(sample_paths: list[Path]) -> None:
    zip_bytes = Path("samples/sample_batch.zip").read_bytes()
    pdfs = extract_pdfs_from_zip(zip_bytes)
    assert len(pdfs) == len(sample_paths)
    assert all(name.endswith(".pdf") for name, _ in pdfs)


def test_expand_named_files_accepts_pdf_and_zip(sample_bytes: dict[str, bytes]) -> None:
    zip_bytes = Path("samples/sample_batch.zip").read_bytes()
    expanded = expand_named_files(
        [
            ("single.pdf", sample_bytes["APP-001_old_tom_pass.pdf"]),
            ("batch.zip", zip_bytes),
        ]
    )
    assert len(expanded) == 7


def test_missing_label_area_process_result(sample_bytes: dict[str, bytes]) -> None:
    result = process_pdf("APP-006_missing_label_area.pdf", sample_bytes["APP-006_missing_label_area.pdf"])
    assert result.overall_status == STATUS_REVIEW
    assert any("Label area" in warning for warning in result.warnings)


def test_image_bytes_convert_to_single_page_pdf() -> None:
    pdf_bytes = image_bytes_to_pdf_bytes(_make_scanned_application_image())
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        assert document.page_count == 1
        assert document[0].rect.width == 612
    finally:
        document.close()


def test_process_scanned_image_file_returns_review_result() -> None:
    result = process_application_file("scan.png", _make_scanned_application_image())
    assert result.filename == "scan.png"
    assert result.overall_status == STATUS_REVIEW


def test_zip_expansion_includes_scanned_images() -> None:
    image_bytes = _make_scanned_application_image()
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scan.png", image_bytes)
        archive.writestr("ignore.txt", b"not supported")

    files = extract_application_files_from_zip(zip_buffer.getvalue())
    assert len(files) == 1
    assert files[0][0].endswith("scan.png")


def _make_scanned_application_image() -> bytes:
    image = Image.new("RGB", (612, 1008), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 592, 988), outline="black")
    draw.text((34, 155), "4. SERIAL NUMBER APP-SCAN", fill="black")
    draw.text((34, 205), "6. BRAND NAME SCANNED SAMPLE", fill="black")
    draw.text((34, 690), "AFFIX COMPLETE SET OF LABELS BELOW", fill="black")
    draw.text((80, 740), "SCANNED SAMPLE 45% Alc./Vol. 750 mL", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
