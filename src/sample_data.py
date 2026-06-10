"""Synthetic completed application PDF generation."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
import zipfile

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.constants import GOVERNMENT_WARNING
from src.form_mapping import FORM_REGIONS


SAMPLE_DIR = Path("samples/applications")
SOURCE_FORM = Path("docs/source/f510031.pdf")
SOURCE_LABEL_RECT = (24.6108, 681.248, 589.351, 979.0804)


@dataclass(frozen=True)
class SampleSpec:
    filename: str
    fields: dict[str, str | bool]
    label_lines: list[str]
    expected_status: str
    note: str
    raster_label: bool = False
    artwork_label: bool = False
    blank_label: bool = False
    include_formula_approval: bool = True
    formula_approval_id: str | None = None
    formula_approval_unit: str = "% by Volume"
    formula_approval_identifier_label: str = "TTB Formula ID"
    formula_approval_alcohol_label: str = "Alcohol Content of Finished Product"
    extra_formula_approvals_before: tuple[dict[str, str | bool], ...] = ()
    expected_status_without_ocr: str | None = None
    instruction_pages_before_supplemental_label: int = 0


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

    small_batch_fields = {
        **BASE_FIELDS,
        "brand_name": "COPPER RIDGE VODKA",
        "fanciful_name": "",
        "class_type": "Vodka",
        "formula": "F-2001",
        "alcohol_content": "40% ABV",
        "net_contents": "1000 mL",
        "bottler_producer": "Copper Ridge Distilling Co.",
    }
    copper_label = [
        "COPPER RIDGE VODKA",
        "DISTILLED SPIRITS",
        "Class/Type: Vodka",
        "40% Alc./Vol.",
        "1000 mL",
        "Bottled by Copper Ridge Distilling Co.",
        GOVERNMENT_WARNING,
    ]
    bourbon_fields = {
        **BASE_FIELDS,
        "brand_name": "RIVER BEND BOURBON",
        "fanciful_name": "Reserve Selection",
        "class_type": "Straight Bourbon Whiskey",
        "formula": "F-3001",
        "alcohol_content": "50% ABV",
        "bottler_producer": "River Bend Spirits LLC",
    }
    bourbon_label = [
        "RIVER BEND BOURBON",
        "Reserve Selection",
        "DISTILLED SPIRITS",
        "Class/Type: Straight Bourbon Whiskey",
        "100 Proof",
        "750 mL",
        "Bottled by River Bend Spirits LLC",
        GOVERNMENT_WARNING,
    ]
    wine_fields = {
        **BASE_FIELDS,
        "product_type": "WINE",
        "brand_name": "SUNSET HOLLOW",
        "fanciful_name": "Red Blend",
        "formula": "W-1001",
        "grape_varietals": "Cabernet Sauvignon; Merlot",
        "wine_appellation": "California",
        "class_type": "Red Wine",
        "alcohol_content": "13.5% ABV",
        "net_contents": "750 mL",
        "bottler_producer": "Sunset Hollow Winery",
    }
    wine_label = [
        "SUNSET HOLLOW",
        "Red Blend",
        "WINE",
        "Class/Type: Red Wine",
        "13.5% Alc./Vol.",
        "750 mL",
        "Bottled by Sunset Hollow Winery",
        GOVERNMENT_WARNING,
    ]
    malt_fields = {
        **BASE_FIELDS,
        "product_type": "MALT BEVERAGES",
        "brand_name": "HARBOR LIGHT LAGER",
        "fanciful_name": "",
        "formula": "MB-1001",
        "class_type": "Flavored Malt Beverage",
        "alcohol_content": "5.5% ABV",
        "net_contents": "12 fl oz",
        "bottler_producer": "Harbor Light Brewing Co.",
    }
    malt_label = [
        "HARBOR LIGHT LAGER",
        "MALT BEVERAGES",
        "Class/Type: Flavored Malt Beverage",
        "5.5% Alc./Vol.",
        "12 fl oz",
        "Brewed by Harbor Light Brewing Co.",
        GOVERNMENT_WARNING,
    ]

    return [
        SampleSpec(
            filename="APP-001_old_tom_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-001"},
            label_lines=good_label,
            expected_status="Pass",
            note="Fully passing label with matching approved formula alcohol content, application summary, and affixed label text.",
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
            note="Approved formula expects 45% ABV but label shows 40% ABV.",
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
        SampleSpec(
            filename="APP-007_artwork_vodka_pass.pdf",
            fields={**small_batch_fields, "serial_number": "APP-007"},
            label_lines=copper_label,
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="High-contrast raster label with color artwork should pass when OCR is available.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-008_artwork_brand_mismatch_fail.pdf",
            fields={**small_batch_fields, "serial_number": "APP-008", "bottler_producer": "North Coast Bottling Co."},
            label_lines=[
                line.replace("COPPER RIDGE VODKA", "MOUNTAIN FORK VODKA").replace(
                    "Copper Ridge Distilling Co.", "North Coast Bottling Co."
                )
                for line in copper_label
            ],
            expected_status="Fail",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label has a materially different brand name.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-009_artwork_wrong_net_contents_fail.pdf",
            fields={**small_batch_fields, "serial_number": "APP-009"},
            label_lines=[line.replace("1000 mL", "750 mL") for line in copper_label],
            expected_status="Fail",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label shows a different net contents value.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-010_artwork_title_case_warning_fail.pdf",
            fields={**small_batch_fields, "serial_number": "APP-010"},
            label_lines=[
                *copper_label[:-1],
                "Government Warning: Drinking during pregnancy may cause birth defects. Drinking may impair driving.",
            ],
            expected_status="Fail",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label has a title-case and altered government warning.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-011_artwork_missing_warning_fail.pdf",
            fields={**small_batch_fields, "serial_number": "APP-011"},
            label_lines=copper_label[:-1],
            expected_status="Fail",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label omits the required government warning.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-012_artwork_low_contrast_review.pdf",
            fields={**small_batch_fields, "serial_number": "APP-012"},
            label_lines=copper_label,
            expected_status="Needs Review",
            note="Color-artwork label is intentionally low contrast and should require review.",
            artwork_label=True,
            raster_label=True,
        ),
        SampleSpec(
            filename="APP-013_missing_formula_support_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-013", "formula": "F-9999"},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Item 9 has a Formula ID but the package lacks the matching formula approval page.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-014_formula_range_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-014", "formula": "F-1400", "alcohol_content": "25-30% ABV"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "27% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Approved formula final alcohol range covers the label ABV.",
        ),
        SampleSpec(
            filename="APP-015_formula_range_fail.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-015", "formula": "F-1500", "alcohol_content": "25-30% ABV"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "35% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Fail",
            note="Approved formula final alcohol range does not cover the label ABV.",
        ),
        SampleSpec(
            filename="APP-016_bourbon_proof_artwork_pass.pdf",
            fields={**bourbon_fields, "serial_number": "APP-016"},
            label_lines=bourbon_label,
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork bourbon label uses proof rather than percent ABV.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-017_wine_artwork_pass.pdf",
            fields={**wine_fields, "serial_number": "APP-017"},
            label_lines=wine_label,
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork wine label exercises wine product type and appellation context.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-018_malt_artwork_pass.pdf",
            fields={**malt_fields, "serial_number": "APP-018"},
            label_lines=malt_label,
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork malt beverage label exercises malt product type and fl oz normalization.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-019_import_country_missing_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-019", "imported": True, "country_of_origin": ""},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Imported product has no extracted country of origin.",
        ),
        SampleSpec(
            filename="APP-020_item15_missing_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-020", "item_15": "BOTTLE EMBOSSED WITH LOT CODE"},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Item 15 container text is supplied in the application but not found on the label.",
        ),
        SampleSpec(
            filename="APP-021_apostrophe_artwork_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-021", "brand_name": "DISTILLER'S CUT", "fanciful_name": ""},
            label_lines=[
                "DISTILLERS CUT",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label confirms apostrophe-insensitive brand matching.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-022_artwork_wrong_bottler_review.pdf",
            fields={**small_batch_fields, "serial_number": "APP-022"},
            label_lines=[line.replace("Copper Ridge Distilling Co.", "Canyon Creek Spirits") for line in copper_label],
            expected_status="Needs Review",
            expected_status_without_ocr="Needs Review",
            note="Color-artwork label has a bottler/producer difference that should be reviewed.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-023_no_formula_required_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-023",
                "brand_name": "VALLEY TABLE WINE",
                "fanciful_name": "",
                "formula": "NO FORMULA REQUIRED",
                "class_type": "Red Wine",
                "alcohol_content": "13% ABV",
            },
            label_lines=[
                "VALLEY TABLE WINE",
                "WINE",
                "Class/Type: Red Wine",
                "13% Alc./Vol.",
                "750 mL",
                "Bottled by Sunset Hollow Winery",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Item 9 states no formula is required and the label still matches application alcohol content.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-024_import_country_artwork_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-024",
                "brand_name": "CASA VERDE TEQUILA",
                "fanciful_name": "Blanco",
                "formula": "F-2400",
                "class_type": "Tequila",
                "alcohol_content": "40% ABV",
                "bottler_producer": "Borderland Imports LLC",
                "country_of_origin": "Mexico",
                "imported": True,
            },
            label_lines=[
                "CASA VERDE TEQUILA",
                "Blanco",
                "DISTILLED SPIRITS",
                "Class/Type: Tequila",
                "40% Alc./Vol.",
                "750 mL",
                "Product of Mexico",
                "Imported by Borderland Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Imported color-artwork label includes the expected country of origin.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-025_import_country_missing_on_label_review.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-025",
                "brand_name": "CASA VERDE TEQUILA",
                "fanciful_name": "Blanco",
                "formula": "F-2500",
                "class_type": "Tequila",
                "alcohol_content": "40% ABV",
                "bottler_producer": "Borderland Imports LLC",
                "country_of_origin": "Mexico",
                "imported": True,
            },
            label_lines=[
                "CASA VERDE TEQUILA",
                "Blanco",
                "DISTILLED SPIRITS",
                "Class/Type: Tequila",
                "40% Alc./Vol.",
                "750 mL",
                "Imported by Borderland Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Imported application has an expected country of origin that is not clearly on the label.",
        ),
        SampleSpec(
            filename="APP-026_missing_expected_brand_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-026", "brand_name": ""},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Required brand value is missing from the application extraction and must not be invented from label OCR.",
        ),
        SampleSpec(
            filename="APP-027_product_type_mismatch_fail.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-027"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "MALT BEVERAGES",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Fail",
            note="Readable label shows a different product type than the completed application.",
        ),
        SampleSpec(
            filename="APP-028_formula_document_missing_final_alcohol_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-028", "formula": "F-2800", "alcohol_content": ""},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Matching formula approval document is present but lacks extractable final alcohol content.",
        ),
        SampleSpec(
            filename="APP-029_formula_id_prefix_mismatch_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-029", "formula": "F-2900"},
            label_lines=good_label,
            expected_status="Needs Review",
            note="Formula approval page has a longer prefix-sharing ID and must not satisfy the Item 9 Formula ID.",
            formula_approval_id="F-29001",
        ),
        SampleSpec(
            filename="APP-030_wine_cask_spirits_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-030",
                "brand_name": "CELLAR CASK WHISKEY",
                "fanciful_name": "Wine Cask Finish",
                "formula": "F-3000",
                "class_type": "Whiskey",
                "alcohol_content": "45% ABV",
                "bottler_producer": "Cellar Cask Distilling Co.",
            },
            label_lines=[
                "CELLAR CASK WHISKEY",
                "Wine Cask Finish",
                "DISTILLED SPIRITS",
                "Class/Type: Whiskey",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Cellar Cask Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            expected_status_without_ocr="Needs Review",
            note="Distilled spirits label mentions wine as a cask-finish descriptor without changing product type.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-031_tequila_agave_missing_abv_review.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-031",
                "brand_name": "CASA VERDE TEQUILA",
                "fanciful_name": "Blanco",
                "formula": "F-3100",
                "class_type": "Tequila",
                "alcohol_content": "40% ABV",
                "bottler_producer": "Borderland Imports LLC",
                "country_of_origin": "Mexico",
                "imported": True,
            },
            label_lines=[
                "CASA VERDE TEQUILA",
                "Blanco",
                "100% Agave",
                "DISTILLED SPIRITS",
                "Class/Type: Tequila",
                "750 mL",
                "Product of Mexico",
                "Imported by Borderland Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Label has a non-alcohol percentage but no readable ABV/proof statement.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-032_low_proof_liqueur_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-032",
                "brand_name": "ORCHARD CREAM LIQUEUR",
                "fanciful_name": "Vanilla Pear",
                "formula": "L-4001",
                "class_type": "Liqueur",
                "alcohol_content": "40 Proof",
                "bottler_producer": "Orchard House Spirits LLC",
            },
            label_lines=[
                "ORCHARD CREAM LIQUEUR",
                "Vanilla Pear",
                "DISTILLED SPIRITS",
                "Class/Type: Liqueur",
                "20% Alc./Vol.",
                "750 mL",
                "Bottled by Orchard House Spirits LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Approved formula gives final alcohol as 40 proof, which should normalize to 20% ABV.",
            formula_approval_unit="Proof",
        ),
        SampleSpec(
            filename="APP-033_serving_size_missing_net_contents_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-033"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "Serving size 50 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            expected_status_without_ocr="Needs Review",
            note="Label has a serving-size volume but no clear net contents statement, so net contents need review rather than a false mismatch.",
            artwork_label=True,
        ),
        SampleSpec(
            filename="APP-034_formula_ttb_id_number_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-034", "formula": "DS-3400", "alcohol_content": "46% ABV"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "46% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Formula support uses a TTB ID Number label instead of a TTB Formula ID label.",
            formula_approval_identifier_label="TTB ID Number",
        ),
        SampleSpec(
            filename="APP-035_alc_by_vol_order_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-035", "formula": "F-3500"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "Alc. 45% by Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content as Alc. value by Vol., which should normalize as ABV.",
        ),
        SampleSpec(
            filename="APP-036_missing_fanciful_name_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-036", "formula": "F-3600"},
            label_lines=[
                "OLD TOM GIN",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Application supplies a fanciful name, but the label does not clearly show it.",
        ),
        SampleSpec(
            filename="APP-037_proof_before_value_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-037", "formula": "F-3700"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "Proof 90",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states proof before the value, which should normalize to ABV.",
        ),
        SampleSpec(
            filename="APP-038_alcohol_by_volume_order_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-038", "formula": "F-3800"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "Alcohol 45% by Volume",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol value before by-volume wording, which should normalize as ABV.",
        ),
        SampleSpec(
            filename="APP-039_brand_only_in_bottler_line_fail.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-039",
                "formula": "F-3900",
                "bottler_producer": "Old Tom Gin",
            },
            label_lines=[
                "MOUNTAIN FORK VODKA",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Old Tom Gin",
                GOVERNMENT_WARNING,
            ],
            expected_status="Fail",
            note="Expected brand appears only in the bottler line while the primary brand is materially different.",
        ),
        SampleSpec(
            filename="APP-040_class_type_only_in_brand_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-040", "formula": "F-4000"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Class/type value appears only inside the brand name and is not clearly stated as class/type.",
        ),
        SampleSpec(
            filename="APP-041_bottler_only_in_brand_review.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-041",
                "formula": "F-4100",
                "brand_name": "EXAMPLE DISTILLING CO.",
                "fanciful_name": "House Gin",
                "bottler_producer": "Example Distilling Co.",
            },
            label_lines=[
                "EXAMPLE DISTILLING CO.",
                "House Gin",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Expected bottler/producer appears as brand text only, with no responsible-party statement.",
        ),
        SampleSpec(
            filename="APP-042_produced_and_bottled_by_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-042", "formula": "F-4200"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Produced and bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Responsible-party statement uses combined produced-and-bottled wording.",
        ),
        SampleSpec(
            filename="APP-043_ocr_damaged_warning_heading_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-043", "formula": "F-4300"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING.replace("GOVERNMENT WARNING", "G0VERNMENT WARNlNG"),
            ],
            expected_status="Needs Review",
            note="Warning statement is close to canonical, but the all-caps heading has OCR-like character damage.",
        ),
        SampleSpec(
            filename="APP-044_conflicting_abv_values_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-044", "formula": "F-4400"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "Back label states 40% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Label contains both matching and conflicting alcohol-content values.",
        ),
        SampleSpec(
            filename="APP-045_conflicting_net_contents_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-045", "formula": "F-4500"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "Net Contents 750 mL",
                "Back label states 1 L",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Label contains both matching and conflicting net-contents values.",
        ),
        SampleSpec(
            filename="APP-046_brand_word_order_mismatch_fail.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-046", "formula": "F-4600"},
            label_lines=[
                "TOM OLD GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Fail",
            note="Brand tokens are reordered, which should not pass as a harmless brand variation.",
        ),
        SampleSpec(
            filename="APP-047_wine_brand_contains_spirit_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-047",
                "brand_name": "SPIRIT HILL WINE",
                "fanciful_name": "Estate Red",
                "formula": "W-4700",
                "bottler_producer": "Spirit Hill Winery",
            },
            label_lines=[
                "SPIRIT HILL WINE",
                "Estate Red",
                "WINE",
                "Class/Type: Red Wine",
                "13.5% Alc./Vol.",
                "750 mL",
                "Bottled by Spirit Hill Winery",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Wine brand contains the word Spirit, but explicit wine label text controls product-type matching.",
        ),
        SampleSpec(
            filename="APP-048_class_type_substring_review.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-048", "formula": "F-4800"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Ginger Liqueur",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Expected class/type Gin appears only as a word fragment inside Ginger and must not pass.",
        ),
        SampleSpec(
            filename="APP-049_product_type_brand_word_review.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-049",
                "brand_name": "SPIRIT HILL ESTATE RED",
                "fanciful_name": "Estate Red",
                "formula": "W-4900",
                "bottler_producer": "Spirit Hill Winery",
            },
            label_lines=[
                "SPIRIT HILL ESTATE RED",
                "Estate Red",
                "13.5% Alc./Vol.",
                "750 mL",
                "Bottled by Spirit Hill Winery",
                GOVERNMENT_WARNING,
            ],
            expected_status="Needs Review",
            note="Product-type word appears only in the brand while explicit wine/class wording is missing.",
        ),
        SampleSpec(
            filename="APP-050_product_type_first_line_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-050", "formula": "F-5000"},
            label_lines=[
                "DISTILLED SPIRITS",
                "OLD TOM GIN",
                "Botanical Reserve",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Explicit product type appears before the brand and should still verify.",
        ),
        SampleSpec(
            filename="APP-051_us_origin_abbreviation_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-051",
                "formula": "F-5100",
                "imported": True,
                "country_of_origin": "United States",
            },
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Product of U.S.A.",
                "Imported by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported origin uses U.S.A. abbreviation for application country United States.",
        ),
        SampleSpec(
            filename="APP-052_centiliter_net_contents_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-052", "formula": "F-5200"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "75 cL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents in centiliters, equivalent to the application 750 mL value.",
        ),
        SampleSpec(
            filename="APP-053_percent_alc_by_vol_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-053", "formula": "F-5300"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc. by Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content with the common percent Alc. by Vol. wording.",
        ),
        SampleSpec(
            filename="APP-054_stones_throw_case_pass.pdf",
            fields={
                **stones_fields,
                "serial_number": "APP-054",
                "brand_name": "Stone's Throw",
                "formula": "F-5400",
            },
            label_lines=[
                "STONE'S THROW",
                "DISTILLED SPIRITS",
                "Class/Type: Straight Bourbon Whiskey",
                "90 Proof",
                "750ML",
                "Bottled by Stone Throw Spirits LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Assignment example: application brand Stone's Throw matches label brand STONE'S THROW despite capitalization.",
        ),
        SampleSpec(
            filename="APP-055_produce_of_origin_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-055",
                "brand_name": "CHATEAU LUMIERE",
                "fanciful_name": "Red Blend",
                "formula": "W-5500",
                "country_of_origin": "France",
                "imported": True,
                "bottler_producer": "Example Imports LLC",
            },
            label_lines=[
                "CHATEAU LUMIERE",
                "Red Blend",
                "WINE",
                "Class/Type: Red Wine",
                "13.5% Alc./Vol.",
                "750 mL",
                "Produce of France",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported wine uses common Produce of France origin wording.",
        ),
        SampleSpec(
            filename="APP-056_pint_net_contents_pass.pdf",
            fields={
                **malt_fields,
                "serial_number": "APP-056",
                "formula": "MB-5600",
                "net_contents": "500 mL",
            },
            label_lines=[
                "HARBOR LIGHT LAGER",
                "MALT BEVERAGES",
                "Class/Type: Flavored Malt Beverage",
                "5.5% Alc./Vol.",
                "1 Pint 0.9 FL OZ",
                "Brewed by Harbor Light Brewing Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents as a compound pint and fluid-ounce amount equivalent to 500 mL.",
        ),
        SampleSpec(
            filename="APP-057_plain_ounce_net_contents_pass.pdf",
            fields={**malt_fields, "serial_number": "APP-057", "formula": "MB-5700"},
            label_lines=[
                "HARBOR LIGHT LAGER",
                "MALT BEVERAGES",
                "Class/Type: Flavored Malt Beverage",
                "5.5% Alc./Vol.",
                "12 OZ",
                "Brewed by Harbor Light Brewing Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents as plain 12 OZ, equivalent to the application 12 fl oz value.",
        ),
        SampleSpec(
            filename="APP-058_distilled_by_responsible_party_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-058", "formula": "F-5800"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Distilled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Distilled spirits label uses Distilled by as responsible-party wording.",
        ),
        SampleSpec(
            filename="APP-059_beer_product_type_first_line_pass.pdf",
            fields={
                **malt_fields,
                "serial_number": "APP-059",
                "brand_name": "SUNNY FARMS",
                "fanciful_name": "Crisp Malt",
                "formula": "MB-5900",
                "class_type": "Specialty",
            },
            label_lines=[
                "BEER",
                "SUNNY FARMS",
                "Crisp Malt",
                "Class/Type: Specialty",
                "5.5% Alc./Vol.",
                "12 fl oz",
                "Brewed by Harbor Light Brewing Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Malt beverage label puts BEER before a brand that does not itself contain beer-style product words.",
        ),
        SampleSpec(
            filename="APP-060_blended_by_responsible_party_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-060", "formula": "F-6000"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Blended by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Distilled spirits label uses Blended by as responsible-party wording.",
        ),
        SampleSpec(
            filename="APP-061_bottled_for_responsible_party_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-061", "formula": "F-6100"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled for Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Distilled spirits label uses Bottled for as responsible-party wording.",
        ),
        SampleSpec(
            filename="APP-062_fractional_pint_net_contents_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-062", "formula": "F-6200", "net_contents": "8 fl oz"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "1/2 Pint",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents as fractional 1/2 Pint, equivalent to the application 8 fl oz value.",
        ),
        SampleSpec(
            filename="APP-063_written_net_contents_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-063", "formula": "F-6300"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "Seven Hundred Fifty Milliliters",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label spells out net contents as Seven Hundred Fifty Milliliters, equivalent to the application 750 mL value.",
        ),
        SampleSpec(
            filename="APP-064_alcohol_by_vol_abbreviation_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-064", "formula": "F-6400"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "Alcohol 45% by Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content as Alcohol 45% by Vol., which should normalize as ABV.",
        ),
        SampleSpec(
            filename="APP-065_degrees_proof_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-065", "formula": "F-6500"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "90 degrees proof",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states proof with degrees wording, which should normalize to 45% ABV.",
        ),
        SampleSpec(
            filename="APP-066_class_type_implies_distilled_spirits_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-066", "formula": "F-6600"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Distilled spirits product type is supported by a clear Gin class/type statement even without the literal DISTILLED SPIRITS phrase.",
        ),
        SampleSpec(
            filename="APP-067_dual_unit_net_contents_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-067", "formula": "F-6700"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "Net Contents 750 mL / 25.4 FL OZ",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states both metric and rounded U.S. customary net contents for the same 750 mL package.",
        ),
        SampleSpec(
            filename="APP-068_imported_by_from_origin_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-068",
                "brand_name": "CHATEAU LUMIERE",
                "fanciful_name": "Estate Red",
                "formula": "NO FORMULA REQUIRED",
                "alcohol_content": "13% ABV",
                "bottler_producer": "Example Imports LLC",
                "country_of_origin": "France",
                "imported": True,
            },
            label_lines=[
                "CHATEAU LUMIERE",
                "Estate Red",
                "WINE",
                "Class/Type: Red Wine",
                "13% Alc./Vol.",
                "750 mL",
                "Imported by Example Imports LLC from France",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported wine origin is stated as Imported by Example Imports LLC from France.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-069_alcohol_colon_by_volume_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-069", "formula": "F-6900"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "Alcohol: 45% by Volume",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content with colon wording, Alcohol: 45% by Volume.",
        ),
        SampleSpec(
            filename="APP-070_comma_thousands_net_contents_pass.pdf",
            fields={**small_batch_fields, "serial_number": "APP-070", "formula": "F-7000"},
            label_lines=[
                "COPPER RIDGE VODKA",
                "DISTILLED SPIRITS",
                "Class/Type: Vodka",
                "40% Alc./Vol.",
                "Net Contents 1,000 mL",
                "Bottled by Copper Ridge Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents with a comma thousands separator, 1,000 mL.",
        ),
        SampleSpec(
            filename="APP-071_hard_cider_wine_product_type_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-071",
                "brand_name": "ORCHARD RIDGE",
                "fanciful_name": "Dry Apple",
                "formula": "NO FORMULA REQUIRED",
                "class_type": "Hard Cider",
                "alcohol_content": "6.8% ABV",
                "net_contents": "355 mL",
                "bottler_producer": "Orchard Ridge Ciderworks",
            },
            label_lines=[
                "ORCHARD RIDGE",
                "Dry Apple",
                "HARD CIDER",
                "Class/Type: Hard Cider",
                "6.8% Alc./Vol.",
                "355 mL",
                "Bottled by Orchard Ridge Ciderworks",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Wine product type is supported by hard-cider label and class/type wording.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-072_uk_origin_abbreviation_pass.pdf",
            fields={
                **wine_fields,
                "serial_number": "APP-072",
                "brand_name": "THAMES CELLARS",
                "fanciful_name": "Reserve Red",
                "formula": "NO FORMULA REQUIRED",
                "alcohol_content": "13% ABV",
                "bottler_producer": "Example Imports LLC",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "THAMES CELLARS",
                "Reserve Red",
                "WINE",
                "Class/Type: Red Wine",
                "13% Alc./Vol.",
                "750 mL",
                "Product of U.K.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported wine origin uses U.K. abbreviation for application country United Kingdom.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-073_compact_percent_vol_pass.pdf",
            fields={**wine_fields, "serial_number": "APP-073", "formula": "W-7300"},
            label_lines=[
                "SUNSET HOLLOW",
                "Red Blend",
                "WINE",
                "Class/Type: Red Wine",
                "13.5% vol",
                "750 mL",
                "Bottled by Sunset Hollow Winery",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content with compact percent-vol wording.",
        ),
        SampleSpec(
            filename="APP-074_ampersand_brand_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-074",
                "brand_name": "SMITH & SONS",
                "fanciful_name": "Heritage Reserve",
                "formula": "F-7400",
                "class_type": "Bourbon Whiskey",
                "alcohol_content": "45% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Smith and Sons Distilling Co.",
            },
            label_lines=[
                "SMITH AND SONS",
                "Heritage Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Bourbon Whiskey",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Smith and Sons Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Brand ampersand in the application matches AND on the label as a harmless text variation.",
        ),
        SampleSpec(
            filename="APP-075_company_abbreviation_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-075",
                "brand_name": "ACME DISTILLING CO.",
                "fanciful_name": "Fieldhouse Vodka",
                "formula": "F-7500",
                "class_type": "Vodka",
                "alcohol_content": "40% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Acme Distilling Co.",
            },
            label_lines=[
                "ACME DISTILLING COMPANY",
                "Fieldhouse Vodka",
                "DISTILLED SPIRITS",
                "Class/Type: Vodka",
                "40% Alc./Vol.",
                "750 mL",
                "Bottled by Acme Distilling Company",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Brand and bottler Co. abbreviations match Company on the label as harmless legal-suffix variations.",
        ),
        SampleSpec(
            filename="APP-076_saint_abbreviation_brand_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-076",
                "brand_name": "SAINT GEORGE GIN",
                "fanciful_name": "Coastal Dry",
                "formula": "F-7600",
                "class_type": "Gin",
                "alcohol_content": "45% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Saint George Distilling Co.",
            },
            label_lines=[
                "ST. GEORGE GIN",
                "Coastal Dry",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by St. George Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Brand Saint abbreviation in the label matches Saint in the application as a harmless word variation.",
        ),
        SampleSpec(
            filename="APP-077_percent_by_volume_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-077", "formula": "F-7700"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% by volume",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states alcohol content with percent-by-volume shorthand.",
        ),
        SampleSpec(
            filename="APP-078_decimal_comma_litre_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-078", "formula": "F-7800"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "0,75 L",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents as decimal-comma litres.",
        ),
        SampleSpec(
            filename="APP-079_british_millilitres_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-079", "formula": "F-7900"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 millilitres",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Label states net contents with British millilitres spelling.",
        ),
        SampleSpec(
            filename="APP-080_scotland_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-080",
                "brand_name": "HIGHLAND FORGE WHISKY",
                "fanciful_name": "",
                "formula": "F-8000",
                "class_type": "Whisky",
                "alcohol_content": "46% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Highland Forge Distilling Co.",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "HIGHLAND FORGE WHISKY",
                "DISTILLED SPIRITS",
                "Class/Type: Whisky",
                "46% Alc./Vol.",
                "750 mL",
                "Product of Scotland",
                "Bottled by Highland Forge Distilling Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported origin names Scotland while the application country is United Kingdom.",
        ),
        SampleSpec(
            filename="APP-081_republic_ireland_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-081",
                "brand_name": "EMERALD GLEN WHISKEY",
                "fanciful_name": "",
                "formula": "F-8100",
                "class_type": "Irish Whiskey",
                "alcohol_content": "40% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Emerald Glen Distilling Co.",
                "country_of_origin": "Ireland",
                "imported": True,
            },
            label_lines=[
                "EMERALD GLEN WHISKEY",
                "DISTILLED SPIRITS",
                "Class/Type: Irish Whiskey",
                "40% Alc./Vol.",
                "750 mL",
                "Product of Republic of Ireland",
                "Bottled by Emerald Glen Distilling Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported origin names Republic of Ireland while the application country is Ireland.",
        ),
        SampleSpec(
            filename="APP-082_finished_alcohol_formula_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-082", "formula": "F-8200"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Formula support states final ABV as Finished Alcohol Content.",
            formula_approval_alcohol_label="Finished Alcohol Content",
        ),
        SampleSpec(
            filename="APP-083_final_product_alcohol_formula_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-083",
                "formula": "F-8300",
                "alcohol_content": "40 Proof",
            },
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "40 Proof",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Formula support states final proof as Final Product Alcohol Content.",
            formula_approval_unit="Proof",
            formula_approval_alcohol_label="Final Product Alcohol Content",
        ),
        SampleSpec(
            filename="APP-084_distilled_in_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-084",
                "brand_name": "HIGHLAND FORGE WHISKY",
                "fanciful_name": "",
                "formula": "F-8400",
                "class_type": "Whisky",
                "alcohol_content": "46% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Highland Forge Distilling Co.",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "HIGHLAND FORGE WHISKY",
                "DISTILLED SPIRITS",
                "Class/Type: Whisky",
                "46% Alc./Vol.",
                "750 mL",
                "Distilled in Scotland",
                "Bottled by Highland Forge Distilling Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported spirits origin is stated as Distilled in Scotland for a United Kingdom application country.",
        ),
        SampleSpec(
            filename="APP-085_brewed_in_origin_pass.pdf",
            fields={
                **malt_fields,
                "serial_number": "APP-085",
                "brand_name": "LOWLAND ABBEY ALE",
                "fanciful_name": "",
                "formula": "MB-8500",
                "class_type": "Ale",
                "bottler_producer": "Lowland Abbey Brewing Co.",
                "country_of_origin": "Belgium",
                "imported": True,
            },
            label_lines=[
                "LOWLAND ABBEY ALE",
                "MALT BEVERAGE",
                "Class/Type: Ale",
                "5.5% Alc./Vol.",
                "12 fl oz",
                "Brewed in Belgium",
                "Brewed by Lowland Abbey Brewing Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported malt beverage origin is stated as Brewed in Belgium.",
        ),
        SampleSpec(
            filename="APP-086_packed_by_responsible_party_pass.pdf",
            fields={**wine_fields, "serial_number": "APP-086", "formula": "W-8600"},
            label_lines=[
                "SUNSET HOLLOW",
                "Red Blend",
                "WINE",
                "Class/Type: Red Wine",
                "13.5% Alc./Vol.",
                "750 mL",
                "Packed by Sunset Hollow Winery",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Wine label uses Packed by as responsible-party wording.",
        ),
        SampleSpec(
            filename="APP-087_blended_in_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-087",
                "brand_name": "HIGHLAND FORGE WHISKY",
                "fanciful_name": "",
                "formula": "F-8700",
                "class_type": "Blended Scotch Whisky",
                "alcohol_content": "43% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Highland Forge Blenders Ltd.",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "HIGHLAND FORGE WHISKY",
                "DISTILLED SPIRITS",
                "Class/Type: Blended Scotch Whisky",
                "43% Alc./Vol.",
                "750 mL",
                "Blended in Scotland",
                "Bottled by Highland Forge Blenders Ltd.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported spirits origin is stated as Blended in Scotland for a United Kingdom application country.",
        ),
        SampleSpec(
            filename="APP-088_distilled_and_bottled_in_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-088",
                "brand_name": "HIGHLAND FORGE WHISKY",
                "fanciful_name": "",
                "formula": "F-8800",
                "class_type": "Scotch Whisky",
                "alcohol_content": "46% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Highland Forge Distilling Co.",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "HIGHLAND FORGE WHISKY",
                "DISTILLED SPIRITS",
                "Class/Type: Scotch Whisky",
                "46% Alc./Vol.",
                "750 mL",
                "Distilled and bottled in Scotland",
                "Bottled by Highland Forge Distilling Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported spirits origin is stated as Distilled and bottled in Scotland for a United Kingdom application country.",
        ),
        SampleSpec(
            filename="APP-089_distilled_matured_bottled_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-089",
                "brand_name": "HIGHLAND FORGE WHISKY",
                "fanciful_name": "",
                "formula": "F-8900",
                "class_type": "Single Malt Scotch Whisky",
                "alcohol_content": "46% ABV",
                "net_contents": "750 mL",
                "bottler_producer": "Highland Forge Distilling Co.",
                "country_of_origin": "United Kingdom",
                "imported": True,
            },
            label_lines=[
                "HIGHLAND FORGE WHISKY",
                "DISTILLED SPIRITS",
                "Class/Type: Single Malt Scotch Whisky",
                "46% Alc./Vol.",
                "750 mL",
                "Distilled, matured and bottled in Scotland",
                "Bottled by Highland Forge Distilling Co.",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported spirits origin is stated as Distilled, matured and bottled in Scotland for a United Kingdom application country.",
        ),
        SampleSpec(
            filename="APP-090_ipa_class_type_malt_pass.pdf",
            fields={
                **malt_fields,
                "serial_number": "APP-090",
                "brand_name": "HARBOR LIGHT",
                "fanciful_name": "",
                "formula": "MB-9000",
                "class_type": "IPA",
                "alcohol_content": "6.5% ABV",
                "net_contents": "12 fl oz",
                "bottler_producer": "Harbor Light Brewing Co.",
            },
            label_lines=[
                "HARBOR LIGHT",
                "Class/Type: IPA",
                "6.5% Alc./Vol.",
                "12 fl oz",
                "Brewed by Harbor Light Brewing Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Malt beverage product type is inferred from IPA class/type shorthand.",
        ),
        SampleSpec(
            filename="APP-091_canned_by_responsible_party_pass.pdf",
            fields={
                **malt_fields,
                "serial_number": "APP-091",
                "brand_name": "HARBOR LIGHT LAGER",
                "fanciful_name": "",
                "formula": "MB-9100",
                "class_type": "Lager",
                "alcohol_content": "5.5% ABV",
                "net_contents": "12 fl oz",
                "bottler_producer": "Harbor Light Brewing Co.",
            },
            label_lines=[
                "HARBOR LIGHT LAGER",
                "MALT BEVERAGE",
                "Class/Type: Lager",
                "5.5% Alc./Vol.",
                "12 fl oz",
                "Brewed and canned by Harbor Light Brewing Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Malt beverage label uses Brewed and canned by as responsible-party wording.",
        ),
        SampleSpec(
            filename="APP-092_formula_id_separator_variant_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-092", "formula": "F 9200"},
            label_lines=[
                "OLD TOM GIN",
                "Botanical Reserve",
                "DISTILLED SPIRITS",
                "Class/Type: Gin",
                "45% Alc./Vol.",
                "750 mL",
                "Bottled by Example Distilling Co.",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Application Formula ID uses a space while the submitted formula approval uses a hyphenated ID.",
            formula_approval_id="F-9200",
        ),
        SampleSpec(
            filename="APP-093_supplemental_label_after_instructions_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-093", "formula": "F-9300"},
            label_lines=good_label,
            expected_status="Pass",
            note="Page-one label area is blank, attached instructions are skipped, and a later supplemental label page is verified.",
            blank_label=True,
            instruction_pages_before_supplemental_label=3,
        ),
        SampleSpec(
            filename="APP-094_long_attachment_before_label_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-094", "formula": "F-9400"},
            label_lines=good_label,
            expected_status="Pass",
            note="Supplemental label appears after more than twelve attached instruction pages and still verifies.",
            blank_label=True,
            instruction_pages_before_supplemental_label=13,
        ),
        SampleSpec(
            filename="APP-095_wine_of_origin_pass.pdf",
            fields={
                **BASE_FIELDS,
                "serial_number": "APP-095",
                "product_type": "WINE",
                "brand_name": "CHATEAU LUMIERE",
                "fanciful_name": "Red Blend",
                "formula": "NO FORMULA REQUIRED",
                "class_type": "Red Wine",
                "alcohol_content": "13% ABV",
                "bottler_producer": "Example Imports LLC",
                "country_of_origin": "France",
                "imported": True,
            },
            label_lines=[
                "CHATEAU LUMIERE",
                "Red Blend",
                "WINE",
                "Class/Type: Red Wine",
                "13% Alc./Vol.",
                "750 mL",
                "Wine of France",
                "Imported by Example Imports LLC",
                GOVERNMENT_WARNING,
            ],
            expected_status="Pass",
            note="Imported wine states origin as Wine of France, a product-style country-of-origin statement.",
            include_formula_approval=False,
        ),
        SampleSpec(
            filename="APP-096_multiple_formula_documents_pass.pdf",
            fields={**BASE_FIELDS, "serial_number": "APP-096", "formula": "F-9600"},
            label_lines=good_label,
            expected_status="Pass",
            note="Package includes an unrelated approved formula before the matching Formula ID; only the matching formula document is used.",
            extra_formula_approvals_before=(
                {
                    "formula": "F-4000",
                    "brand_name": "UNRELATED VODKA",
                    "class_type": "Vodka",
                    "alcohol_content": "40% ABV",
                },
            ),
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
    document = _new_document()
    page = document[0]
    if SOURCE_FORM.exists():
        _fill_source_form_widgets(page, spec.fields)
        _draw_hidden_summary_block(page, spec.fields)
        _prepare_source_label_area(page)
    else:
        _cover_label_area(page)
        _draw_form_values(page, spec.fields)
        _draw_summary_block(page, spec.fields)
    if spec.blank_label:
        pass
    elif spec.artwork_label:
        _draw_artwork_label(page, spec.label_lines, low_quality=spec.raster_label)
    elif spec.raster_label:
        _draw_raster_label(page, spec.label_lines)
    else:
        _draw_text_label(page, spec.label_lines)
    if spec.instruction_pages_before_supplemental_label:
        _append_instruction_pages(document, spec.instruction_pages_before_supplemental_label)
        _append_supplemental_label_page(document, spec.label_lines)
    if spec.include_formula_approval:
        for approval_fields in spec.extra_formula_approvals_before:
            _append_formula_approval_page(document, {**spec.fields, **approval_fields})
        _append_formula_approval_page(
            document,
            spec.fields,
            formula_id_override=spec.formula_approval_id,
            formula_unit=spec.formula_approval_unit,
            formula_identifier_label=spec.formula_approval_identifier_label,
            formula_alcohol_label=spec.formula_approval_alcohol_label,
        )
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
        "| File | Expected with OCR | Expected without OCR | Purpose |",
        "| --- | --- | --- | --- |",
    ]
    for spec in sample_specs():
        no_ocr_status = spec.expected_status_without_ocr or spec.expected_status
        lines.append(f"| `{spec.filename}` | {spec.expected_status} | {no_ocr_status} | {spec.note} |")
    lines.extend(
        [
            "",
            "These PDFs are synthetic completed applications. When `docs/source/f510031.pdf` is available locally, the generator fills the real TTB form template. Otherwise it falls back to a controlled TTB-like one-page layout.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _new_document() -> fitz.Document:
    if SOURCE_FORM.exists():
        source = fitz.open(SOURCE_FORM)
        document = fitz.open()
        document.insert_pdf(source, from_page=0, to_page=0)
        source.close()
        return document
    return _new_sample_document()


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


def _fill_source_form_widgets(page: fitz.Page, fields: dict[str, str | bool]) -> None:
    serial_digits = "".join(ch for ch in str(fields.get("serial_number", "")) if ch.isdigit())[-4:].zfill(4)
    field_values = {
        "YEAR 1": "2",
        "YEAR 2": "6",
        "SERIAL NUMBER 1": serial_digits[0],
        "SERIAL NUMBER 2": serial_digits[1],
        "SERIAL NUMBER 3": serial_digits[2],
        "SERIAL NUMBER 4": serial_digits[3],
        "2.  PLANT REGISTRY/BASIC PERMIT/BREWER'S NO. (Required)": "DSP-OR-10001",
        "6. BRAND NAME (Required)": str(fields.get("brand_name", "") or ""),
        "7. FANCIFUL NAME (If any)": str(fields.get("fanciful_name", "") or ""),
        "8. NAME AND ADDRESS OF APPLICANT AS SHOWN ON PLANT REGISTRY, BASIC": str(fields.get("applicant_name_address", "") or ""),
        "8a. MAILING ADDRESS, IF DIFFERENT": str(fields.get("mailing_address", "") or ""),
        "9.  FORMULA": str(fields.get("formula", "") or ""),
        "10. GRAPE VARIETAL(S) Wine only": str(fields.get("grape_varietals", "") or ""),
        "11.  WINE APPELLATION (If on label)": str(fields.get("wine_appellation", "") or ""),
        "12.  PHONE NUMBER": str(fields.get("phone", "") or ""),
        "13.  EMAIL ADDRESS": str(fields.get("email", "") or ""),
        "15.  SHOW ANY INFORMATION THAT IS BLOWN, BRANDED, OR EMBOSSED ON THE CONTAINER (e.g., net contents) ONLY IF IT DOES NOT APPEAR ON THE LABELS": str(fields.get("item_15", "") or ""),
        "16.  DATE OF APPLICATION": "06/06/2026",
        "18.  PRINT NAME OF APPLICANT OR AUTHORIZED AGENT": "Example Distilling Co.",
    }

    for widget in page.widgets() or []:
        if widget.field_name in field_values:
            widget.field_value = field_values[widget.field_name]
            widget.update()
        elif widget.field_type_string == "CheckBox":
            _set_source_checkbox(widget, fields)


def _set_source_checkbox(widget: fitz.Widget, fields: dict[str, str | bool]) -> None:
    states = (widget.button_states() or {}).get("normal", [])
    state_names = {str(state).lower(): str(state) for state in states}
    value = "Off"
    rect = widget.rect

    if "domes" in state_names and not fields.get("imported"):
        value = state_names["domes"]
    elif "import" in state_names and fields.get("imported"):
        value = state_names["import"]
    elif "spirits" in state_names and fields.get("product_type") == "DISTILLED SPIRITS":
        value = state_names["spirits"]
    elif "wine" in state_names and fields.get("product_type") == "WINE":
        value = state_names["wine"]
    elif "malt" in state_names and fields.get("product_type") == "MALT BEVERAGES":
        value = state_names["malt"]
    elif "yes" in state_names and 265 <= rect.y0 <= 276:
        value = state_names["yes"]

    widget.field_value = value
    widget.update()


def _prepare_source_label_area(page: fitz.Page) -> None:
    for widget in list(page.widgets() or []):
        if widget.field_name.endswith("_af_image"):
            page.delete_widget(widget)
            break
    rect = fitz.Rect(*SOURCE_LABEL_RECT)
    page.draw_rect(rect, color=(0.75, 0.75, 0.75), fill=(1, 1, 1), width=0.7)


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
    page.insert_textbox(fitz.Rect(rect.x0 + 5, rect.y0 + 5, rect.x1 - 5, rect.y1 - 5), _summary_block_text(fields), fontsize=6.2, fontname="helv")


def _draw_hidden_summary_block(page: fitz.Page, fields: dict[str, str | bool]) -> None:
    for index, line in enumerate(_summary_block_text(fields).splitlines()):
        page.insert_text((8, 600 + index * 1.35), line, fontsize=1, fontname="helv", color=(1, 1, 1), overlay=True)


def _append_formula_approval_page(
    document: fitz.Document,
    fields: dict[str, str | bool],
    *,
    formula_id_override: str | None = None,
    formula_unit: str = "% by Volume",
    formula_identifier_label: str = "TTB Formula ID",
    formula_alcohol_label: str = "Alcohol Content of Finished Product",
) -> None:
    page = document.new_page(width=612, height=792)
    formula_id = formula_id_override or str(fields.get("formula", "") or "")
    low_alcohol, high_alcohol = _low_high_values(fields.get("alcohol_content", ""))
    lines = [
        "FORMULAS ONLINE APPROVAL DETERMINATION",
        "",
        f"{formula_identifier_label}: {formula_id}",
        "Status: Approved",
        f"Company Formula Number: {formula_id}",
        f"Brand Name: {fields.get('brand_name', '')}",
        f"Class/Type: {fields.get('class_type', '')}",
        "",
        "Yield Summary",
        "Total Yield: 100.0 Percentage",
        f"{formula_alcohol_label}: Low {low_alcohol} High {high_alcohol} Unit {formula_unit}",
        "",
        "Ingredients List:",
        "Finished alcohol, botanicals, purified water, and approved flavor materials.",
        "",
        "Method of Manufacture:",
        "Blend approved ingredients, adjust to final alcohol content, filter, and bottle.",
        "",
        "This synthetic approval page represents the formula documentation submitted with the completed application package.",
    ]
    page.insert_textbox(
        fitz.Rect(54, 54, 558, 720),
        "\n".join(lines),
        fontsize=10,
        fontname="helv",
        color=(0, 0, 0),
    )


def _append_instruction_pages(document: fitz.Document, count: int) -> None:
    for _ in range(count):
        page = document.new_page(width=612, height=792)
        page.insert_textbox(
            fitz.Rect(42, 42, 570, 720),
            "\n\n".join(
                (
                    "GENERAL INSTRUCTIONS",
                    "PAPERWORK REDUCTION ACT NOTICE",
                    "This instruction page is attached to the completed application package and must not be read as label text.",
                )
            ),
            fontsize=11,
            fontname="helv",
        )


def _append_supplemental_label_page(document: fitz.Document, label_lines: list[str]) -> None:
    page = document.new_page(width=612, height=792)
    label_rect = fitz.Rect(72, 96, 540, 600)
    page.draw_rect(label_rect, color=(0, 0, 0), fill=(1, 1, 1), width=1.2)
    y = label_rect.y0 + 44
    for index, line in enumerate(label_lines):
        if index == 0:
            text_width = fitz.get_text_length(line, fontname="helv", fontsize=26)
            page.insert_text((label_rect.x0 + (label_rect.width - text_width) / 2, y), line, fontsize=26, fontname="helv")
            y += 34
        elif _looks_like_warning_line(line):
            page.insert_textbox(
                fitz.Rect(label_rect.x0 + 18, label_rect.y1 - 82, label_rect.x1 - 18, label_rect.y1 - 20),
                line,
                fontsize=6.5,
                fontname="helv",
            )
        else:
            page.insert_textbox(
                fitz.Rect(label_rect.x0 + 36, y, label_rect.x1 - 36, y + 18),
                line,
                fontsize=10,
                fontname="helv",
                align=1,
            )
            y += 22


def _low_high_values(value: str | bool) -> tuple[str, str]:
    matches = re.findall(r"\d{1,3}(?:\.\d+)?", str(value))
    if not matches:
        text = str(value)
        return text, text
    if len(matches) == 1:
        return matches[0], matches[0]
    return matches[0], matches[1]


def _summary_block_text(fields: dict[str, str | bool]) -> str:
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
    return "\n".join(lines)


def _draw_text_label(page: fitz.Page, label_lines: list[str]) -> None:
    label_rect = _inner_label_rect(page)
    page.draw_rect(label_rect, color=(0, 0, 0), fill=(1, 1, 1), width=1.2)
    y = label_rect.y0 + 14
    for index, line in enumerate(label_lines):
        if index == 0:
            text_width = fitz.get_text_length(line, fontname="helv", fontsize=17)
            page.insert_text((label_rect.x0 + (label_rect.width - text_width) / 2, y + 18), line, fontsize=17, fontname="helv")
            y += 25
        elif _looks_like_warning_line(line):
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
        font = title_font if index == 0 else warning_font if _looks_like_warning_line(line) else body_font
        if index == 0:
            draw.text((42, y), line, fill=(75, 75, 72), font=font)
            y += 52
        elif _looks_like_warning_line(line):
            draw.multiline_text((28, 258), _wrap(line, 100), fill=(110, 110, 105), font=font, spacing=2)
        else:
            draw.text((70, y), line, fill=(85, 85, 80), font=font)
            y += 28
    image = image.rotate(7, expand=True, fillcolor=(255, 255, 255)).filter(ImageFilter.GaussianBlur(radius=1.15))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(label_rect, stream=buffer.getvalue(), keep_proportion=True)


def _draw_artwork_label(page: fitz.Page, label_lines: list[str], *, low_quality: bool = False) -> None:
    label_rect = _inner_label_rect(page)
    width, height = 2200, 920
    title = label_lines[0] if label_lines else "LABEL"
    palette = _artwork_palette(title)
    image = Image.new("RGB", (width, height), palette["background"])
    draw = ImageDraw.Draw(image)

    try:
        title_font = ImageFont.truetype("arial.ttf", 96)
        subtitle_font = ImageFont.truetype("arial.ttf", 54)
        body_font = ImageFont.truetype("arial.ttf", 44)
        warning_font = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        warning_font = ImageFont.load_default()

    draw.rectangle((18, 18, width - 18, height - 18), outline=palette["border"], width=10)
    draw.rectangle((18, 18, width - 18, 118), fill=palette["band"])
    draw.ellipse((-190, 100, 560, 840), fill=palette["accent"])
    draw.polygon([(width - 640, 120), (width - 18, 18), (width - 18, height - 18), (width - 820, height - 74)], fill=palette["accent2"])
    draw.rectangle((105, 62, width - 105, 188), fill=palette["panel"], outline=palette["border"], width=4)
    draw.rectangle((140, 220, width - 140, height - 190), fill=palette["panel"], outline=palette["border"], width=3)

    _draw_centered(draw, title, title_font, width // 2, 78, palette["text"])
    y = 238
    for index, line in enumerate(label_lines[1:]):
        if _looks_like_warning_line(line):
            continue
        font = subtitle_font if index == 0 else body_font
        _draw_centered(draw, line, font, width // 2, y, palette["text"])
        y += 70 if index == 0 else 56

    warning = next((line for line in label_lines if _looks_like_warning_line(line)), "")
    if warning:
        warning_box = (118, height - 282, width - 118, height - 44)
        draw.rectangle(warning_box, fill=palette["warning_panel"])
        draw.multiline_text(
            (warning_box[0] + 26, warning_box[1] + 16),
            _wrap(warning, 76),
            fill=palette["text"],
            font=warning_font,
            spacing=6,
        )

    if low_quality:
        image = image.resize((width // 2, height // 2), Image.Resampling.BILINEAR)
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        image = image.rotate(6, expand=True, fillcolor=palette["background"]).filter(ImageFilter.GaussianBlur(radius=3.0))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(label_rect, stream=buffer.getvalue(), keep_proportion=True)


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, center_x: int, y: int, fill: tuple[int, int, int]) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    x = center_x - (bbox[2] - bbox[0]) // 2
    draw.text((x, y), text, fill=fill, font=font)


def _artwork_palette(seed: str) -> dict[str, tuple[int, int, int]]:
    palettes = [
        {
            "background": (230, 241, 238),
            "band": (18, 76, 93),
            "band_text": (255, 255, 250),
            "panel": (250, 250, 244),
            "accent": (244, 190, 74),
            "accent2": (186, 219, 202),
            "border": (22, 55, 61),
            "text": (16, 30, 38),
            "warning_panel": (255, 255, 250),
        },
        {
            "background": (238, 230, 221),
            "band": (102, 37, 41),
            "band_text": (255, 252, 244),
            "panel": (255, 252, 244),
            "accent": (226, 147, 83),
            "accent2": (74, 115, 142),
            "border": (72, 45, 38),
            "text": (35, 26, 22),
            "warning_panel": (255, 252, 244),
        },
        {
            "background": (228, 235, 247),
            "band": (38, 48, 103),
            "band_text": (255, 255, 255),
            "panel": (251, 251, 255),
            "accent": (130, 188, 214),
            "accent2": (237, 202, 93),
            "border": (34, 44, 92),
            "text": (19, 26, 55),
            "warning_panel": (255, 255, 255),
        },
    ]
    return palettes[sum(ord(char) for char in seed) % len(palettes)]


def _cover_label_area(page: fitz.Page) -> None:
    rect = _label_area_rect(page)
    page.draw_rect(rect, color=None, fill=(1, 1, 1), width=0)


def _inner_label_rect(page: fitz.Page) -> fitz.Rect:
    rect = _label_area_rect(page)
    return fitz.Rect(rect.x0 + 30, rect.y0 + 25, rect.x1 - 30, rect.y1 - 20)


def _label_area_rect(page: fitz.Page) -> fitz.Rect:
    for widget in page.widgets() or []:
        if widget.field_name.endswith("_af_image"):
            return widget.rect
    if SOURCE_FORM.exists():
        return fitz.Rect(*SOURCE_LABEL_RECT)
    return FORM_REGIONS["label_area"].to_rect(page.rect)


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


def _looks_like_warning_line(line: str) -> bool:
    normalized = line.upper().replace("0", "O").replace("1", "I").replace("L", "I")
    return "GOVERNMENT WARNING" in normalized or "GOVERNMENT WARN" in normalized
