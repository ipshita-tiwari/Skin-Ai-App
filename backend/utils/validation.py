"""
File validation utilities.
Enforces size limits, MIME types, and basic security checks.
Uses magic bytes only (no imghdr) so it works on Python 3.13+.
"""
from typing import Tuple

from backend.config import get_settings


def _get_image_type_from_magic(content: bytes) -> str:
    """Detect image type from magic bytes. Returns 'jpeg', 'png', 'webp', or ''."""
    if len(content) < 12:
        return ""
    # JPEG: FFD8 FF
    if content[:2] == b"\xff\xd8":
        return "jpeg"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    # WebP: RIFF....WEBP
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return ""


def validate_skin_image(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validate uploaded skin image: size, type, and magic bytes.
    Returns (is_valid, error_message).
    """
    settings = get_settings()
    if len(content) > settings.max_skin_image_size:
        return False, f"Image too large. Max size: {settings.max_skin_image_size // (1024*1024)} MB"

    img_type = _get_image_type_from_magic(content)
    if img_type not in ("jpeg", "png", "webp"):
        return False, "Invalid image format. Use JPEG, PNG, or WebP."

    if ".." in filename or "\0" in filename:
        return False, "Invalid filename."

    return True, ""


def validate_blood_report(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validate uploaded blood report (PDF or image).
    Returns (is_valid, error_message).
    """
    settings = get_settings()
    if len(content) > settings.max_blood_report_size:
        return False, f"Report too large. Max size: {settings.max_blood_report_size // (1024*1024)} MB"

    if content[:4] == b"%PDF":
        return True, ""

    img_type = _get_image_type_from_magic(content)
    if img_type in ("jpeg", "png", "webp"):
        return True, ""

    if ".." in filename or "\0" in filename:
        return False, "Invalid filename."

    return False, "Invalid report format. Use PDF or image (JPEG/PNG/WebP)."
