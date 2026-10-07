"""
Rule-based skincare recommendation engine.
Produces a customized routine with detailed product specs: moisturizer type/ingredients,
serum category/percentage/concentration, toner, and weekly masks/procedures.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _step(
    step: str,
    product_type: str,
    reason: str,
    category: str = "",
    percentage: str = "",
    concentration: str = "",
    product_details: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    """Build a step dict with optional detail fields for frontend."""
    d: Dict[str, Any] = {
        "step": step,
        "product_type": product_type,
        "reason": reason,
    }
    if category:
        d["category"] = category
    if percentage:
        d["percentage"] = percentage
    if concentration:
        d["concentration"] = concentration
    if product_details:
        d["product_details"] = product_details
    for k, v in extra.items():
        if v not in (None, ""):
            d[k] = v
    return d


def _kb_ingredient_names(kb_result: Dict[str, Any]) -> List[str]:
    ings = kb_result.get("recommended_ingredients") or []
    return [i.get("name", "") for i in ings if i.get("name")]


def _pick_kb_treatment(kb_result: Dict[str, Any], slot: str) -> Dict[str, Any]:
    """Choose a leave-on treatment from the local knowledge base for AM or PM."""
    names = [n.lower() for n in _kb_ingredient_names(kb_result)]
    am_first = ("vitamin c", "niacinamide", "hyaluronic", "centella", "panthenol", "azelaic", "zinc")
    pm_first = ("retinol", "adapalene", "azelaic", "niacinamide", "salicylic", "lactic", "glycolic", "peptides")
    order = am_first if slot == "am" else pm_first
    ings = kb_result.get("recommended_ingredients") or []
    for needle in order:
        for ing in ings:
            if needle in (ing.get("name") or "").lower():
                return ing
    return ings[0] if ings else {}


def build_recommendation(
    skin_result: Dict[str, Any],
    lab_result: Dict[str, Any],
    kb_result: Optional[Dict[str, Any]] = None,
    uses_actives: Optional[str] = None,
    sensitivities: Optional[str] = None,
    text_input: Optional[str] = None,
    severe_symptoms: bool = False,
) -> Dict[str, Any]:
    """
    Build customized routine with full details: moisturizer, serum (category/%/concentration),
    toner, and weekly masks/procedures.
    """
    explanations: List[str] = []
    lab_notes: List[str] = []
    kb_result = kb_result or {}

    skin_type = skin_result.get("skin_type", "normal")
    conditions = skin_result.get("conditions", [])
    lab_values = lab_result.get("values", {})
    kb_ings = kb_result.get("recommended_ingredients") or []
    kb_names = ", ".join(_kb_ingredient_names(kb_result)[:5]) if kb_ings else ""

    # --- Morning routine ---
    am_steps: List[Dict[str, Any]] = []

    # Cleanser
    if skin_type in ("dry", "normal") or "dry_patches" in conditions:
        am_steps.append(_step(
            "Cleanser",
            "Gentle hydrating cleanser",
            "Avoid stripping natural oils; supports barrier.",
            product_details="Look for: ceramides, glycerin, no sulfates. Cream or milky texture.",
        ))
    elif skin_type == "oily" or "oiliness" in conditions:
        am_steps.append(_step(
            "Cleanser",
            "Light gel or foaming cleanser (non-comedogenic)",
            "Controls oil without over-drying.",
            product_details="Look for: salicylic acid (0.5–2%) optional, niacinamide. Avoid heavy oils.",
        ))
    else:
        am_steps.append(_step(
            "Cleanser",
            "Gentle daily cleanser",
            "Basic cleansing for balanced skin.",
            product_details="pH-balanced (around 5.5), sulfate-free preferred.",
        ))

    # Toner (detailed)
    if skin_type == "dry" or "dry_patches" in conditions:
        am_steps.append(_step(
            "Toner",
            "Hydrating toner",
            "Restore moisture and prep skin for serums.",
            product_details="Look for: hyaluronic acid, glycerin, centella, green tea. Avoid: high alcohol, astringents. Apply to damp skin.",
            toner_type="Hydrating",
        ))
    elif skin_type == "oily" or "oiliness" in conditions:
        am_steps.append(_step(
            "Toner",
            "Balancing / pore-refining toner",
            "Balance pH and lightly control oil.",
            product_details="Look for: niacinamide (2–5%), salicylic acid (0.5–1%), or witch hazel (alcohol-free). Avoid: stripping alcohol-heavy toners.",
            toner_type="Balancing",
        ))
    else:
        am_steps.append(_step(
            "Toner",
            "Light hydrating or antioxidant toner",
            "Prep skin and add a light layer of hydration or antioxidants.",
            product_details="Look for: hyaluronic acid, vitamin E, ferulic acid. Optional: gentle exfoliant (PHA).",
            toner_type="Hydrating or antioxidant",
        ))

    # Serum AM – prefer local knowledge-base ingredient when matched
    am_kb = _pick_kb_treatment(kb_result, "am")
    if am_kb:
        am_steps.append(_step(
            "Treatment",
            am_kb.get("name", "Hydrating serum"),
            am_kb.get("benefit") or "Selected from the built-in knowledge base for your described concerns.",
            category="Local knowledge base",
            product_details=am_kb.get("usage") or "Apply after cleanser, before moisturizer.",
            concentration=am_kb.get("caution") or "",
        ))
    elif skin_type in ("sensitive", "dry") or "redness" in conditions:
        am_steps.append(_step(
            "Treatment",
            "Soothing / barrier serum",
            "May help calm and support the barrier before moisturizer.",
            category="Soothing / Barrier repair",
            percentage="5–10% niacinamide if tolerated",
            concentration="Look for panthenol, centella, or ceramides if niacinamide is not tolerated.",
            product_details="Apply to damp skin. Layer under moisturizer.",
        ))
    else:
        am_steps.append(_step(
            "Treatment",
            "Vitamin C antioxidant serum (optional)",
            "Commonly used to support a brighter-looking appearance under sunscreen.",
            category="Antioxidant (Vitamin C)",
            percentage="10–15% L-ascorbic acid (or a gentler derivative if new to vitamin C)",
            concentration="Optional step. Skip if sensitive or if you already use vitamin C.",
            product_details="Apply to dry skin after cleanser, before moisturizer.",
        ))

    # Moisturizer AM – type and key ingredients
    if skin_type == "dry" or "dry_patches" in conditions:
        am_steps.append(_step(
            "Moisturizer (AM)",
            "Rich cream or barrier-repair moisturizer",
            "Restore hydration and strengthen barrier.",
            product_details="Type: Cream or balm. Key ingredients: ceramides, cholesterol, fatty acids, hyaluronic acid, shea butter or squalane. Avoid: heavy fragrances if sensitive.",
            moisturizer_type="Cream / barrier repair",
            ingredients="Ceramides, HA, squalane, cholesterol",
        ))
    elif skin_type == "oily":
        am_steps.append(_step(
            "Moisturizer (AM)",
            "Lightweight gel or oil-free moisturizer",
            "Hydration without adding shine or clogging pores.",
            product_details="Type: Gel or gel-cream. Key ingredients: hyaluronic acid, niacinamide, zinc, lightweight silicones. Oil-free, non-comedogenic.",
            moisturizer_type="Gel / gel-cream",
            ingredients="HA, niacinamide, oil-free",
        ))
    else:
        am_steps.append(_step(
            "Moisturizer (AM)",
            "Light lotion or gel-cream",
            "Maintain hydration without heaviness.",
            product_details="Type: Lotion or gel-cream. Key ingredients: hyaluronic acid, ceramides, niacinamide (optional).",
            moisturizer_type="Lotion / gel-cream",
            ingredients="HA, ceramides",
        ))

    # Sunscreen
    am_steps.append(_step(
        "Sunscreen",
        "Broad-spectrum SPF 30+ (daily)",
        "Essential for preventing UV damage and aging. Reapply every 2 hours if outdoors.",
        product_details="Mineral (zinc/titanium) or chemical; choose one that doesn’t pill under makeup. At least 1/4 tsp for face.",
    ))

    # --- Evening routine ---
    pm_steps: List[Dict[str, Any]] = []

    pm_steps.append(_step(
        "Cleanser",
        "Same as AM or double cleanse if you wear makeup/sunscreen",
        "Remove sunscreen and impurities; oil cleanse first if double cleansing.",
        product_details="First step: oil or balm cleanser. Second: same as AM cleanser.",
    ))

    # Toner PM (can repeat or use same)
    pm_steps.append(_step(
        "Toner",
        "Same as AM or slightly more hydrating at night",
        "Prep skin for treatment serums.",
        product_details="Reapply same toner as AM for consistency.",
    ))

    # Serum PM – treatment from knowledge base when possible (no prescriptions)
    pm_kb = _pick_kb_treatment(kb_result, "pm")
    uses = (uses_actives or "").strip().lower()
    if uses in ("yes", "sometimes"):
        pm_steps.append(_step(
            "Treatment",
            "Keep your current active; add barrier support",
            "You already use actives. Do not duplicate retinol, vitamin C, or AHA/BHA in the same routine.",
            category="Barrier support",
            product_details="Use ceramides, panthenol, or peptides at night. Keep sunscreen in the morning.",
        ))
    elif pm_kb:
        pm_steps.append(_step(
            "Treatment",
            pm_kb.get("name", "Night treatment"),
            pm_kb.get("benefit") or "From the built-in knowledge base.",
            category="Local knowledge base",
            product_details=pm_kb.get("usage") or "Night only if the ingredient is a retinoid or acid.",
            concentration=pm_kb.get("caution") or "",
        ))
    elif skin_type in ("dry", "sensitive") or "redness" in conditions:
        pm_steps.append(_step(
            "Treatment",
            "Soothing / barrier serum",
            "May help comfort skin overnight.",
            category="Soothing / Barrier",
            percentage="Panthenol or 5% niacinamide if tolerated",
            concentration="Centella, panthenol, ceramides. Avoid extra strong actives.",
            product_details="Apply to damp skin.",
        ))
    else:
        pm_steps.append(_step(
            "Treatment",
            "Retinol (optional, if tolerated)",
            "Commonly used to support the look of texture. Start slowly. This is not a prescription.",
            category="Retinoid (cosmetic)",
            percentage="Low-strength retinol a few nights per week",
            concentration="Use 2–3x per week at first. Do not combine with AHA/BHA on the same night.",
            product_details="Night only. Moisturizer after. SPF the next morning. Avoid if pregnant unless a clinician advises.",
        ))

    # Moisturizer PM
    if skin_type == "dry" or "dry_patches" in conditions:
        pm_steps.append(_step(
            "Moisturizer (PM)",
            "Richer cream or overnight mask",
            "Overnight repair and barrier support.",
            product_details="Type: Rich cream or sleeping mask. Key ingredients: ceramides, peptides, squalane, shea butter. Can layer over serum.",
            moisturizer_type="Rich cream / sleeping mask",
            ingredients="Ceramides, peptides, squalane",
        ))
    else:
        pm_steps.append(_step(
            "Moisturizer (PM)",
            "Same as AM or slightly richer at night",
            "Overnight repair and hydration.",
            product_details="Type: Lotion or cream. Same key ingredients as AM; optional: add a few drops of face oil if dry.",
            moisturizer_type="Lotion / cream",
            ingredients="HA, ceramides",
        ))

    routine = [
        {"time": "AM", "steps": am_steps},
        {"time": "PM", "steps": pm_steps},
    ]

    # --- Weekly treatments: masks and procedures ---
    weekly_treatments: List[Dict[str, Any]] = []

    if skin_type == "oily" or "oiliness" in conditions:
        weekly_treatments.append({
            "name": "Clay or purifying mask",
            "type": "Face mask",
            "frequency": "1–2 times per week",
            "details": "Use a clay (kaolin/bentonite) or charcoal mask on oily areas. Leave 5–10 min. Follow with hydrating toner and moisturizer.",
            "reason": "Helps control oil and clear pores without over-drying.",
        })
        weekly_treatments.append({
            "name": "Chemical exfoliation (BHA)",
            "type": "Procedure",
            "frequency": "1–2 times per week (e.g. Tue, Fri)",
            "details": "Salicylic acid 2% (BHA) leave-on product or peel. Use in PM, not on same night as retinol when starting. Start 1x/week.",
            "reason": "Unclogs pores and reduces blackheads; ideal for oily/acne-prone.",
        })
    elif skin_type == "dry" or "dry_patches" in conditions:
        weekly_treatments.append({
            "name": "Hydrating or sheet mask",
            "type": "Face mask",
            "frequency": "1–2 times per week",
            "details": "Hydrating sheet mask or thick hydrating mask (HA, ceramides, honey). Leave 15–20 min. Seal with moisturizer after.",
            "reason": "Boosts hydration and barrier; good after a long day or travel.",
        })
        weekly_treatments.append({
            "name": "Gentle exfoliation (PHA or low % AHA)",
            "type": "Procedure",
            "frequency": "1 time per week (e.g. Sunday PM)",
            "details": "PHA (gluconolactone) or lactic acid 5–10%. Use in PM. Skip if using retinol the same night. Moisturize well after.",
            "reason": "Gentle turnover without stripping; helps dullness and flakiness.",
        })
    else:
        weekly_treatments.append({
            "name": "Hydrating or antioxidant mask",
            "type": "Face mask",
            "frequency": "1 time per week",
            "details": "Hydrating (HA, aloe) or antioxidant (vitamin C, green tea) mask. Leave 10–15 min.",
            "reason": "Maintains hydration and glow.",
        })
        weekly_treatments.append({
            "name": "Gentle exfoliation (AHA or PHA)",
            "type": "Procedure",
            "frequency": "1–2 times per week (e.g. Wed, Sat PM)",
            "details": "Glycolic 5–8% or lactic 5–10%, or PHA. Use in PM. Don’t use same night as retinol when starting. SPF next day.",
            "reason": "Smooth texture and brightness; support cell turnover.",
        })

    # Sensitive/redness: add calming mask
    if skin_type == "sensitive" or "redness" in conditions:
        weekly_treatments.append({
            "name": "Calming / soothing mask",
            "type": "Face mask",
            "frequency": "1–2 times per week",
            "details": "Centella, cica, oatmeal, or colloidal oatmeal mask. Avoid strong actives. Leave 10 min.",
            "reason": "Reduces redness and soothes irritation.",
        })

    # Explanation
    explanations.append(skin_result.get("explanation", "Skin analysis completed."))
    explanations.append(
        f"Routine tailored for {skin_type} skin with focus on: "
        + (", ".join(conditions) if conditions else "general care")
        + ". Below: product types, serum concentrations, moisturizer details, toner, and weekly masks/procedures."
    )

    # Lab-based notes (unchanged)
    def v(name: str):
        return lab_values.get(name, {}).get("value")

    hb = v("hemoglobin")
    if hb is not None:
        if hb < 12:
            lab_notes.append("Low hemoglobin (CBC) can cause pale, dull skin and fatigue; discuss with your doctor for possible anemia.")
        elif hb >= 12:
            lab_notes.append("Hemoglobin (CBC) is in a reasonable range for skin and energy.")

    vit_d = v("vitamin_d")
    if vit_d is not None:
        if vit_d < 20:
            lab_notes.append("Low Vitamin D may affect skin barrier and immunity; consider supplementation and discuss with your doctor.")
        elif vit_d < 30:
            lab_notes.append("Vitamin D in suboptimal range; adequate sun exposure or supplementation may help (consult a doctor).")
        else:
            lab_notes.append("Vitamin D level is in a good range for skin and overall health.")

    b12 = v("vitamin_b12")
    if b12 is not None:
        if b12 < 400:
            lab_notes.append("Vitamin B12 in lower range may affect skin vitality and energy; consider medical advice.")
        else:
            lab_notes.append("Vitamin B12 is in a good range for skin and nervous system health.")

    ferritin = v("ferritin")
    serum_iron_val = v("serum_iron")
    if ferritin is not None:
        if ferritin < 30:
            lab_notes.append("Low ferritin can contribute to dull skin, hair loss, and fatigue; consider discussing with your doctor.")
        elif ferritin >= 30:
            lab_notes.append("Ferritin is in a reasonable range for skin and hair health.")
    if serum_iron_val is not None and ferritin is None and serum_iron_val < 60:
        lab_notes.append("Low serum iron may affect skin and energy; discuss with your doctor.")

    fasting_glucose_val = v("fasting_glucose") or v("glucose")
    if fasting_glucose_val is not None:
        if fasting_glucose_val >= 126:
            lab_notes.append("Elevated fasting glucose can affect skin (glycation, healing); discuss with your doctor.")
        elif fasting_glucose_val >= 100:
            lab_notes.append("Fasting glucose in borderline range; diet and exercise may help skin and overall health.")
        else:
            lab_notes.append("Fasting glucose is in a good range for skin and metabolic health.")

    hba1c_val = v("hba1c")
    if hba1c_val is not None:
        if hba1c_val >= 6.5:
            lab_notes.append("HbA1c in diabetic range; blood sugar control is important for skin healing and health—see your doctor.")
        elif hba1c_val >= 5.7:
            lab_notes.append("HbA1c in prediabetic range; lifestyle changes can benefit skin and overall health.")

    fasting_insulin_val = v("fasting_insulin") or v("insulin")
    if fasting_insulin_val is not None and fasting_insulin_val > 25:
        lab_notes.append("Elevated fasting insulin may be linked to oilier skin and acne; consider discussing insulin resistance with your doctor.")

    tsh_val = v("tsh")
    if tsh_val is not None:
        if tsh_val > 4.5:
            lab_notes.append("Elevated TSH may suggest underactive thyroid, which can cause dry skin and hair; discuss with your doctor.")
        elif tsh_val < 0.4:
            lab_notes.append("Low TSH may suggest overactive thyroid; can affect skin—discuss with your doctor.")
        else:
            lab_notes.append("TSH is in normal range; thyroid is relevant for skin and hair health.")

    test_val = v("testosterone")
    if test_val is not None and test_val > 1000:
        lab_notes.append("High testosterone can contribute to oilier skin and acne; discuss with your doctor if concerning.")

    dheas_val = v("dheas")
    if dheas_val is not None and dheas_val > 400:
        lab_notes.append("Elevated DHEAS can be associated with oilier skin and acne; discuss with your doctor if relevant.")

    prolactin_val = v("prolactin")
    if prolactin_val is not None and prolactin_val > 25:
        lab_notes.append("Elevated prolactin can sometimes affect skin and hormones; discuss with your doctor if symptomatic.")

    if (v("lh") is not None or v("fsh") is not None):
        lab_notes.append("LH/FSH were considered for hormonal context relevant to skin; interpret with your healthcare provider.")

    zinc_val = v("zinc")
    if zinc_val is not None and zinc_val < 60:
        lab_notes.append("Zinc supports skin healing and oil regulation; low levels may be worth discussing with a doctor.")

    if not lab_notes and lab_values:
        lab_notes.append("Lab values were read; no specific supplement advice from this report. Always interpret labs with a healthcare provider.")

    disclaimer = (
        "This guidance is educational and not a medical diagnosis. "
        "Consult a licensed dermatologist for personalized treatment."
    )

    detected = kb_result.get("detected_concerns") or []
    possible = [c.get("name") for c in detected if c.get("name")]
    if not possible:
        possible = [skin_type.replace("_", " ").title() + " skin (from available inputs)"]

    image_conf = float(skin_result.get("confidence") or 0)
    if severe_symptoms:
        confidence_level = "Low"
    elif detected and (not skin_result.get("prediction_uncertain")):
        confidence_level = "Medium" if image_conf and image_conf < 0.7 else "Medium"
        if detected and (text_input or "").strip():
            confidence_level = "High" if len(detected) >= 1 and image_conf >= 0.7 else "Medium"
        if skin_result.get("meta", {}).get("source") == "text" and detected:
            confidence_level = "Medium"
    else:
        confidence_level = "Low"

    if kb_result.get("unknown"):
        confidence_level = "Low"

    why = {
        "symptom_matches": [c.get("name") for c in detected] or ["Limited symptom match from the built-in database."],
        "skin_type_correlation": f"Routine adjusted for {skin_type} skin.",
        "blood_correlation": lab_notes[0] if lab_notes else "No blood report correlation used.",
    }

    when_derm = [
        "If symptoms worsen, spread, bleed, or include fever or severe pain, see a dermatologist promptly.",
        "See a dermatologist for cystic or scarring breakouts, sudden rashes, or anything that looks unlike typical dryness or oiliness.",
    ]
    if severe_symptoms:
        when_derm.insert(
            0,
            "Urgent: your description includes severe warning signs (such as bleeding, spreading infection, fever, or severe pain). Seek in-person dermatology or urgent care now. Do not start new actives.",
        )

    lifestyle = [
        "Daily broad-spectrum sunscreen if you go outdoors.",
        "Avoid picking at breakouts.",
        "Introduce only one new active at a time.",
    ]
    if sensitivities:
        lifestyle.append(f"Avoid products containing your listed sensitivities: {sensitivities}.")
    if uses_actives and uses_actives.lower() in ("yes", "sometimes"):
        lifestyle.append("Keep current actives; do not stack extra acids or retinoids on the same night.")

    if severe_symptoms:
        # Strip aggressive weekly acids/retinoids
        weekly_treatments = [
            {
                "name": "Pause actives",
                "type": "Safety",
                "frequency": "Until seen by a clinician",
                "details": "Use a bland cleanser, plain moisturizer, and sunscreen only.",
                "reason": "Severe symptoms should not be self-treated with strong actives.",
            }
        ]

    return {
        "routine": routine,
        "weekly_treatments": weekly_treatments,
        "explanation": " ".join(explanations)
        + ((" Knowledge base matched: " + kb_names + ".") if kb_names else "")
        + ((" " + kb_result.get("message", "")) if kb_result.get("unknown") else ""),
        "lab_notes": lab_notes,
        "disclaimer": disclaimer,
        "skin_summary": {"skin_type": skin_type, "conditions": conditions},
        "lab_summary": {"parsed_count": len(lab_values), "values": lab_values},
        "possible_condition": possible,
        "why": why,
        "confidence_level": confidence_level,
        "when_to_see_dermatologist": when_derm,
        "lifestyle": lifestyle,
        "knowledge_warnings": kb_result.get("warnings") or [],
        "severe_symptoms": severe_symptoms,
    }
