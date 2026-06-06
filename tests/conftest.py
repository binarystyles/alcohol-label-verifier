from __future__ import annotations

from pathlib import Path

import pytest

from src.sample_data import generate_samples
from src.sample_data import sample_specs


@pytest.fixture(scope="session")
def sample_paths() -> list[Path]:
    paths = sorted(Path("samples/applications").glob("*.pdf"))
    expected_names = {spec.filename for spec in sample_specs()}
    if {path.name for path in paths} == expected_names:
        return paths
    return generate_samples()


@pytest.fixture(scope="session")
def sample_bytes(sample_paths: list[Path]) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sample_paths}
