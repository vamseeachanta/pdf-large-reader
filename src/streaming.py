"""
ABOUTME: PDF streaming module for memory-efficient page processing
ABOUTME: Provides generators for streaming and chunking large PDFs
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import fitz  # PyMuPDF
from PIL import Image

from .assessment import PDFAnalysis
from .utils import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class PDFPage:
    """Represents a single PDF page with extracted content."""
    page_number: int  # Page number (1-indexed)
    text: str  # Extracted text content
    images: List[Image.Image]  # Extracted images as PIL Image objects
    metadata: Dict[str, Any]  # Page metadata (size, rotation, etc.)
    layout: Optional[Dict] = None  # Layout information (optional)


@dataclass
class ProcessingStrategy:
    """Defines PDF processing strategy and parameters."""
    strategy_type: str  # 'full_load' | 'stream_pages' | 'chunk_batch'
    chunk_size: int  # Pages per chunk
    memory_limit: int  # RAM limit for operation (bytes)
    estimated_time: float  # Estimated processing time (seconds)


def stream_pdf_pages(
    file_path: Path,
    chunk_size: int = 1,
    progress_callback: Optional[Callable] = None
) -> Iterator[PDFPage]:
    """
    Stream PDF pages one at a time or in small chunks.

    This is a generator function that yields PDFPage objects without loading
    the entire PDF into memory. Suitable for PDFs 10-100MB.

    Args:
        file_path: Path to PDF file
        chunk_size: Number of pages per yield (default: 1 for true streaming)
        progress_callback: Optional function(current, total) for progress updates

    Yields:
        PDFPage objects with text, images, and metadata

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF

    Example:
        >>> for page in stream_pdf_pages(Path("large.pdf")):
        ...     print(f"Page {page.page_number}: {len(page.text)} chars")
    """
    logger.info(f"Streaming PDF: {file_path} (chunk_size={chunk_size})")

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Open PDF
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {e}")

    try:
        total_pages = doc.page_count
        logger.debug(f"Total pages: {total_pages}")

        # Stream pages
        for page_num in range(total_pages):
            # Extract page content
            page = doc[page_num]

            # Extract text
            text = page.get_text()

            # Extract images
            images = []
            image_list = page.get_images(full=True)
            for img_index in image_list:
                try:
                    xref = img_index[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    # Convert to PIL Image
                    import io
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    images.append(pil_image)
                except Exception as e:
                    logger.warning(f"Failed to extract image on page {page_num + 1}: {e}")

            # Get page metadata
            metadata = {
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
                "mediabox": page.mediabox,
            }

            # Create PDFPage object
            pdf_page = PDFPage(
                page_number=page_num + 1,  # 1-indexed for user display
                text=text,
                images=images,
                metadata=metadata,
                layout=None  # Layout extraction not implemented yet
            )

            # Update progress
            if progress_callback:
                progress_callback(page_num + 1, total_pages)

            # Yield page
            yield pdf_page

            logger.debug(f"Streamed page {page_num + 1}/{total_pages}")

    finally:
        doc.close()
        logger.info(f"Finished streaming PDF: {file_path}")


def chunk_pdf(
    file_path: Path,
    chunk_pages: int = 10,
    overlap: int = 0
) -> Iterator[List[PDFPage]]:
    """
    Process PDF in multi-page chunks with optional overlap.

    This generator yields lists of PDFPage objects, processing the PDF in
    batches for optimal memory usage. Suitable for PDFs ≥100MB.

    Args:
        file_path: Path to PDF file
        chunk_pages: Pages per chunk (default: 10)
        overlap: Overlap pages between chunks (default: 0)

    Yields:
        Lists of PDFPage objects (one list per chunk)

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF
        ValueError: If overlap >= chunk_pages

    Example:
        >>> for chunk in chunk_pdf(Path("huge.pdf"), chunk_pages=10, overlap=2):
        ...     print(f"Processing {len(chunk)} pages")
        ...     # Process chunk
    """
    logger.info(f"Chunking PDF: {file_path} (chunk_pages={chunk_pages}, overlap={overlap})")

    # Validate parameters
    if overlap >= chunk_pages:
        raise ValueError(f"Overlap ({overlap}) must be less than chunk_pages ({chunk_pages})")

    # Validate file exists
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    # Open PDF
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {e}")

    try:
        total_pages = doc.page_count
        logger.debug(f"Total pages: {total_pages}, will create ~{(total_pages + chunk_pages - 1) // chunk_pages} chunks")

        # Calculate step size (accounting for overlap)
        step_size = chunk_pages - overlap

        # Process in chunks
        chunk_num = 0
        start_page = 0

        while start_page < total_pages:
            # Calculate chunk boundaries
            end_page = min(start_page + chunk_pages, total_pages)

            # Extract pages in this chunk
            chunk: List[PDFPage] = []

            for page_num in range(start_page, end_page):
                # Extract page content
                page = doc[page_num]

                # Extract text
                text = page.get_text()

                # Extract images
                images = []
                image_list = page.get_images(full=True)
                for img_index in image_list:
                    try:
                        xref = img_index[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        # Convert to PIL Image
                        import io
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        images.append(pil_image)
                    except Exception as e:
                        logger.warning(f"Failed to extract image on page {page_num + 1}: {e}")

                # Get page metadata
                metadata = {
                    "width": page.rect.width,
                    "height": page.rect.height,
                    "rotation": page.rotation,
                    "mediabox": page.mediabox,
                }

                # Create PDFPage object
                pdf_page = PDFPage(
                    page_number=page_num + 1,  # 1-indexed
                    text=text,
                    images=images,
                    metadata=metadata,
                    layout=None
                )

                chunk.append(pdf_page)

            # Yield chunk
            chunk_num += 1
            logger.debug(f"Yielding chunk {chunk_num}: pages {start_page + 1}-{end_page}")
            yield chunk

            # Move to next chunk (with overlap)
            start_page += step_size

    finally:
        doc.close()
        logger.info(f"Finished chunking PDF: {file_path}")


def select_strategy(pdf_analysis: PDFAnalysis) -> ProcessingStrategy:
    """
    Select optimal processing strategy based on PDF analysis.

    Converts PDFAnalysis results into concrete ProcessingStrategy with
    execution parameters (chunk size, memory limit, time estimate).

    Args:
        pdf_analysis: PDFAnalysis object from assess_pdf()

    Returns:
        ProcessingStrategy with strategy type, chunk size, memory limit,
        and estimated processing time

    Example:
        >>> from assessment import assess_pdf
        >>> analysis = assess_pdf(Path("file.pdf"))
        >>> strategy = select_strategy(analysis)
        >>> print(f"Using {strategy.strategy_type} with {strategy.chunk_size} pages per chunk")
    """
    logger.info(f"Selecting strategy for: {pdf_analysis.recommended_strategy}")

    # Strategy parameters based on recommendation
    if pdf_analysis.recommended_strategy == "full_load":
        # Load entire PDF into memory
        chunk_size = pdf_analysis.page_count  # All pages at once
        memory_limit = pdf_analysis.estimated_memory * 2  # 2x file size buffer
        # Estimate: ~1 second per 10 pages for small PDFs
        estimated_time = max(1.0, pdf_analysis.page_count / 10.0)

    elif pdf_analysis.recommended_strategy == "stream_pages":
        # Process one page at a time
        chunk_size = 1  # Single page
        memory_limit = pdf_analysis.estimated_memory // pdf_analysis.page_count * 5  # ~5 pages in memory
        # Estimate: ~0.5 seconds per page
        estimated_time = pdf_analysis.page_count * 0.5

    else:  # chunk_batch
        # Process in multi-page chunks
        # Determine chunk size based on complexity
        if pdf_analysis.complexity_score > 70:
            chunk_size = 5  # Smaller chunks for complex PDFs
        else:
            chunk_size = 10  # Standard chunk size

        memory_limit = pdf_analysis.estimated_memory // pdf_analysis.page_count * (chunk_size + 5)
        # Estimate: ~0.3 seconds per page (faster due to batching)
        estimated_time = pdf_analysis.page_count * 0.3

    strategy = ProcessingStrategy(
        strategy_type=pdf_analysis.recommended_strategy,
        chunk_size=chunk_size,
        memory_limit=memory_limit,
        estimated_time=estimated_time
    )

    logger.info(
        f"Selected strategy: {strategy.strategy_type}, "
        f"chunk_size={strategy.chunk_size}, "
        f"memory_limit={strategy.memory_limit:,} bytes, "
        f"estimated_time={strategy.estimated_time:.1f}s"
    )

    return strategy
