"""
Regex-based parser for Perplexity nutrition output.

Handles pipe-separated, comma-separated, newline-separated, and mixed formats.
Returns a flat dict with all recognized nutrition fields (missing → 0).
"""

import re
from typing import Dict

# Canonical field names → (aliases for matching, unit suffix for regex)
FIELD_SPEC: list[tuple[str, list[str], str]] = [
    # Tier 1
    ("calories",        ["calories", "cals", "energy", "cal"],                      r"kcal|cal"),
    ("protein",         ["protein", "prot"],                                         r"g"),
    ("total_fat",       ["total fat", "fat"],                                        r"g"),
    ("saturated_fat",   ["saturated fat", "sat fat", "sat\.? fat"],                 r"g"),
    ("trans_fat",       ["trans fat"],                                                r"g"),
    ("unsaturated_fat", ["unsaturated fat", "unsat fat", "unsat\.? fat", "mono\+poly", "monounsaturated fat", "polyunsaturated fat"],  r"g"),
    ("total_carbs",     ["total carbohydrates", "total carbs", "carbohydrates", "carbs", "carb"],  r"g"),
    ("fiber",           ["fiber", "fibre", "dietary fiber"],                         r"g"),
    ("sugar",           ["sugar", "sugars", "total sugar", "total sugars"],          r"g"),
    ("added_sugar",     ["added sugar", "added sugars"],                             r"g"),
    ("sodium",          ["sodium", "na"],                                            r"mg"),
    ("cholesterol",     ["cholesterol", "chol"],                                     r"mg"),

    # Tier 2
    ("calcium",         ["calcium", "ca"],                                           r"mg"),
    ("iron",            ["iron", "fe"],                                              r"mg"),
    ("potassium",       ["potassium", "k"],                                          r"mg"),
    ("vitamin_c",       ["vitamin c", "vit c", "vit\.? c"],                         r"mg"),
    ("vitamin_d",       ["vitamin d", "vit d", "vit\.? d"],                         r"[µu]g|mcg|iu"),
    ("magnesium",       ["magnesium", "mg(?=\s*:)"],                                r"mg"),
    ("zinc",            ["zinc", "zn"],                                              r"mg"),
    ("phosphorus",      ["phosphorus", "phos"],                                      r"mg"),

    # Tier 3
    ("vitamin_a",       ["vitamin a", "vit a", "vit\.? a"],                         r"[µu]g(?:\s*rae)?|mcg|iu"),
    ("vitamin_e",       ["vitamin e", "vit e", "vit\.? e"],                         r"mg"),
    ("vitamin_k",       ["vitamin k", "vit k", "vit\.? k"],                         r"[µu]g|mcg"),
    ("vitamin_b1",      ["vitamin b1", "thiamine", "b1"],                            r"mg"),
    ("vitamin_b2",      ["vitamin b2", "riboflavin", "b2"],                          r"mg"),
    ("vitamin_b3",      ["vitamin b3", "niacin", "b3"],                              r"mg"),
    ("vitamin_b6",      ["vitamin b6", "pyridoxine", "b6"],                          r"mg"),
    ("vitamin_b12",     ["vitamin b12", "cobalamin", "b12"],                         r"[µu]g|mcg"),
    ("folate",          ["folate", "folic acid", "vitamin b9", "b9"],                r"[µu]g(?:\s*dfe)?|mcg"),
    ("selenium",        ["selenium", "se"],                                          r"[µu]g|mcg"),
    ("copper",          ["copper", "cu"],                                            r"[µu]g|mcg|mg"),
    ("manganese",       ["manganese", "mn"],                                         r"mg"),
    ("iodine",          ["iodine"],                                                  r"[µu]g|mcg"),
    ("chromium",        ["chromium", "cr"],                                          r"[µu]g|mcg"),
    ("caffeine",        ["caffeine"],                                                r"mg"),
    ("water",           ["water"],                                                   r"ml|g"),
]

# Pre-compile patterns: look for  "FieldName: <number> <unit>"
_PATTERNS: list[tuple[str, re.Pattern]] = []
for canonical, aliases, unit_pat in FIELD_SPEC:
    alias_re = "|".join(aliases)
    # Match: alias <optional colon/equals> <number with optional decimal> <optional unit>
    pat = re.compile(
        rf"(?:{alias_re})\s*[:=]?\s*([\d,]+\.?\d*)\s*(?:{unit_pat})?\b",
        re.IGNORECASE,
    )
    _PATTERNS.append((canonical, pat))

# Display-friendly names and units for UI
DISPLAY_NAMES: Dict[str, str] = {
    "calories": "Calories", "protein": "Protein", "total_fat": "Total Fat",
    "saturated_fat": "Saturated Fat", "trans_fat": "Trans Fat",
    "unsaturated_fat": "Unsaturated Fat", "total_carbs": "Total Carbs",
    "fiber": "Fiber", "sugar": "Sugar", "added_sugar": "Added Sugar",
    "sodium": "Sodium", "cholesterol": "Cholesterol",
    "calcium": "Calcium", "iron": "Iron", "potassium": "Potassium",
    "vitamin_c": "Vitamin C", "vitamin_d": "Vitamin D",
    "magnesium": "Magnesium", "zinc": "Zinc", "phosphorus": "Phosphorus",
    "vitamin_a": "Vitamin A", "vitamin_e": "Vitamin E", "vitamin_k": "Vitamin K",
    "vitamin_b1": "B1 (Thiamine)", "vitamin_b2": "B2 (Riboflavin)",
    "vitamin_b3": "B3 (Niacin)", "vitamin_b6": "Vitamin B6",
    "vitamin_b12": "Vitamin B12", "folate": "Folate (B9)",
    "selenium": "Selenium", "copper": "Copper", "manganese": "Manganese",
    "iodine": "Iodine", "chromium": "Chromium", "caffeine": "Caffeine",
    "water": "Water",
}

UNITS: Dict[str, str] = {
    "calories": "kcal", "protein": "g", "total_fat": "g",
    "saturated_fat": "g", "trans_fat": "g", "unsaturated_fat": "g",
    "total_carbs": "g", "fiber": "g", "sugar": "g", "added_sugar": "g",
    "sodium": "mg", "cholesterol": "mg",
    "calcium": "mg", "iron": "mg", "potassium": "mg",
    "vitamin_c": "mg", "vitamin_d": "µg", "magnesium": "mg",
    "zinc": "mg", "phosphorus": "mg",
    "vitamin_a": "µg RAE", "vitamin_e": "mg", "vitamin_k": "µg",
    "vitamin_b1": "mg", "vitamin_b2": "mg", "vitamin_b3": "mg",
    "vitamin_b6": "mg", "vitamin_b12": "µg", "folate": "µg DFE",
    "selenium": "µg", "copper": "µg", "manganese": "mg",
    "iodine": "µg", "chromium": "µg", "caffeine": "mg", "water": "ml",
}

TIER1_FIELDS = [
    "calories", "protein", "total_fat", "saturated_fat", "trans_fat",
    "unsaturated_fat", "total_carbs", "fiber", "sugar", "added_sugar",
    "sodium", "cholesterol",
]

TIER2_FIELDS = [
    "calcium", "iron", "potassium", "vitamin_c", "vitamin_d",
    "magnesium", "zinc", "phosphorus",
]

TIER3_FIELDS = [
    "vitamin_a", "vitamin_e", "vitamin_k", "vitamin_b1", "vitamin_b2",
    "vitamin_b3", "vitamin_b6", "vitamin_b12", "folate", "selenium",
    "copper", "manganese", "iodine", "chromium", "caffeine", "water",
]

ALL_FIELDS = TIER1_FIELDS + TIER2_FIELDS + TIER3_FIELDS


def parse_nutrition(text: str) -> Dict[str, float]:
    """
    Parse a Perplexity nutrition output string and return a dict of field → value.
    Missing fields default to 0.
    """
    result: Dict[str, float] = {f: 0.0 for f in ALL_FIELDS}
    for canonical, pattern in _PATTERNS:
        m = pattern.search(text)
        if m:
            val_str = m.group(1).replace(",", "")
            try:
                result[canonical] = float(val_str)
            except ValueError:
                pass
    return result


def extract_food_name(text: str) -> str:
    """
    Try to extract a food/meal name from the first line of the Perplexity output.
    Returns a cleaned string or empty string.
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if not lines:
        return ""
    first = lines[0]
    # If the first line contains a colon with a number, it's likely a nutrition field, skip
    if re.search(r":\s*\d", first):
        return ""
    # Clean up markdown bold, bullets, etc.
    name = re.sub(r"[*#\-•]+", "", first).strip()
    # Truncate if too long
    return name[:100] if name else ""
