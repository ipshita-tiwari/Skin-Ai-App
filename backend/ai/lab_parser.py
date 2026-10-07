"""
Structured lab value parser.
Parses OCR text to extract common blood/lab markers relevant to skin health.
Output is used by the rule-based recommendation engine.
"""
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Lab names and aliases used for skin-related analysis (case-insensitive).
# Order matters: first match wins. (regex_pattern, canonical_name, unit_hint)
# Required/suggested tests for skin: CBC, Vitamin D, B12, Iron/Ferritin, Blood sugar, Thyroid, Testosterone, DHEAS, Prolactin, LH/FSH, Fasting insulin.
LAB_PATTERNS = [
    # CBC
    (r"\b(?:Hb|Hemoglobin|Hgb)\b", "hemoglobin", "g/dL"),
    (r"\b(?:RBC|Red\s*Blood\s*Cell|Erythrocyte)\b", "rbc", "million/µL"),
    (r"\b(?:WBC|White\s*Blood\s*Cell|Leucocyte)\b", "wbc", "/µL"),
    (r"\b(?:Platelet|PLT)\b", "platelet", "/µL"),
    (r"\b(?:PCV|Hematocrit|Hct)\b", "hematocrit", "%"),
    # Vitamins & minerals
    (r"\b(?:Vitamin\s*D|Vit\s*D|25-?OH\s*D|25OHD)\b", "vitamin_d", "ng/mL"),
    (r"\b(?:B12|Vitamin\s*B12|Cobalamin)\b", "vitamin_b12", "pg/mL"),
    (r"\b(?:Ferritin)\b", "ferritin", "ng/mL"),
    (r"\b(?:Serum\s*Iron|Iron\s*Serum|Iron)\b", "serum_iron", "µg/dL"),
    (r"\b(?:TIBC)\b", "tibc", "µg/dL"),
    (r"\b(?:Zinc)\b", "zinc", "µg/dL"),
    # Blood sugar
    (r"\b(?:Fasting\s*Glucose|FBS|Fasting\s*Blood\s*Sugar|Glucose\s*Fasting)\b", "fasting_glucose", "mg/dL"),
    (r"\b(?:Glucose)\b", "glucose", "mg/dL"),
    (r"\b(?:HbA1c|Hba1c|A1C|Glycated\s*Hemoglobin)\b", "hba1c", "%"),
    (r"\b(?:Fasting\s*Insulin|Insulin\s*Fasting)\b", "fasting_insulin", "µIU/mL"),
    (r"\b(?:Insulin)\b", "insulin", "µIU/mL"),
    # Thyroid
    (r"\b(?:TSH)\b", "tsh", "mIU/L"),
    (r"\b(?:T3|Free\s*T3|FT3)\b", "t3", "pg/mL"),
    (r"\b(?:T4|Free\s*T4|FT4|Thyroxine)\b", "t4", "ng/dL"),
    # Hormones (skin-relevant)
    (r"\b(?:Testosterone\s*Total|Total\s*Testosterone|Testosterone)\b", "testosterone", "ng/dL"),
    (r"\b(?:DHEA-?S|DHEAS|DHEA\s*Sulfate)\b", "dheas", "µg/dL"),
    (r"\b(?:Prolactin)\b", "prolactin", "ng/mL"),
    (r"\b(?:LH|Luteinizing)\b", "lh", "mIU/mL"),
    (r"\b(?:FSH|Follicle\s*Stimulating)\b", "fsh", "mIU/mL"),
    # Other
    (r"\b(?:Creatinine)\b", "creatinine", "mg/dL"),
    (r"\b(?:CRP|C-Reactive)\b", "crp", "mg/L"),
    (r"\b(?:Bilirubin)\b", "bilirubin", "mg/dL"),
]

# List of tests we use for skin analysis (for UI and missing-test messaging).
RECOMMENDED_SKIN_LAB_TESTS = [
    "CBC (e.g. Hemoglobin, RBC, WBC, Platelets)",
    "Vitamin D",
    "Vitamin B12",
    "Iron / Ferritin",
    "Blood sugar (Fasting glucose or HbA1c)",
    "Thyroid (TSH, T3, T4)",
    "Testosterone",
    "DHEAS",
    "Prolactin",
    "LH / FSH",
    "Fasting insulin",
]


def parse_numeric_value(s: str) -> Optional[float]:
    """Extract first reasonable number from string (handles decimals, commas)."""
    # Remove commas, match number with optional decimal
    s = s.replace(",", ".")
    match = re.search(r"(\d+\.?\d*)\s*(?:ng/mL|mg/dL|pg/mL|mIU/L|µg/dL|mg/L|g/dL)?", s)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def parse_lab_values(ocr_text: str) -> Dict[str, Any]:
    """
    Parse OCR text and return structured lab values.
    Returns dict: { "values": { "vitamin_d": {"value": 32, "unit": "ng/mL"}, ... }, "raw_snippets": [...] }
    """
    if not ocr_text or not ocr_text.strip():
        return {
            "values": {},
            "raw_snippets": [],
            "explanation": "No text extracted from report.",
            "recommended_tests": RECOMMENDED_SKIN_LAB_TESTS,
        }

    lines = [ln.strip() for ln in ocr_text.splitlines() if ln.strip()]
    full_text = " ".join(lines).replace("\n", " ")
    values = {}
    raw_snippets = []

    for pattern, canonical_name, unit_hint in LAB_PATTERNS:
        for m in re.finditer(pattern, full_text, re.IGNORECASE):
            # Take surrounding context (e.g. 50 chars after match) to find number
            start = m.start()
            end = min(len(full_text), m.end() + 60)
            snippet = full_text[start:end]
            raw_snippets.append({"name": canonical_name, "snippet": snippet})
            num = parse_numeric_value(snippet)
            if num is not None and canonical_name not in values:
                values[canonical_name] = {"value": num, "unit": unit_hint}

    explanation = (
        f"Parsed {len(values)} lab value(s) from report. "
        "Used for supplement and lifestyle recommendations."
    )
    return {
        "values": values,
        "raw_snippets": raw_snippets[:20],
        "explanation": explanation,
        "recommended_tests": RECOMMENDED_SKIN_LAB_TESTS,
    }
