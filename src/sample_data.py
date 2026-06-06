"""Synthetic completed application PDF generation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import zipfile

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.constants import GOVERNMENT_WARNING
from src.form_mapping import FORM_REGIONS


SAMPLE_DIR = Path("samples/applications")


@dataclass(frozen=True)
class SampleSpec:
    filename: str
    fields: dict[str, str | bool]
    label_lines: list[str]
    expected_status: str
    note: str
    raster_label: bool = False
    blank_label: bool = False


BASE_FIELDS: dict[str, str | bool] = {
    "product_type": "DISTILLED SPIRITS",
    "brand_name": "OLD TOM GIN",
    "fanciful_name": "Botanical Reserve",
    "applicant_name_address": "Example Distilling Co., 100 Market Street, Portland, OR",
    "mailing_address": "",
    "formula": "F-1001",
    "grape_varietals": "",
    "wine_appellation": "",
    "phone": "202-555-0100",
    "email": "labels@example.test",
    "application_type": "Certificate of Label Approval",
    "item_15": "",
    "class_type": "Gin",
    "alcohol_content": "45% ABV",
    "net_contents": "750 mL",
    "bottler_producer": "Example Distilling Co.",
    "country_of_origin": "",
    "imported": False,
}


def sample_specs() -> list[SampleSpec]:
    good_label = [
        "OLD TOM GIN",
        "Botanical Reserve",
        "DISTILLED SPIRITS",
        "Class/Type: Gin",
        "45% Alc./Vol.",
        "750 mL",
        "Bottled by Example Distilling Co.",
        GOVERNMENT_WARNING,
    ]

    stones_fields = {
        **BASE_FIELDS,
        "serial_number": "APP-002",
        "brand_name": "STONE'S THROW",
        "fanciful_name": "",
        "class_type": "Straight Bourbon Whiskey",
        "alcohol_content": "45% ABV",
        "bottler_producer": "Stone Throw Spirits LLC",
    }
    stones_label = [
        "STONES THROW",
        "DISTILLED SPIRITS",
        "Class/Type: Straight Bourbon Whiskey",
        "90 Proof",
        "750ML",
        "Bottled by Stone Throw Spirits LLC",
        GOVERNMENT_WARNING,
    ]

    return [
        SampleSpec(
            filename="APP-001_old_tom_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-001"},
            label_lines=good_label,
            expected_status="Pass",
            note="Fully passing label with matching application summary and affixed label text.",
        ),
        SampleSpec(
            filename="APP-002_stones_throw_variation.pdf",
            fields=stones_fields,
            label_lines=stones_label,
            expected_status="Pass",
            note="Brand punctuation/case variation should not fail.",
        ),
        SampleSpec(
            filename="APP-003_wrong_abv.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-003"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "40% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Fail",
            note="Application expects 45% ABV but label shows 40% ABV.",
        ),
        SampleSpec(
            filename="APP-004_bad_warning.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-004"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                "Government Warning: Drinking during pregnancy may cause birth defects. Drinking may impair driving.",
            ],
            expected_status="Fail",
            note="Warning heading is title case and the statement is materially altered.",
        ),
        SampleSpec(
            filename="APP-005_low_quality_rotated.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-005"},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Rasterized low-quality rotated label should require human review if OCR is uncertain.",
            raster_label=True,
        ),
        SampleSpec(
            filename="APP-006_missing_label_area.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-006"},
            label_lines=[],
            expected_status="Needs Review",
            note="Application data is present but the affixed label area is blank.",
            blank_label=True,
        ),
    ]


def generate_samples(output_dir: Path = SAMPLE_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for spec in sample_specs():
        path = output_dir / spec.filename
        create_sample_pdf(spec, path)
        generated.append(path)
    create_sample_zip(generated, Path("samples/sample_batch.zip"))
    write_expected_outcomes(Path("samples/expected_outcomes.md"))
    return generated


def create_sample_pdf(spec: SampleSpec, output_path: Path) -> None:
    document = _new_sample_document()
    page = document[0]
    _cover_label_area(page)
    _draw_form_values(page, spec.fields)
    _draw_summary_block(page, spec.fields)
    if spec.blank_label:
        pass
    elif spec.raster_label:
        _draw_raster_label(page, spec.label_lines)
    else:
        _draw_text_label(page, spec.label_lines)
    document.set_metadata({"title": spec.filename, "subject": "Synthetic completed TTB application"})
    document.save(output_path, garbage=4, deflate=True)
    document.close()


def create_sample_zip(pdf_paths: list[Path], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in pdf_paths:
            archive.write(path, arcname=path.name)


def write_expected_outcomes(output_path: Path) -> None:
    lines = [
        "# Expected Sample Outcomes",
        "",
        "| File | Expected status | Purpose |",
        "| --- | --- | --- |",
    ]
    for spec in sample_specs():
        lines.append(f"| `{spec.filename}` | {spec.expected_status} | {spec.note} |")
    lines.extend(
        [
            "",
            "These PDFs are synthetic completed applications. They use a controlled TTB-like one-page form layout so sample coordinates remain deterministic across developer machines.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _new_sample_document() -> fitz.Document:
    document = fitz.open()
    page = document.new_page(width=612, height=1008)
    page.insert_text((170, 48), "APPLICATION FOR LABEL/BOTTLE APPROVAL", fontsize=15, fontname="helv")
    page.insert_text((34, 78), "Synthetic completed TTB application package for verifier testing", fontsize=8, fontname="helv")
    for field_name, region in FORM_REGIONS.items():
        rect = region.to_rect(page.rect)
        page.draw_rect(rect, color=(0, 0, 0), width=0.5)
        if field_name != "label_area":
            page.insert_text((rect.x0 + 3, rect.y0 + 10), region.description, fontsize=6.5, fontname="helv")
    page.insert_text((24, FORM_REGIONS["label_area"].to_rect(page.rect).y0 - 8), "AFFIX COMPLETE SET OF LABELS BELOW", fontsize=8)
    return document


def _draw_form_values(page: fitz.Page, fields: dict[str, str | bool]) -> None:
    for field_name in (
        "serial_number",
        "product_type",
        "brand_name",
        "fanciful_name",
        "applicant_name_address",
        "formula",
        "phone",
        "email",
        "application_type",
        "item_15",
    ):
        value = str(fields.get(field_name, "") or "")
        if not value:
            continue
        rect = FORM_REGIONS[field_name].to_rect(page.rect)
        target = fitz.Rect(rect.x0 + 6, rect.y0 + 13, rect.x1 - 4, rect.y1 - 2)
        page.insert_textbox(target, value, fontsize=7.5, fontname="helv", color=(0, 0, 0))


def _draw_summary_block(page: fitz.Page, fields: dict[str, str | bool]) -> None:
    rect = fitz.Rect(285, 438, 590, 672)
    page.draw_rect(rect, color=(0, 0, 0), fill=(1, 1, 1), width=0.5)
    lines = ["APPLICATION DATA SUMMARY"]
    for key in (
        "serial_number",
        "product_type",
        "brand_name",
        "fanciful_name",
        "applicant_name_address",
        "mailing_address",
        "formula",
        "grape_varietals",
        "wine_appellation",
        "phone",
        "email",
        "application_type",
        "item_15",
        "class_type",
        "alcohol_content",
        "net_contents",
        "bottler_producer",
        "country_of_origin",
        "imported",
    ):
        value = fields.get(key, "")
        lines.append(f"{_display_key(key)}: {value}")
    lines.append("END APPLICATION DATA SUMMARY")
    page.insert_textbox(fitz.Rect(rect.x0 + 5, rect.y0 + 5, rect.x1 - 5, rect.y1 - 5), "\n".join(lines), fontsize=6.2, fontname="helv")


def _draw_text_label(page: fitz.Page, label_lines: list[str]) -> None:
    label_rect = _inner_label_rect(page)
    page.draw_rect(label_rect, color=(0, 0, 0), fill=(1, 1, 1), width=1.2)
    y = label_rect.y0 + 14
    for index, line in enumerate(label_lines):
        if index == 0:
            text_width = fitz.get_text_length(line, fontname="helv", fontsize=17)
            page.insert_text((label_rect.x0 + (label_rect.width - text_width) / 2, y + 18), line, fontsize=17, fontname="helv")
            y += 25
        elif line.startswith("GOVERNMENT WARNING") or line.startswith("Government Warning"):
            page.insert_textbox(fitz.Rect(label_rect.x0 + 12, label_rect.y1 - 72, label_rect.x1 - 12, label_rect.y1 - 12), line, fontsize=5.8, fontname="helv")
        else:
            page.insert_textbox(fitz.Rect(label_rect.x0 + 20, y, label_rect.x1 - 20, y + 16), line, fontsize=8.8, fontname="helv", align=1)
            y += 17


def _draw_raster_label(page: fitz.Page, label_lines: list[str]) -> None:
    label_rect = _inner_label_rect(page)
    image = Image.new("RGB", (820, 360), (238, 238, 232))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 38)
        body_font = ImageFont.truetype("arial.ttf", 21)
        warning_font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        warning_font = ImageFont.load_default()

    draw.rectangle((8, 8, 812, 352), outline=(120, 120, 120), width=2)
    y = 25
    for index, line in enumerate(label_lines):
        font = title_font if index == 0 else warning_font if "WARNING" in line else body_font
        if index == 0:
            draw.text((42, y), line, fill=(75, 75, 72), font=font)
            y += 52
        elif "WARNING" in line:
            draw.multiline_text((28, 258), _wrap(line, 100), fill=(110, 110, 105), font=font, spacing=2)
        else:
            draw.text((70, y), line, fill=(85, 85, 80), font=font)
            y += 28
    image = image.rotate(7, expand=True, fillcolor=(255, 255, 255)).filter(ImageFilter.GaussianBlur(radius=1.15))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(label_rect, stream=buffer.getvalue(), keep_proportion=True)


def _cover_label_area(page: fitz.Page) -> None:
    rect = FORM_REGIONS["label_area"].to_rect(page.rect)
    page.draw_rect(rect, color=None, fill=(1, 1, 1), width=0)


def _inner_label_rect(page: fitz.Page) -> fitz.Rect:
    rect = FORM_REGIONS["label_area"].to_rect(page.rect)
    return fitz.Rect(rect.x0 + 30, rect.y0 + 25, rect.x1 - 30, rect.y1 - 20)


def _display_key(key: str) -> str:
    return key.replace("_", " ").title()


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
