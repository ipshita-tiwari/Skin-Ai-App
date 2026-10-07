"""
Orchestrates the full analysis pipeline: skin image -> classifier,
optional blood report -> OCR -> lab parser -> recommendation engine.
Supports text-only path (no photo): user describes concerns + short Q&A -> synthetic skin_result -> same recommendation.
"""
import logging
import re
from typing import Dict, Any, Optional, List

from backend.ai.skin_classifier import analyze_skin_image
from backend.ai.ocr_extractor import extract_text_from_blood_report
from backend.ai.lab_parser import parse_lab_values, RECOMMENDED_SKIN_LAB_TESTS
from backend.ai.recommendation_engine import build_recommendation
from backend.ai.skincare_recommendation_service import (
    detect_severe_symptoms,
    engine_conditions_from_kb,
    get_skincare_recommendations,
)

logger = logging.getLogger(__name__)

# Valid values for text-based flow (normalized to recommendation_engine skin_type / conditions)
SKIN_TYPES = ("dry", "oily", "normal", "combination", "sensitive")
CONCERN_TO_CONDITIONS = {
    "acne": "oiliness",
    "oiliness": "oiliness",
    "oily": "oiliness",
    "blackheads": "oiliness",
    "whiteheads": "oiliness",
    "enlarged": "oiliness",
    "pores": "oiliness",
    "excess oil": "oiliness",
    "dryness": "dry_patches",
    "dry": "dry_patches",
    "dehydrated": "dry_patches",
    "dullness": "dry_patches",
    "fine_lines": "dry_patches",
    "texture": "dry_patches",
    "barrier": "dry_patches",
    "redness": "redness",
    "sensitivity": "redness",
    "sensitive": "redness",
    "dark_spots": "dry_patches",
    "pigmentation": "dry_patches",
}


def _build_skin_result_from_text(
    text_input: Optional[str] = None,
    skin_type_self: Optional[str] = None,
    concerns: Optional[str] = None,
    uses_actives: Optional[str] = None,
    sensitivities: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a synthetic skin_result from chat/text and follow-up answers for the recommendation engine."""
    skin_type = "normal"
    conditions: List[str] = []
    combined = (text_input or "").lower() + " " + (skin_type_self or "").lower() + " " + (concerns or "").lower()

    # Infer skin type from self-report or keywords
    if skin_type_self:
        st = skin_type_self.strip().lower()
        for s in SKIN_TYPES:
            if s in st or st == s:
                skin_type = s
                break
    if not skin_type_self or skin_type == "normal":
        if any(w in combined for w in ["dry", "flaky", "tight", "dehydrated"]):
            skin_type = "dry"
        elif any(w in combined for w in ["oily", "shine", "greasy", "acne", "breakout"]):
            skin_type = "oily"
        elif any(w in combined for w in ["sensitive", "red", "reactive", "sting"]):
            skin_type = "sensitive"
        elif any(w in combined for w in ["combination", "t-zone", "oily and dry"]):
            skin_type = "combination"

    # Map concerns to conditions
    if concerns:
        for part in re.split(r"[,;]", concerns):
            part = part.strip().lower()
            for key, cond in CONCERN_TO_CONDITIONS.items():
                if key in part and cond not in conditions:
                    conditions.append(cond)
    if "red" in combined or "sensitive" in combined or "redness" in combined:
        if "redness" not in conditions:
            conditions.append("redness")
    if "oil" in combined or "acne" in combined:
        if "oiliness" not in conditions:
            conditions.append("oiliness")
    if "dry" in combined or "dull" in combined:
        if "dry_patches" not in conditions:
            conditions.append("dry_patches")
    if not conditions:
        conditions = ["even_tone"]

    explanation = (
        f"Analysis based on your description and answers. Skin type: {skin_type}. "
        + (f"Concerns: {concerns}." if concerns else "")
        + (f" Uses actives: {uses_actives}." if uses_actives else "")
        + (f" Sensitivities: {sensitivities}." if sensitivities else "")
    )
    return {
        "skin_type": skin_type,
        "conditions": conditions,
        "confidence": 0.7,
        "explanation": explanation.strip(),
        "meta": {"source": "text", "text_input": (text_input or "")[:200]},
    }


def run_analysis(
    skin_image_bytes: Optional[bytes] = None,
    blood_report_bytes: Optional[bytes] = None,
    blood_report_is_pdf: bool = False,
    text_input: Optional[str] = None,
    skin_type_self: Optional[str] = None,
    concerns: Optional[str] = None,
    uses_actives: Optional[str] = None,
    sensitivities: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run full pipeline. Either skin_image_bytes OR (text_input or skin_type_self) must be provided.
    """
    if skin_image_bytes:
        skin_result = analyze_skin_image(skin_image_bytes)
        logger.info("Skin analysis (image) done: type=%s", skin_result.get("skin_type"))
    else:
        if not (text_input or skin_type_self):
            raise ValueError("Provide either a skin photo or describe your skin / answer the questions.")
        skin_result = _build_skin_result_from_text(
            text_input=text_input,
            skin_type_self=skin_type_self,
            concerns=concerns,
            uses_actives=uses_actives,
            sensitivities=sensitivities,
        )
        logger.info("Skin analysis (text) done: type=%s", skin_result.get("skin_type"))

    lab_result: Dict[str, Any] = {
        "values": {},
        "raw_snippets": [],
        "explanation": "No blood report provided. For full skin-related analysis, upload a report containing the recommended tests.",
        "recommended_tests": RECOMMENDED_SKIN_LAB_TESTS,
    }
    if blood_report_bytes:
        ocr_text = extract_text_from_blood_report(blood_report_bytes, blood_report_is_pdf)
        lab_result = parse_lab_values(ocr_text)
        logger.info("Lab parsing done: %d values", len(lab_result.get("values", {})))

    extra_labels: List[str] = []
    if concerns:
        extra_labels.extend([p.strip() for p in re.split(r"[,;]", concerns) if p.strip()])
    if skin_type_self:
        extra_labels.append(skin_type_self)

    combined_text = " ".join(
        part for part in (text_input or "", concerns or "", skin_type_self or "") if part
    )
    kb_result = get_skincare_recommendations(
        combined_text,
        extra_concerns=extra_labels,
        sensitivities=sensitivities,
        uses_actives=uses_actives,
    )

    kb_conditions = engine_conditions_from_kb(kb_result)
    merged_conditions = list(skin_result.get("conditions") or [])
    for c in kb_conditions:
        if c not in merged_conditions:
            merged_conditions.append(c)
    skin_result["conditions"] = merged_conditions or ["even_tone"]

    if skin_type_self:
        st = skin_type_self.strip().lower()
        for s in SKIN_TYPES:
            if s in st:
                skin_result["skin_type"] = s
                break

    image_confidence = float(skin_result.get("confidence") or 0)
    if skin_image_bytes and image_confidence < 0.7:
        skin_result["prediction_uncertain"] = True
        note = (
            "Image model confidence is below 70%, so the photo prediction is uncertain. "
            "Your written description and selected concerns were used as the primary signal."
        )
        skin_result["explanation"] = (skin_result.get("explanation") or "") + " " + note

    severe = detect_severe_symptoms(combined_text)
    recommendation = build_recommendation(
        skin_result,
        lab_result,
        kb_result=kb_result,
        uses_actives=uses_actives,
        sensitivities=sensitivities,
        text_input=text_input,
        severe_symptoms=severe,
    )

    return {
        "skin_analysis": skin_result,
        "lab_analysis": lab_result,
        "recommendation": recommendation,
        "knowledge_base": kb_result,
        "success": True,
    }
