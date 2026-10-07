"""
OCR extraction using pytesseract.
Extracts text from images and PDF pages for lab value parsing.
If Tesseract is not installed, OCR returns empty text (no crash).
"""
import logging
from io import BytesIO
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import pytesseract
except ImportError:
    pytesseract = None  # type: ignore
    logger.warning("pytesseract not installed; OCR will return empty text.")

# Optional: set tesseract path on Windows if not in PATH
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Run Tesseract OCR on an image.
    Returns raw text; lab_parser will structure it.
    If Tesseract is missing or fails, returns "".
    """
    if pytesseract is None:
        return ""
    try:
        img = Image.open(BytesIO(image_bytes))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img)
        return text.strip() or ""
    except Exception as e:
        logger.warning("OCR from image failed: %s", e)
        return ""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF by rendering pages to images then OCR.
    Requires pdf2image (and poppler) for PDF to image conversion.
    Falls back to empty string if pdf2image not available or fails.
    """
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.warning("pdf2image not available; install it and poppler for PDF support.")
        return ""

    if pytesseract is None:
        return ""
    try:
        images = convert_from_bytes(pdf_bytes, dpi=150)
        texts = []
        for img in images:
            text = pytesseract.image_to_string(img)
            if text.strip():
                texts.append(text.strip())
        return "\n\n".join(texts) if texts else ""
    except Exception as e:
        logger.warning("OCR from PDF failed: %s", e)
        return ""


def extract_text_from_blood_report(
    content: bytes, is_pdf: bool
) -> str:
    """
    Dispatch to image or PDF OCR based on content type.
    """
    if is_pdf:
        return extract_text_from_pdf(content)
    return extract_text_from_image(content)
