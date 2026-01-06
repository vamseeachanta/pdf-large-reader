"""
ABOUTME: PDF assessment module for analyzing PDF files before processing
ABOUTME: Determines optimal processing strategy based on file size, complexity, and issues
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class MemoryEstimate:
    """Memory usage estimation for PDF processing."""
    min_memory: int  # Minimum RAM needed (bytes)
    recommended_memory: int  # Recommended RAM (bytes)
    peak_memory: int  # Peak usage estimate (bytes)
    per_page_avg: int  # Average memory per page (bytes)


@dataclass
class PDFIssue:
    """Detected issue in PDF file."""
    issue_type: str  # 'encryption', 'corruption', 'missing_fonts', 'encoding'
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    page_number: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class PDFAnalysis:
    """Complete PDF analysis results."""
    file_size: int  # File size in bytes
    page_count: int  # Number of pages
    estimated_memory: int  # Estimated RAM needed (bytes)
    complexity_score: float  # 0-100 (higher = more complex)
    recommended_strategy: str  # 'full_load' | 'stream_pages' | 'chunk_batch'
    issues: List[str]  # List of issue descriptions
    metadata: Dict[str, Any] = field(default_factory=dict)


def assess_pdf(file_path: Path) -> PDFAnalysis:
    """
    Analyze PDF file and determine optimal processing strategy.

    Args:
        file_path: Path to PDF file

    Returns:
        PDFAnalysis object with file characteristics and recommendations

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF
    """
    logger.info(f"Assessing PDF: {file_path}")

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Get file size
    file_size = file_path.stat().st_size
    logger.debug(f"File size: {file_size:,} bytes")

    # Open PDF to get metadata
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {e}")

    try:
        # Get page count
        page_count = doc.page_count
        logger.debug(f"Page count: {page_count}")

        # Get metadata
        metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "producer": doc.metadata.get("producer", ""),
            "format": doc.metadata.get("format", ""),
            "encryption": doc.metadata.get("encryption", ""),
        }

        # Calculate complexity score
        complexity_score = _calculate_complexity_score(doc, file_size, page_count)
        logger.debug(f"Complexity score: {complexity_score:.2f}")

        # Detect issues
        issues_list = detect_pdf_issues(file_path)
        issue_descriptions = [f"{issue.severity.upper()}: {issue.message}" for issue in issues_list]

        # Estimate memory usage
        memory_estimate = estimate_memory_usage(file_path)
        estimated_memory = memory_estimate.recommended_memory

        # Determine processing strategy
        recommended_strategy = _select_strategy(file_size, page_count, complexity_score, issues_list)
        logger.info(f"Recommended strategy: {recommended_strategy}")

        return PDFAnalysis(
            file_size=file_size,
            page_count=page_count,
            estimated_memory=estimated_memory,
            complexity_score=complexity_score,
            recommended_strategy=recommended_strategy,
            issues=issue_descriptions,
            metadata=metadata
        )

    finally:
        doc.close()


def estimate_memory_usage(file_path: Path) -> MemoryEstimate:
    """
    Estimate memory requirements for processing PDF.

    Args:
        file_path: Path to PDF file

    Returns:
        MemoryEstimate with min/recommended/peak memory estimates

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF
    """
    logger.debug(f"Estimating memory usage for: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    file_size = file_path.stat().st_size

    try:
        doc = fitz.open(file_path)
        page_count = doc.page_count
        doc.close()
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {e}")

    # Memory estimation formulas
    # Base memory: File size for document structure
    base_memory = file_size

    # Per-page memory estimation
    # Average: ~5MB per page for text + images + layout
    # Complex pages (images, tables): ~10MB
    # Simple pages (text only): ~2MB
    avg_per_page = 5 * 1024 * 1024  # 5MB default

    # Adjust based on file size per page
    size_per_page = file_size / page_count if page_count > 0 else 0
    if size_per_page > 200 * 1024:  # >200KB per page suggests complex content
        avg_per_page = 10 * 1024 * 1024  # 10MB per page
    elif size_per_page < 50 * 1024:  # <50KB per page suggests simple text
        avg_per_page = 2 * 1024 * 1024  # 2MB per page

    # Memory estimates
    # Min: Base + 1 page
    min_memory = base_memory + avg_per_page

    # Recommended: Base + 5 pages simultaneously
    recommended_memory = base_memory + (avg_per_page * 5)

    # Peak: Base + 10 pages + overhead (20%)
    peak_memory = int((base_memory + (avg_per_page * 10)) * 1.2)

    logger.debug(
        f"Memory estimate - Min: {min_memory:,}, "
        f"Recommended: {recommended_memory:,}, "
        f"Peak: {peak_memory:,}"
    )

    return MemoryEstimate(
        min_memory=min_memory,
        recommended_memory=recommended_memory,
        peak_memory=peak_memory,
        per_page_avg=avg_per_page
    )


def detect_pdf_issues(file_path: Path) -> List[PDFIssue]:
    """
    Detect potential processing issues in PDF.

    Args:
        file_path: Path to PDF file

    Returns:
        List of PDFIssue objects (empty if no issues)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
    """
    logger.debug(f"Detecting PDF issues: {file_path}")

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    issues: List[PDFIssue] = []

    try:
        doc = fitz.open(file_path)

        # Check for encryption
        if doc.is_encrypted:
            issues.append(PDFIssue(
                issue_type="encryption",
                severity="critical",
                message="PDF is encrypted and may require password",
                details={"encryption_method": doc.metadata.get("encryption", "Unknown")}
            ))

        # Check for corruption (basic check)
        try:
            # Try to access first and last page
            if doc.page_count > 0:
                _ = doc[0]
                if doc.page_count > 1:
                    _ = doc[-1]
        except Exception as e:
            issues.append(PDFIssue(
                issue_type="corruption",
                severity="critical",
                message=f"PDF may be corrupted: {str(e)}",
                details={"error": str(e)}
            ))

        # Check each page for issues
        for page_num in range(doc.page_count):
            try:
                page = doc[page_num]

                # Check for missing fonts
                fonts = page.get_fonts(full=True)
                for font_info in fonts:
                    font_name = font_info[3]  # Font name
                    if not font_name or font_name.startswith("Invalid"):
                        issues.append(PDFIssue(
                            issue_type="missing_fonts",
                            severity="medium",
                            message=f"Missing or invalid font on page {page_num + 1}",
                            page_number=page_num + 1,
                            details={"font_info": font_info}
                        ))

                # Check for text extraction issues
                try:
                    text = page.get_text()
                    # Check for encoding issues (lots of � characters)
                    if text.count("�") > len(text) * 0.1:  # >10% replacement chars
                        issues.append(PDFIssue(
                            issue_type="encoding",
                            severity="medium",
                            message=f"Possible encoding issues on page {page_num + 1}",
                            page_number=page_num + 1,
                            details={"replacement_char_percent": text.count("�") / len(text) * 100}
                        ))
                except Exception as e:
                    issues.append(PDFIssue(
                        issue_type="extraction",
                        severity="high",
                        message=f"Text extraction failed on page {page_num + 1}: {str(e)}",
                        page_number=page_num + 1,
                        details={"error": str(e)}
                    ))

            except Exception as e:
                issues.append(PDFIssue(
                    issue_type="corruption",
                    severity="high",
                    message=f"Cannot access page {page_num + 1}: {str(e)}",
                    page_number=page_num + 1,
                    details={"error": str(e)}
                ))

        doc.close()

    except Exception as e:
        issues.append(PDFIssue(
            issue_type="corruption",
            severity="critical",
            message=f"Cannot open PDF: {str(e)}",
            details={"error": str(e)}
        ))

    logger.info(f"Detected {len(issues)} issues")
    return issues


def _calculate_complexity_score(doc: fitz.Document, file_size: int, page_count: int) -> float:
    """
    Calculate PDF complexity score (0-100).

    Higher scores indicate more complex documents requiring more processing resources.

    Args:
        doc: PyMuPDF document object
        file_size: File size in bytes
        page_count: Number of pages

    Returns:
        Complexity score (0-100)
    """
    score = 0.0

    # Factor 1: File size per page (0-30 points)
    # Large files per page suggest images, complex layouts
    size_per_page = file_size / page_count if page_count > 0 else 0
    if size_per_page > 500 * 1024:  # >500KB per page
        score += 30
    elif size_per_page > 200 * 1024:  # >200KB per page
        score += 20
    elif size_per_page > 100 * 1024:  # >100KB per page
        score += 10

    # Factor 2: Total page count (0-20 points)
    if page_count > 1000:
        score += 20
    elif page_count > 500:
        score += 15
    elif page_count > 100:
        score += 10
    elif page_count > 50:
        score += 5

    # Factor 3: Sample first 3 pages for content complexity (0-30 points)
    pages_to_sample = min(3, page_count)
    total_images = 0
    total_fonts = 0

    for page_num in range(pages_to_sample):
        try:
            page = doc[page_num]

            # Count images
            image_list = page.get_images(full=True)
            total_images += len(image_list)

            # Count unique fonts
            fonts = page.get_fonts(full=True)
            total_fonts += len(fonts)

        except Exception:
            # If page access fails, assume complex
            score += 10

    # Average per page
    avg_images = total_images / pages_to_sample if pages_to_sample > 0 else 0
    avg_fonts = total_fonts / pages_to_sample if pages_to_sample > 0 else 0

    # Images complexity
    if avg_images > 5:
        score += 15
    elif avg_images > 2:
        score += 10
    elif avg_images > 0:
        score += 5

    # Font complexity (more fonts = more complex formatting)
    if avg_fonts > 10:
        score += 15
    elif avg_fonts > 5:
        score += 10
    elif avg_fonts > 2:
        score += 5

    # Factor 4: Metadata complexity (0-10 points)
    if doc.is_encrypted:
        score += 10
    elif doc.metadata.get("encryption"):
        score += 5

    # Factor 5: Format version (0-10 points)
    # Newer PDF versions tend to have more complex features
    pdf_format = doc.metadata.get("format", "")
    if "1.7" in pdf_format or "2.0" in pdf_format:
        score += 10
    elif "1.6" in pdf_format or "1.5" in pdf_format:
        score += 5

    # Cap at 100
    return min(score, 100.0)


def _select_strategy(
    file_size: int,
    page_count: int,
    complexity_score: float,
    issues: List[PDFIssue]
) -> str:
    """
    Select optimal processing strategy based on PDF characteristics.

    Strategies:
    - full_load: Load entire PDF into memory (<10MB, low complexity)
    - stream_pages: Process one page at a time (10-100MB, medium complexity)
    - chunk_batch: Process in multi-page chunks (≥100MB, high complexity)

    Args:
        file_size: File size in bytes
        page_count: Number of pages
        complexity_score: Complexity score (0-100)
        issues: List of detected issues

    Returns:
        Strategy name: 'full_load' | 'stream_pages' | 'chunk_batch'
    """
    # Critical issues force careful processing
    has_critical_issues = any(issue.severity == "critical" for issue in issues)

    # Size thresholds
    MB_10 = 10 * 1024 * 1024
    MB_100 = 100 * 1024 * 1024

    # Strategy selection logic
    if has_critical_issues:
        # Critical issues require careful page-by-page processing
        return "stream_pages"

    if file_size < MB_10 and complexity_score < 50:
        # Small, simple files: load everything
        return "full_load"

    if file_size >= MB_100 or complexity_score > 70 or page_count > 500:
        # Large or complex files: chunk processing
        return "chunk_batch"

    # Default: stream pages
    return "stream_pages"
