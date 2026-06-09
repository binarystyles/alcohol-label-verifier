"""Batch orchestration and export helpers."""

from __future__ import annotations

import pandas as pd

from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.models import ApplicationResult
from src.pdf_intake import expand_named_files, process_application_file_cached


APPLICATION_FIELD_EXPORT_COLUMNS = (
    "filename",
    "application_id",
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
)


def process_batch(named_files: list[tuple[str, bytes]], cache: dict | None = None) -> list[ApplicationResult]:
    application_files = expand_named_files(named_files)
    return [process_application_file_cached(filename, data, cache=cache) for filename, data in application_files]


def summary_dataframe(results: list[ApplicationResult]) -> pd.DataFrame:
    return pd.DataFrame([result.to_summary_dict() for result in results])


def field_results_dataframe(results: list[ApplicationResult]) -> pd.DataFrame:
    rows: list[dict] = []
    for result in results:
        for field in result.field_results:
            row = field.to_dict()
            row["filename"] = result.filename
            row["application_id"] = result.application_id
            rows.append(row)
    return pd.DataFrame(rows)


def application_fields_dataframe(results: list[ApplicationResult]) -> pd.DataFrame:
    rows: list[dict] = []
    for result in results:
        extracted = dict(result.extracted_application_fields)
        row = {
            "filename": result.filename,
            "application_id": result.application_id,
        }
        for column in APPLICATION_FIELD_EXPORT_COLUMNS:
            if column not in row:
                row[column] = extracted.get(column, "")
        rows.append(row)
    return pd.DataFrame(rows, columns=APPLICATION_FIELD_EXPORT_COLUMNS)


def summary_metrics(results: list[ApplicationResult]) -> dict[str, int]:
    return {
        "total": len(results),
        "pass": sum(result.overall_status == STATUS_PASS for result in results),
        "needs_review": sum(result.overall_status == STATUS_REVIEW for result in results),
        "fail": sum(result.overall_status == STATUS_FAIL for result in results),
        "unreadable": sum(any("unreadable" in warning.lower() for warning in result.warnings) for result in results),
        "missing_label_area": sum(any("label area" in warning.lower() and "missing" in warning.lower() for warning in result.warnings) for result in results),
    }
