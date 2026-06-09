from __future__ import annotations

from src.constants import GOVERNMENT_WARNING
from src.normalize import (
    contains_title_case_warning,
    extract_abv_values,
    extract_net_contents_values,
    extract_product_type,
    fuzzy_score,
    government_warning_matches,
    normalize_name,
    ordered_fuzzy_score,
)


def test_text_normalization_handles_brand_punctuation() -> None:
    assert normalize_name("Stone's Throw") == "STONES THROW"
    assert normalize_name("Stone's   Throw") == "STONES THROW"


def test_brand_fuzzy_matching_allows_harmless_variations() -> None:
    score = fuzzy_score("STONE'S THROW", "STONES THROW Straight Bourbon Whiskey")
    assert score >= 88


def test_fuzzy_score_does_not_match_inside_larger_words() -> None:
    assert fuzzy_score("Gin", "Ginger Liqueur") < 74
    assert fuzzy_score("Reserve", "Reserved Batch") < 86
    assert fuzzy_score("Reserve", "Reserve Selection") == 100
    assert fuzzy_score("Example Distilling Co.", "Bottled by Example Distilling Company") >= 86


def test_ordered_fuzzy_score_preserves_brand_word_order() -> None:
    assert ordered_fuzzy_score("OLD TOM GIN", "OLD TOM GIN Reserve") == 100
    assert ordered_fuzzy_score("OLD TOM GIN", "TOM OLD GIN") < 74
    assert ordered_fuzzy_score("OLD TOM GIN", "OLD TOMATO GIN") < 92


def test_product_type_matching() -> None:
    assert extract_product_type("distilled spirits") == "DISTILLED SPIRITS"
    assert extract_product_type("malt beverage lager") == "MALT BEVERAGES"
    assert extract_product_type("wine") == "WINE"
    assert extract_product_type("SPIRIT HILL WINE Red Wine") == "WINE"
    assert extract_product_type("Wine Cask Finish DISTILLED SPIRITS") == "DISTILLED SPIRITS"
    assert extract_product_type("Wine barrel aged ale") == "MALT BEVERAGES"


def test_abv_and_proof_extraction_normalize_to_abv() -> None:
    assert extract_abv_values("45% Alc./Vol.") == [45.0]
    assert extract_abv_values("90 Proof") == [45.0]
    assert extract_abv_values("Proof 90") == [45.0]
    assert extract_abv_values("45 percent alcohol by volume") == [45.0]
    assert extract_abv_values("Alc. 45% by Vol.") == [45.0]
    assert extract_abv_values("Alcohol 45% by Volume") == [45.0]
    assert extract_abv_values("45% Alc. by Vol.") == [45.0]
    assert extract_abv_values("45% Alcohol by Vol.") == [45.0]
    assert extract_abv_values("45% alc by volume") == [45.0]
    assert extract_abv_values("100% Agave") == []
    assert extract_abv_values("100% Agave 40% Alc./Vol.") == [40.0]
    assert extract_abv_values("40% Alc./Vol. 1000 mL") == [40.0]
    assert extract_abv_values("5.5% Alc./Vol. 12 fl oz") == [5.5]


def test_net_contents_extraction_normalizes_units() -> None:
    values = extract_net_contents_values("750ML 0.75 L .75 liters 750 milliliters")
    assert values == [750.0]
    assert extract_net_contents_values("12 fl oz") == [354.882]
    assert extract_net_contents_values("75 cL 75cl 70 centiliters") == [750.0, 700.0]
    assert extract_net_contents_values("Serving size 50 mL") == []
    assert extract_net_contents_values("Net Contents 750 mL\nServing size 50 mL") == [750.0]


def test_government_warning_validation_exact_statement() -> None:
    assert government_warning_matches(GOVERNMENT_WARNING)


def test_title_case_warning_is_detected() -> None:
    assert contains_title_case_warning("Government Warning: do not drink during pregnancy")
