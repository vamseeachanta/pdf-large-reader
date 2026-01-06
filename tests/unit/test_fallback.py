"""
ABOUTME: Unit tests for fallback module
ABOUTME: Tests Codex and Chrome extension fallback functionality
"""

import base64
import unittest
from unittest.mock import MagicMock, patch

import fitz  # PyMuPDF

from src.fallback import (
    extract_with_chrome,
    extract_with_codex,
    get_fallback_stats,
    increment_total_pages,
    reset_fallback_stats,
    should_use_fallback,
)


class TestShouldUseFallback(unittest.TestCase):
    """Test fallback decision logic."""

    def setUp(self):
        """Reset statistics before each test."""
        reset_fallback_stats()

    def test_scanned_pdf_detection(self):
        """Test detection of scanned PDF without OCR."""
        # Create mock page with minimal text
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""  # No extractable text
        mock_page.number = 0

        should_use, reason = should_use_fallback(mock_page, 50)

        assert should_use is True
        assert reason == "scanned_pdf"

    def test_high_complexity_score(self):
        """Test fallback for high complexity score."""
        # Create mock page with normal text but high complexity
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Some normal text content here"
        mock_page.number = 0

        should_use, reason = should_use_fallback(mock_page, 90)

        assert should_use is True
        assert reason == "high_complexity"

    def test_complex_multi_column_layout(self):
        """Test detection of complex multi-column layout."""
        # Create mock page with many text blocks spanning page width
        mock_page = MagicMock()
        mock_page.rect.width = 612  # Standard page width

        # Create many text blocks with wide horizontal distribution
        blocks = []
        for i in range(25):
            x_pos = 50 + (i % 5) * 120  # Spread across page (exceeds 70% threshold)
            blocks.append({
                "type": 0,
                "bbox": [x_pos, 100 + (i * 20), x_pos + 80, 115 + (i * 20)]
            })

        # Use side_effect to handle different call modes
        def get_text_side_effect(mode=None):
            if mode == "dict":
                return {"blocks": blocks}
            else:
                return "Lots of text in multiple columns"

        mock_page.get_text.side_effect = get_text_side_effect

        should_use, reason = should_use_fallback(mock_page, 70)

        assert should_use is True
        assert reason == "complex_layout"

    def test_many_fonts_detection(self):
        """Test detection of documents with many fonts."""
        # Create mock page with normal text
        mock_page = MagicMock()
        mock_page.number = 0

        # Use side_effect to handle different call modes
        def get_text_side_effect(mode=None):
            if mode == "dict":
                return {
                    "blocks": [
                        {"type": 0, "bbox": [100, 100, 200, 120]},
                        {"type": 0, "bbox": [100, 130, 200, 150]}
                    ]
                }
            else:
                return "Text with many fonts"

        mock_page.get_text.side_effect = get_text_side_effect
        mock_page.get_fonts.return_value = [(i, f"font{i}") for i in range(20)]  # 20 fonts

        should_use, reason = should_use_fallback(mock_page, 70)

        assert should_use is True
        assert reason == "many_fonts"

    def test_standard_pdf_no_fallback(self):
        """Test that standard PDF doesn't trigger fallback."""
        # Create mock page with normal characteristics
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.rect.width = 612

        # Use side_effect to handle different call modes
        def get_text_side_effect(mode=None):
            if mode == "dict":
                return {
                    "blocks": [
                        {"type": 0, "bbox": [100, 100, 200, 120]},
                        {"type": 0, "bbox": [100, 130, 200, 150]},
                        {"type": 0, "bbox": [100, 160, 200, 180]}
                    ]
                }
            else:
                return "Normal text content here with good amount of text"

        mock_page.get_text.side_effect = get_text_side_effect

        # Normal number of fonts
        mock_page.get_fonts.return_value = [(1, "Arial"), (2, "Times")]

        should_use, reason = should_use_fallback(mock_page, 50)

        assert should_use is False
        assert reason == "standard"

    def test_minimal_text_triggers_fallback(self):
        """Test that minimal text triggers scanned PDF detection."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "123"  # Very little text
        mock_page.number = 0

        should_use, reason = should_use_fallback(mock_page, 40)

        assert should_use is True
        assert reason == "scanned_pdf"


class TestExtractWithCodex(unittest.TestCase):
    """Test Codex API extraction."""

    def setUp(self):
        """Reset statistics before each test."""
        reset_fallback_stats()

    def test_extract_with_valid_api_key(self):
        """Test Codex extraction with valid API key."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 0

        # Mock pixmap
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"fake_image_data"
        mock_page.get_pixmap.return_value = mock_pix

        # Call extraction
        result = extract_with_codex(mock_page, "fake_api_key", model="gpt-4o")

        # Verify result
        assert result is not None
        assert len(result) > 0
        assert "page 1" in result.lower()

        # Verify statistics updated
        stats = get_fallback_stats()
        assert stats["codex_calls"] == 1
        assert stats["fallback_used"] == 1

    def test_extract_without_api_key(self):
        """Test that missing API key raises error."""
        mock_page = MagicMock()
        mock_page.number = 0

        with self.assertRaises(ValueError) as context:
            extract_with_codex(mock_page, "", model="gpt-4o")

        assert "api key is required" in str(context.exception).lower()

    def test_extract_updates_statistics(self):
        """Test that extraction updates fallback statistics."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 0
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"image"
        mock_page.get_pixmap.return_value = mock_pix

        # Call multiple times
        extract_with_codex(mock_page, "key1")
        extract_with_codex(mock_page, "key2")

        stats = get_fallback_stats()
        assert stats["codex_calls"] == 2
        assert stats["fallback_used"] == 2

    def test_extract_with_custom_model(self):
        """Test Codex extraction with custom model."""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"image"
        mock_page.get_pixmap.return_value = mock_pix

        result = extract_with_codex(mock_page, "api_key", model="gpt-4-turbo")

        assert result is not None
        assert "gpt-4-turbo" in result


class TestExtractWithChrome(unittest.TestCase):
    """Test Chrome extension extraction."""

    def setUp(self):
        """Reset statistics before each test."""
        reset_fallback_stats()

    def test_extract_with_valid_image(self):
        """Test Chrome extraction with valid image."""
        page_image = b"fake_png_image_data"

        result = extract_with_chrome(page_image)

        assert result is not None
        assert len(result) > 0
        assert "chrome" in result.lower()

        # Verify statistics
        stats = get_fallback_stats()
        assert stats["chrome_calls"] == 1
        assert stats["fallback_used"] == 1

    def test_extract_with_empty_image(self):
        """Test that empty image raises error."""
        with self.assertRaises(ValueError) as context:
            extract_with_chrome(b"")

        assert "invalid page image" in str(context.exception).lower()

    def test_extract_with_none_image(self):
        """Test that None image raises error."""
        with self.assertRaises(ValueError):
            extract_with_chrome(None)

    def test_extract_updates_statistics(self):
        """Test that Chrome extraction updates statistics."""
        extract_with_chrome(b"image1")
        extract_with_chrome(b"image2")
        extract_with_chrome(b"image3")

        stats = get_fallback_stats()
        assert stats["chrome_calls"] == 3
        assert stats["fallback_used"] == 3


class TestFallbackStatistics(unittest.TestCase):
    """Test fallback statistics tracking."""

    def setUp(self):
        """Reset statistics before each test."""
        reset_fallback_stats()

    def test_initial_statistics(self):
        """Test initial statistics are zero."""
        stats = get_fallback_stats()

        assert stats["total_pages"] == 0
        assert stats["fallback_used"] == 0
        assert stats["codex_calls"] == 0
        assert stats["chrome_calls"] == 0
        assert stats["fallback_percentage"] == 0.0

    def test_increment_total_pages(self):
        """Test incrementing total pages counter."""
        increment_total_pages()
        increment_total_pages()
        increment_total_pages()

        stats = get_fallback_stats()
        assert stats["total_pages"] == 3

    def test_fallback_percentage_calculation(self):
        """Test fallback percentage calculation."""
        # Process 100 pages, use fallback on 5
        for _ in range(100):
            increment_total_pages()

        # Simulate 5 fallback uses
        mock_page = MagicMock()
        mock_page.number = 0
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"img"
        mock_page.get_pixmap.return_value = mock_pix

        for _ in range(5):
            extract_with_codex(mock_page, "key")

        stats = get_fallback_stats()
        assert stats["total_pages"] == 100
        assert stats["fallback_used"] == 5
        assert stats["fallback_percentage"] == 5.0

    def test_reset_statistics(self):
        """Test resetting statistics."""
        # Add some data
        increment_total_pages()
        increment_total_pages()

        mock_page = MagicMock()
        mock_page.number = 0
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"img"
        mock_page.get_pixmap.return_value = mock_pix

        extract_with_codex(mock_page, "key")

        # Reset
        reset_fallback_stats()

        stats = get_fallback_stats()
        assert stats["total_pages"] == 0
        assert stats["fallback_used"] == 0
        assert stats["codex_calls"] == 0
        assert stats["chrome_calls"] == 0

    def test_mixed_fallback_usage(self):
        """Test statistics with mixed Codex and Chrome usage."""
        # Process 50 pages
        for _ in range(50):
            increment_total_pages()

        # Use Codex 2 times
        mock_page = MagicMock()
        mock_page.number = 0
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"img"
        mock_page.get_pixmap.return_value = mock_pix

        extract_with_codex(mock_page, "key")
        extract_with_codex(mock_page, "key")

        # Use Chrome 3 times
        extract_with_chrome(b"img")
        extract_with_chrome(b"img")
        extract_with_chrome(b"img")

        stats = get_fallback_stats()
        assert stats["total_pages"] == 50
        assert stats["fallback_used"] == 5  # 2 Codex + 3 Chrome
        assert stats["codex_calls"] == 2
        assert stats["chrome_calls"] == 3
        assert stats["fallback_percentage"] == 10.0  # 5/50 * 100

    def test_zero_division_in_percentage(self):
        """Test percentage calculation with zero pages."""
        stats = get_fallback_stats()
        assert stats["fallback_percentage"] == 0.0  # Should not raise division by zero


if __name__ == "__main__":
    unittest.main()
