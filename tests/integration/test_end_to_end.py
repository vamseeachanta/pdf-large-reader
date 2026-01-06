"""
ABOUTME: End-to-end integration tests for pdf-large-reader
ABOUTME: Tests complete workflow from PDF loading through extraction and output
"""

import unittest
import tempfile
from pathlib import Path
import fitz  # PyMuPDF

from src.main import (
    process_large_pdf,
    extract_text_only,
    extract_pages_with_images,
    extract_pages_with_tables,
    extract_everything
)
from src.streaming import PDFPage


class TestEndToEndWorkflow(unittest.TestCase):
    """Test complete end-to-end workflows."""

    def setUp(self):
        """Create a simple test PDF for integration testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = Path(self.temp_dir) / "test.pdf"

        # Create a simple multi-page PDF
        doc = fitz.open()

        # Page 1: Simple text
        page1 = doc.new_page()
        page1.insert_text((72, 72), "Page 1: Simple text content")

        # Page 2: More text
        page2 = doc.new_page()
        page2.insert_text((72, 72), "Page 2: Additional content")
        page2.insert_text((72, 100), "Multiple lines of text")

        # Page 3: Text with formatting
        page3 = doc.new_page()
        page3.insert_text((72, 72), "Page 3: Formatted content", fontsize=14)
        page3.insert_text((72, 100), "This is a test document", fontsize=12)

        doc.save(self.test_pdf_path)
        doc.close()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_text_only_extraction(self):
        """Test simple text-only extraction workflow."""
        # Use convenience function
        text = extract_text_only(self.test_pdf_path)

        # Verify text was extracted
        self.assertIsInstance(text, str)
        self.assertIn("Page 1", text)
        self.assertIn("Page 2", text)
        self.assertIn("Page 3", text)
        self.assertGreater(len(text), 0)

    def test_generator_output_format(self):
        """Test generator output format end-to-end."""
        # Process with generator format
        result = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="generator"
        )

        # Should be a generator
        pages = list(result)

        # Verify we got all pages
        self.assertEqual(len(pages), 3)

        # Verify each page structure
        for i, page in enumerate(pages, 1):
            self.assertIsInstance(page, PDFPage)
            self.assertEqual(page.page_number, i)
            self.assertIsInstance(page.text, str)
            self.assertIsInstance(page.images, list)
            self.assertIsInstance(page.metadata, dict)

    def test_list_output_format(self):
        """Test list output format end-to-end."""
        # Process with list format
        pages = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="list"
        )

        # Should be a list
        self.assertIsInstance(pages, list)
        self.assertEqual(len(pages), 3)

        # Verify page content
        self.assertIn("Page 1", pages[0].text)
        self.assertIn("Page 2", pages[1].text)
        self.assertIn("Page 3", pages[2].text)

    def test_text_output_format(self):
        """Test text output format end-to-end."""
        # Process with text format
        text = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="text"
        )

        # Should be a single string
        self.assertIsInstance(text, str)

        # Should contain all pages
        self.assertIn("Page 1", text)
        self.assertIn("Page 2", text)
        self.assertIn("Page 3", text)

    def test_auto_strategy_selection(self):
        """Test that auto strategy selection works."""
        # Process with auto strategy
        result = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="text",
            auto_strategy=True
        )

        # Should complete successfully
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_manual_chunk_size(self):
        """Test manual chunk size specification."""
        # Process with specific chunk size
        pages = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="list",
            chunk_size=1,
            auto_strategy=False
        )

        # Should process all pages
        self.assertEqual(len(pages), 3)

    def test_extract_pages_with_images_convenience(self):
        """Test extract_pages_with_images convenience function."""
        # Use convenience function
        pages = extract_pages_with_images(self.test_pdf_path)

        # Should return list of pages
        self.assertIsInstance(pages, list)
        self.assertEqual(len(pages), 3)

        # Verify each page has images list (even if empty)
        for page in pages:
            self.assertIsInstance(page.images, list)

    def test_extract_pages_with_tables_convenience(self):
        """Test extract_pages_with_tables convenience function."""
        # Use convenience function
        pages = extract_pages_with_tables(self.test_pdf_path)

        # Should return list of pages
        self.assertIsInstance(pages, list)
        self.assertEqual(len(pages), 3)

        # Verify metadata exists
        for page in pages:
            self.assertIsInstance(page.metadata, dict)

    def test_extract_everything_convenience(self):
        """Test extract_everything convenience function."""
        # Use convenience function
        pages = extract_everything(self.test_pdf_path)

        # Should return list of pages
        self.assertIsInstance(pages, list)
        self.assertEqual(len(pages), 3)

        # Verify full page structure
        for page in pages:
            self.assertIsInstance(page, PDFPage)
            self.assertIsInstance(page.text, str)
            self.assertIsInstance(page.images, list)
            self.assertIsInstance(page.metadata, dict)

    def test_combined_extraction_options(self):
        """Test processing with both images and tables extraction."""
        # Process with all extraction options
        pages = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="list",
            extract_images=True,
            extract_tables=True
        )

        # Should process successfully
        self.assertEqual(len(pages), 3)

        # Each page should have extraction structures
        for page in pages:
            self.assertIsInstance(page.images, list)
            self.assertIsInstance(page.metadata, dict)

    def test_progress_callback_integration(self):
        """Test progress callback integration."""
        progress_calls = []

        def progress_callback(current: int, total: int):
            progress_calls.append((current, total))

        # Process with progress callback
        text = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="text",
            progress_callback=progress_callback
        )

        # Should have called progress callback
        self.assertGreater(len(progress_calls), 0)

        # Should have processed all pages
        self.assertIn("Page 1", text)

    def test_invalid_file_path(self):
        """Test error handling for invalid file path."""
        with self.assertRaises(FileNotFoundError):
            process_large_pdf(
                pdf_path="/nonexistent/file.pdf",
                output_format="text"
            )

    def test_invalid_output_format(self):
        """Test error handling for invalid output format."""
        with self.assertRaises(ValueError):
            process_large_pdf(
                pdf_path=self.test_pdf_path,
                output_format="invalid_format"
            )


class TestMemoryEfficiency(unittest.TestCase):
    """Test memory-efficient processing."""

    def setUp(self):
        """Create a larger test PDF."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = Path(self.temp_dir) / "large_test.pdf"

        # Create a PDF with many pages
        doc = fitz.open()

        for i in range(50):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i+1}: Test content with multiple lines")
            page.insert_text((72, 100), "Additional text to increase page complexity")
            page.insert_text((72, 128), "More content for testing memory efficiency")

        doc.save(self.test_pdf_path)
        doc.close()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generator_memory_efficiency(self):
        """Test that generator format is memory-efficient."""
        # Process with generator (should not load all pages at once)
        result = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="generator"
        )

        # Consume generator one page at a time
        page_count = 0
        for page in result:
            self.assertIsInstance(page, PDFPage)
            page_count += 1

        # Should have processed all 50 pages
        self.assertEqual(page_count, 50)

    def test_chunking_strategy(self):
        """Test that chunking strategy works for large files."""
        # Process with explicit chunking
        pages = process_large_pdf(
            pdf_path=self.test_pdf_path,
            output_format="list",
            chunk_size=10,
            auto_strategy=False
        )

        # Should process all pages successfully
        self.assertEqual(len(pages), 50)

        # Verify sequential page numbering
        for i, page in enumerate(pages, 1):
            self.assertEqual(page.page_number, i)


class TestRobustness(unittest.TestCase):
    """Test robustness and error recovery."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_pdf(self):
        """Test handling of PDF with no text content."""
        # Create a PDF with one empty page (PyMuPDF requires at least one page)
        empty_pdf_path = Path(self.temp_dir) / "empty.pdf"
        doc = fitz.open()
        doc.new_page()  # Add empty page with no text
        doc.save(empty_pdf_path)
        doc.close()

        # Should return empty string for page with no text
        text = extract_text_only(empty_pdf_path)
        self.assertEqual(text, "")

    def test_single_page_pdf(self):
        """Test handling of single-page PDF."""
        # Create a single-page PDF
        single_page_path = Path(self.temp_dir) / "single.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Single page content")
        doc.save(single_page_path)
        doc.close()

        # Process single-page PDF
        pages = process_large_pdf(
            pdf_path=single_page_path,
            output_format="list"
        )

        self.assertEqual(len(pages), 1)
        self.assertIn("Single page", pages[0].text)


if __name__ == "__main__":
    unittest.main()
