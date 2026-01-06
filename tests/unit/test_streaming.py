"""
ABOUTME: Unit tests for streaming module
ABOUTME: Tests stream_pdf_pages, chunk_pdf, select_strategy functions
"""

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from PIL import Image

from src.streaming import (
    PDFPage,
    ProcessingStrategy,
    stream_pdf_pages,
    chunk_pdf,
    select_strategy,
)
from src.assessment import PDFAnalysis


class TestPDFPage(unittest.TestCase):
    """Test PDFPage dataclass."""

    def test_pdf_page_creation(self):
        """Test creating PDFPage with all fields."""
        page = PDFPage(
            page_number=1,
            text="Sample text",
            images=[],
            metadata={"width": 612, "height": 792},
            layout=None,
        )

        assert page.page_number == 1
        assert page.text == "Sample text"
        assert page.images == []
        assert page.metadata == {"width": 612, "height": 792}
        assert page.layout is None

    def test_pdf_page_with_images(self):
        """Test PDFPage with PIL images."""
        # Create sample PIL image
        img = Image.new("RGB", (100, 100), color="red")

        page = PDFPage(
            page_number=2,
            text="Text with image",
            images=[img],
            metadata={"width": 612, "height": 792},
        )

        assert len(page.images) == 1
        assert isinstance(page.images[0], Image.Image)
        assert page.images[0].size == (100, 100)

    def test_pdf_page_default_layout(self):
        """Test PDFPage with default layout (None)."""
        page = PDFPage(
            page_number=3,
            text="Default layout",
            images=[],
            metadata={},
        )

        assert page.layout is None


class TestProcessingStrategy(unittest.TestCase):
    """Test ProcessingStrategy dataclass."""

    def test_processing_strategy_creation(self):
        """Test creating ProcessingStrategy."""
        strategy = ProcessingStrategy(
            strategy_type="stream_pages",
            chunk_size=1,
            memory_limit=10485760,
            estimated_time=50.0,
        )

        assert strategy.strategy_type == "stream_pages"
        assert strategy.chunk_size == 1
        assert strategy.memory_limit == 10485760
        assert strategy.estimated_time == 50.0

    def test_full_load_strategy(self):
        """Test full_load strategy parameters."""
        strategy = ProcessingStrategy(
            strategy_type="full_load",
            chunk_size=100,
            memory_limit=20971520,
            estimated_time=10.0,
        )

        assert strategy.strategy_type == "full_load"
        assert strategy.chunk_size == 100

    def test_chunk_batch_strategy(self):
        """Test chunk_batch strategy parameters."""
        strategy = ProcessingStrategy(
            strategy_type="chunk_batch",
            chunk_size=10,
            memory_limit=52428800,
            estimated_time=30.0,
        )

        assert strategy.strategy_type == "chunk_batch"
        assert strategy.chunk_size == 10


class TestStreamPDFPages(unittest.TestCase):
    """Test stream_pdf_pages function."""

    def test_file_not_found(self):
        """Test error when PDF file doesn't exist."""
        non_existent = Path("/tmp/nonexistent.pdf")

        with self.assertRaises(FileNotFoundError) as cm:
            list(stream_pdf_pages(non_existent))

        assert "PDF file not found" in str(cm.exception)

    def test_invalid_pdf_file(self):
        """Test error when file is not a valid PDF."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            invalid_pdf = tmp_path / "invalid.pdf"
            invalid_pdf.write_text("Not a PDF file")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_fitz.open.side_effect = Exception("Invalid PDF")

                with self.assertRaises(ValueError) as cm:
                    list(stream_pdf_pages(invalid_pdf))

                assert "Invalid PDF file" in str(cm.exception)

    def test_stream_single_page(self):
        """Test streaming a single-page PDF."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "single.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                # Setup mock document
                mock_doc = MagicMock()
                mock_doc.page_count = 1
                mock_fitz.open.return_value = mock_doc

                # Setup mock page
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Page 1 text"
                mock_page.get_images.return_value = []
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.__getitem__.return_value = mock_page

                # Stream pages
                pages = list(stream_pdf_pages(pdf_file))

                # Verify results
                assert len(pages) == 1
                assert pages[0].page_number == 1
                assert pages[0].text == "Page 1 text"
                assert pages[0].images == []
                assert pages[0].metadata["width"] == 612
                assert pages[0].metadata["height"] == 792

                # Verify document was closed
                mock_doc.close.assert_called_once()

    def test_stream_multiple_pages(self):
        """Test streaming multiple pages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "multi.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 3
                mock_fitz.open.return_value = mock_doc

                # Setup mock pages
                mock_pages = []
                for i in range(3):
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = f"Page {i + 1} text"
                    mock_page.get_images.return_value = []
                    mock_page.rect.width = 612
                    mock_page.rect.height = 792
                    mock_page.rotation = 0
                    mock_page.mediabox = (0, 0, 612, 792)
                    mock_pages.append(mock_page)

                mock_doc.__getitem__.side_effect = lambda idx: mock_pages[idx]

                # Stream pages
                pages = list(stream_pdf_pages(pdf_file))

                # Verify results
                assert len(pages) == 3
                for i, page in enumerate(pages):
                    assert page.page_number == i + 1
                    assert page.text == f"Page {i + 1} text"
                    assert page.images == []

                mock_doc.close.assert_called_once()

    def test_stream_with_progress_callback(self):
        """Test streaming with progress callback."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "progress.pdf"
            pdf_file.write_bytes(b"fake pdf")

            progress_calls = []

            def progress_callback(current, total):
                progress_calls.append((current, total))

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 2
                mock_fitz.open.return_value = mock_doc

                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_page.get_images.return_value = []
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.__getitem__.return_value = mock_page

                # Stream with callback
                list(stream_pdf_pages(pdf_file, progress_callback=progress_callback))

                # Verify callback was called
                assert len(progress_calls) == 2
                assert progress_calls[0] == (1, 2)
                assert progress_calls[1] == (2, 2)

    def test_stream_with_images(self):
        """Test streaming pages with images."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "images.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 1
                mock_fitz.open.return_value = mock_doc

                # Create fake image data
                fake_image = Image.new("RGB", (50, 50), color="blue")
                img_bytes = io.BytesIO()
                fake_image.save(img_bytes, format="PNG")
                img_bytes.seek(0)

                # Setup mock page with image
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Page with image"
                mock_page.get_images.return_value = [(123, 0, 0, 0, 0, 0, 0)]
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.extract_image.return_value = {"image": img_bytes.getvalue()}
                mock_doc.__getitem__.return_value = mock_page

                # Stream pages
                pages = list(stream_pdf_pages(pdf_file))

                # Verify image extraction
                assert len(pages) == 1
                assert len(pages[0].images) == 1
                assert isinstance(pages[0].images[0], Image.Image)
                assert pages[0].images[0].size == (50, 50)

    def test_stream_image_extraction_failure(self):
        """Test graceful handling of image extraction failure."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "bad_image.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 1
                mock_fitz.open.return_value = mock_doc

                # Setup mock page with image that fails extraction
                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_page.get_images.return_value = [(123, 0, 0, 0, 0, 0, 0)]
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.extract_image.side_effect = Exception("Image extraction failed")
                mock_doc.__getitem__.return_value = mock_page

                # Stream pages - should not crash
                pages = list(stream_pdf_pages(pdf_file))

                # Verify page was returned despite image failure
                assert len(pages) == 1
                assert pages[0].images == []  # Failed image not included

    def test_document_cleanup_on_error(self):
        """Test that document is closed even on error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "error.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 1
                mock_fitz.open.return_value = mock_doc

                # Make page access raise error
                mock_doc.__getitem__.side_effect = Exception("Page error")

                # Try to stream - should raise error
                with self.assertRaises(Exception):
                    list(stream_pdf_pages(pdf_file))

                # Document should still be closed
                mock_doc.close.assert_called_once()


class TestChunkPDF(unittest.TestCase):
    """Test chunk_pdf function."""

    def test_invalid_overlap(self):
        """Test error when overlap >= chunk_pages."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "test.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with self.assertRaises(ValueError) as cm:
                list(chunk_pdf(pdf_file, chunk_pages=10, overlap=10))

            assert "must be less than chunk_pages" in str(cm.exception)

            with self.assertRaises(ValueError) as cm:
                list(chunk_pdf(pdf_file, chunk_pages=10, overlap=15))

            assert "must be less than chunk_pages" in str(cm.exception)

    def test_file_not_found(self):
        """Test error when PDF file doesn't exist."""
        non_existent = Path("/tmp/nonexistent.pdf")

        with self.assertRaises(FileNotFoundError):
            list(chunk_pdf(non_existent))

    def test_chunk_single_chunk(self):
        """Test chunking PDF that fits in one chunk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "small.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 5  # Less than default chunk_pages=10
                mock_fitz.open.return_value = mock_doc

                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_page.get_images.return_value = []
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.__getitem__.return_value = mock_page

                # Chunk PDF
                chunks = list(chunk_pdf(pdf_file))

                # Should have one chunk with 5 pages
                assert len(chunks) == 1
                assert len(chunks[0]) == 5

    def test_chunk_multiple_chunks(self):
        """Test chunking PDF into multiple chunks."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "large.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 25  # Will create 3 chunks (10+10+5)
                mock_fitz.open.return_value = mock_doc

                mock_pages = []
                for i in range(25):
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = f"Page {i + 1}"
                    mock_page.get_images.return_value = []
                    mock_page.rect.width = 612
                    mock_page.rect.height = 792
                    mock_page.rotation = 0
                    mock_page.mediabox = (0, 0, 612, 792)
                    mock_pages.append(mock_page)

                mock_doc.__getitem__.side_effect = lambda idx: mock_pages[idx]

                # Chunk PDF with default chunk_pages=10
                chunks = list(chunk_pdf(pdf_file))

                # Verify chunks
                assert len(chunks) == 3
                assert len(chunks[0]) == 10  # Pages 1-10
                assert len(chunks[1]) == 10  # Pages 11-20
                assert len(chunks[2]) == 5   # Pages 21-25

                # Verify page numbers are correct
                assert chunks[0][0].page_number == 1
                assert chunks[0][-1].page_number == 10
                assert chunks[1][0].page_number == 11
                assert chunks[1][-1].page_number == 20
                assert chunks[2][0].page_number == 21
                assert chunks[2][-1].page_number == 25

    def test_chunk_with_overlap(self):
        """Test chunking with overlap between chunks."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "overlap.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 20
                mock_fitz.open.return_value = mock_doc

                mock_pages = []
                for i in range(20):
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = f"Page {i + 1}"
                    mock_page.get_images.return_value = []
                    mock_page.rect.width = 612
                    mock_page.rect.height = 792
                    mock_page.rotation = 0
                    mock_page.mediabox = (0, 0, 612, 792)
                    mock_pages.append(mock_page)

                mock_doc.__getitem__.side_effect = lambda idx: mock_pages[idx]

                # Chunk with overlap=2
                # chunk_pages=10, overlap=2 → step_size=8
                # Chunk 1: pages 0-9 (pages 1-10)
                # Chunk 2: pages 8-17 (pages 9-18, overlap with 9-10)
                # Chunk 3: pages 16-19 (pages 17-20, overlap with 17-18)
                chunks = list(chunk_pdf(pdf_file, chunk_pages=10, overlap=2))

                assert len(chunks) == 3

                # Verify overlap: last 2 pages of chunk N should be first 2 of chunk N+1
                assert chunks[0][-2].page_number == 9  # Second-to-last of chunk 0
                assert chunks[0][-1].page_number == 10  # Last of chunk 0
                assert chunks[1][0].page_number == 9   # First of chunk 1
                assert chunks[1][1].page_number == 10  # Second of chunk 1

    def test_chunk_custom_size(self):
        """Test chunking with custom chunk size."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_file = tmp_path / "custom.pdf"
            pdf_file.write_bytes(b"fake pdf")

            with patch("src.streaming.fitz") as mock_fitz:
                mock_doc = MagicMock()
                mock_doc.page_count = 15
                mock_fitz.open.return_value = mock_doc

                mock_page = MagicMock()
                mock_page.get_text.return_value = "Text"
                mock_page.get_images.return_value = []
                mock_page.rect.width = 612
                mock_page.rect.height = 792
                mock_page.rotation = 0
                mock_page.mediabox = (0, 0, 612, 792)

                mock_doc.__getitem__.return_value = mock_page

                # Chunk with chunk_pages=5
                chunks = list(chunk_pdf(pdf_file, chunk_pages=5))

                # Should have 3 chunks of 5 pages each
                assert len(chunks) == 3
                assert all(len(chunk) == 5 for chunk in chunks)


class TestSelectStrategy(unittest.TestCase):
    """Test select_strategy function."""

    def test_full_load_strategy(self):
        """Test selection of full_load strategy."""
        analysis = PDFAnalysis(
            file_size=5 * 1024 * 1024,  # 5MB
            page_count=50,
            estimated_memory=10 * 1024 * 1024,
            complexity_score=30.0,
            recommended_strategy="full_load",
            issues=[],
        )

        strategy = select_strategy(analysis)

        assert strategy.strategy_type == "full_load"
        assert strategy.chunk_size == 50  # All pages at once
        assert strategy.memory_limit == 10 * 1024 * 1024 * 2  # 2x estimated memory
        assert strategy.estimated_time == max(1.0, 50 / 10.0)  # ~5 seconds

    def test_stream_pages_strategy(self):
        """Test selection of stream_pages strategy."""
        analysis = PDFAnalysis(
            file_size=50 * 1024 * 1024,  # 50MB
            page_count=100,
            estimated_memory=100 * 1024 * 1024,
            complexity_score=50.0,
            recommended_strategy="stream_pages",
            issues=[],
        )

        strategy = select_strategy(analysis)

        assert strategy.strategy_type == "stream_pages"
        assert strategy.chunk_size == 1  # One page at a time
        # memory_limit = estimated_memory / page_count * 5
        expected_limit = 100 * 1024 * 1024 // 100 * 5
        assert strategy.memory_limit == expected_limit
        assert strategy.estimated_time == 100 * 0.5  # 50 seconds

    def test_chunk_batch_strategy_normal_complexity(self):
        """Test chunk_batch with normal complexity."""
        analysis = PDFAnalysis(
            file_size=150 * 1024 * 1024,  # 150MB
            page_count=200,
            estimated_memory=300 * 1024 * 1024,
            complexity_score=50.0,  # Normal complexity
            recommended_strategy="chunk_batch",
            issues=[],
        )

        strategy = select_strategy(analysis)

        assert strategy.strategy_type == "chunk_batch"
        assert strategy.chunk_size == 10  # Standard chunk size for normal complexity
        expected_limit = 300 * 1024 * 1024 // 200 * (10 + 5)
        assert strategy.memory_limit == expected_limit
        assert strategy.estimated_time == 200 * 0.3  # 60 seconds

    def test_chunk_batch_strategy_high_complexity(self):
        """Test chunk_batch with high complexity."""
        analysis = PDFAnalysis(
            file_size=150 * 1024 * 1024,  # 150MB
            page_count=200,
            estimated_memory=300 * 1024 * 1024,
            complexity_score=80.0,  # High complexity
            recommended_strategy="chunk_batch",
            issues=[],
        )

        strategy = select_strategy(analysis)

        assert strategy.strategy_type == "chunk_batch"
        assert strategy.chunk_size == 5  # Smaller chunks for high complexity
        expected_limit = 300 * 1024 * 1024 // 200 * (5 + 5)
        assert strategy.memory_limit == expected_limit
        assert strategy.estimated_time == 200 * 0.3

    def test_strategy_with_issues(self):
        """Test strategy selection with detected issues."""
        analysis = PDFAnalysis(
            file_size=50 * 1024 * 1024,
            page_count=100,
            estimated_memory=100 * 1024 * 1024,
            complexity_score=50.0,
            recommended_strategy="stream_pages",
            issues=["WARNING: Missing fonts on page 5"],
        )

        strategy = select_strategy(analysis)

        # Strategy should still be selected based on recommended_strategy
        assert strategy.strategy_type == "stream_pages"

    def test_minimum_time_estimate(self):
        """Test that time estimate has minimum of 1 second for full_load."""
        analysis = PDFAnalysis(
            file_size=1 * 1024 * 1024,  # 1MB
            page_count=5,  # Very small PDF
            estimated_memory=2 * 1024 * 1024,
            complexity_score=20.0,
            recommended_strategy="full_load",
            issues=[],
        )

        strategy = select_strategy(analysis)

        # Even for 5 pages (0.5s estimate), should be minimum 1.0s
        assert strategy.estimated_time == 1.0


if __name__ == "__main__":
    unittest.main()
