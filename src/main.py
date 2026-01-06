"""
ABOUTME: Main API for large PDF processing with memory-efficient strategies
ABOUTME: Integrates assessment, streaming, extraction, and fallback modules
"""

import logging
from pathlib import Path
from typing import Callable, Generator, List, Optional, Union

import fitz  # PyMuPDF

from .assessment import PDFAnalysis, assess_pdf
from .extraction import extract_page_full
from .fallback import extract_with_codex, should_use_fallback
from .streaming import PDFPage, chunk_pdf, select_strategy, stream_pdf_pages
from .utils import ProgressTracker

logger = logging.getLogger(__name__)


def process_large_pdf(
    pdf_path: Union[str, Path],
    output_format: str = "generator",
    extract_images: bool = False,
    extract_tables: bool = False,
    chunk_size: Optional[int] = None,
    fallback_api_key: Optional[str] = None,
    fallback_model: str = "gpt-4o",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    auto_strategy: bool = True
) -> Union[Generator[PDFPage, None, None], List[PDFPage], str]:
    """
    Process large PDF files with automatic strategy selection and memory optimization.

    This high-level API automatically:
    - Assesses PDF characteristics (size, complexity, issues)
    - Selects optimal processing strategy (full_load, stream_pages, chunk_batch)
    - Extracts content (text, images, tables) as requested
    - Uses AI fallback for complex/scanned pages when API key provided
    - Tracks progress and manages memory efficiently

    Args:
        pdf_path: Path to PDF file (str or Path object)
        output_format: Output format - 'generator' (default), 'list', or 'text'
            - 'generator': Memory-efficient generator yielding PDFPage objects
            - 'list': List of all PDFPage objects (loads all in memory)
            - 'text': Concatenated text string from all pages
        extract_images: Extract images from pages (default: False)
        extract_tables: Extract tables as DataFrames (default: False)
        chunk_size: Pages per chunk (None = auto-select based on strategy)
        fallback_api_key: OpenAI API key for fallback extraction (optional)
        fallback_model: Model for fallback (default: 'gpt-4o')
        progress_callback: Optional callback function(current_page, total_pages)
        auto_strategy: Automatically select strategy based on PDF analysis (default: True)

    Returns:
        Generator[PDFPage], List[PDFPage], or str depending on output_format

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF is invalid or parameters are incorrect
        RuntimeError: If processing fails

    Example:
        >>> # Memory-efficient streaming (default)
        >>> for page in process_large_pdf("huge.pdf"):
        ...     print(f"Page {page.page_number}: {len(page.text)} chars")

        >>> # Extract all pages with images and tables
        >>> pages = process_large_pdf(
        ...     "document.pdf",
        ...     output_format="list",
        ...     extract_images=True,
        ...     extract_tables=True
        ... )

        >>> # Get all text as single string
        >>> text = process_large_pdf("document.pdf", output_format="text")

        >>> # With fallback for scanned PDFs
        >>> pages = process_large_pdf(
        ...     "scanned.pdf",
        ...     fallback_api_key="sk-...",
        ...     progress_callback=lambda cur, tot: print(f"{cur}/{tot}")
        ... )
    """
    logger.info(f"Processing PDF: {pdf_path}")

    # Convert to Path object
    pdf_path = Path(pdf_path)

    # Validate file exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Validate output format
    valid_formats = ["generator", "list", "text"]
    if output_format not in valid_formats:
        raise ValueError(f"output_format must be one of {valid_formats}, got: {output_format}")

    # Step 1: Assess PDF
    logger.info("Step 1: Assessing PDF characteristics...")
    analysis = assess_pdf(pdf_path)
    logger.info(
        f"Assessment complete - Pages: {analysis.page_count}, "
        f"Size: {analysis.file_size:,} bytes, "
        f"Complexity: {analysis.complexity_score:.1f}, "
        f"Strategy: {analysis.recommended_strategy}"
    )

    # Step 2: Select processing strategy
    if auto_strategy:
        logger.info("Step 2: Selecting optimal processing strategy...")
        strategy = select_strategy(analysis)
        if chunk_size is None:
            chunk_size = strategy.chunk_size
        logger.info(
            f"Strategy selected: {strategy.strategy_type}, "
            f"chunk_size={chunk_size}, "
            f"estimated_time={strategy.estimated_time:.1f}s"
        )
    else:
        # Manual strategy
        if chunk_size is None:
            chunk_size = 1  # Default to single-page streaming
        logger.info(f"Using manual strategy with chunk_size={chunk_size}")

    # Step 3: Process PDF based on strategy and output format
    logger.info("Step 3: Processing PDF content...")

    if output_format == "generator":
        # Return generator for memory-efficient streaming
        return _process_as_generator(
            pdf_path,
            chunk_size,
            extract_images,
            extract_tables,
            fallback_api_key,
            fallback_model,
            progress_callback,
            analysis
        )

    elif output_format == "list":
        # Process all pages and return as list
        pages = list(_process_as_generator(
            pdf_path,
            chunk_size,
            extract_images,
            extract_tables,
            fallback_api_key,
            fallback_model,
            progress_callback,
            analysis
        ))
        logger.info(f"Processing complete - Extracted {len(pages)} pages")
        return pages

    else:  # output_format == "text"
        # Extract all text and concatenate
        logger.info("Extracting text from all pages...")
        text_parts = []
        for page in _process_as_generator(
            pdf_path,
            chunk_size,
            extract_images,
            extract_tables,
            fallback_api_key,
            fallback_model,
            progress_callback,
            analysis
        ):
            text_parts.append(page.text)

        full_text = "\n\n".join(text_parts)
        logger.info(f"Text extraction complete - {len(full_text):,} characters")
        return full_text


def _process_as_generator(
    pdf_path: Path,
    chunk_size: int,
    extract_images: bool,
    extract_tables: bool,
    fallback_api_key: Optional[str],
    fallback_model: str,
    progress_callback: Optional[Callable[[int, int], None]],
    analysis: PDFAnalysis
) -> Generator[PDFPage, None, None]:
    """
    Internal generator for processing PDF pages.

    Handles streaming, extraction, and fallback logic.
    """
    logger.debug("Starting page-by-page processing...")

    # Open PDF for fallback decision logic
    doc = fitz.open(pdf_path)

    try:
        total_pages = doc.page_count

        # Stream pages
        for page_obj in stream_pdf_pages(pdf_path, chunk_size=1, progress_callback=progress_callback):
            page_num = page_obj.page_number - 1  # Convert to 0-indexed

            # Get PyMuPDF page for fallback decision
            fitz_page = doc[page_num]

            # Check if fallback is needed
            use_fallback, reason = should_use_fallback(fitz_page, analysis.complexity_score)

            if use_fallback and fallback_api_key:
                logger.info(f"Page {page_obj.page_number}: Using fallback extraction (reason: {reason})")
                try:
                    # Extract using fallback
                    fallback_text = extract_with_codex(fitz_page, fallback_api_key, fallback_model)
                    # Replace page text with fallback result
                    page_obj.text = fallback_text
                except Exception as e:
                    logger.error(f"Fallback extraction failed: {e}, using standard extraction")
                    # Keep original text if fallback fails

            elif use_fallback and not fallback_api_key:
                logger.warning(
                    f"Page {page_obj.page_number}: Fallback recommended ({reason}) "
                    f"but no API key provided"
                )

            # Extract additional content if requested
            if extract_images or extract_tables:
                # Re-extract with full extraction
                page_obj = extract_page_full(
                    fitz_page,
                    extract_images_flag=extract_images,
                    extract_tables_flag=extract_tables
                )

                # If we used fallback text, replace it back
                if use_fallback and fallback_api_key:
                    try:
                        fallback_text = extract_with_codex(fitz_page, fallback_api_key, fallback_model)
                        page_obj.text = fallback_text
                    except Exception:
                        pass  # Keep standard text

            yield page_obj

    finally:
        doc.close()
        logger.info("PDF processing complete")


# Convenience functions for common use cases

def extract_text_only(pdf_path: Union[str, Path]) -> str:
    """
    Extract all text from PDF as a single string.

    Convenience function for simple text extraction without images or tables.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Concatenated text from all pages

    Example:
        >>> text = extract_text_only("document.pdf")
        >>> print(f"Extracted {len(text)} characters")
    """
    return process_large_pdf(pdf_path, output_format="text")


def extract_pages_with_images(
    pdf_path: Union[str, Path],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[PDFPage]:
    """
    Extract all pages with text and images.

    Convenience function for extracting text + images without tables.

    Args:
        pdf_path: Path to PDF file
        progress_callback: Optional progress callback

    Returns:
        List of PDFPage objects with text and images

    Example:
        >>> pages = extract_pages_with_images("document.pdf")
        >>> for page in pages:
        ...     print(f"Page {page.page_number}: {len(page.images)} images")
    """
    return process_large_pdf(
        pdf_path,
        output_format="list",
        extract_images=True,
        extract_tables=False,
        progress_callback=progress_callback
    )


def extract_pages_with_tables(
    pdf_path: Union[str, Path],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[PDFPage]:
    """
    Extract all pages with text and tables.

    Convenience function for extracting text + tables without images.

    Args:
        pdf_path: Path to PDF file
        progress_callback: Optional progress callback

    Returns:
        List of PDFPage objects with text and tables in metadata

    Example:
        >>> pages = extract_pages_with_tables("report.pdf")
        >>> for page in pages:
        ...     tables = page.metadata.get("tables", [])
        ...     print(f"Page {page.page_number}: {len(tables)} tables")
    """
    return process_large_pdf(
        pdf_path,
        output_format="list",
        extract_images=False,
        extract_tables=True,
        progress_callback=progress_callback
    )


def extract_everything(
    pdf_path: Union[str, Path],
    fallback_api_key: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[PDFPage]:
    """
    Extract all content: text, images, tables, with optional AI fallback.

    Convenience function for comprehensive extraction of all content types.

    Args:
        pdf_path: Path to PDF file
        fallback_api_key: Optional OpenAI API key for complex/scanned pages
        progress_callback: Optional progress callback

    Returns:
        List of PDFPage objects with text, images, and tables

    Example:
        >>> pages = extract_everything("document.pdf", fallback_api_key="sk-...")
        >>> for page in pages:
        ...     print(f"Page {page.page_number}:")
        ...     print(f"  Text: {len(page.text)} chars")
        ...     print(f"  Images: {len(page.images)}")
        ...     print(f"  Tables: {len(page.metadata.get('tables', []))}")
    """
    return process_large_pdf(
        pdf_path,
        output_format="list",
        extract_images=True,
        extract_tables=True,
        fallback_api_key=fallback_api_key,
        progress_callback=progress_callback
    )
