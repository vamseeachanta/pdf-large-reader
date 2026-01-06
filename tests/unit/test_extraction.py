"""
ABOUTME: Unit tests for extraction module
ABOUTME: Tests text, image, and table extraction functions
"""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
from PIL import Image

from src.extraction import (
    extract_images,
    extract_page_full,
    extract_tables,
    extract_text,
)
from src.streaming import PDFPage


class TestExtractText(unittest.TestCase):
    """Test text extraction function."""

    def test_extract_text_with_layout_preservation(self):
        """Test text extraction with layout preservation."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Text with    preserved    layout"

        # Extract text with layout
        result = extract_text(mock_page, preserve_layout=True)

        # Verify
        assert result == "Text with    preserved    layout"
        mock_page.get_text.assert_called_once_with("text")

    def test_extract_text_without_layout_preservation(self):
        """Test text extraction without layout preservation."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Plain text without layout"

        # Extract text without layout
        result = extract_text(mock_page, preserve_layout=False)

        # Verify
        assert result == "Plain text without layout"
        mock_page.get_text.assert_called_once_with()

    def test_extract_text_empty_page(self):
        """Test text extraction from empty page."""
        # Create mock page with no text
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""

        # Extract text
        result = extract_text(mock_page, preserve_layout=True)

        # Verify
        assert result == ""

    def test_extract_text_multiline(self):
        """Test text extraction with multiple lines."""
        # Create mock page with multiline text
        mock_page = MagicMock()
        multiline_text = "Line 1\nLine 2\nLine 3"
        mock_page.get_text.return_value = multiline_text

        # Extract text
        result = extract_text(mock_page, preserve_layout=True)

        # Verify
        assert result == multiline_text
        assert result.count("\n") == 2


class TestExtractImages(unittest.TestCase):
    """Test image extraction function."""

    def test_extract_images_single_image(self):
        """Test extraction of single image."""
        # Create mock page with one image
        mock_page = MagicMock()

        # Create fake image data
        fake_image = Image.new("RGB", (100, 100), color="red")
        img_bytes = io.BytesIO()
        fake_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Setup mock
        mock_page.get_images.return_value = [(123, 0, 0, 0, 0, 0, 0)]
        mock_page.parent.extract_image.return_value = {"image": img_bytes.getvalue()}

        # Extract images
        images = extract_images(mock_page)

        # Verify
        assert len(images) == 1
        assert isinstance(images[0], Image.Image)
        assert images[0].size == (100, 100)

    def test_extract_images_multiple_images(self):
        """Test extraction of multiple images."""
        # Create mock page with multiple images
        mock_page = MagicMock()

        # Create fake image data
        fake_image1 = Image.new("RGB", (50, 50), color="blue")
        fake_image2 = Image.new("RGB", (75, 75), color="green")

        img_bytes1 = io.BytesIO()
        fake_image1.save(img_bytes1, format="PNG")
        img_bytes1.seek(0)

        img_bytes2 = io.BytesIO()
        fake_image2.save(img_bytes2, format="PNG")
        img_bytes2.seek(0)

        # Setup mock
        mock_page.get_images.return_value = [
            (123, 0, 0, 0, 0, 0, 0),
            (456, 0, 0, 0, 0, 0, 0),
        ]
        mock_page.parent.extract_image.side_effect = [
            {"image": img_bytes1.getvalue()},
            {"image": img_bytes2.getvalue()},
        ]

        # Extract images
        images = extract_images(mock_page)

        # Verify
        assert len(images) == 2
        assert images[0].size == (50, 50)
        assert images[1].size == (75, 75)

    def test_extract_images_no_images(self):
        """Test extraction when page has no images."""
        # Create mock page with no images
        mock_page = MagicMock()
        mock_page.get_images.return_value = []

        # Extract images
        images = extract_images(mock_page)

        # Verify
        assert len(images) == 0
        assert images == []

    def test_extract_images_error_handling(self):
        """Test image extraction error handling."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.get_images.return_value = [
            (123, 0, 0, 0, 0, 0, 0),
            (456, 0, 0, 0, 0, 0, 0),
        ]

        # First image succeeds, second fails
        fake_image = Image.new("RGB", (50, 50), color="blue")
        img_bytes = io.BytesIO()
        fake_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        mock_page.parent.extract_image.side_effect = [
            {"image": img_bytes.getvalue()},
            Exception("Failed to extract image"),
        ]

        # Extract images
        images = extract_images(mock_page)

        # Verify - should get first image, skip second
        assert len(images) == 1
        assert images[0].size == (50, 50)


class TestExtractTables(unittest.TestCase):
    """Test table extraction function."""

    def test_extract_tables_with_table_structure(self):
        """Test table extraction with table-like structure."""
        # Create mock page with table-like text blocks
        mock_page = MagicMock()

        # Create mock text blocks arranged in a table
        # Header row
        header_blocks = [
            {
                "type": 0,
                "bbox": [100, 100, 200, 120],
                "lines": [{"spans": [{"text": "Column1"}]}],
            },
            {
                "type": 0,
                "bbox": [220, 100, 320, 120],
                "lines": [{"spans": [{"text": "Column2"}]}],
            },
        ]

        # Data row 1
        data_row1 = [
            {
                "type": 0,
                "bbox": [100, 130, 200, 150],
                "lines": [{"spans": [{"text": "Value1"}]}],
            },
            {
                "type": 0,
                "bbox": [220, 130, 320, 150],
                "lines": [{"spans": [{"text": "Value2"}]}],
            },
        ]

        # Data row 2
        data_row2 = [
            {
                "type": 0,
                "bbox": [100, 160, 200, 180],
                "lines": [{"spans": [{"text": "Value3"}]}],
            },
            {
                "type": 0,
                "bbox": [220, 160, 320, 180],
                "lines": [{"spans": [{"text": "Value4"}]}],
            },
        ]

        all_blocks = header_blocks + data_row1 + data_row2

        mock_page.get_text.return_value = {"blocks": all_blocks}

        # Extract tables
        tables = extract_tables(mock_page)

        # Verify
        assert len(tables) == 1
        assert isinstance(tables[0], pd.DataFrame)
        assert tables[0].shape == (2, 2)  # 2 rows, 2 columns
        assert list(tables[0].columns) == ["Column1", "Column2"]

    def test_extract_tables_no_tables(self):
        """Test table extraction with no table structure."""
        # Create mock page with too few blocks for a table
        mock_page = MagicMock()
        mock_page.get_text.return_value = {"blocks": []}

        # Extract tables
        tables = extract_tables(mock_page)

        # Verify
        assert len(tables) == 0

    def test_extract_tables_insufficient_blocks(self):
        """Test table extraction with insufficient blocks."""
        # Create mock page with only 1-2 blocks
        mock_page = MagicMock()
        blocks = [
            {
                "type": 0,
                "bbox": [100, 100, 200, 120],
                "lines": [{"spans": [{"text": "Text"}]}],
            }
        ]
        mock_page.get_text.return_value = {"blocks": blocks}

        # Extract tables
        tables = extract_tables(mock_page)

        # Verify
        assert len(tables) == 0

    def test_extract_tables_single_column(self):
        """Test table extraction with single column structure."""
        # Create mock page with blocks in single column
        mock_page = MagicMock()
        blocks = [
            {
                "type": 0,
                "bbox": [100, 100, 200, 120],
                "lines": [{"spans": [{"text": "Row1"}]}],
            },
            {
                "type": 0,
                "bbox": [100, 130, 200, 150],
                "lines": [{"spans": [{"text": "Row2"}]}],
            },
            {
                "type": 0,
                "bbox": [100, 160, 200, 180],
                "lines": [{"spans": [{"text": "Row3"}]}],
            },
        ]
        mock_page.get_text.return_value = {"blocks": blocks}

        # Extract tables - should not detect as table (only 1 column)
        tables = extract_tables(mock_page)

        # Verify
        assert len(tables) == 0


class TestExtractPageFull(unittest.TestCase):
    """Test full page extraction function."""

    def test_extract_page_full_text_only(self):
        """Test full extraction with text only."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "Page text content"
        mock_page.get_images.return_value = []
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_page.rotation = 0
        mock_page.mediabox = (0, 0, 612, 792)

        # Extract page (no images, no tables)
        pdf_page = extract_page_full(
            mock_page, extract_images_flag=False, extract_tables_flag=False
        )

        # Verify
        assert isinstance(pdf_page, PDFPage)
        assert pdf_page.page_number == 1
        assert pdf_page.text == "Page text content"
        assert pdf_page.images == []
        assert "tables" not in pdf_page.metadata

    def test_extract_page_full_with_images(self):
        """Test full extraction with images."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "Page with images"
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_page.rotation = 0
        mock_page.mediabox = (0, 0, 612, 792)

        # Create fake image
        fake_image = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        fake_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        mock_page.get_images.return_value = [(123, 0, 0, 0, 0, 0, 0)]
        mock_page.parent.extract_image.return_value = {"image": img_bytes.getvalue()}

        # Extract page with images
        pdf_page = extract_page_full(
            mock_page, extract_images_flag=True, extract_tables_flag=False
        )

        # Verify
        assert pdf_page.page_number == 1
        assert len(pdf_page.images) == 1
        assert pdf_page.images[0].size == (100, 100)

    def test_extract_page_full_with_tables(self):
        """Test full extraction with tables."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 2
        mock_page.get_images.return_value = []
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_page.rotation = 0
        mock_page.mediabox = (0, 0, 612, 792)

        # Setup for text extraction
        text_return = "Page with table"

        def get_text_side_effect(mode=None):
            if mode == "text":
                return text_return
            elif mode == "dict":
                # Return table-like structure
                return {
                    "blocks": [
                        {
                            "type": 0,
                            "bbox": [100, 100, 200, 120],
                            "lines": [{"spans": [{"text": "Header1"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [220, 100, 320, 120],
                            "lines": [{"spans": [{"text": "Header2"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [100, 130, 200, 150],
                            "lines": [{"spans": [{"text": "Data1"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [220, 130, 320, 150],
                            "lines": [{"spans": [{"text": "Data2"}]}],
                        },
                    ]
                }
            else:
                return text_return

        mock_page.get_text.side_effect = get_text_side_effect

        # Extract page with tables
        pdf_page = extract_page_full(
            mock_page, extract_images_flag=False, extract_tables_flag=True
        )

        # Verify
        assert pdf_page.page_number == 3  # 0-indexed, so page 2 -> page 3
        assert "tables" in pdf_page.metadata
        assert len(pdf_page.metadata["tables"]) == 1

    def test_extract_page_full_with_all_features(self):
        """Test full extraction with text, images, and tables."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 1
        mock_page.rect.width = 612
        mock_page.rect.height = 792
        mock_page.rotation = 0
        mock_page.mediabox = (0, 0, 612, 792)

        # Setup for text extraction
        text_return = "Complete page content"

        def get_text_side_effect(mode=None):
            if mode == "text":
                return text_return
            elif mode == "dict":
                return {
                    "blocks": [
                        {
                            "type": 0,
                            "bbox": [100, 100, 200, 120],
                            "lines": [{"spans": [{"text": "Col1"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [220, 100, 320, 120],
                            "lines": [{"spans": [{"text": "Col2"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [100, 130, 200, 150],
                            "lines": [{"spans": [{"text": "Val1"}]}],
                        },
                        {
                            "type": 0,
                            "bbox": [220, 130, 320, 150],
                            "lines": [{"spans": [{"text": "Val2"}]}],
                        },
                    ]
                }
            else:
                return text_return

        mock_page.get_text.side_effect = get_text_side_effect

        # Setup for image extraction
        fake_image = Image.new("RGB", (80, 80), color="green")
        img_bytes = io.BytesIO()
        fake_image.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        mock_page.get_images.return_value = [(789, 0, 0, 0, 0, 0, 0)]
        mock_page.parent.extract_image.return_value = {"image": img_bytes.getvalue()}

        # Extract page with all features
        pdf_page = extract_page_full(
            mock_page, extract_images_flag=True, extract_tables_flag=True
        )

        # Verify all features
        assert pdf_page.page_number == 2
        assert pdf_page.text == "Complete page content"
        assert len(pdf_page.images) == 1
        assert pdf_page.images[0].size == (80, 80)
        assert "tables" in pdf_page.metadata
        assert len(pdf_page.metadata["tables"]) == 1

    def test_extract_page_full_metadata(self):
        """Test that metadata is correctly populated."""
        # Create mock page
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = "Test page"
        mock_page.get_images.return_value = []
        mock_page.rect.width = 595.276  # A4 width
        mock_page.rect.height = 841.890  # A4 height
        mock_page.rotation = 90
        mock_page.mediabox = (0, 0, 595.276, 841.890)

        # Extract page
        pdf_page = extract_page_full(mock_page)

        # Verify metadata
        assert pdf_page.metadata["width"] == 595.276
        assert pdf_page.metadata["height"] == 841.890
        assert pdf_page.metadata["rotation"] == 90
        assert pdf_page.metadata["mediabox"] == (0, 0, 595.276, 841.890)


if __name__ == "__main__":
    unittest.main()
