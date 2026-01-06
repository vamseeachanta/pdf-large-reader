"""
ABOUTME: CLI integration tests for pdf-large-reader
ABOUTME: Tests command-line interface with real PDF processing
"""

import unittest
import tempfile
import subprocess
import sys
from pathlib import Path
import fitz  # PyMuPDF


class TestCLIIntegration(unittest.TestCase):
    """Test CLI end-to-end functionality."""

    def setUp(self):
        """Create test PDFs for CLI testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = Path(self.temp_dir) / "test.pdf"
        self.output_path = Path(self.temp_dir) / "output.txt"

        # Create a simple test PDF
        doc = fitz.open()

        page1 = doc.new_page()
        page1.insert_text((72, 72), "CLI Test Page 1")

        page2 = doc.new_page()
        page2.insert_text((72, 72), "CLI Test Page 2")

        doc.save(self.test_pdf_path)
        doc.close()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_cli(self, *args):
        """
        Run CLI command and return result.

        Args:
            *args: Command-line arguments

        Returns:
            (returncode, stdout, stderr) tuple
        """
        cmd = [
            sys.executable,
            "-m", "src.cli",
            *args
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return result.returncode, result.stdout, result.stderr

    def test_basic_text_extraction(self):
        """Test basic text extraction via CLI."""
        returncode, stdout, stderr = self.run_cli(str(self.test_pdf_path))

        # Should succeed
        self.assertEqual(returncode, 0)

        # Should contain extracted text
        self.assertIn("CLI Test Page 1", stdout)
        self.assertIn("CLI Test Page 2", stdout)

    def test_output_to_file(self):
        """Test output to file via CLI."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--output", str(self.output_path)
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Output file should exist
        self.assertTrue(self.output_path.exists())

        # Read output file
        output_text = self.output_path.read_text()
        self.assertIn("CLI Test Page 1", output_text)

    def test_verbose_mode(self):
        """Test verbose logging mode."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--verbose"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_quiet_mode(self):
        """Test quiet mode (suppress output)."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--quiet"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Stdout should be empty (quiet mode)
        self.assertEqual(stdout.strip(), "")

    def test_extract_images_flag(self):
        """Test --extract-images flag."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--extract-images"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_extract_tables_flag(self):
        """Test --extract-tables flag."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--extract-tables"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_combined_extraction_flags(self):
        """Test combined extraction flags."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--extract-images",
            "--extract-tables"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_custom_chunk_size(self):
        """Test --chunk-size option."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--chunk-size", "1"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_no_auto_strategy(self):
        """Test --no-auto-strategy flag."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--no-auto-strategy"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

    def test_output_format_list(self):
        """Test --output-format list."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--output-format", "list"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Should contain page markers
        self.assertIn("=== Page 1 ===", stdout)
        self.assertIn("=== Page 2 ===", stdout)

    def test_output_format_generator(self):
        """Test --output-format generator."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--output-format", "generator"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Should contain page markers
        self.assertIn("=== Page 1 ===", stdout)

    def test_file_not_found_error(self):
        """Test error handling for missing file."""
        returncode, stdout, stderr = self.run_cli(
            "/nonexistent/file.pdf"
        )

        # Should fail with exit code 1
        self.assertEqual(returncode, 1)

    def test_invalid_output_format(self):
        """Test error handling for invalid output format."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--output-format", "invalid"
        )

        # Should fail (argparse validation)
        self.assertNotEqual(returncode, 0)

    def test_short_form_options(self):
        """Test short-form CLI options."""
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "-o", str(self.output_path),
            "-v"  # verbose
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Output file should exist
        self.assertTrue(self.output_path.exists())

    def test_help_option(self):
        """Test --help option."""
        returncode, stdout, stderr = self.run_cli("--help")

        # Help should exit with 0
        self.assertEqual(returncode, 0)

        # Should contain usage information
        self.assertIn("pdf-large-reader", stdout)
        self.assertIn("--extract-images", stdout)

    def test_version_option(self):
        """Test --version option."""
        returncode, stdout, stderr = self.run_cli("--version")

        # Version should exit with 0
        self.assertEqual(returncode, 0)

        # Should contain version number
        self.assertIn("1.3.0", stdout)


class TestCLIWorkflow(unittest.TestCase):
    """Test complete CLI workflows."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_pdf_path = Path(self.temp_dir) / "workflow_test.pdf"

        # Create a multi-page PDF with content
        doc = fitz.open()

        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), f"Workflow Test Page {i+1}")
            page.insert_text((72, 100), f"Content for page {i+1}")

        doc.save(self.test_pdf_path)
        doc.close()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def run_cli(self, *args):
        """Run CLI command."""
        cmd = [
            sys.executable,
            "-m", "src.cli",
            *args
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        return result.returncode, result.stdout, result.stderr

    def test_complete_extraction_workflow(self):
        """Test complete extraction workflow via CLI."""
        output_file = Path(self.temp_dir) / "complete_output.txt"

        # Run complete extraction
        returncode, stdout, stderr = self.run_cli(
            str(self.test_pdf_path),
            "--extract-images",
            "--extract-tables",
            "--output", str(output_file),
            "--verbose"
        )

        # Should succeed
        self.assertEqual(returncode, 0)

        # Output file should exist and contain all pages
        self.assertTrue(output_file.exists())
        output_text = output_file.read_text()

        # Verify all pages present
        for i in range(1, 6):
            self.assertIn(f"Page {i}", output_text)

    def test_batch_processing_workflow(self):
        """Test batch processing multiple files."""
        # Create multiple test PDFs
        pdf_files = []
        for i in range(3):
            pdf_path = Path(self.temp_dir) / f"batch_{i}.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), f"Batch file {i}")
            doc.save(pdf_path)
            doc.close()
            pdf_files.append(pdf_path)

        # Process each file
        for pdf_file in pdf_files:
            output_file = pdf_file.with_suffix('.txt')

            returncode, stdout, stderr = self.run_cli(
                str(pdf_file),
                "--output", str(output_file)
            )

            self.assertEqual(returncode, 0)
            self.assertTrue(output_file.exists())


if __name__ == "__main__":
    unittest.main()
