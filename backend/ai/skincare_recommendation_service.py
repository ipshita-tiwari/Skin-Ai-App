"""
Local skincare knowledge-base matcher.

Reads backend/data/skin_knowledge_base.json only — no internet, no external APIs.
Matching uses concern names, aliases, and keywords in the user's natural-language text.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

_KB_PATH = Path(__file__).resolve().parent.parent / "data" / "skin_knowledge_base.json"

UNKNOWN_MESSAGE = (
    "I don't have enough information in my built-in skincare database for this concern yet."
)

SEVERE_PATTERNS = (
    r"\bbleed(?:ing|s)?\b",
    r"\bblood\b",
    r"\bfever\b",
    r"\bsevere pain\b",
    r"\bspreading infection\b",
    r"\brapidly spreading\b",
    r"\bopen wound\b",
    r"\bpus\b",
    r"\bswelling (?:of|around) (?:the )?eye",
    r"\bvision (?:change|loss)\b",
)

STRONG_ACTIVES = {
    "retinol",
    "adapalene",
    "glycolic acid",
    "lactic acid",
    "salicylic acid",
}

RETINOIDS = {"retinol", "adapalene"}
ACIDS = {"glycolic acid", "lactic acid", "salicylic acid"}

CONCERN_TO_ENGINE_CONDITION = {
    "dry_skin": "dry_patches",
    "dehydrated_skin": "dry_patches",
    "barrier_damage": "dry_patches",
    "dullness": "dry_patches",
    "fine_lines": "dry_patches",
    "acne": "oiliness",
    "oily_skin": "oiliness",
    "excess_oil": "oiliness",
    "blackheads": "oiliness",
    "whiteheads": "oiliness",
    "enlarged_pores": "oiliness",
    "redness": "redness",
    "sensitive_skin": "redness",
}


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("’", "'")
    text = re.sub(r"[^a-z0-9\s'-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@lru_cache(maxsize=1)
def load_knowledge_base() -> Dict[str, Any]:
    with _KB_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def detect_severe_symptoms(text: str) -> bool:
    n = _normalize(text)
    return any(re.search(p, n) for p in SEVERE_PATTERNS)


def _allergy_blocked(ingredient_name: str, sensitivities: str) -> bool:
    if not sensitivities:
        return False
    n = _normalize(sensitivities)
    ing = _normalize(ingredient_name)
    if not n or not ing:
        return False
    if ing in n:
        return True
    # also match key tokens of 2+ chars
    for tok in ing.split():
        if len(tok) >= 4 and re.search(rf"\b{re.escape(tok)}\b", n):
            return True
    return False


def _score_concern(text: str, key: str, concern: Dict[str, Any]) -> int:
    if not text:
        return 0
    score = 0
    name = _normalize(concern.get("name", ""))
    if name and name in text:
        score += 4
    key_phrase = key.replace("_", " ")
    if key_phrase and key_phrase in text:
        score += 3
    aliases = [_normalize(a) for a in concern.get("aliases", [])]
    aliases.sort(key=len, reverse=True)
    for alias in aliases:
        if len(alias) < 3:
            continue
        if alias in text:
            score += 3 if " " in alias else 2
    return score


def _match_extra_labels(labels: Sequence[str], key: str, concern: Dict[str, Any]) -> int:
    score = 0
    names = {_normalize(concern.get("name", "")), key.replace("_", " "), _normalize(key)}
    aliases = {_normalize(a) for a in concern.get("aliases", [])}
    for raw in labels:
        lab = _normalize(raw)
        if not lab:
            continue
        if lab in names or lab in aliases:
            score += 5
            continue
        if any(lab in n or n in lab for n in names if len(lab) >= 4):
            score += 4
    return score


def _dedupe_ingredients(
    items: List[Dict[str, Any]],
    sensitivities: str,
) -> List[Dict[str, Any]]:
    ranked: Dict[str, Dict[str, Any]] = {}
    for item in items:
        name = item["name"]
        if _allergy_blocked(name, sensitivities):
            continue
        key = _normalize(name)
        prev = ranked.get(key)
        if prev is None or item["rank_score"] > prev["rank_score"]:
            ranked[key] = item
    ordered = sorted(ranked.values(), key=lambda x: (-x["rank_score"], x.get("priority", 99)))
    return _limit_strong_actives(ordered)


def _limit_strong_actives(ingredients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Avoid recommending several strong actives together."""
    has_retinoid = False
    has_acid = False
    kept: List[Dict[str, Any]] = []
    for ing in ingredients:
        n = _normalize(ing["name"])
        is_retinoid = any(r in n for r in RETINOIDS)
        is_acid = any(a in n for a in ACIDS)
        if is_retinoid and has_acid:
            continue
        if is_acid and has_retinoid:
            continue
        if is_acid and has_acid:
            # keep first acid only in the top list
            continue
        if is_retinoid and has_retinoid:
            continue
        if is_retinoid:
            has_retinoid = True
        if is_acid:
            has_acid = True
        kept.append(ing)
    return kept


def get_skincare_recommendations(
    user_input: str,
    extra_concerns: Optional[Sequence[str]] = None,
    sensitivities: Optional[str] = None,
    uses_actives: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normalize input, match local concerns, rank ingredients, return UI-ready payload.
    Never fetches from the internet.
    """
    kb = load_knowledge_base()
    text = _normalize(user_input)
    extras = list(extra_concerns or [])
    sensitivities = sensitivities or ""
    uses = _normalize(uses_actives or "")

    matches: List[Tuple[str, int, Dict[str, Any]]] = []
    for key, concern in kb.items():
        score = _score_concern(text, key, concern)
        score += _match_extra_labels(extras, key, concern)
        if score > 0:
            matches.append((key, score, concern))

    matches.sort(key=lambda m: m[1], reverse=True)
    # keep the most relevant (avoid dumping the whole DB)
    matches = [m for m in matches if m[1] >= 2][:4]

    if not matches and not text and not extras:
        return {
            "detected_concerns": [],
            "recommended_ingredients": [],
            "unknown": True,
            "message": "Insufficient data for a safe recommendation.",
            "warnings": [],
            "usage_guidance": [],
            "source": "local_knowledge_base",
        }

    if not matches:
        return {
            "detected_concerns": [],
            "recommended_ingredients": [],
            "unknown": True,
            "message": UNKNOWN_MESSAGE,
            "warnings": [],
            "usage_guidance": [],
            "source": "local_knowledge_base",
        }

    collected: List[Dict[str, Any]] = []
    detected = []
    warnings: List[str] = []
    guidance: List[str] = []

    for key, score, concern in matches:
        detected.append(
            {
                "id": key,
                "name": concern.get("name", key),
                "description": concern.get("description", ""),
                "match_score": score,
            }
        )
        if concern.get("usage_guidance"):
            guidance.append(concern["usage_guidance"])
        for w in concern.get("warnings") or []:
            if w not in warnings:
                warnings.append(w)
        for ing in concern.get("ingredients") or []:
            priority = int(ing.get("priority") or 99)
            collected.append(
                {
                    "name": ing["name"],
                    "benefit": ing.get("benefit", ""),
                    "priority": priority,
                    "usage": ing.get("usage", ""),
                    "caution": ing.get("caution", ""),
                    "concern": concern.get("name", key),
                    "rank_score": score * 10 + (10 - min(priority, 10)),
                }
            )

    ingredients = _dedupe_ingredients(collected, sensitivities)

    already_actives = uses in ("yes", "sometimes")
    if already_actives:
        warnings.append(
            "You already use actives (such as retinol, vitamin C, or AHA/BHA). "
            "Avoid adding another strong active in the same routine; focus on moisturizer and sunscreen."
        )
        # de-emphasize extra retinoids/acids if user already uses actives
        filtered = []
        for ing in ingredients:
            n = _normalize(ing["name"])
            if any(s in n for s in STRONG_ACTIVES):
                continue
            filtered.append(ing)
        if filtered:
            ingredients = filtered

    skipped_allergy = [
        ing["name"]
        for ing in collected
        if _allergy_blocked(ing["name"], sensitivities)
    ]
    if skipped_allergy:
        unique = sorted(set(skipped_allergy))
        warnings.append(
            "Skipped because of your listed sensitivity/allergy: " + ", ".join(unique) + "."
        )

    return {
        "detected_concerns": detected,
        "recommended_ingredients": [
            {
                "name": i["name"],
                "benefit": i["benefit"],
                "priority": i["priority"],
                "usage": i.get("usage", ""),
                "caution": i.get("caution", ""),
                "concern": i.get("concern", ""),
            }
            for i in ingredients[:8]
        ],
        "unknown": False,
        "message": "",
        "warnings": warnings,
        "usage_guidance": guidance[:3],
        "source": "local_knowledge_base",
    }


def engine_conditions_from_kb(kb_result: Dict[str, Any]) -> List[str]:
    conditions: List[str] = []
    for c in kb_result.get("detected_concerns") or []:
        mapped = CONCERN_TO_ENGINE_CONDITION.get(c.get("id", ""))
        if mapped and mapped not in conditions:
            conditions.append(mapped)
    return conditions
