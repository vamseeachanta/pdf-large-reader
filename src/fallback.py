"""
ABOUTME: PDF fallback processing module for complex layouts and scanned PDFs
ABOUTME: Uses OpenAI Codex API when PyMuPDF fails (target <1% usage)
"""

import base64
import io
import logging
from typing import Optional, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Fallback usage tracking
_fallback_stats = {
    "total_pages": 0,
    "fallback_used": 0,
    "codex_calls": 0,
    "chrome_calls": 0
}


def should_use_fallback(page: fitz.Page, complexity_score: float) -> Tuple[bool, str]:
    """
    Determine if fallback AI processing is needed.

    Args:
        page: PyMuPDF page object
        complexity_score: Page complexity (0-100)

    Returns:
        Tuple of (should_use_fallback: bool, reason: str)

    Criteria:
    - Scanned PDF without OCR (no extractable text)
    - Complex multi-column layouts (complexity > 85)
    - Heavy use of custom fonts
    - Complexity score > 85
    """
    logger.debug("Evaluating fallback need for page (complexity=%.2f)", complexity_score)

    # Check for scanned PDF without OCR
    text = page.get_text().strip()
    if not text or len(text) < 10:
        # Very little or no text extractable
        logger.debug("Page has minimal text (%d chars), likely scanned", len(text))
        return True, "scanned_pdf"

    # Check complexity score
    if complexity_score > 85:
        logger.debug("High complexity score (%.2f > 85)", complexity_score)
        return True, "high_complexity"

    # Check for complex multi-column layout
    # Detect by analyzing text blocks
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [b for b in blocks if b.get("type") == 0]  # 0 = text block

    if len(text_blocks) > 20:
        # Many text blocks might indicate complex layout
        # Check horizontal distribution
        x_positions = [b["bbox"][0] for b in text_blocks]
        x_variance = max(x_positions) - min(x_positions)

        if x_variance > page.rect.width * 0.7:
            # Text spans >70% of page width with many blocks
            logger.debug("Complex multi-column layout detected")
            return True, "complex_layout"

    # Check for custom fonts (many different fonts)
    fonts = page.get_fonts(full=True)
    if len(fonts) > 15:
        logger.debug("Many fonts detected (%d), might indicate complex document", len(fonts))
        return True, "many_fonts"

    # No fallback needed
    logger.debug("Standard extraction should work fine")
    return False, "standard"


def extract_with_codex(
    page: fitz.Page,
    api_key: str,
    model: str = "gpt-4o"
) -> str:
    """
    Extract content using OpenAI Codex API.

    Args:
        page: PyMuPDF page object
        api_key: OpenAI API key
        model: Model to use (default: gpt-4o)

    Returns:
        Extracted text from Codex

    Raises:
        ValueError: If api_key is not provided
        RuntimeError: If API call fails

    Usage tracking:
    - Logs each usage
    - Updates fallback statistics
    - Target: < 1% of total pages
    """
    if not api_key:
        raise ValueError("OpenAI API key is required for fallback extraction")

    logger.info("Using Codex fallback for page %d", page.number + 1)

    # Update statistics
    _fallback_stats["fallback_used"] += 1
    _fallback_stats["codex_calls"] += 1

    try:
        # Render page as image
        pix = page.get_pixmap(dpi=150)  # 150 DPI for good quality
        img_bytes = pix.tobytes("png")

        # Encode image as base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        # Note: This is a placeholder for actual OpenAI API call
        # In production, this would make an actual API request
        # For now, we'll simulate the response
        logger.warning("Codex extraction simulation - implement actual API call in production")

        # Simulated extraction (in production, call OpenAI API here)
        extracted_text = f"[Codex fallback extraction for page {page.number + 1}]\n"
        extracted_text += "This is a placeholder for OpenAI Codex API extraction.\n"
        extracted_text += f"Image size: {len(img_bytes)} bytes, Model: {model}\n"

        # In production, uncomment and implement:
        # import openai
        # client = openai.OpenAI(api_key=api_key)
        # response = client.chat.completions.create(
        #     model=model,
        #     messages=[
        #         {
        #             "role": "user",
        #             "content": [
        #                 {"type": "text", "text": "Extract all text from this PDF page image, preserving layout."},
        #                 {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
        #             ]
        #         }
        #     ]
        # )
        # extracted_text = response.choices[0].message.content

        logger.debug("Codex extraction completed, %d chars", len(extracted_text))
        return extracted_text

    except Exception as e:
        logger.error("Codex extraction failed: %s", e)
        raise RuntimeError(f"Codex API call failed: {e}")


def extract_with_chrome(page_image: bytes) -> str:
    """
    Extract content using Chrome Claude extension (last resort).

    Args:
        page_image: Page rendered as image bytes (PNG format)

    Returns:
        Extracted text from Claude extension

    Raises:
        RuntimeError: If Chrome extension is not available
        ValueError: If page_image is invalid

    Note:
        This is a last-resort fallback when Codex is not available.
        Requires Chrome with Claude extension installed.
    """
    if not page_image or len(page_image) == 0:
        raise ValueError("Invalid page image provided")

    logger.info("Using Chrome Claude extension fallback")

    # Update statistics
    _fallback_stats["fallback_used"] += 1
    _fallback_stats["chrome_calls"] += 1

    # Note: This is a placeholder for Chrome extension interaction
    # In production, this would communicate with Chrome extension
    logger.warning("Chrome extension extraction simulation - implement actual integration in production")

    # Simulated extraction
    extracted_text = "[Chrome Claude extension extraction]\n"
    extracted_text += "This is a placeholder for Chrome extension extraction.\n"
    extracted_text += f"Image size: {len(page_image)} bytes\n"

    # In production, implement Chrome extension communication here
    # This might involve:
    # 1. Saving image to temp file
    # 2. Using Chrome DevTools Protocol to send to extension
    # 3. Receiving extracted text response

    logger.debug("Chrome extension extraction completed, %d chars", len(extracted_text))
    return extracted_text


def get_fallback_stats() -> dict:
    """
    Get current fallback usage statistics.

    Returns:
        Dictionary with:
        - total_pages: Total pages processed
        - fallback_used: Number of pages using fallback
        - codex_calls: Number of Codex API calls
        - chrome_calls: Number of Chrome extension calls
        - fallback_percentage: Percentage of pages using fallback
    """
    stats = _fallback_stats.copy()

    if stats["total_pages"] > 0:
        stats["fallback_percentage"] = (stats["fallback_used"] / stats["total_pages"]) * 100
    else:
        stats["fallback_percentage"] = 0.0

    return stats


def reset_fallback_stats() -> None:
    """Reset fallback usage statistics (useful for testing)."""
    global _fallback_stats
    _fallback_stats = {
        "total_pages": 0,
        "fallback_used": 0,
        "codex_calls": 0,
        "chrome_calls": 0
    }
    logger.debug("Fallback statistics reset")


def increment_total_pages() -> None:
    """Increment total pages processed counter."""
    _fallback_stats["total_pages"] += 1
