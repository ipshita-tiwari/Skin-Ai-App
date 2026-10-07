"""
Placeholder skin condition classifier.
Uses simple heuristics on image stats; replace with a real CV/ML model later.
Returns structured labels for the recommendation engine.
"""
import logging
from io import BytesIO
from typing import List, Dict, Any

from PIL import Image

logger = logging.getLogger(__name__)


def analyze_skin_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyze skin image and return condition hints.
    This is a PLACEHOLDER: in production, replace with a trained model
    (e.g. CNN for skin type/conditions) or call an external vision API.

    Returns dict with:
      - skin_type: str (e.g. "normal", "dry", "oily", "combination")
      - conditions: list of detected hints (e.g. "dry_patches", "oiliness")
      - confidence: float 0-1
      - explanation: str for explainability
    """
    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        # Downsample so large phone photos cannot hang or OOM the server
        sample = img.copy()
        sample.thumbnail((128, 128))
        pixels = list(sample.getdata())
        n = max(len(pixels), 1)

        # Placeholder: use simple color stats as proxy for "condition"
        r_avg = sum(p[0] for p in pixels) / n
        g_avg = sum(p[1] for p in pixels) / n
        b_avg = sum(p[2] for p in pixels) / n
        brightness = (r_avg + g_avg + b_avg) / 3
        r_var = sum((p[0] - r_avg) ** 2 for p in pixels) / n
        g_var = sum((p[1] - g_avg) ** 2 for p in pixels) / n
        b_var = sum((p[2] - b_avg) ** 2 for p in pixels) / n
        variance = (r_var + g_var + b_var) / 3

        # Heuristic mapping (placeholder only)
        if brightness < 100 and variance > 800:
            skin_type = "dry"
            conditions = ["dry_patches", "possible_roughness"]
        elif r_avg > g_avg + 15:
            skin_type = "sensitive"
            conditions = ["redness", "sensitivity"]
        elif brightness > 140:
            skin_type = "oily"
            conditions = ["oiliness", "shine"]
        else:
            skin_type = "normal"
            conditions = ["even_tone"]

        # Confidence is fake for placeholder; real model would output this
        confidence = 0.65
        explanation = (
            f"Image analyzed ({w}x{h} px). Placeholder logic inferred "
            f"skin type: {skin_type}, conditions: {', '.join(conditions)}. "
            "Replace this module with a trained skin analysis model for real use."
        )

        return {
            "skin_type": skin_type,
            "conditions": conditions,
            "confidence": round(confidence, 2),
            "explanation": explanation,
            "meta": {"width": w, "height": h},
        }
    except Exception as e:
        logger.exception("Skin image analysis failed: %s", e)
        return {
            "skin_type": "normal",
            "conditions": [],
            "confidence": 0.0,
            "explanation": f"Analysis could not be completed: {str(e)}. Showing default routine.",
            "meta": {},
            "error": str(e),
        }
