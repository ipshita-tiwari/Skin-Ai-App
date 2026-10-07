"""
REST API routes for skin analysis and health check.
Accepts either: (1) skin photo + optional report, or (2) chat/text + follow-up answers. At least one required.
"""
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse

from backend.utils.validation import validate_skin_image, validate_blood_report
from backend.services.analysis_service import run_analysis
from backend.ai.feedback_handler import process_feedback
from backend.ai.skincare_recommendation_service import get_skincare_recommendations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
async def health():
    """Health check for load balancers and monitoring."""
    return {"status": "ok", "service": "skin-ai-assistant"}


@router.post("/analyze")
async def analyze(
    skin_image: Optional[UploadFile] = File(None, description="Skin photo (optional if using chat)"),
    blood_report: Optional[UploadFile] = File(None, description="Optional blood report (PDF or image)"),
    text_input: Optional[str] = Form(None, description="Describe your skin/problems (optional if uploading photo)"),
    skin_type_self: Optional[str] = Form(None, description="Self-reported skin type"),
    concerns: Optional[str] = Form(None, description="Main concerns (comma-separated)"),
    uses_actives: Optional[str] = Form(None, description="Do you use retinol/vitamin C/AHA/BHA?"),
    sensitivities: Optional[str] = Form(None, description="Any sensitivities or allergies"),
):
    """
    At least one of: skin photo OR (text_input or skin_type_self) is required.
    Optional: blood report in all cases.
    Returns analysis and skincare routine.
    """
    has_photo = skin_image and skin_image.filename and skin_image.filename.strip()
    has_text = bool((text_input or "").strip()) or bool((skin_type_self or "").strip())

    if not has_photo and not has_text:
        raise HTTPException(
            status_code=400,
            detail="Please either upload a skin photo or describe your skin / answer the questions in the chat box.",
        )

    skin_bytes: Optional[bytes] = None
    if has_photo:
        content = await skin_image.read()
        ok, err = validate_skin_image(content, skin_image.filename or "")
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        skin_bytes = content

    blood_bytes: Optional[bytes] = None
    blood_is_pdf = False
    if blood_report and blood_report.filename and blood_report.filename.strip():
        blood_bytes = await blood_report.read()
        ok, err = validate_blood_report(blood_bytes, blood_report.filename)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        blood_is_pdf = blood_report.filename.lower().endswith(".pdf")

    text_clean = (text_input or "").strip() or None
    skin_type_clean = (skin_type_self or "").strip() or None
    concerns_clean = (concerns or "").strip() or None
    uses_actives_clean = (uses_actives or "").strip() or None
    sensitivities_clean = (sensitivities or "").strip() or None

    try:
        result = run_analysis(
            skin_image_bytes=skin_bytes,
            blood_report_bytes=blood_bytes,
            blood_report_is_pdf=blood_is_pdf,
            text_input=text_clean,
            skin_type_self=skin_type_clean,
            concerns=concerns_clean,
            uses_actives=uses_actives_clean,
            sensitivities=sensitivities_clean,
        )
        return JSONResponse(content=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Analysis failed: %s", e)
        err_msg = str(e)
        if not err_msg or len(err_msg) > 200:
            err_msg = "Analysis failed. Please try again."
        raise HTTPException(status_code=500, detail=err_msg)


@router.post("/ingredients")
async def ingredients(
    text_input: str = Body("", embed=True),
    concerns: Optional[list] = Body(None, embed=True),
    sensitivities: Optional[str] = Body(None, embed=True),
    uses_actives: Optional[str] = Body(None, embed=True),
):
    """Match concerns to the local knowledge base only (no internet)."""
    try:
        result = get_skincare_recommendations(
            text_input or "",
            extra_concerns=concerns or [],
            sensitivities=sensitivities,
            uses_actives=uses_actives,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Ingredient match failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not match ingredients. Please try again.")


@router.post("/feedback")
async def feedback(
    message: str = Body(..., embed=True),
    routine_summary: Optional[dict] = Body(None, embed=True),
):
    """
    Post-report chat: user can send appreciation or say an ingredient doesn't suit / isn't available.
    Returns a reply indicating if that ingredient can be ignored (optional) or suggests an alternative.
    """
    try:
        result = process_feedback(message, routine_summary)
        return JSONResponse(content=result)
    except Exception as e:
        logger.exception("Feedback failed: %s", e)
        raise HTTPException(status_code=500, detail="Could not process your message. Please try again.")
