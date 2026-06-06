"""Streamlit application for batch alcohol label verification."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.batch import (
    application_fields_dataframe,
    field_results_dataframe,
    process_batch,
    summary_dataframe,
    summary_metrics,
)
from src.constants import STATUS_FAIL, STATUS_PASS, STATUS_REVIEW
from src.pdf_intake import expand_named_files, process_pdf_cached


st.set_page_config(page_title="Alcohol Label Verification", layout="wide")


def main() -> None:
    st.title("Alcohol Label Verification")
    st.write(
        "Select completed TTB application PDFs. Each PDF is treated as its own self-contained "
        "verification package with application data and affixed label artwork inside the same file."
    )

    if "result_cache" not in st.session_state:
        st.session_state.result_cache = {}
    if "results" not in st.session_state:
        st.session_state.results = []
    if "loaded_files" not in st.session_state:
        st.session_state.loaded_files = []

    uploaded_pdfs = st.file_uploader(
        "Select completed TTB application PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    uploaded_zip = st.file_uploader("Or select a ZIP containing completed application PDFs", type=["zip"])

    actions = st.columns([1, 1, 4])
    verify_clicked = actions[0].button("Verify Applications", type="primary", use_container_width=True)
    sample_clicked = actions[1].button("Load Sample Applications", use_container_width=True)

    named_files = _uploaded_to_named_files(uploaded_pdfs, uploaded_zip)
    if sample_clicked:
        named_files = _load_sample_files()
        st.session_state.loaded_files = named_files
        st.info(f"Loaded {len(named_files)} sample applications.")
    elif named_files:
        st.session_state.loaded_files = named_files

    if verify_clicked:
        if not st.session_state.loaded_files:
            st.warning("Select one or more completed application PDFs, or load the sample applications.")
        else:
            st.session_state.results = _run_batch(st.session_state.loaded_files, st.session_state.result_cache)

    results = st.session_state.results
    if results:
        _render_results(results)


def _uploaded_to_named_files(uploaded_pdfs, uploaded_zip) -> list[tuple[str, bytes]]:
    named_files: list[tuple[str, bytes]] = []
    for uploaded in uploaded_pdfs or []:
        named_files.append((uploaded.name, uploaded.getvalue()))
    if uploaded_zip is not None:
        named_files.append((uploaded_zip.name, uploaded_zip.getvalue()))
    return named_files


def _load_sample_files() -> list[tuple[str, bytes]]:
    sample_dir = Path("samples/applications")
    files = sorted(sample_dir.glob("*.pdf"))
    return [(path.name, path.read_bytes()) for path in files]


def _run_batch(named_files: list[tuple[str, bytes]], cache: dict) -> list:
    pdfs = expand_named_files(named_files)
    progress = st.progress(0)
    status = st.empty()
    results = []
    total = len(pdfs)
    for index, (filename, data) in enumerate(pdfs, start=1):
        status.write(f"Processing {index} of {total}: {filename}")
        results.append(process_pdf_cached(filename, data, cache=cache))
        progress.progress(index / total)
    status.write("Verification complete.")
    return results


def _render_results(results: list) -> None:
    metrics = summary_metrics(results)
    cols = st.columns(6)
    cols[0].metric("Total", metrics["total"])
    cols[1].metric("Pass", metrics["pass"])
    cols[2].metric("Needs Review", metrics["needs_review"])
    cols[3].metric("Fail", metrics["fail"])
    cols[4].metric("Unreadable", metrics["unreadable"])
    cols[5].metric("Missing Label Area", metrics["missing_label_area"])

    summary_df = summary_dataframe(results)
    detail_df = field_results_dataframe(results)
    fields_df = application_fields_dataframe(results)

    status_filter = st.segmented_control(
        "Status filter",
        options=["All", STATUS_PASS, STATUS_REVIEW, STATUS_FAIL],
        default="All",
    )
    visible_summary = summary_df if status_filter == "All" else summary_df[summary_df["overall_status"] == status_filter]
    st.dataframe(visible_summary, use_container_width=True, hide_index=True)

    download_cols = st.columns(3)
    download_cols[0].download_button(
        "Download summary CSV",
        data=summary_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
    download_cols[1].download_button(
        "Download detailed field-results CSV",
        data=detail_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_field_results.csv",
        mime="text/csv",
        use_container_width=True,
    )
    download_cols[2].download_button(
        "Download extracted application data CSV",
        data=fields_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_application_fields.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("Application Details")
    for result in results:
        if status_filter != "All" and result.overall_status != status_filter:
            continue
        with st.expander(f"{result.overall_status} - {result.filename}", expanded=result.overall_status != STATUS_PASS):
            st.write(result.short_summary)
            if result.warnings:
                st.warning(" ".join(result.warnings))
            if result.errors:
                st.error(" ".join(result.errors))

            tab_fields, tab_results, tab_label, tab_app = st.tabs(
                ["Extracted application fields", "Field results", "Label OCR text", "Application OCR text"]
            )
            with tab_fields:
                st.dataframe(pd.DataFrame([result.extracted_application_fields]), use_container_width=True)
            with tab_results:
                st.dataframe(pd.DataFrame([field.to_dict() for field in result.field_results]), use_container_width=True)
            with tab_label:
                st.text_area("Label OCR text", result.label_ocr_text or "No readable label text extracted.", height=240)
            with tab_app:
                st.text_area("Application OCR text", result.application_ocr_text or "No application text extracted.", height=240)


if __name__ == "__main__":
    main()

