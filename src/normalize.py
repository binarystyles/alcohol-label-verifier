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
    if _contains_token_sequence(expected_norm.split(), actual_norm.split()):
        return 100.0
    return float(fuzz.token_set_ratio(expected_norm, actual_norm))


def ordered_fuzzy_score(expected: str | None, actual: str | None) -> float:
    expected_norm = normalize_name(expected)
    actual_norm = normalize_name(actual)
    if not expected_norm or not actual_norm:
        return 0.0
    if _contains_token_sequence(expected_norm.split(), actual_norm.split()):
        return 100.0
    return float(fuzz.ratio(expected_norm, actual_norm))


def best_fuzzy_score(expected: str | None, candidates: Iterable[str]) -> float:
    return max((fuzzy_score(expected, candidate) for candidate in candidates), default=0.0)


def _contains_token_sequence(expected_tokens: list[str], actual_tokens: list[str]) -> bool:
    if not expected_tokens or len(expected_tokens) > len(actual_tokens):
        return False
    width = len(expected_tokens)
    return any(actual_tokens[index : index + width] == expected_tokens for index in range(len(actual_tokens) - width + 1))


def extract_product_type(text: str | None) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    if "DISTILLED SPIRITS" in normalized:
        return "DISTILLED SPIRITS"
    if "MALT BEVERAGES" in normalized or "MALT BEVERAGE" in normalized or "MALT LIQUOR" in normalized:
        return "MALT BEVERAGES"
    if re.search(r"\b(?:BEER|ALE|LAGER|STOUT|PORTER)\b", normalized) and not re.search(
        r"\b(?:RED|WHITE|ROSE|SPARKLING|TABLE|DESSERT)\s+WINE\b", normalized
    ):
        return "MALT BEVERAGES"
    if re.search(r"\bWINE\b", normalized):
        return "WINE"
    if re.search(
        r"\b(?:GIN|VODKA|RUM|TEQUILA|MEZCAL|WHISKEY|WHISKY|BOURBON|BRANDY|COGNAC|LIQUEUR|CORDIAL|SCHNAPPS|AQUAVIT)\b",
        normalized,
    ):
        return "DISTILLED SPIRITS"
    if "SPIRIT" in normalized or "LIQUOR" in normalized:
        return "DISTILLED SPIRITS"
    if re.search(r"\b(?:BEER|ALE|LAGER|STOUT|PORTER)\b", normalized):
        return "MALT BEVERAGES"
    return ""


ABV_PATTERNS = (
    re.compile(
        r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)\s*(?:ALC\.?\s*(?:/|BY\s+)?\s*VOL(?:UME)?\.?|ABV|ALCOHOL\s+BY\s+VOL(?:UME)?\.?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:ALC\.?\s*(?:/|BY\s+)?\s*VOL(?:UME)?\.?|ABV)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:ALC\.?\s*(?:/|BY\s+)?\s*VOL(?:UME)?\.?|ABV|ALCOHOL\s+BY\s+VOL(?:UME)?\.?)\s*:?\s*(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"ALC\.?\s*(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)?\s*(?:BY\s+VOL\.?|BY\s+VOLUME)",
        re.IGNORECASE,
    ),
    re.compile(
        r"ALCOHOL\s+(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:%|PERCENT)?\s*BY\s+VOL(?:UME)?\.?",
        re.IGNORECASE,
    ),
)
PROOF_PATTERNS = (
    re.compile(r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?:\u00b0|DEGREES?)?\s*PROOF", re.IGNORECASE),
    re.compile(r"PROOF\s*:?\s*(?P<num>\d{1,3}(?:\.\d+)?)", re.IGNORECASE),
)


def extract_abv_values(text: str | None) -> list[float]:
    if not text:
        return []
    values: list[float] = []
    for pattern in ABV_PATTERNS:
        for match in pattern.finditer(text):
            if _keyword_follows_completed_abv_statement(text, match.start()):
                continue
            value = float(match.group("num"))
            if 0 < value <= 100:
                values.append(round(value, 3))
    for pattern in PROOF_PATTERNS:
        for match in pattern.finditer(text):
            proof = float(match.group("num"))
            if 0 < proof <= 200:
                values.append(round(proof / 2.0, 3))
    return _dedupe_floats(values)


def normalize_abv(text: str | None) -> float | None:
    values = extract_abv_values(text)
    return values[0] if values else None


def _keyword_follows_completed_abv_statement(text: str, start: int) -> bool:
    prefix = text[max(0, start - 16) : start]
    return bool(re.search(r"\d{1,3}(?:\.\d+)?\s*(?:%|PERCENT)\s*$", prefix, flags=re.IGNORECASE))


NET_CONTENTS_UNIT_PATTERN = (
    r"ML|M\.L\.|MILLILITERS?|CL|C\.L\.|CENTILITERS?|CENTILITRES?|L|LITERS?|LITRES?|"
    r"PT\.?|PINTS?|FL\.?\s*OZ\.?|FLUID\s+OUNCES?|OZ\.?|OUNCES?"
)
NUMBER_WORD_PATTERN = (
    r"ZERO|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|"
    r"SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|THIRTY|FORTY|FOURTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY|HUNDRED|THOUSAND|AND"
)
NET_CONTENTS_COMPOUND_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?P<pints>\d+(?:\.\d+)?)\s*(?:PT\.?|PINTS?)\s+(?P<ounces>\d+(?:\.\d+)?)\s*(?:FL\.?\s*OZ\.?|FLUID\s+OUNCES?|OZ\.?|OUNCES?)\b",
    re.IGNORECASE,
)
NET_CONTENTS_FRACTION_PATTERN = re.compile(
    rf"(?<![A-Z0-9])(?P<num>\d+)\s*/\s*(?P<den>\d+)\s*(?P<unit>{NET_CONTENTS_UNIT_PATTERN})\b",
    re.IGNORECASE,
)
NET_CONTENTS_WORD_PATTERN = re.compile(
    rf"(?<![A-Z0-9])(?P<words>(?:{NUMBER_WORD_PATTERN})(?:[\s-]+(?:{NUMBER_WORD_PATTERN}))*)\s+(?P<unit>{NET_CONTENTS_UNIT_PATTERN})\b",
    re.IGNORECASE,
)
NET_CONTENTS_PATTERN = re.compile(
    rf"(?<![A-Z0-9/])(?P<num>(?:\d+(?:\.\d+)?)|(?:\.\d+))\s*(?P<unit>{NET_CONTENTS_UNIT_PATTERN})\b",
    re.IGNORECASE,
)


def extract_net_contents_values(text: str | None) -> list[float]:
    if not text:
        return []
    values: list[float] = []
    compound_spans: list[tuple[int, int]] = []
    for match in NET_CONTENTS_COMPOUND_PATTERN.finditer(text):
        if _is_non_net_contents_volume(text, match.start(), match.end()):
            continue
        pints = float(match.group("pints"))
        ounces = float(match.group("ounces"))
        milliliters = (pints * 473.176) + (ounces * 29.5735)
        if 0 < milliliters < 100000:
            values.append(round(milliliters, 3))
            compound_spans.append(match.span())
    for match in NET_CONTENTS_FRACTION_PATTERN.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in compound_spans):
            continue
        if _is_non_net_contents_volume(text, match.start(), match.end()):
            continue
        denominator = float(match.group("den"))
        if denominator == 0:
            continue
        number = float(match.group("num")) / denominator
        milliliters = _net_unit_to_milliliters(number, match.group("unit"))
        if 0 < milliliters < 100000:
            values.append(round(milliliters, 3))
            compound_spans.append(match.span())
    for match in NET_CONTENTS_WORD_PATTERN.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in compound_spans):
            continue
        if _is_non_net_contents_volume(text, match.start(), match.end()):
            continue
        number = _parse_number_words(match.group("words"))
        if number is None:
            continue
        milliliters = _net_unit_to_milliliters(number, match.group("unit"))
        if 0 < milliliters < 100000:
            values.append(round(milliliters, 3))
            compound_spans.append(match.span())
    for match in NET_CONTENTS_PATTERN.finditer(text):
        if any(start <= match.start() and match.end() <= end for start, end in compound_spans):
            continue
        if _is_non_net_contents_volume(text, match.start(), match.end()):
            continue
        number = float(match.group("num"))
        milliliters = _net_unit_to_milliliters(number, match.group("unit"))
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


def _net_unit_to_milliliters(number: float, unit_text: str) -> float:
    unit = re.sub(r"[^A-Z]+", "", unit_text.upper())
    if "OZ" in unit or "OUNCE" in unit:
        return number * 29.5735
    if unit in {"PT", "PINT", "PINTS"}:
        return number * 473.176
    if unit.startswith("C"):
        return number * 10
    if unit.startswith("M"):
        return number
    return number * 1000


def _parse_number_words(text: str) -> float | None:
    singles = {
        "ZERO": 0,
        "ONE": 1,
        "TWO": 2,
        "THREE": 3,
        "FOUR": 4,
        "FIVE": 5,
        "SIX": 6,
        "SEVEN": 7,
        "EIGHT": 8,
        "NINE": 9,
        "TEN": 10,
        "ELEVEN": 11,
        "TWELVE": 12,
        "THIRTEEN": 13,
        "FOURTEEN": 14,
        "FIFTEEN": 15,
        "SIXTEEN": 16,
        "SEVENTEEN": 17,
        "EIGHTEEN": 18,
        "NINETEEN": 19,
    }
    tens = {
        "TWENTY": 20,
        "THIRTY": 30,
        "FORTY": 40,
        "FOURTY": 40,
        "FIFTY": 50,
        "SIXTY": 60,
        "SEVENTY": 70,
        "EIGHTY": 80,
        "NINETY": 90,
    }
    tokens = re.findall(r"[A-Z]+", normalize_text(text))
    if not tokens:
        return None
    total = 0
    current = 0
    saw_value = False
    for token in tokens:
        if token == "AND":
            continue
        if token in singles:
            current += singles[token]
            saw_value = True
        elif token in tens:
            current += tens[token]
            saw_value = True
        elif token == "HUNDRED":
            if current == 0:
                return None
            current *= 100
            saw_value = True
        elif token == "THOUSAND":
            if current == 0:
                return None
            total += current * 1000
            current = 0
            saw_value = True
        else:
            return None
    if not saw_value:
        return None
    return float(total + current)


def _is_non_net_contents_volume(text: str, start: int, end: int) -> bool:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    line = normalize_text(text[line_start:line_end])
    return bool(
        re.search(
            r"\b(SERVING\s+SIZE|SERVINGS?|PER\s+SERVING|CALORIES?|CARBS?|CARBOHYDRATES?|SUGARS?|RECIPE|MIX\s+WITH)\b",
            line,
        )
    )
