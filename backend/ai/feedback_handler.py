"""
Post-report feedback handler.
Covers a wide range of possible queries: any ingredient, product type, or concern.
User can send appreciation or say something doesn't suit / isn't available.
We reply whether it can be ignored (optional) or suggest alternatives.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# (importance, display_name, alternative_suggestion)
# importance: "optional" | "recommended" | "important"
def _opt(name: str, suggestion: str) -> Tuple[str, str, str]:
    return ("optional", name, suggestion)
def _rec(name: str, suggestion: str) -> Tuple[str, str, str]:
    return ("recommended", name, suggestion)
def _imp(name: str, suggestion: str) -> Tuple[str, str, str]:
    return ("important", name, suggestion)

# Build a comprehensive map: keyword (lowercase) -> (importance, display_name, suggestion)
# Include typos and common variations. Longer phrases first when they share a word.
_INGREDIENT_ENTRIES = [
    # Sun protection (important)
    ("sunscreen", _imp("Sunscreen", "Sun protection matters. Try another formula (mineral or chemical) or brand. Don't skip when going out.")),
    ("spf", _imp("SPF", "Try a different SPF formulation (e.g. mineral, gel, or tinted).")),
    ("sunblock", _imp("Sunblock", "Same as sunscreen; try another product.")),
    ("sun block", _imp("Sunblock", "Same as sunscreen; try another product.")),
    # Actives – retinoids
    ("tretinoin", _rec("Tretinoin", "Prescription retinoid. If you can't use it, try retinol or bakuchiol, or skip.")),
    ("retinol", _rec("Retinol", "Helps texture and turnover. Alternatives: bakuchiol or gentle PHA. Skip if sensitive.")),
    ("retinoid", _rec("Retinoid", "Same as retinol. Alternatives: bakuchiol or PHA.")),
    ("retinols", _rec("Retinol", "Same as retinol. You can skip or use bakuchiol instead.")),
    ("adapalene", _rec("Adapalene", "Retinoid for acne. Alternatives: benzoyl peroxide or salicylic; or skip if not available.")),
    ("retinal", _rec("Retinal", "Retinoid; same advice as retinol. Bakuchiol or PHA are alternatives.")),
    ("bakuchiol", _opt("Bakuchiol", "Retinol alternative; optional. Skipping is fine.")),
    # Vitamin C & antioxidants
    ("vitamin c", _opt("Vitamin C", "Antioxidant step is optional. Use vitamin E, ferulic, or resveratrol, or skip.")),
    ("vit c", _opt("Vitamin C", "Same as vitamin C. Optional; other antioxidants or skip.")),
    ("ascorbic", _opt("Vitamin C (L-ascorbic)", "Optional antioxidant. Other forms of vitamin C or other antioxidants are fine.")),
    ("l-ascorbic", _opt("Vitamin C", "Optional. Ethyl ascorbic or other antioxidants can substitute.")),
    ("vitamin e", _opt("Vitamin E", "Optional. Many moisturizers contain it; no need for a separate product.")),
    ("vit e", _opt("Vitamin E", "Optional. Often in moisturizers already.")),
    ("ferulic", _opt("Ferulic acid", "Often with vitamin C. Optional antioxidant.")),
    ("resveratrol", _opt("Resveratrol", "Optional antioxidant. Skipping is fine.")),
    ("green tea", _opt("Green tea", "Optional antioxidant/soothing. Skip or use other antioxidants.")),
    ("caffeine", _opt("Caffeine (in skincare)", "Optional; often in eye products. Skip if not available.")),
    # Niacinamide & calming
    ("niacinamide", _opt("Niacinamide", "Optional. Skip or use centella, panthenol, or zinc.")),
    ("niacinnamide", _opt("Niacinamide", "Optional. Skip or use centella, panthenol, or zinc.")),
    ("niacinamid", _opt("Niacinamide", "Optional. Alternatives: centella, panthenol.")),
    ("centella", _opt("Centella / cica", "Soothing; optional. Panthenol, aloe, or oat are alternatives.")),
    ("cica", _opt("Centella / cica", "Soothing; optional. Panthenol or aloe can substitute.")),
    ("panthenol", _opt("Panthenol", "Soothing/hydrating; optional. Aloe or centella work too.")),
    ("b5", _opt("Panthenol (B5)", "Soothing; optional. Skip or use aloe/centella.")),
    ("beta glucan", _opt("Beta-glucan", "Soothing/hydrating; optional.")),
    ("beta-glucan", _opt("Beta-glucan", "Soothing; optional.")),
    ("aloe", _opt("Aloe", "Soothing; optional. Centella or panthenol can substitute.")),
    ("oat", _opt("Oat", "Soothing; optional. Good in cleansers or moisturizers; skip if not available.")),
    ("colloidal oatmeal", _opt("Colloidal oatmeal", "Soothing; optional. Other calming ingredients work too.")),
    ("licorice", _opt("Licorice root", "Brightening/soothing; optional. Skip or use other brighteners.")),
    ("licorice root", _opt("Licorice root", "Optional. Other brightening ingredients: vitamin C, alpha arbutin.")),
    ("alpha arbutin", _opt("Alpha arbutin", "Brightening; optional. Vitamin C or niacinamide can substitute.")),
    ("arbutin", _opt("Alpha arbutin", "Brightening; optional. Skip or use vitamin C.")),
    ("kojic", _opt("Kojic acid", "Brightening; optional. Alpha arbutin or vitamin C are alternatives.")),
    ("tranexamic", _opt("Tranexamic acid", "For dark spots; optional. Alpha arbutin or vitamin C can help.")),
    ("azelaic", _opt("Azelaic acid", "For acne and pigmentation; optional. Alternatives: niacinamide or salicylic.")),
    ("azelaic acid", _opt("Azelaic acid", "Optional. Niacinamide or salicylic if not available.")),
    # Exfoliants
    ("aha", _opt("AHA", "Chemical exfoliation is optional. Skip or use PHA/lactic less often.")),
    ("bha", _opt("BHA", "Optional for pores/acne. Gentle cleanser or skip.")),
    ("pha", _opt("PHA", "Gentle exfoliant; optional. Skipping is fine.")),
    ("glycolic", _opt("Glycolic acid", "Optional exfoliant. Lactic or PHA, or skip.")),
    ("glycolic acid", _opt("Glycolic acid", "Optional. Lactic acid or PHA are alternatives.")),
    ("lactic", _opt("Lactic acid", "Optional exfoliant. Skip or use PHA.")),
    ("lactic acid", _opt("Lactic acid", "Optional. Glycolic or PHA, or skip.")),
    ("mandelic", _opt("Mandelic acid", "Gentle AHA; optional. Skip or use PHA.")),
    ("salicylic", _opt("Salicylic acid", "Optional for pores/acne. Gentle cleanser or skip.")),
    ("salicylic acid", _opt("Salicylic acid", "Optional. BHA alternatives or skip.")),
    ("sulfur", _opt("Sulfur", "For acne; optional. Benzoyl peroxide or salicylic, or skip.")),
    ("benzoyl peroxide", _opt("Benzoyl peroxide", "For acne; optional. Salicylic or sulfur, or skip.")),
    ("bp", _opt("Benzoyl peroxide", "For acne; optional. Salicylic is an alternative.")),
    # Barrier & hydration
    ("ceramide", _rec("Ceramides", "Good for barrier. Look for cholesterol, fatty acids, or barrier creams.")),
    ("ceramides", _rec("Ceramides", "Barrier support. Alternatives: barrier creams with cholesterol and fatty acids.")),
    ("cholesterol", _opt("Cholesterol (in skincare)", "Barrier ingredient; optional. Ceramides or fatty acids in other products.")),
    ("hyaluronic", _rec("Hyaluronic acid", "Common in moisturizers. Try another HA product or glycerin-based hydration.")),
    ("ha", _rec("Hyaluronic acid", "Glycerin can substitute for hydration.")),
    ("hyaluronic acid", _rec("Hyaluronic acid", "Glycerin or other humectants if not available.")),
    ("glycerin", _opt("Glycerin", "Very common; easy to find elsewhere. Optional.")),
    ("glycerol", _opt("Glycerin", "Same as glycerin; optional.")),
    ("urea", _opt("Urea", "Hydrating/gentle exfoliant; optional. Other moisturizers work too.")),
    ("allantoin", _opt("Allantoin", "Soothing; optional. Panthenol or aloe can substitute.")),
    ("squalane", _opt("Squalane", "Emollient; optional. Other oils or ceramides.")),
    ("squalene", _opt("Squalane", "Same as squalane; optional.")),
    ("shea", _opt("Shea butter", "Emollient; optional. Other butters or oils.")),
    ("shea butter", _opt("Shea butter", "Emollient; optional. Squalane or ceramides.")),
    ("jojoba", _opt("Jojoba oil", "Emollient; optional. Other lightweight oils or squalane.")),
    ("argan", _opt("Argan oil", "Emollient; optional. Other oils or skip.")),
    ("rosehip", _opt("Rosehip oil", "Optional. Other oils or skip.")),
    ("marula", _opt("Marula oil", "Emollient; optional.")),
    # Peptides & others
    ("peptide", _opt("Peptides", "Optional for anti-aging. Skipping is fine.")),
    ("peptides", _opt("Peptides", "Optional. Rest of routine stays the same.")),
    ("snail", _opt("Snail mucin", "Hydrating/repair; optional. HA or glycerin can substitute.")),
    ("snail mucin", _opt("Snail mucin", "Optional. HA or centella for hydration/soothing.")),
    ("propolis", _opt("Propolis", "Soothing/antioxidant; optional. Honey or centella.")),
    ("honey", _opt("Honey", "Humectant/soothing; optional. Skip or use other hydrators.")),
    ("mushroom", _opt("Mushroom extract", "Soothing/antioxidant; optional. Centella or green tea.")),
    ("tea tree", _opt("Tea tree oil", "For acne; optional. Salicylic or benzoyl peroxide, or skip.")),
    ("witch hazel", _opt("Witch hazel", "Astringent; optional. Use alcohol-free if possible, or skip. Niacinamide or gentle toner as alternative.")),
    # Masks & treatments
    ("clay mask", _opt("Clay mask", "Can be drying. Skip or use rarely; prefer hydrating or soothing masks.")),
    ("clay", _opt("Clay mask", "Can be drying. Skip or use hydrating/sheet mask instead.")),
    ("sheet mask", _opt("Sheet mask", "Optional. Regular moisturizer is enough if you skip.")),
    ("hydrating mask", _opt("Hydrating mask", "Optional. Extra moisturizer or serum can substitute.")),
    ("charcoal mask", _opt("Charcoal mask", "Optional for pores. Clay or BHA, or skip.")),
    ("exfoliating mask", _opt("Exfoliating mask", "Optional. Use AHA/BHA product instead, or skip.")),
    ("peel", _opt("Chemical peel", "Optional. At-home AHA/BHA or skip.")),
    ("peeling", _opt("Exfoliation", "Optional. Reduce frequency or skip.")),
    # Product types (general)
    ("cleanser", _opt("Cleanser", "Use any gentle cleanser you have. Avoid sulfates if sensitive.")),
    ("oil cleanser", _opt("Oil cleanser", "First step of double cleanse; optional. Use micellar or gentle cleanser.")),
    ("toner", _opt("Toner", "Optional step. You can go straight to serum or moisturizer.")),
    ("essence", _opt("Essence", "Optional. Serum or moisturizer can replace it.")),
    ("serum", _opt("Serum", "Optional step. Focus on cleanser, moisturizer, and sunscreen if needed.")),
    ("moisturizer", _opt("Moisturizer", "Important for hydration but many options. Try another brand or type (gel/cream).")),
    ("moisturiser", _opt("Moisturizer", "Same as moisturizer; try another product.")),
    ("cream", _opt("Cream", "Many options. Try gel-cream or lotion if cream doesn't suit.")),
    ("gel", _opt("Gel", "Optional format. Cream or lotion can substitute.")),
    ("lotion", _opt("Lotion", "Optional. Cream or gel-cream if preferred.")),
    ("oil", _opt("Face oil", "Optional. Squalane or moisturizer can provide similar benefit.")),
    ("face oil", _opt("Face oil", "Optional. Add a few drops to moisturizer or skip.")),
    ("spot treatment", _opt("Spot treatment", "Optional. Use salicylic or benzoyl peroxide product if needed, or skip.")),
    ("eye cream", _opt("Eye cream", "Optional. Your regular moisturizer is fine for the eye area.")),
    ("lip balm", _opt("Lip balm", "Optional; use any hydrating lip product.")),
    # Preservatives & misc
    ("fragrance", _opt("Fragrance", "Fragrance-free options exist. Often better to avoid if sensitive.")),
    ("parfum", _opt("Fragrance", "Same as fragrance; choose fragrance-free.")),
    ("alcohol", _opt("Alcohol (drying)", "Avoid drying alcohol; many alcohol-free options. Optional to avoid.")),
    ("denat alcohol", _opt("Alcohol", "Drying alcohol; optional to avoid. Use alcohol-free toner.")),
    ("sulfate", _opt("Sulfates", "Can be stripping. Sulfate-free cleansers are widely available.")),
    ("sls", _opt("SLS", "Surfactant; optional to avoid. Use sulfate-free cleanser.")),
    ("sles", _opt("SLES", "Surfactant; sulfate-free alternatives exist.")),
    ("silicone", _opt("Silicones", "Optional. Many silicone-free products available if you prefer.")),
    ("silicones", _opt("Silicones", "Optional. Silicone-free moisturizers exist.")),
    ("mineral oil", _opt("Mineral oil", "Emollient; optional. Many alternatives exist.")),
    ("vitamin a", _opt("Vitamin A (retinol)", "Same as retinol; see retinol.")),
    ("zinc", _opt("Zinc", "In sunscreen or calming products; optional. Mineral sunscreen uses zinc.")),
    ("titanium", _opt("Titanium dioxide", "Often in mineral sunscreen; optional. Zinc-only sunscreen is an alternative.")),
]

INGREDIENT_INFO = {k: v for k, v in _INGREDIENT_ENTRIES}

# Extra triggers so we treat almost any "problem" message as ingredient-related
INGREDIENT_RELATED_PHRASES = [
    "doesn't suit", "does not suit", "dont suit", "don't suit", "do not suit",
    "not available", "unavailable", "can't find", "cant find", "cannot find",
    "don't have", "dont have", "do not have", "i don't have", "i dont have", "no have",
    "allergic", "allergy", "sensitive to", "doesn't work", "does not work", "dont work",
    "irritat", "burn", "sting", "avoid", "skip", "replace", "alternative", "substitute",
    "no ", "without ", "will dry", "dries ", "drying", "dry my", "dry skin", "too dry",
    "too strong", "too harsh", "break me out", "breakout", "break out", "pilling",
    "not available", "hard to find", "expensive", "can't afford", "cant afford",
    "don't like", "dont like", "doesn't like", "is it necessary", "do i need",
    "can i skip", "should i use", "optional", "necessary", "important to use",
]
INGREDIENT_RELATED_WORDS = [
    "ingredient", "product", "serum", "moisturizer", "moisturiser", "toner", "mask",
    "clay", "cleanser", "sunscreen", "spf", "cream", "gel", "oil", "acid", "vitamin",
    "retinol", "niacinamide", "ha", "ceramide", "peptide", "step", "routine",
]


def _normalize(s: str) -> str:
    return " ".join(s.lower().split())


def _detect_ingredients(text: str) -> List[Tuple[str, str, str]]:
    """Return list of (display_name, importance, suggestion). Longer keys first."""
    normalized = _normalize(text)
    found: List[Tuple[str, str, str]] = []
    for key in sorted(INGREDIENT_INFO.keys(), key=len, reverse=True):
        importance, display_name, suggestion = INGREDIENT_INFO[key]
        if re.search(r"\b" + re.escape(key) + r"\b", normalized):
            if not any(f[0] == display_name for f in found):
                found.append((display_name, importance, suggestion))
    return found


def _is_appreciation(text: str) -> bool:
    t = _normalize(text)
    appreciation_words = [
        "thank", "thanks", "great", "helpful", "good", "appreciate", "love", "awesome",
        "perfect", "excellent", "amazing", "super", "wonderful",
    ]
    return any(w in t for w in appreciation_words) and len(t.split()) <= 15


def _is_ingredient_related(normalized: str) -> bool:
    if any(phrase in normalized for phrase in INGREDIENT_RELATED_PHRASES):
        return True
    if any(word in normalized for word in INGREDIENT_RELATED_WORDS):
        return True
    # Heuristic: "i don't have X", "X doesn't work", "no X", "without X"
    if re.search(r"(don't|dont|do not|can't|cant)\s+(have|use|find)", normalized):
        return True
    if re.search(r"(don't|doesn't|dont|doesnt)\s+(suit|work)", normalized):
        return True
    if re.search(r"\b(not|no)\s+(available|have|use)\b", normalized):
        return True
    return False


def _extract_mentioned_thing(text: str) -> Optional[str]:
    """Try to extract a short phrase the user is asking about (e.g. after 'don't have' or 'without')."""
    normalized = _normalize(text)
    # After "don't have", "without", "no" + word
    for pattern in [
        r"(?:don't|dont|do not)\s+have\s+([^,.!?]+)",
        r"without\s+([^,.!?]+)",
        r"(?:can't|cant)\s+find\s+([^,.!?]+)",
        r"(?:not|no)\s+(\w+(?:\s+\w+){0,3})\s+(?:available|here)",
        r"(\w+(?:\s+\w+)?)\s+(?:doesn't|doesnt|don't|dont)\s+(?:suit|work)",
        r"(\w+(?:\s+\w+)?)\s+(?:will\s+)?dry",
        r"(?:allergic|sensitive)\s+to\s+([^,.!?]+)",
    ]:
        m = re.search(pattern, normalized)
        if m:
            return m.group(1).strip()[:50]
    return None


def process_feedback(message: str, routine_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process any feedback: appreciation, or any ingredient/product that doesn't suit or isn't available.
    Covers a wide range of possible queries; fallback for unrecognized items.
    """
    message = (message or "").strip()
    if not message:
        return {"reply": "Please type a message—e.g. thanks, or an ingredient/product that doesn't suit you or isn't available.", "ingredient_optional": None, "ingredient_name": None}

    if _is_appreciation(message):
        return {
            "reply": "We're glad the routine helped! If any ingredient or product doesn't suit you or isn't available, tell us here and we'll say whether you can skip it or suggest an alternative.",
            "ingredient_optional": None,
            "ingredient_name": None,
        }

    normalized = _normalize(message)
    ingredient_related = _is_ingredient_related(normalized)

    if ingredient_related:
        found = _detect_ingredients(message)
        if found:
            parts = []
            any_optional = False
            for display_name, importance, suggestion in found:
                if importance == "optional":
                    any_optional = True
                    parts.append(f"**{display_name}**: Optional—you can safely skip it or ignore it. {suggestion}")
                elif importance == "recommended":
                    any_optional = True
                    parts.append(f"**{display_name}**: Recommended but not mandatory. {suggestion}")
                else:
                    parts.append(f"**{display_name}**: Important for protection or results. {suggestion}")
            reply = " ".join(parts) if len(parts) == 1 else ("Here's what we suggest: " + " ".join(parts))
            return {"reply": reply, "ingredient_optional": any_optional, "ingredient_name": found[0][0] if found else None}

        # No specific ingredient matched: use fallback so we still address the query
        mentioned = _extract_mentioned_thing(message)
        if mentioned:
            reply = (
                f"For **{mentioned}**: we don't have it in our detailed list, but in general most ingredients and steps (except sunscreen) are optional. "
                "You can skip that step or try a different product. For sun protection, try another formulation rather than skipping entirely."
            )
        else:
            reply = (
                "Most ingredients and steps in a routine are optional except sunscreen. "
                "You can skip or substitute anything that doesn't suit you or isn't available. "
                "If you name a specific ingredient (e.g. retinol, vitamin C, clay mask, niacinamide), we can say if it's optional or suggest an alternative."
            )
        return {"reply": reply, "ingredient_optional": True, "ingredient_name": mentioned}

    # Generic reply only when message doesn't look like ingredient feedback
    return {
        "reply": "You can share appreciation, or tell us which ingredient or product doesn't suit you or isn't available—we'll say if it can be ignored or suggest an alternative.",
        "ingredient_optional": None,
        "ingredient_name": None,
    }
