"""
ABOUTME: Unit tests for CLI module
ABOUTME: Tests command-line interface argument parsing and execution
"""

import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cli import (
    create_parser,
    format_output,
    main
)
from src.streaming import PDFPage


class TestCreateParser(unittest.TestCase):
    """Test argument parser creation and configuration."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == 'pdf-large-reader'

    def test_required_arguments(self):
        """Test that pdf_path is required."""
        parser = create_parser()

        # Should fail without pdf_path
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_default_values(self):
        """Test default argument values."""
        parser = create_parser()
        args = parser.parse_args(['test.pdf'])

        assert args.pdf_path == 'test.pdf'
        assert args.output_format == 'text'
        assert args.output is None
        assert args.extract_images is False
        assert args.extract_tables is False
        assert args.chunk_size is None
        assert args.no_auto_strategy is False
        assert args.fallback_api_key is None
        assert args.fallback_model == 'gpt-4o'
        assert args.verbose is False
        assert args.quiet is False

    def test_output_format_choices(self):
        """Test output format validation."""
        parser = create_parser()

        # Valid choices
        for fmt in ['generator', 'list', 'text']:
            args = parser.parse_args(['test.pdf', '--output-format', fmt])
            assert args.output_format == fmt

        # Invalid choice should fail
        with self.assertRaises(SystemExit):
            parser.parse_args(['test.pdf', '--output-format', 'invalid'])

    def test_extraction_flags(self):
        """Test extraction option flags."""
        parser = create_parser()

        args = parser.parse_args([
            'test.pdf',
            '--extract-images',
            '--extract-tables'
        ])

        assert args.extract_images is True
        assert args.extract_tables is True

    def test_fallback_options(self):
        """Test fallback configuration options."""
        parser = create_parser()

        args = parser.parse_args([
            'test.pdf',
            '--fallback-api-key', 'sk-test-key',
            '--fallback-model', 'gpt-4-turbo'
        ])

        assert args.fallback_api_key == 'sk-test-key'
        assert args.fallback_model == 'gpt-4-turbo'

    def test_chunk_size_option(self):
        """Test chunk size configuration."""
        parser = create_parser()

        args = parser.parse_args([
            'test.pdf',
            '--chunk-size', '10'
        ])

        assert args.chunk_size == 10

    def test_output_file_option(self):
        """Test output file specification."""
        parser = create_parser()

        args = parser.parse_args([
            'test.pdf',
            '--output', 'results.txt'
        ])

        assert args.output == 'results.txt'

        # Test short form
        args = parser.parse_args(['test.pdf', '-o', 'out.txt'])
        assert args.output == 'out.txt'

    def test_logging_options(self):
        """Test verbose and quiet flags."""
        parser = create_parser()

        # Verbose
        args = parser.parse_args(['test.pdf', '--verbose'])
        assert args.verbose is True

        # Verbose short form
        args = parser.parse_args(['test.pdf', '-v'])
        assert args.verbose is True

        # Quiet
        args = parser.parse_args(['test.pdf', '--quiet'])
        assert args.quiet is True

        # Quiet short form
        args = parser.parse_args(['test.pdf', '-q'])
        assert args.quiet is True


class TestFormatOutput(unittest.TestCase):
    """Test output formatting."""

    def test_format_text_output(self):
        """Test text output formatting."""
        result = "Extracted text content"

        output = format_output(result, 'text', False, False)

        assert output == "Extracted text content"

    def test_format_list_output_text_only(self):
        """Test list output with text only."""
        pages = [
            PDFPage(page_number=1, text="Page 1 text", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2 text", images=[], metadata={})
        ]

        output = format_output(pages, 'list', False, False)

        assert "=== Page 1 ===" in output
        assert "Page 1 text" in output
        assert "=== Page 2 ===" in output
        assert "Page 2 text" in output

    def test_format_list_output_with_images(self):
        """Test list output with image count."""
        pages = [
            PDFPage(
                page_number=1,
                text="Page 1 text",
                images=[MagicMock(), MagicMock()],
                metadata={}
            )
        ]

        output = format_output(pages, 'list', True, False)

        assert "Page 1 text" in output
        assert "[2 images extracted]" in output

    def test_format_list_output_with_tables(self):
        """Test list output with table count."""
        pages = [
            PDFPage(
                page_number=1,
                text="Page 1 text",
                images=[],
                metadata={"tables": [MagicMock(), MagicMock(), MagicMock()]}
            )
        ]

        output = format_output(pages, 'list', False, True)

        assert "Page 1 text" in output
        assert "[3 tables extracted]" in output

    def test_format_generator_output(self):
        """Test generator output formatting."""
        pages = [
            PDFPage(page_number=1, text="Page 1", images=[], metadata={}),
            PDFPage(page_number=2, text="Page 2", images=[], metadata={})
        ]

        output = format_output(iter(pages), 'generator', False, False)

        assert "=== Page 1 ===" in output
        assert "Page 1" in output
        assert "=== Page 2 ===" in output
        assert "Page 2" in output


class TestMain(unittest.TestCase):
    """Test main CLI entry point."""

    @patch('src.cli.Path')
    @patch('src.cli.process_large_pdf')
    def test_main_success_stdout(self, mock_process, mock_path):
        """Test successful execution with stdout output."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_process.return_value = "Extracted text"

        # Capture stdout
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = main(['test.pdf'])

        # Verify
        assert exit_code == 0
        assert "Extracted text" in mock_stdout.getvalue()
        mock_process.assert_called_once()

    @patch('src.cli.Path')
    @patch('src.cli.process_large_pdf')
    def test_main_success_file_output(self, mock_process, mock_path):
        """Test successful execution with file output."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.parent.mkdir = MagicMock()
        mock_path_instance.write_text = MagicMock()
        mock_path.return_value = mock_path_instance

        mock_process.return_value = "Extracted text"

        # Execute
        exit_code = main(['test.pdf', '--output', 'results.txt'])

        # Verify
        assert exit_code == 0
        mock_path_instance.write_text.assert_called_once_with(
            "Extracted text",
            encoding='utf-8'
        )

    @patch('src.cli.Path')
    def test_main_file_not_found(self, mock_path):
        """Test error handling for missing file."""
        # Setup mock
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance

        # Execute
        exit_code = main(['missing.pdf'])

        # Verify
        assert exit_code == 1

    @patch('src.cli.Path')
    @patch('src.cli.process_large_pdf')
    def test_main_processing_error(self, mock_process, mock_path):
        """Test error handling for processing failure."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_process.side_effect = RuntimeError("Processing failed")

        # Execute
        exit_code = main(['test.pdf'])

        # Verify
        assert exit_code == 1

    @patch('src.cli.Path')
    @patch('src.cli.process_large_pdf')
    def test_main_with_all_options(self, mock_process, mock_path):
        """Test execution with all CLI options."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_process.return_value = "Extracted text"

        # Execute with all options
        exit_code = main([
            'test.pdf',
            '--output-format', 'text',
            '--extract-images',
            '--extract-tables',
            '--chunk-size', '5',
            '--no-auto-strategy',
            '--fallback-api-key', 'sk-test',
            '--fallback-model', 'gpt-4-turbo',
            '--output', 'results.txt',
            '--verbose'
        ])

        # Verify
        assert exit_code == 0

        # Verify all parameters passed to process_large_pdf
        call_args = mock_process.call_args
        assert call_args[1]['extract_images'] is True
        assert call_args[1]['extract_tables'] is True
        assert call_args[1]['chunk_size'] == 5
        assert call_args[1]['fallback_api_key'] == 'sk-test'
        assert call_args[1]['fallback_model'] == 'gpt-4-turbo'
        assert call_args[1]['auto_strategy'] is False

    @patch('src.cli.Path')
    @patch('src.cli.process_large_pdf')
    def test_main_quiet_mode(self, mock_process, mock_path):
        """Test that quiet mode suppresses stdout."""
        # Setup mocks
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        mock_process.return_value = "Extracted text"

        # Capture stdout
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            exit_code = main(['test.pdf', '--quiet'])

        # Verify no output to stdout
        assert exit_code == 0
        assert mock_stdout.getvalue() == ""


if __name__ == "__main__":
    unittest.main()
