"""Shared constants for the alcohol label verifier."""

GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink "
    "alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

STATUS_PASS = "Pass"
STATUS_REVIEW = "Needs Review"
STATUS_FAIL = "Fail"

PRODUCT_TYPES = ("WINE", "DISTILLED SPIRITS", "MALT BEVERAGES")

CRITICAL_FIELDS = {
    "brand_name",
    "formula",
    "government_warning",
    "alcohol_content",
    "net_contents",
}

BRAND_PASS_THRESHOLD = 88
BRAND_REVIEW_THRESHOLD = 74
CLASS_TYPE_PASS_THRESHOLD = 86
CLASS_TYPE_REVIEW_THRESHOLD = 76
TEXT_FIELD_PASS_THRESHOLD = 86

LOW_CONFIDENCE_THRESHOLD = 0.55
