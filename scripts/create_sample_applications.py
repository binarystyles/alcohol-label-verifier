"""Generate synthetic completed application PDFs for demos and tests."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.batch import process_batch, summary_dataframe
from src.sample_data import generate_samples


def main() -> None:
    generated = generate_samples()
    results = process_batch([(path.name, path.read_bytes()) for path in generated], cache={})
    summary_dataframe(results).to_csv(ROOT / "samples" / "extracted_results_example.csv", index=False)
    print(f"Generated {len(generated)} sample PDFs in {ROOT / 'samples' / 'applications'}")
    print(f"Generated {ROOT / 'samples' / 'sample_batch.zip'}")
    print(f"Generated {ROOT / 'samples' / 'extracted_results_example.csv'}")


if __name__ == "__main__":
    main()

