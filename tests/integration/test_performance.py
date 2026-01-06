"""
ABOUTME: Performance and benchmark integration tests
ABOUTME: Tests memory usage, processing speed, and scalability
"""

import unittest
import tempfile
import time
import tracemalloc
from pathlib import Path
import fitz  # PyMuPDF

from src.main import process_large_pdf


class TestPerformance(unittest.TestCase):
    """Test performance and memory efficiency."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_pdf(self, num_pages: int, complexity: str = "simple") -> Path:
        """
        Create a test PDF with specified characteristics.

        Args:
            num_pages: Number of pages
            complexity: "simple", "medium", or "complex"

        Returns:
            Path to created PDF
        """
        pdf_path = Path(self.temp_dir) / f"test_{num_pages}_{complexity}.pdf"
        doc = fitz.open()

        for i in range(num_pages):
            page = doc.new_page()

            if complexity == "simple":
                page.insert_text((72, 72), f"Page {i+1}: Simple text")

            elif complexity == "medium":
                # Add multiple text blocks
                for j in range(10):
                    page.insert_text((72, 72 + j*20), f"Page {i+1} Line {j+1}")

            elif complexity == "complex":
                # Add many text blocks with different fonts
                for j in range(20):
                    page.insert_text(
                        (72, 72 + j*15),
                        f"Page {i+1} Complex Line {j+1}",
                        fontsize=10 + (j % 4)
                    )

        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def measure_memory(self, func, *args, **kwargs):
        """
        Measure memory usage of function execution.

        Args:
            func: Function to measure
            *args, **kwargs: Function arguments

        Returns:
            (result, peak_memory_mb) tuple
        """
        tracemalloc.start()

        result = func(*args, **kwargs)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)  # Convert to MB
        return result, peak_mb

    def measure_time(self, func, *args, **kwargs):
        """
        Measure execution time of function.

        Args:
            func: Function to measure
            *args, **kwargs: Function arguments

        Returns:
            (result, elapsed_seconds) tuple
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        return result, elapsed

    def test_small_pdf_performance(self):
        """Test performance with small PDF (10 pages)."""
        pdf_path = self.create_test_pdf(10, "simple")

        # Measure time
        result, elapsed = self.measure_time(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text"
        )

        # Should complete quickly (< 5 seconds)
        self.assertLess(elapsed, 5.0)

        # Should extract text successfully
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_medium_pdf_performance(self):
        """Test performance with medium PDF (50 pages)."""
        pdf_path = self.create_test_pdf(50, "medium")

        # Measure time
        result, elapsed = self.measure_time(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text"
        )

        # Should complete in reasonable time (< 30 seconds)
        self.assertLess(elapsed, 30.0)

        # Should extract all pages
        self.assertIn("Page 1", result)
        self.assertIn("Page 50", result)

    def test_large_pdf_performance(self):
        """Test performance with large PDF (100 pages)."""
        pdf_path = self.create_test_pdf(100, "simple")

        # Measure time
        result, elapsed = self.measure_time(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text"
        )

        # Should complete in reasonable time (< 60 seconds)
        self.assertLess(elapsed, 60.0)

        # Should extract all pages
        self.assertIn("Page 1", result)
        self.assertIn("Page 100", result)

    def test_generator_memory_efficiency(self):
        """Test that generator format uses minimal memory."""
        pdf_path = self.create_test_pdf(50, "medium")

        # Measure memory with generator format
        def process_generator():
            result = process_large_pdf(
                pdf_path=pdf_path,
                output_format="generator"
            )
            # Consume generator
            pages = list(result)
            return pages

        pages, peak_memory = self.measure_memory(process_generator)

        # Generator should use reasonable memory (< 100 MB for 50 pages)
        self.assertLess(peak_memory, 100.0)

        # Should process all pages
        self.assertEqual(len(pages), 50)

    def test_list_format_memory_usage(self):
        """Test memory usage with list format."""
        pdf_path = self.create_test_pdf(50, "medium")

        # Measure memory with list format
        pages, peak_memory = self.measure_memory(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="list"
        )

        # List format will use more memory but should still be reasonable
        # (< 200 MB for 50 pages)
        self.assertLess(peak_memory, 200.0)

        # Should process all pages
        self.assertEqual(len(pages), 50)

    def test_text_format_memory_usage(self):
        """Test memory usage with text format."""
        pdf_path = self.create_test_pdf(50, "medium")

        # Measure memory with text format
        text, peak_memory = self.measure_memory(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text"
        )

        # Text format should be memory-efficient
        self.assertLess(peak_memory, 150.0)

        # Should extract text
        self.assertGreater(len(text), 0)

    def test_chunking_performance(self):
        """Test that chunking improves performance for large PDFs."""
        pdf_path = self.create_test_pdf(100, "simple")

        # Test with chunking
        result_chunked, time_chunked = self.measure_time(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text",
            chunk_size=10
        )

        # Test without auto-strategy (single chunk)
        result_single, time_single = self.measure_time(
            process_large_pdf,
            pdf_path=pdf_path,
            output_format="text",
            chunk_size=100,
            auto_strategy=False
        )

        # Both should produce same result
        self.assertEqual(len(result_chunked), len(result_single))

        # Chunking should not be significantly slower
        # (Allow up to 2x slower, accounting for overhead)
        self.assertLess(time_chunked, time_single * 2.0)

    def test_scalability(self):
        """Test that performance scales linearly with page count."""
        # Create PDFs of different sizes
        sizes = [10, 20, 40]
        times = []

        for size in sizes:
            pdf_path = self.create_test_pdf(size, "simple")

            result, elapsed = self.measure_time(
                process_large_pdf,
                pdf_path=pdf_path,
                output_format="text"
            )

            times.append(elapsed)

        # Time should roughly scale linearly
        # (20 pages should not take more than 3x time of 10 pages)
        self.assertLess(times[1], times[0] * 3.0)
        self.assertLess(times[2], times[1] * 3.0)


class TestResourceLimits(unittest.TestCase):
    """Test behavior under resource constraints."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_large_pdf(self, num_pages: int) -> Path:
        """Create a large test PDF."""
        pdf_path = Path(self.temp_dir) / f"large_{num_pages}.pdf"
        doc = fitz.open()

        for i in range(num_pages):
            page = doc.new_page()
            # Add substantial text to each page
            for j in range(50):
                page.insert_text((72, 72 + j*10), f"Page {i+1} Line {j+1}: Test content")

        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_very_large_pdf(self):
        """Test handling of very large PDF (200+ pages)."""
        pdf_path = self.create_large_pdf(200)

        # Process with generator (memory-efficient)
        result = process_large_pdf(
            pdf_path=pdf_path,
            output_format="generator"
        )

        # Consume generator page by page
        page_count = 0
        for page in result:
            page_count += 1
            if page_count % 50 == 0:
                # Checkpoint every 50 pages
                self.assertIsNotNone(page.text)

        # Should process all pages
        self.assertEqual(page_count, 200)

    def test_memory_constrained_processing(self):
        """Test that chunking helps with memory constraints."""
        pdf_path = self.create_large_pdf(100)

        # Process with small chunks to limit memory
        pages = process_large_pdf(
            pdf_path=pdf_path,
            output_format="list",
            chunk_size=5
        )

        # Should successfully process all pages
        self.assertEqual(len(pages), 100)


if __name__ == "__main__":
    unittest.main()
