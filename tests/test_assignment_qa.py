from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from PIL import Image, ImageDraw
from streamlit.testing.v1 import AppTest

from src.constants import GOVERNMENT_WARNING, STATUS_FAIL, STATUS_REVIEW
from src.extractors import extract_application, extract_label
from src.models import ApplicationFields, LabelExtraction
from src.pdf_intake import SUPPORTED_UPLOAD_TYPES, expand_named_files, process_application_file
from src.verifier import verify_application


ROOT = Path(__file__).resolve().parents[1]


def test_streamlit_ui_exposes_only_completed_pdf_batch_workflow() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"))
    app.run(timeout=20)

    assert app.title[0].value == "Alcohol Label Verification"
    assert not any(toggle.label == "Dark mode" for toggle in app.toggle)
    assert [uploader.label for uploader in app.file_uploader] == [
        "Select completed TTB application files",
        "Or select a ZIP containing completed application files",
    ]
    assert any(button.label == "Verify Applications" for button in app.button)
    assert not any(button.label == "Load Sample Applications" for button in app.button)

    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "SUPPORTED_UPLOAD_TYPES" in source
    assert 'type=["zip"]' in source
    assert 'type=["csv"]' not in source
    assert "read_csv" not in source
    assert "label image" not in source.lower()
    assert "use_container_width" not in source
    assert "dark_mode" not in source
    assert 'key=f"label_ocr_' in source
    assert 'key=f"application_ocr_' in source
    assert "Download original application" in source
    assert "pdf" in SUPPORTED_UPLOAD_TYPES
    assert "png" in SUPPORTED_UPLOAD_TYPES
    assert "jpg" in SUPPORTED_UPLOAD_TYPES


def test_streamlit_results_render_multiple_applications_without_duplicate_widget_ids(sample_bytes: dict[str, bytes]) -> None:
    app = AppTest.from_file(str(ROOT / "app.py"))
    app.run(timeout=20)
    app.file_uploader[0].set_value(
        [
            ("APP-001_old_tom_pass.pdf", sample_bytes["APP-001_old_tom_pass.pdf"], "application/pdf"),
            ("APP-003_wrong_abv.pdf", sample_bytes["APP-003_wrong_abv.pdf"], "application/pdf"),
            ("APP-006_missing_label_area.pdf", sample_bytes["APP-006_missing_label_area.pdf"], "application/pdf"),
        ]
    ).run(timeout=20)
    app.button[0].click().run(timeout=120)

    assert len(app.exception) == 0
    assert app.selectbox[0].label == "Status filter"
    assert sorted(app.session_state["review_files"]) == [
        "APP-001_old_tom_pass.pdf",
        "APP-003_wrong_abv.pdf",
        "APP-006_missing_label_area.pdf",
    ]
    assert [area.label for area in app.text_area] == [
        "Label OCR text",
        "Application OCR text",
        "Label OCR text",
        "Application OCR text",
        "Label OCR text",
        "Application OCR text",
    ]
    app.selectbox[0].set_value(STATUS_FAIL).run(timeout=20)
    assert len(app.exception) == 0
    assert app.selectbox[0].value == STATUS_FAIL


def test_csvs_are_download_outputs_only() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert source.count("download_button(") == 4
    assert "Download summary CSV" in source
    assert "Download detailed field-results CSV" in source
    assert "Download extracted application data CSV" in source
    assert "Download original application" in source


def test_pdf_and_zip_intake_treat_each_pdf_as_own_package(sample_bytes: dict[str, bytes]) -> None:
    zip_bytes = (ROOT / "samples" / "sample_batch.zip").read_bytes()
    image_bytes = _make_scanned_application_image()
    mixed_zip = BytesIO()
    with zipfile.ZipFile(mixed_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scan.png", image_bytes)
        archive.writestr("notes.txt", b"not an application")

    expanded = expand_named_files(
        [
            ("one.pdf", sample_bytes["APP-001_old_tom_pass.pdf"]),
            ("batch.zip", zip_bytes),
            ("scan.png", image_bytes),
            ("mixed.zip", mixed_zip.getvalue()),
        ]
    )
    assert len(expanded) == len(sample_bytes) + 3
    assert any(name.lower().endswith(".png") for name, _ in expanded)
    assert all(name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")) for name, _ in expanded)


def test_scanned_image_application_is_processed_without_separate_label_upload() -> None:
    result = process_application_file("scanned-application.png", _make_scanned_application_image())
    assert result.filename == "scanned-application.png"
    assert result.overall_status == STATUS_REVIEW
    assert "separate" not in " ".join(result.warnings).lower()


def test_streamlit_bad_zip_upload_renders_review_without_exception() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"))
    app.run(timeout=20)
    app.file_uploader[1].set_value([("bad.zip", b"not a zip file", "application/zip")]).run(timeout=20)
    app.button[0].click().run(timeout=60)

    assert len(app.exception) == 0
    assert app.selectbox[0].label == "Status filter"
    assert any("bad.zip" in str(dataframe.value) for dataframe in app.dataframe)


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
        "docs/TOOLS_USED.md",
        "requirements.txt",
        "packages.txt",
        "Dockerfile",
        ".dockerignore",
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
    assert "!docs/source/f510031.pdf" in gitignore
    assert "__pycache__/" in gitignore
    assert ".pytest_cache/" in gitignore
    assert ".venv/" in gitignore
    assert "uploads/" in gitignore


def test_dockerignore_excludes_source_docs_and_local_artifacts() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "docs/source/*" in dockerignore
    assert "!docs/source/f510031.pdf" in dockerignore
    assert ".git/" in dockerignore
    assert "__pycache__/" in dockerignore
    assert ".pytest_cache/" in dockerignore
    assert ".venv/" in dockerignore
    assert "uploads/" in dockerignore


def _make_scanned_application_image() -> bytes:
    image = Image.new("RGB", (612, 1008), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 592, 988), outline="black")
    draw.text((34, 155), "4. SERIAL NUMBER APP-SCAN", fill="black")
    draw.text((34, 205), "6. BRAND NAME SCANNED SAMPLE", fill="black")
    draw.text((34, 690), "AFFIX COMPLETE SET OF LABELS BELOW", fill="black")
    draw.text((80, 740), "SCANNED SAMPLE 45% Alc./Vol. 750 mL", fill="black")
    draw.multiline_text((80, 790), _wrap(GOVERNMENT_WARNING, 82), fill="black", spacing=2)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _wrap(text: str, width: int) -> str:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(item) + 1 for item in current) + len(word) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)
