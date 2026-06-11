"""Streamlit application for batch alcohol label verification."""

from __future__ import annotations

import streamlit as st

import src.batch as batch
import src.constants as constants


if not hasattr(constants, "STATUS_PASS"):
    constants.STATUS_PASS = "Pass"
if not hasattr(constants, "STATUS_REVIEW"):
    constants.STATUS_REVIEW = "Needs Review"
if not hasattr(constants, "STATUS_FAIL"):
    constants.STATUS_FAIL = "Fail"

STATUS_PASS = constants.STATUS_PASS
STATUS_REVIEW = constants.STATUS_REVIEW
STATUS_FAIL = constants.STATUS_FAIL
import src.pdf_intake as pdf_intake

SUPPORTED_UPLOAD_TYPES = getattr(pdf_intake, "SUPPORTED_UPLOAD_TYPES", ["pdf", "png", "jpg", "jpeg", "tif", "tiff", "bmp"])


st.set_page_config(page_title="Alcohol Label Verification", layout="wide")


def main() -> None:
    _apply_light_theme()
    st.title("Alcohol Label Verification")
    st.write(
        "Select completed TTB application PDFs or scanned application images. Each file is treated "
        "as its own self-contained verification package with application data and affixed label artwork inside."
    )

    if "result_cache" not in st.session_state:
        st.session_state.result_cache = {}
    if "results" not in st.session_state:
        st.session_state.results = []
    if "loaded_files" not in st.session_state:
        st.session_state.loaded_files = []
    if "review_files" not in st.session_state:
        st.session_state.review_files = {}

    uploaded_files = st.file_uploader(
        "Select completed TTB application files",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=True,
    )
    uploaded_zip = st.file_uploader("Or select a ZIP containing completed application files", type=["zip"])

    actions = st.columns([1, 5])
    verify_clicked = actions[0].button("Verify Applications", type="primary", width="stretch")

    named_files = _uploaded_to_named_files(uploaded_files, uploaded_zip)
    if named_files:
        st.session_state.loaded_files = named_files

    if verify_clicked:
        if not st.session_state.loaded_files:
            st.warning("Select one or more completed application files.")
        else:
            st.session_state.results, st.session_state.review_files = _run_batch(
                st.session_state.loaded_files, st.session_state.result_cache
            )

    results = st.session_state.results
    if results:
        _render_results(results, st.session_state.review_files)


def _apply_light_theme() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: light; }
        [data-testid="stAppViewContainer"] { background: #ffffff; color: #111827; }
        [data-testid="stHeader"] { background: rgba(255, 255, 255, 0.92); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _uploaded_to_named_files(uploaded_files, uploaded_zip) -> list[tuple[str, bytes]]:
    named_files: list[tuple[str, bytes]] = []
    for uploaded in uploaded_files or []:
        named_files.append((uploaded.name, uploaded.getvalue()))
    if uploaded_zip is not None:
        named_files.append((uploaded_zip.name, uploaded_zip.getvalue()))
    return named_files


def _run_batch(named_files: list[tuple[str, bytes]], cache: dict) -> tuple[list, dict[str, bytes]]:
    pdfs = pdf_intake.expand_named_files(named_files)
    review_files = {filename: data for filename, data in pdfs}
    processor = getattr(pdf_intake, "process_application_file_cached", pdf_intake.process_pdf_cached)
    progress = st.progress(0)
    status = st.empty()
    results = []
    total = len(pdfs)
    for index, (filename, data) in enumerate(pdfs, start=1):
        status.write(f"Processing {index} of {total}: {filename}")
        results.append(processor(filename, data, cache=cache))
        progress.progress(index / total)
    status.write("Verification complete.")
    return results, review_files


def _render_results(results: list, review_files: dict[str, bytes] | None = None) -> None:
    review_files = review_files or {}
    metrics = _summary_metrics(results)
    cols = st.columns(6)
    cols[0].metric("Total", metrics["total"])
    cols[1].metric("Pass", metrics["pass"])
    cols[2].metric("Needs Review", metrics["needs_review"])
    cols[3].metric("Fail", metrics["fail"])
    cols[4].metric("Unreadable", metrics["unreadable"])
    cols[5].metric("Missing Label Area", metrics["missing_label_area"])

    summary_df = batch.summary_dataframe(results)
    detail_df = batch.field_results_dataframe(results)
    fields_df = batch.application_fields_dataframe(results)

    status_filter = st.selectbox(
        "Status filter",
        options=["All", STATUS_PASS, STATUS_REVIEW, STATUS_FAIL],
        index=0,
    )
    visible_summary = summary_df if status_filter == "All" else summary_df[summary_df["overall_status"] == status_filter]
    st.dataframe(visible_summary, width="stretch", hide_index=True)

    download_cols = st.columns(3)
    download_cols[0].download_button(
        "Download summary CSV",
        data=summary_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_summary.csv",
        mime="text/csv",
        width="stretch",
    )
    download_cols[1].download_button(
        "Download detailed field-results CSV",
        data=detail_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_field_results.csv",
        mime="text/csv",
        width="stretch",
    )
    download_cols[2].download_button(
        "Download extracted application data CSV",
        data=fields_df.to_csv(index=False).encode("utf-8"),
        file_name="alcohol_label_verification_application_fields.csv",
        mime="text/csv",
        width="stretch",
    )

    st.subheader("Application Details")
    for result in results:
        if status_filter != "All" and result.overall_status != status_filter:
            continue
        with st.expander(f"{result.overall_status} - {result.filename}", expanded=result.overall_status != STATUS_PASS):
            original_bytes = review_files.get(result.filename)
            if original_bytes:
                st.download_button(
                    "Download original application",
                    data=original_bytes,
                    file_name=result.filename.replace("/", "_").replace("\\", "_"),
                    mime=_mime_type_for_file(result.filename),
                    key=f"open_original_{result.application_id}_{result.filename}",
                    help="Download the exact uploaded application file for human review.",
                    width="stretch",
                )
            st.write(result.short_summary)
            if result.warnings:
                st.warning(" ".join(result.warnings))
            if result.errors:
                st.error(" ".join(result.errors))

            tab_fields, tab_results, tab_label, tab_app = st.tabs(
                ["Extracted application fields", "Field results", "Label OCR text", "Application OCR text"]
            )
            with tab_fields:
                st.dataframe(batch.application_fields_dataframe([result]), width="stretch")
            with tab_results:
                st.dataframe(batch.field_results_dataframe([result]), width="stretch")
            with tab_label:
                st.text_area(
                    "Label OCR text",
                    result.label_ocr_text or "No readable label text extracted.",
                    height=240,
                    key=f"label_ocr_{result.application_id}_{result.filename}",
                )
            with tab_app:
                st.text_area(
                    "Application OCR text",
                    result.application_ocr_text or "No application text extracted.",
                    height=240,
                    key=f"application_ocr_{result.application_id}_{result.filename}",
                )


def _mime_type_for_file(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith((".tif", ".tiff")):
        return "image/tiff"
    if lower.endswith(".bmp"):
        return "image/bmp"
    if lower.endswith(".zip"):
        return "application/zip"
    return "application/octet-stream"


def _summary_metrics(results: list) -> dict[str, int]:
    return batch.summary_metrics(results)


if __name__ == "__main__":
    main()
