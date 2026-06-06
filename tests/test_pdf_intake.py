from __future__ import annotations

from pathlib import Path

from src.constants import STATUS_PASS, STATUS_REVIEW
from src.pdf_intake import expand_named_files, extract_pdfs_from_zip, process_pdf, sha256_bytes


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

