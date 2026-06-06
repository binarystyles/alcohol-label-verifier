from __future__ import annotations

from pathlib import Path

from src.batch import process_batch
from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.sample_data import sample_specs


def test_generated_sample_data_loads_correctly(sample_paths: list[Path]) -> None:
    assert len(sample_paths) == 6
    assert Path("samples/sample_batch.zip").exists()
    assert Path("samples/expected_outcomes.md").exists()
    assert all(path.exists() and path.stat().st_size > 0 for path in sample_paths)


def test_generated_sample_outcomes(sample_paths: list[Path]) -> None:
    results = process_batch([(path.name, path.read_bytes()) for path in sample_paths], cache={})
    actual = {result.filename: result.overall_status for result in results}
    expected = {spec.filename: spec.expected_status for spec in sample_specs()}
    assert actual == expected


def test_expected_status_set_is_complete() -> None:
    statuses = {spec.expected_status for spec in sample_specs()}
    assert statuses == {STATUS_PASS, STATUS_FAIL, STATUS_REVIEW}

