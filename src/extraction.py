"""
ABOUTME: PDF content extraction module for text, images, and tables
ABOUTME: Provides functions to extract various content types from PDF pages
"""

import io
import logging
from typing import List, Optional

import fitz  # PyMuPDF
import pandas as pd
from PIL import Image

from .streaming import PDFPage

logger = logging.getLogger(__name__)


def extract_text(page: fitz.Page, preserve_layout: bool = True) -> str:
    """
    Extract text from PDF page with optional layout preservation.

    Args:
        page: PyMuPDF page object
        preserve_layout: Maintain text positioning (default: True)

    Returns:
        Extracted text string

    Example:
        >>> doc = fitz.open("document.pdf")
        >>> page = doc[0]
        >>> text = extract_text(page, preserve_layout=True)
        >>> print(text)
        'Document content with preserved layout...'
    """
    logger.debug("Extracting text from page (preserve_layout=%s)", preserve_layout)

    if preserve_layout:
        # Extract text with layout preservation
        # "text" mode maintains spacing and formatting
        text = page.get_text("text")
    else:
        # Extract plain text without layout
        text = page.get_text()

    logger.debug("Extracted %d characters of text", len(text))
    return text


def extract_images(page: fitz.Page) -> List[Image.Image]:
    """
    Extract images from PDF page.

    Args:
        page: PyMuPDF page object

    Returns:
        List of PIL Image objects

    Example:
        >>> doc = fitz.open("document.pdf")
        >>> page = doc[0]
        >>> images = extract_images(page)
        >>> print(f"Found {len(images)} images")
    """
    logger.debug("Extracting images from page")

    images = []
    image_list = page.get_images(full=True)

    for img_index in image_list:
        try:
            xref = img_index[0]
            base_image = page.parent.extract_image(xref)
            image_bytes = base_image["image"]

            # Convert to PIL Image
            pil_image = Image.open(io.BytesIO(image_bytes))
            images.append(pil_image)

            logger.debug("Extracted image: %dx%d", pil_image.width, pil_image.height)

        except Exception as e:
            logger.warning("Failed to extract image: %s", e)
            continue

    logger.info("Extracted %d images from page", len(images))
    return images


def extract_tables(page: fitz.Page) -> List[pd.DataFrame]:
    """
    Extract tables from PDF page as DataFrames.

    Args:
        page: PyMuPDF page object

    Returns:
        List of pandas DataFrames representing tables

    Note:
        This is a basic implementation that attempts to detect table-like
        structures from text positioning. For complex tables, consider
        using specialized libraries like camelot or tabula.

    Example:
        >>> doc = fitz.open("report.pdf")
        >>> page = doc[0]
        >>> tables = extract_tables(page)
        >>> for i, table in enumerate(tables):
        ...     print(f"Table {i}: {table.shape}")
    """
    logger.debug("Extracting tables from page")

    tables = []

    # Get text blocks with position information
    # dict mode provides position and formatting details
    blocks = page.get_text("dict")["blocks"]

    # Simple table detection based on text block alignment
    # This is a basic implementation - production code might use
    # more sophisticated libraries like camelot or tabula

    # Look for blocks with regular vertical/horizontal alignment
    text_blocks = [b for b in blocks if b.get("type") == 0]  # 0 = text block

    if len(text_blocks) < 4:
        # Too few blocks to form a table
        logger.debug("Not enough text blocks for table detection")
        return tables

    # Group blocks by similar y-coordinates (rows)
    rows_dict = {}
    y_tolerance = 5  # pixels

    for block in text_blocks:
        bbox = block.get("bbox", [0, 0, 0, 0])
        y_coord = bbox[1]  # top y coordinate

        # Find existing row with similar y-coordinate
        found_row = False
        for existing_y in rows_dict.keys():
            if abs(y_coord - existing_y) < y_tolerance:
                rows_dict[existing_y].append(block)
                found_row = True
                break

        if not found_row:
            rows_dict[y_coord] = [block]

    # Check if we have a table-like structure
    # (at least 2 rows with 2+ columns each)
    table_rows = [blocks for blocks in rows_dict.values() if len(blocks) >= 2]

    if len(table_rows) >= 2:
        # Create DataFrame from detected table
        data = []
        for row_blocks in sorted(table_rows, key=lambda x: x[0]["bbox"][1]):
            # Sort blocks in row by x-coordinate (left to right)
            sorted_blocks = sorted(row_blocks, key=lambda x: x["bbox"][0])

            # Extract text from each block
            row_data = []
            for block in sorted_blocks:
                # Get text from block
                text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                row_data.append(text.strip())

            data.append(row_data)

        if data:
            # Normalize column counts across all rows
            # Get the maximum number of columns
            max_cols = max(len(row) for row in data)

            # Pad all rows to have the same number of columns
            normalized_data = []
            for row in data:
                if len(row) < max_cols:
                    # Pad with empty strings
                    row = row + [''] * (max_cols - len(row))
                elif len(row) > max_cols:
                    # Truncate (shouldn't happen given max_cols logic, but for safety)
                    row = row[:max_cols]
                normalized_data.append(row)

            try:
                # Create DataFrame with normalized data
                # Use first row as header
                df = pd.DataFrame(normalized_data[1:], columns=normalized_data[0])
                tables.append(df)
                logger.info("Detected table with shape %s", df.shape)
            except Exception as e:
                logger.warning("Failed to create DataFrame from table: %s", e)
                # Skip this table rather than failing entirely

    logger.info("Extracted %d tables from page", len(tables))
    return tables


def extract_page_full(
    page: fitz.Page,
    extract_images_flag: bool = True,
    extract_tables_flag: bool = False
) -> PDFPage:
    """
    Complete page extraction with all content types.

    Args:
        page: PyMuPDF page object
        extract_images_flag: Extract images from page (default: True)
        extract_tables_flag: Extract tables as DataFrames (default: False)

    Returns:
        PDFPage object with text, images, tables, and metadata

    Example:
        >>> doc = fitz.open("document.pdf")
        >>> page = doc[0]
        >>> pdf_page = extract_page_full(page, extract_images=True, extract_tables=True)
        >>> print(f"Text length: {len(pdf_page.text)}")
        >>> print(f"Images: {len(pdf_page.images)}")
        >>> print(f"Tables: {len(pdf_page.metadata.get('tables', []))}")
    """
    logger.debug("Performing full extraction for page")

    # Extract text (always with layout preservation)
    text = extract_text(page, preserve_layout=True)

    # Extract images if requested
    images = []
    if extract_images_flag:
        images = extract_images(page)

    # Extract tables if requested
    tables = []
    if extract_tables_flag:
        tables = extract_tables(page)

    # Get page metadata
    metadata = {
        "width": page.rect.width,
        "height": page.rect.height,
        "rotation": page.rotation,
        "mediabox": page.mediabox,
    }

    # Add tables to metadata if any were extracted
    if tables:
        metadata["tables"] = tables

    # Create PDFPage object
    pdf_page = PDFPage(
        page_number=page.number + 1,  # 1-indexed
        text=text,
        images=images,
        metadata=metadata,
        layout=None  # Layout information can be added in future enhancement
    )

    logger.info(
        "Full extraction complete: %d chars, %d images, %d tables",
        len(text),
        len(images),
        len(tables)
    )

    return pdf_page
