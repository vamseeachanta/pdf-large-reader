"""
Unit tests for PDF assessment module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

from src.assessment import (
    PDFAnalysis,
    MemoryEstimate,
    PDFIssue,
    assess_pdf,
    estimate_memory_usage,
    detect_pdf_issues,
    _calculate_complexity_score,
    _select_strategy,
)


class TestMemoryEstimate:
    """Tests for MemoryEstimate dataclass."""

    def test_memory_estimate_creation(self):
        """Test creating MemoryEstimate object."""
        estimate = MemoryEstimate(
            min_memory=10 * 1024 * 1024,  # 10MB
            recommended_memory=50 * 1024 * 1024,  # 50MB
            peak_memory=100 * 1024 * 1024,  # 100MB
            per_page_avg=5 * 1024 * 1024,  # 5MB
        )

        assert estimate.min_memory == 10 * 1024 * 1024
        assert estimate.recommended_memory == 50 * 1024 * 1024
        assert estimate.peak_memory == 100 * 1024 * 1024
        assert estimate.per_page_avg == 5 * 1024 * 1024

    def test_memory_estimate_dict_conversion(self):
        """Test converting MemoryEstimate to dictionary."""
        estimate = MemoryEstimate(
            min_memory=1000,
            recommended_memory=5000,
            peak_memory=10000,
            per_page_avg=500,
        )

        estimate_dict = asdict(estimate)
        assert estimate_dict["min_memory"] == 1000
        assert estimate_dict["recommended_memory"] == 5000


class TestPDFIssue:
    """Tests for PDFIssue dataclass."""

    def test_pdf_issue_creation(self):
        """Test creating PDFIssue object."""
        issue = PDFIssue(
            issue_type="encryption",
            severity="critical",
            message="PDF is encrypted",
            page_number=1,
            details={"method": "AES-256"},
        )

        assert issue.issue_type == "encryption"
        assert issue.severity == "critical"
        assert issue.message == "PDF is encrypted"
        assert issue.page_number == 1
        assert issue.details["method"] == "AES-256"

    def test_pdf_issue_without_optional_fields(self):
        """Test PDFIssue without optional fields."""
        issue = PDFIssue(
            issue_type="corruption",
            severity="high",
            message="Cannot read page",
        )

        assert issue.page_number is None
        assert issue.details is None


class TestPDFAnalysis:
    """Tests for PDFAnalysis dataclass."""

    def test_pdf_analysis_creation(self):
        """Test creating PDFAnalysis object."""
        analysis = PDFAnalysis(
            file_size=10 * 1024 * 1024,
            page_count=100,
            estimated_memory=50 * 1024 * 1024,
            complexity_score=45.5,
            recommended_strategy="stream_pages",
            issues=["Encryption detected"],
            metadata={"title": "Test Document"},
        )

        assert analysis.file_size == 10 * 1024 * 1024
        assert analysis.page_count == 100
        assert analysis.complexity_score == 45.5
        assert analysis.recommended_strategy == "stream_pages"
        assert len(analysis.issues) == 1

    def test_pdf_analysis_default_metadata(self):
        """Test PDFAnalysis with default metadata."""
        analysis = PDFAnalysis(
            file_size=1000,
            page_count=10,
            estimated_memory=5000,
            complexity_score=20.0,
            recommended_strategy="full_load",
            issues=[],
        )

        assert analysis.metadata == {}


class TestEstimateMemoryUsage:
    """Tests for estimate_memory_usage function."""

    def test_estimate_memory_simple_pdf(self, tmp_path):
        """Test memory estimation for simple PDF."""
        # Create mock PDF file
        pdf_file = tmp_path / "simple.pdf"
        pdf_file.write_bytes(b"fake pdf content" * 1000)  # ~16KB

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 10
            mock_fitz.open.return_value = mock_doc

            estimate = estimate_memory_usage(pdf_file)

            assert estimate.min_memory > 0
            assert estimate.recommended_memory > estimate.min_memory
            assert estimate.peak_memory > estimate.recommended_memory
            assert estimate.per_page_avg > 0

    def test_estimate_memory_large_pdf(self, tmp_path):
        """Test memory estimation for large PDF."""
        # Create mock large PDF file
        pdf_file = tmp_path / "large.pdf"
        pdf_file.write_bytes(b"x" * (50 * 1024 * 1024))  # 50MB

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 100
            mock_fitz.open.return_value = mock_doc

            estimate = estimate_memory_usage(pdf_file)

            # Large file should have higher estimates
            assert estimate.min_memory > 50 * 1024 * 1024
            assert estimate.per_page_avg > 0

    def test_estimate_memory_complex_pages(self, tmp_path):
        """Test memory estimation for PDF with complex pages (>200KB per page)."""
        # Create mock PDF with complex pages
        pdf_file = tmp_path / "complex.pdf"
        # 50MB file with 100 pages = 500KB per page
        pdf_file.write_bytes(b"x" * (50 * 1024 * 1024))

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 100
            mock_fitz.open.return_value = mock_doc

            estimate = estimate_memory_usage(pdf_file)

            # Should use 10MB per page for complex pages
            assert estimate.per_page_avg == 10 * 1024 * 1024

    def test_estimate_memory_simple_text_pages(self, tmp_path):
        """Test memory estimation for PDF with simple text pages (<50KB per page)."""
        # Create mock PDF with simple pages
        pdf_file = tmp_path / "simple_text.pdf"
        # 1MB file with 100 pages = 10KB per page
        pdf_file.write_bytes(b"x" * (1 * 1024 * 1024))

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 100
            mock_fitz.open.return_value = mock_doc

            estimate = estimate_memory_usage(pdf_file)

            # Should use 2MB per page for simple pages
            assert estimate.per_page_avg == 2 * 1024 * 1024

    def test_estimate_memory_file_not_found(self, tmp_path):
        """Test error handling for non-existent file."""
        pdf_file = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            estimate_memory_usage(pdf_file)

    def test_estimate_memory_invalid_pdf(self, tmp_path):
        """Test error handling for invalid PDF."""
        pdf_file = tmp_path / "invalid.pdf"
        pdf_file.write_bytes(b"not a pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_fitz.open.side_effect = Exception("Invalid PDF")

            with pytest.raises(ValueError, match="Invalid PDF file"):
                estimate_memory_usage(pdf_file)


class TestDetectPDFIssues:
    """Tests for detect_pdf_issues function."""

    def test_detect_no_issues(self, tmp_path):
        """Test detecting no issues in clean PDF."""
        pdf_file = tmp_path / "clean.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 1
            mock_doc.metadata = {}

            mock_page = MagicMock()
            mock_page.get_fonts.return_value = [
                (None, None, None, "Arial", None)
            ]
            mock_page.get_text.return_value = "Clean text content"

            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            assert len(issues) == 0

    def test_detect_encryption(self, tmp_path):
        """Test detecting encrypted PDF."""
        pdf_file = tmp_path / "encrypted.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.is_encrypted = True
            mock_doc.page_count = 1
            mock_doc.metadata = {"encryption": "AES-256"}
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            assert len(issues) > 0
            encryption_issues = [i for i in issues if i.issue_type == "encryption"]
            assert len(encryption_issues) == 1
            assert encryption_issues[0].severity == "critical"

    def test_detect_corruption(self, tmp_path):
        """Test detecting corrupted PDF."""
        pdf_file = tmp_path / "corrupted.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 1
            mock_doc.metadata = {}
            mock_doc.__getitem__.side_effect = Exception("Corrupted page")
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            assert len(issues) > 0
            corruption_issues = [i for i in issues if i.issue_type == "corruption"]
            assert len(corruption_issues) > 0

    def test_detect_missing_fonts(self, tmp_path):
        """Test detecting missing fonts."""
        pdf_file = tmp_path / "missing_fonts.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 1
            mock_doc.metadata = {}

            mock_page = MagicMock()
            mock_page.get_fonts.return_value = [
                (None, None, None, "Invalid-Font", None)
            ]
            mock_page.get_text.return_value = "Text"

            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            font_issues = [i for i in issues if i.issue_type == "missing_fonts"]
            assert len(font_issues) > 0
            assert font_issues[0].severity == "medium"

    def test_detect_encoding_issues(self, tmp_path):
        """Test detecting encoding issues (many � characters)."""
        pdf_file = tmp_path / "encoding_issues.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 1
            mock_doc.metadata = {}

            mock_page = MagicMock()
            mock_page.get_fonts.return_value = []
            # 50% replacement characters
            mock_page.get_text.return_value = "�" * 50 + "a" * 50

            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            encoding_issues = [i for i in issues if i.issue_type == "encoding"]
            assert len(encoding_issues) > 0
            assert encoding_issues[0].severity == "medium"

    def test_detect_extraction_failure(self, tmp_path):
        """Test detecting text extraction failures."""
        pdf_file = tmp_path / "extraction_fail.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.is_encrypted = False
            mock_doc.page_count = 1
            mock_doc.metadata = {}

            mock_page = MagicMock()
            mock_page.get_fonts.return_value = []
            mock_page.get_text.side_effect = Exception("Extraction failed")

            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc

            issues = detect_pdf_issues(pdf_file)

            extraction_issues = [i for i in issues if i.issue_type == "extraction"]
            assert len(extraction_issues) > 0
            assert extraction_issues[0].severity == "high"

    def test_detect_file_not_found(self, tmp_path):
        """Test error handling for non-existent file."""
        pdf_file = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            detect_pdf_issues(pdf_file)


class TestCalculateComplexityScore:
    """Tests for _calculate_complexity_score function."""

    def test_complexity_simple_pdf(self):
        """Test complexity score for simple PDF."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.metadata = {"format": "PDF-1.4"}
        mock_doc.page_count = 10

        mock_page = MagicMock()
        mock_page.get_images.return_value = []
        mock_page.get_fonts.return_value = [(None, None, None, "Arial", None)]
        mock_doc.__getitem__.return_value = mock_page

        # Small file, few pages, no images
        score = _calculate_complexity_score(mock_doc, 50 * 1024, 10)

        assert 0 <= score <= 100
        assert score < 30  # Should be low complexity

    def test_complexity_complex_pdf(self):
        """Test complexity score for complex PDF."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_doc.metadata = {"format": "PDF-1.7", "encryption": "AES-256"}
        mock_doc.page_count = 1000

        mock_page = MagicMock()
        # Many images
        mock_page.get_images.return_value = [(i,) for i in range(10)]
        # Many fonts
        mock_page.get_fonts.return_value = [
            (None, None, None, f"Font{i}", None) for i in range(15)
        ]
        mock_doc.__getitem__.return_value = mock_page

        # Large file, many pages, images, fonts, encryption
        score = _calculate_complexity_score(mock_doc, 600 * 1024 * 1024, 1000)

        assert score > 70  # Should be high complexity
        assert score <= 100

    def test_complexity_medium_pdf(self):
        """Test complexity score for medium complexity PDF."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.metadata = {"format": "PDF-1.5"}
        mock_doc.page_count = 100

        mock_page = MagicMock()
        mock_page.get_images.return_value = [(1,), (2,)]
        mock_page.get_fonts.return_value = [
            (None, None, None, f"Font{i}", None) for i in range(5)
        ]
        mock_doc.__getitem__.return_value = mock_page

        score = _calculate_complexity_score(mock_doc, 150 * 1024 * 100, 100)

        assert 30 <= score <= 70  # Medium complexity

    def test_complexity_page_access_failure(self):
        """Test complexity when page access fails."""
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.metadata = {}
        mock_doc.page_count = 3
        mock_doc.__getitem__.side_effect = Exception("Cannot access page")

        score = _calculate_complexity_score(mock_doc, 100 * 1024, 3)

        # Should increase score due to access failures
        assert score > 0


class TestSelectStrategy:
    """Tests for _select_strategy function."""

    def test_select_full_load_strategy(self):
        """Test selecting full_load strategy for small simple PDFs."""
        # Small file, low complexity, no issues
        strategy = _select_strategy(
            file_size=5 * 1024 * 1024,  # 5MB
            page_count=20,
            complexity_score=30.0,
            issues=[],
        )

        assert strategy == "full_load"

    def test_select_stream_pages_strategy(self):
        """Test selecting stream_pages strategy for medium PDFs."""
        # Medium file, medium complexity
        strategy = _select_strategy(
            file_size=50 * 1024 * 1024,  # 50MB
            page_count=200,
            complexity_score=50.0,
            issues=[],
        )

        assert strategy == "stream_pages"

    def test_select_chunk_batch_large_file(self):
        """Test selecting chunk_batch for large files."""
        # Large file
        strategy = _select_strategy(
            file_size=150 * 1024 * 1024,  # 150MB
            page_count=500,
            complexity_score=50.0,
            issues=[],
        )

        assert strategy == "chunk_batch"

    def test_select_chunk_batch_high_complexity(self):
        """Test selecting chunk_batch for high complexity."""
        # High complexity score
        strategy = _select_strategy(
            file_size=50 * 1024 * 1024,
            page_count=200,
            complexity_score=80.0,
            issues=[],
        )

        assert strategy == "chunk_batch"

    def test_select_chunk_batch_many_pages(self):
        """Test selecting chunk_batch for many pages."""
        # Many pages
        strategy = _select_strategy(
            file_size=50 * 1024 * 1024,
            page_count=600,
            complexity_score=40.0,
            issues=[],
        )

        assert strategy == "chunk_batch"

    def test_select_stream_pages_critical_issues(self):
        """Test that critical issues force stream_pages."""
        # Critical issue should override size-based selection
        critical_issue = PDFIssue(
            issue_type="encryption",
            severity="critical",
            message="Encrypted",
        )

        strategy = _select_strategy(
            file_size=5 * 1024 * 1024,  # Small file
            page_count=10,
            complexity_score=20.0,
            issues=[critical_issue],
        )

        assert strategy == "stream_pages"


class TestAssessPDF:
    """Tests for assess_pdf function."""

    def test_assess_pdf_success(self, tmp_path):
        """Test successful PDF assessment."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"fake pdf" * 1000)

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.page_count = 50
            mock_doc.is_encrypted = False
            mock_doc.metadata = {
                "title": "Test PDF",
                "author": "Test Author",
                "format": "PDF-1.5",
            }

            mock_page = MagicMock()
            mock_page.get_images.return_value = []
            mock_page.get_fonts.return_value = [(None, None, None, "Arial", None)]
            mock_page.get_text.return_value = "Clean text"

            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.open.return_value = mock_doc

            analysis = assess_pdf(pdf_file)

            assert isinstance(analysis, PDFAnalysis)
            assert analysis.page_count == 50
            assert analysis.file_size > 0
            assert 0 <= analysis.complexity_score <= 100
            assert analysis.recommended_strategy in ["full_load", "stream_pages", "chunk_batch"]
            assert isinstance(analysis.metadata, dict)

    def test_assess_pdf_file_not_found(self, tmp_path):
        """Test error handling for non-existent file."""
        pdf_file = tmp_path / "nonexistent.pdf"

        with pytest.raises(FileNotFoundError):
            assess_pdf(pdf_file)

    def test_assess_pdf_invalid_file(self, tmp_path):
        """Test error handling for invalid PDF."""
        pdf_file = tmp_path / "invalid.pdf"
        pdf_file.write_bytes(b"not a pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_fitz.open.side_effect = Exception("Invalid PDF")

            with pytest.raises(ValueError, match="Invalid PDF file"):
                assess_pdf(pdf_file)

    def test_assess_pdf_with_issues(self, tmp_path):
        """Test assessment with detected issues."""
        pdf_file = tmp_path / "issues.pdf"
        pdf_file.write_bytes(b"fake pdf")

        with patch("src.assessment.fitz") as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 10
            mock_doc.is_encrypted = True  # Encryption issue
            mock_doc.metadata = {"encryption": "AES-256"}

            mock_fitz.open.return_value = mock_doc

            analysis = assess_pdf(pdf_file)

            assert len(analysis.issues) > 0
            assert any("CRITICAL" in issue for issue in analysis.issues)
