"""
ABOUTME: Unit tests for main module
ABOUTME: Tests high-level API integration and convenience functions
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from src.main import (
    process_large_pdf,
    extract_text_only,
    extract_pages_with_images,
    extract_pages_with_tables,
    extract_everything,
    _process_as_generator
)
from src.streaming import PDFPage
from src.assessment import PDFAnalysis


class TestProcessLargePDF(unittest.TestCase):
    """Test main API function."""

    def setUp(self):
        """Setup common test fixtures."""
        # Mock PDF analysis
        self.mock_analysis = PDFAnalysis(
            file_size=1024 * 1024,  # 1MB
            page_count=10,
            estimated_memory=512 * 1024,
            complexity_score=50.0,
            recommended_strategy="stream_pages",
            issues=[],
            metadata={}
        )

        # Mock processing strategy
        self.mock_strategy = MagicMock()
        self.mock_strategy.strategy_type = "stream_pages"
        self.mock_strategy.chunk_size = 1
        self.mock_strategy.estimated_time = 5.0

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main.select_strategy')
    @patch('src.main._process_as_generator')
    def test_process_generator_output(self, mock_gen, mock_strategy, mock_assess, mock_path):
        """Test process_large_pdf with generator output."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_strategy.return_value = self.mock_strategy

        # Mock generator
        mock_pages = [
            PDFPage(page_number=1, text="Page 1", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2", images=[], metadata={})
        ]
        mock_gen.return_value = iter(mock_pages)

        # Call function
        result = process_large_pdf("test.pdf", output_format="generator")

        # Verify result is generator
        assert hasattr(result, '__iter__')
        pages_list = list(result)
        assert len(pages_list) == 2
        assert pages_list[0].page_number == 1
        assert pages_list[1].page_number == 2

        # Verify calls
        mock_assess.assert_called_once()
        mock_strategy.assert_called_once_with(self.mock_analysis)

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main.select_strategy')
    @patch('src.main._process_as_generator')
    def test_process_list_output(self, mock_gen, mock_strategy, mock_assess, mock_path):
        """Test process_large_pdf with list output."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_strategy.return_value = self.mock_strategy

        # Mock generator
        mock_pages = [
            PDFPage(page_number=1, text="Page 1", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2", images=[], metadata={})
        ]
        mock_gen.return_value = iter(mock_pages)

        # Call function
        result = process_large_pdf("test.pdf", output_format="list")

        # Verify result is list
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0].page_number == 1
        assert result[1].page_number == 2

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main.select_strategy')
    @patch('src.main._process_as_generator')
    def test_process_text_output(self, mock_gen, mock_strategy, mock_assess, mock_path):
        """Test process_large_pdf with text output."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_strategy.return_value = self.mock_strategy

        # Mock generator
        mock_pages = [
            PDFPage(page_number=1, text="Page 1 text", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2 text", images=[], metadata={})
        ]
        mock_gen.return_value = iter(mock_pages)

        # Call function
        result = process_large_pdf("test.pdf", output_format="text")

        # Verify result is string
        assert isinstance(result, str)
        assert "Page 1 text" in result
        assert "Page 2 text" in result
        assert "\n\n" in result  # Pages joined with double newline

    @patch('src.main.Path')
    def test_file_not_found_error(self, mock_path):
        """Test that FileNotFoundError is raised for missing file."""
        # Setup mock
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        # Call function and expect error
        with self.assertRaises(FileNotFoundError) as context:
            process_large_pdf("missing.pdf")

        assert "PDF file not found" in str(context.exception)

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    def test_invalid_output_format_error(self, mock_assess, mock_path):
        """Test that ValueError is raised for invalid output format."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis

        # Call function with invalid format
        with self.assertRaises(ValueError) as context:
            process_large_pdf("test.pdf", output_format="invalid")

        assert "output_format must be one of" in str(context.exception)

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main.select_strategy')
    @patch('src.main._process_as_generator')
    def test_auto_strategy_enabled(self, mock_gen, mock_strategy, mock_assess, mock_path):
        """Test automatic strategy selection when auto_strategy=True."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_strategy.return_value = self.mock_strategy
        mock_gen.return_value = iter([])

        # Call with auto_strategy=True (default)
        process_large_pdf("test.pdf", auto_strategy=True)

        # Verify strategy selection was called
        mock_strategy.assert_called_once_with(self.mock_analysis)

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main._process_as_generator')
    def test_auto_strategy_disabled(self, mock_gen, mock_assess, mock_path):
        """Test manual strategy when auto_strategy=False."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_gen.return_value = iter([])

        # Call with auto_strategy=False
        with patch('src.main.select_strategy') as mock_strategy:
            process_large_pdf("test.pdf", auto_strategy=False, chunk_size=5)

            # Verify strategy selection was NOT called
            mock_strategy.assert_not_called()

    @patch('src.main.Path')
    @patch('src.main.assess_pdf')
    @patch('src.main.select_strategy')
    @patch('src.main._process_as_generator')
    def test_progress_callback(self, mock_gen, mock_strategy, mock_assess, mock_path):
        """Test that progress callback is passed to generator."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_assess.return_value = self.mock_analysis
        mock_strategy.return_value = self.mock_strategy
        mock_gen.return_value = iter([])

        # Create callback
        callback = MagicMock()

        # Call with callback
        process_large_pdf("test.pdf", progress_callback=callback)

        # Verify callback was passed to generator (7th positional argument, index 6)
        call_args = mock_gen.call_args
        assert call_args[0][6] == callback


class TestProcessAsGenerator(unittest.TestCase):
    """Test internal generator function."""

    def setUp(self):
        """Setup common test fixtures."""
        self.mock_analysis = PDFAnalysis(
            file_size=1024 * 1024,
            page_count=2,
            estimated_memory=512 * 1024,
            complexity_score=50.0,
            recommended_strategy="stream_pages",
            issues=[],
            metadata={}
        )

    @patch('src.main.fitz.open')
    @patch('src.main.stream_pdf_pages')
    @patch('src.main.should_use_fallback')
    def test_generator_basic_flow(self, mock_fallback_check, mock_stream, mock_fitz):
        """Test basic generator flow without fallback."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.page_count = 2
        mock_fitz.return_value = mock_doc

        # Mock pages from streaming
        mock_pages = [
            PDFPage(page_number=1, text="Page 1", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2", images=[], metadata={})
        ]
        mock_stream.return_value = iter(mock_pages)

        # Mock fallback check - no fallback needed
        mock_fallback_check.return_value = (False, "standard")

        # Call generator
        result = list(_process_as_generator(
            Path("test.pdf"),
            chunk_size=1,
            extract_images=False,
            extract_tables=False,
            fallback_api_key=None,
            fallback_model="gpt-4o",
            progress_callback=None,
            analysis=self.mock_analysis
        ))

        # Verify results
        assert len(result) == 2
        assert result[0].text == "Page 1"
        assert result[1].text == "Page 2"

        # Verify document was closed
        mock_doc.close.assert_called_once()

    @patch('src.main.fitz.open')
    @patch('src.main.stream_pdf_pages')
    @patch('src.main.should_use_fallback')
    @patch('src.main.extract_with_codex')
    def test_generator_with_fallback(self, mock_codex, mock_fallback_check, mock_stream, mock_fitz):
        """Test generator with fallback extraction."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_page.number = 0
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc

        # Mock pages from streaming
        mock_pages = [
            PDFPage(page_number=1, text="Original text", images=[], metadata={})
        ]
        mock_stream.return_value = iter(mock_pages)

        # Mock fallback check - fallback needed
        mock_fallback_check.return_value = (True, "scanned_pdf")

        # Mock codex extraction
        mock_codex.return_value = "Fallback extracted text"

        # Call generator with API key
        result = list(_process_as_generator(
            Path("test.pdf"),
            chunk_size=1,
            extract_images=False,
            extract_tables=False,
            fallback_api_key="sk-test-key",
            fallback_model="gpt-4o",
            progress_callback=None,
            analysis=self.mock_analysis
        ))

        # Verify fallback text was used
        assert len(result) == 1
        assert result[0].text == "Fallback extracted text"

        # Verify codex was called
        mock_codex.assert_called_once()

    @patch('src.main.fitz.open')
    @patch('src.main.stream_pdf_pages')
    @patch('src.main.should_use_fallback')
    @patch('src.main.extract_page_full')
    def test_generator_with_image_extraction(self, mock_extract_full, mock_fallback_check, mock_stream, mock_fitz):
        """Test generator with image extraction enabled."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc

        # Mock pages from streaming
        mock_pages = [
            PDFPage(page_number=1, text="Page text", images=[], metadata={})
        ]
        mock_stream.return_value = iter(mock_pages)

        # Mock fallback check - no fallback
        mock_fallback_check.return_value = (False, "standard")

        # Mock full extraction
        mock_extracted_page = PDFPage(
            page_number=1,
            text="Page text",
            images=[MagicMock()],  # Mock image
            metadata={}
        )
        mock_extract_full.return_value = mock_extracted_page

        # Call generator with extract_images=True
        result = list(_process_as_generator(
            Path("test.pdf"),
            chunk_size=1,
            extract_images=True,
            extract_tables=False,
            fallback_api_key=None,
            fallback_model="gpt-4o",
            progress_callback=None,
            analysis=self.mock_analysis
        ))

        # Verify full extraction was called
        mock_extract_full.assert_called_once_with(
            mock_page,
            extract_images_flag=True,
            extract_tables_flag=False
        )

        # Verify result has images
        assert len(result) == 1
        assert len(result[0].images) == 1

    @patch('src.main.fitz.open')
    @patch('src.main.stream_pdf_pages')
    @patch('src.main.should_use_fallback')
    @patch('src.main.extract_with_codex')
    def test_generator_fallback_failure_graceful(self, mock_codex, mock_fallback_check, mock_stream, mock_fitz):
        """Test that fallback failure is handled gracefully."""
        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.page_count = 1
        mock_page = MagicMock()
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc

        # Mock pages from streaming
        mock_pages = [
            PDFPage(page_number=1, text="Original text", images=[], metadata={})
        ]
        mock_stream.return_value = iter(mock_pages)

        # Mock fallback check - fallback needed
        mock_fallback_check.return_value = (True, "scanned_pdf")

        # Mock codex extraction failure
        mock_codex.side_effect = Exception("API error")

        # Call generator - should not raise exception
        result = list(_process_as_generator(
            Path("test.pdf"),
            chunk_size=1,
            extract_images=False,
            extract_tables=False,
            fallback_api_key="sk-test-key",
            fallback_model="gpt-4o",
            progress_callback=None,
            analysis=self.mock_analysis
        ))

        # Verify original text was kept after fallback failure
        assert len(result) == 1
        assert result[0].text == "Original text"


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience wrapper functions."""

    @patch('src.main.process_large_pdf')
    def test_extract_text_only(self, mock_process):
        """Test extract_text_only convenience function."""
        # Mock return value
        mock_process.return_value = "Extracted text content"

        # Call function
        result = extract_text_only("test.pdf")

        # Verify
        assert result == "Extracted text content"
        mock_process.assert_called_once_with("test.pdf", output_format="text")

    @patch('src.main.process_large_pdf')
    def test_extract_pages_with_images(self, mock_process):
        """Test extract_pages_with_images convenience function."""
        # Mock return value
        mock_pages = [
            PDFPage(page_number=1, text="Page 1", images=[MagicMock()], metadata={})
        ]
        mock_process.return_value = mock_pages

        # Call function
        callback = MagicMock()
        result = extract_pages_with_images("test.pdf", progress_callback=callback)

        # Verify
        assert result == mock_pages
        mock_process.assert_called_once_with(
            "test.pdf",
            output_format="list",
            extract_images=True,
            extract_tables=False,
            progress_callback=callback
        )

    @patch('src.main.process_large_pdf')
    def test_extract_pages_with_tables(self, mock_process):
        """Test extract_pages_with_tables convenience function."""
        # Mock return value
        mock_pages = [
            PDFPage(page_number=1, text="Page 1", images=[], metadata={"tables": [MagicMock()]})
        ]
        mock_process.return_value = mock_pages

        # Call function
        callback = MagicMock()
        result = extract_pages_with_tables("test.pdf", progress_callback=callback)

        # Verify
        assert result == mock_pages
        mock_process.assert_called_once_with(
            "test.pdf",
            output_format="list",
            extract_images=False,
            extract_tables=True,
            progress_callback=callback
        )

    @patch('src.main.process_large_pdf')
    def test_extract_everything(self, mock_process):
        """Test extract_everything convenience function."""
        # Mock return value
        mock_pages = [
            PDFPage(
                page_number=1,
                text="Page 1",
                images=[MagicMock()],
                metadata={"tables": [MagicMock()]}
            )
        ]
        mock_process.return_value = mock_pages

        # Call function
        callback = MagicMock()
        result = extract_everything(
            "test.pdf",
            fallback_api_key="sk-test-key",
            progress_callback=callback
        )

        # Verify
        assert result == mock_pages
        mock_process.assert_called_once_with(
            "test.pdf",
            output_format="list",
            extract_images=True,
            extract_tables=True,
            fallback_api_key="sk-test-key",
            progress_callback=callback
        )


if __name__ == "__main__":
    unittest.main()
