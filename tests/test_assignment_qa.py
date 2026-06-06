from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.constants import GOVERNMENT_WARNING, STATUS_REVIEW
from src.extractors import extract_application, extract_label
from src.models import ApplicationFields, LabelExtraction
from src.pdf_intake import expand_named_files
from src.verifier import verify_application


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_ui_exposes_only_completed_pdf_batch_workflow() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"))
    app.run(timeout=20)

    assert app.title[0].value == "Alcohol Label Verification"
    assert [uploader.label for uploader in app.file_uploader] == [
        "Select completed TTB application PDFs",
        "Or select a ZIP containing completed application PDFs",
    ]
    assert any(button.label == "Verify Applications" for button in app.button)
    assert any(button.label == "Load Sample Applications" for button in app.button)

    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'type=["pdf"]' in source
    assert 'type=["zip"]' in source
    assert 'type=["csv"]' not in source
    assert "read_csv" not in source
    assert "label image" not in source.lower()


def test_csvs_are_download_outputs_only() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert source.count("download_button(") == 3
    assert "Download summary CSV" in source
    assert "Download detailed field-results CSV" in source
    assert "Download extracted application data CSV" in source


def test_pdf_and_zip_intake_treat_each_pdf_as_own_package(sample_bytes: dict[str, bytes]) -> None:
    zip_bytes = (ROOT / "samples" / "sample_batch.zip").read_bytes()
    expanded = expand_named_files(
        [
            ("one.pdf", sample_bytes["APP-001_old_tom_pass.pdf"]),
            ("batch.zip", zip_bytes),
        ]
    )
    assert len(expanded) == 7
    assert all(name.lower().endswith(".pdf") for name, _ in expanded)


def test_application_and_label_text_are_extracted_from_separate_regions(sample_bytes: dict[str, bytes]) -> None:
    pdf_bytes = sample_bytes["APP-001_old_tom_pass.pdf"]
    application = extract_application(pdf_bytes)
    label = extract_label(pdf_bytes)

    assert application.fields.brand_name == "OLD TOM GIN"
    assert "GOVERNMENT WARNING" not in application.application_ocr_text
    assert "OLD TOM GIN" in label.text
    assert "GOVERNMENT WARNING" in label.text


def test_label_ocr_is_not_used_to_invent_missing_expected_values() -> None:
    fields = ApplicationFields(
        serial_number="APP-MISSING",
        product_type="DISTILLED SPIRITS",
        class_type="Gin",
        alcohol_content="45% ABV",
        net_contents="750 mL",
    )
    label = LabelExtraction(
        text=f"OLD TOM GIN DISTILLED SPIRITS Gin 45% Alc./Vol. 750 mL {GOVERNMENT_WARNING}",
        confidence=0.97,
    )

    result = verify_application(
        filename="missing-brand.pdf",
        fields=fields,
        label=label,
        application_ocr_text="",
        processing_time_seconds=0.1,
    )
    brand = next(field for field in result.field_results if field.field == "brand_name")
    assert result.overall_status == STATUS_REVIEW
    assert brand.status == STATUS_REVIEW
    assert brand.expected == ""
    assert brand.reason == "Expected application value could not be extracted."


def test_required_docs_and_deployment_files_exist() -> None:
    required = [
        "README.md",
        "docs/APPROACH.md",
        "docs/ASSUMPTIONS.md",
        "docs/FORM_MAPPING.md",
        "requirements.txt",
        "packages.txt",
        "Dockerfile",
        ".streamlit/config.toml",
    ]
    for relative_path in required:
        assert (ROOT / relative_path).exists(), relative_path


def test_runtime_code_has_no_cloud_ai_or_network_clients() -> None:
    forbidden = (
        "openai",
        "anthropic",
        "requests.",
        "urllib",
        "aiohttp",
        "socket.",
        "fetch(",
        "api_key",
    )
    for path in [ROOT / "app.py", *sorted((ROOT / "src").glob("*.py"))]:
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, f"{token} found in {path}"


def test_gitignore_excludes_source_docs_and_local_artifacts() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "docs/source/*" in gitignore
    assert "__pycache__/" in gitignore
    assert ".pytest_cache/" in gitignore
    assert ".venv/" in gitignore
    assert "uploads/" in gitignore

