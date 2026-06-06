from __future__ import annotations

from pathlib import Path

from src.batch import application_fields_dataframe, field_results_dataframe, process_batch, summary_dataframe, summary_metrics
from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.ocr import tesseract_available
from src.sample_data import sample_specs


def test_batch_processing_one_pdf(sample_bytes: dict[str, bytes]) -> None:
    results = process_batch([("APP-001_old_tom_pass.pdf", sample_bytes["APP-001_old_tom_pass.pdf"])], cache={})
    assert len(results) == 1
    assert results[0].overall_status == STATUS_PASS


def test_batch_processing_multiple_pdfs(sample_bytes: dict[str, bytes]) -> None:
    results = process_batch(
        [
            ("APP-001_old_tom_pass.pdf", sample_bytes["APP-001_old_tom_pass.pdf"]),
            ("APP-003_wrong_abv.pdf", sample_bytes["APP-003_wrong_abv.pdf"]),
            ("APP-006_missing_label_area.pdf", sample_bytes["APP-006_missing_label_area.pdf"]),
        ],
        cache={},
    )
    assert [result.overall_status for result in results] == [STATUS_PASS, STATUS_FAIL, STATUS_REVIEW]


def test_zip_batch_processing(sample_paths: list[Path]) -> None:
    zip_bytes = Path("samples/sample_batch.zip").read_bytes()
    results = process_batch([("sample_batch.zip", zip_bytes)], cache={})
    assert len(results) == len(sample_paths)
    metrics = summary_metrics(results)
    expected_statuses = [_expected_status(spec) for spec in sample_specs()]
    assert metrics["pass"] == expected_statuses.count(STATUS_PASS)
    assert metrics["fail"] == expected_statuses.count(STATUS_FAIL)
    assert metrics["needs_review"] == expected_statuses.count(STATUS_REVIEW)


def test_export_dataframes_have_expected_rows(sample_bytes: dict[str, bytes]) -> None:
    results = process_batch([("APP-001_old_tom_pass.pdf", sample_bytes["APP-001_old_tom_pass.pdf"])], cache={})
    assert len(summary_dataframe(results)) == 1
    assert len(field_results_dataframe(results)) == 11
    assert len(application_fields_dataframe(results)) == 1


def _expected_status(spec) -> str:
    if tesseract_available():
        return spec.expected_status
    return spec.expected_status_without_ocr or spec.expected_status
