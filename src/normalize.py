"""Text normalization and deterministic value extraction helpers."""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from rapidfuzz import fuzz

from src.constants import GOVERNMENT_WARNING


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = (
        value.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"\s+", " ", value)
    return value.strip().upper()


def normalize_for_match(value: str | None) -> str:
    value = normalize_text(value)
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    value = re.sub(r"\b0\b", "O", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_name(value: str | None) -> str:
    value = normalize_text(value)
    value = value.replace("&", " AND ")
    value = re.sub(r"['`]", "", value)
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fuzzy_score(expected: str | None, actual: str | None) -> float:
    expected_norm = normalize_name(expected)
    actual_norm = normalize_name(actual)
    if not expected_norm or not actual_norm:
        return 0.0
    if expected_norm in actual_norm:
        return 100.0
    return float(fuzz.token_set_ratio(expected_norm, actual_norm))


def best_fuzzy_score(expected: str | None, candidates: Iterable[str]) -> float:
    return max((fuzzy_score(expected, candidate) for candidate in candidates), default=0.0)


def extract_product_type(text: str | None) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    if "DISTILLED SPIRITS" in normalized:
        return "DISTILLED SPIRITS"
    if "MALT BEVERAGES" in normalized or "MALT BEVERAGE" in normalized:
        return "MALT BEVERAGES"
    if "SPIRIT" in normalized or "LIQUOR" in normalized:
        return "DISTILLED SPIRITS"
    if "BEER" in normalized or "ALE" in normalized or "LAGER" in normalized:
        return "MALT BEVERAGES"
    if re.search(r"\bWINE\b", normalized):
        return "WINE"
    return ""


ABV_PATTERNS = (
    re.compile(
        r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)\s*(?:ALC\.?\s*/?\s*VOL\.?|ABV|ALCOHOL BY VOLUME)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:ALC\.?\s*/?\s*VOL\.?|ABV)",
        re.IGNORECASE,
    ),
)
PROOF_PATTERN = re.compile(r"(?P<num>\d{1,3}(?:\.\d+)?)\s*PROOF", re.IGNORECASE)


def extract_abv_values(text: str | None) -> list[float]:
    if not text:
        return []
    values: list[float] = []
    for pattern in ABV_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group("num"))
            if 0 < value <= 100:
                values.append(round(value, 3))
    for match in PROOF_PATTERN.finditer(text):
        proof = float(match.group("num"))
        if 0 < proof <= 200:
            values.append(round(proof / 2.0, 3))
    return _dedupe_floats(values)


def normalize_abv(text: str | None) -> float | None:
    values = extract_abv_values(text)
    return values[0] if values else None


NET_CONTENTS_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<num>(?:\d+(?:\.\d+)?)|(?:\.\d+))\s*(?P<unit>ML|M\.L\.|MILLILITERS?|L|LITERS?|LITRES?|FL\.?\s*OZ\.?|FLUID\s+OUNCES?)\b",
    re.IGNORECASE,
)


def extract_net_contents_values(text: str | None) -> list[float]:
    if not text:
        return []
    values: list[float] = []
    for match in NET_CONTENTS_PATTERN.finditer(text):
        number = float(match.group("num"))
        unit = re.sub(r"[^A-Z]+", "", match.group("unit").upper())
        if "OZ" in unit or "OUNCE" in unit:
            milliliters = number * 29.5735
        elif unit.startswith("M"):
            milliliters = number
        else:
            milliliters = number * 1000
        if 0 < milliliters < 100000:
            values.append(round(milliliters, 3))
    return _dedupe_floats(values)


def normalize_net_contents(text: str | None) -> float | None:
    values = extract_net_contents_values(text)
    return values[0] if values else None


def normalize_warning_for_compare(text: str | None) -> str:
    text = normalize_text(text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def government_warning_matches(text: str | None) -> bool:
    label = normalize_warning_for_compare(text)
    canonical = normalize_warning_for_compare(GOVERNMENT_WARNING)
    return bool(canonical and canonical in label)


def government_warning_similarity(text: str | None) -> float:
    label = normalize_warning_for_compare(text)
    canonical = normalize_warning_for_compare(GOVERNMENT_WARNING)
    if not label or not canonical:
        return 0.0
    return float(fuzz.partial_ratio(canonical, label))


def contains_title_case_warning(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"\bGovernment Warning\b", text)) and "GOVERNMENT WARNING" not in text


def snippet_around(text: str | None, target: str | None = None, width: int = 220) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not target:
        return cleaned[:width]
    normalized_cleaned = normalize_text(cleaned)
    normalized_target = normalize_text(target)
    index = normalized_cleaned.find(normalized_target[:40])
    if index < 0:
        return cleaned[:width]
    start = max(0, index - width // 3)
    end = min(len(cleaned), start + width)
    return cleaned[start:end]


def _dedupe_floats(values: list[float]) -> list[float]:
    deduped: list[float] = []
    for value in values:
        if not any(abs(value - seen) < 0.01 for seen in deduped):
            deduped.append(value)
    return deduped
