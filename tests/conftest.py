from __future__ import annotations

from pathlib import Path

import pytest

from src.sample_data import generate_samples
from src.sample_data import create_sample_zip
from src.sample_data import sample_specs


@pytest.fixture(scope="session")
def sample_paths() -> list[Path]:
    paths = sorted(Path("samples/applications").glob("*.pdf"))
    expected_names = {spec.filename for spec in sample_specs()}
    if {path.name for path in paths} == expected_names:
        _ensure_sample_batch_zip(paths)
        return paths
    generated = generate_samples()
    _ensure_sample_batch_zip(generated)
    return generated


@pytest.fixture(scope="session")
def sample_bytes(sample_paths: list[Path]) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sample_paths}


def _ensure_sample_batch_zip(paths: list[Path]) -> None:
    batch_zip = Path("samples/sample_batch.zip")
    if not batch_zip.exists():
        create_sample_zip(paths, batch_zip)
