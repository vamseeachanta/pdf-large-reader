"""
ABOUTME: Command-line interface for pdf-large-reader
ABOUTME: Provides CLI access to all main API functions with progress tracking
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from .main import (
    process_large_pdf,
    extract_text_only,
    extract_pages_with_images,
    extract_pages_with_tables,
    extract_everything
)
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='pdf-large-reader',
        description='Process large PDF files with memory-efficient strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all text to stdout
  pdf-large-reader document.pdf --output-format text

  # Extract pages with images to file
  pdf-large-reader document.pdf --extract-images --output results.txt

  # Use AI fallback for scanned PDFs
  pdf-large-reader scanned.pdf --fallback-api-key sk-... --output-format text

  # Extract everything with progress bar
  pdf-large-reader large.pdf --extract-images --extract-tables --verbose

  # Custom chunk size without auto-strategy
  pdf-large-reader huge.pdf --chunk-size 10 --no-auto-strategy
        """
    )

    # Required arguments
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to PDF file to process'
    )

    # Output options
    parser.add_argument(
        '--output-format',
        type=str,
        choices=['generator', 'list', 'text'],
        default='text',
        help='Output format (default: text)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path (default: stdout)'
    )

    # Extraction options
    parser.add_argument(
        '--extract-images',
        action='store_true',
        help='Extract images from pages'
    )

    parser.add_argument(
        '--extract-tables',
        action='store_true',
        help='Extract tables from pages'
    )

    # Processing options
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=None,
        help='Pages per chunk (default: auto-selected)'
    )

    parser.add_argument(
        '--no-auto-strategy',
        action='store_true',
        help='Disable automatic strategy selection'
    )

    # Fallback options
    parser.add_argument(
        '--fallback-api-key',
        type=str,
        default=None,
        help='OpenAI API key for fallback extraction'
    )

    parser.add_argument(
        '--fallback-model',
        type=str,
        default='gpt-4o',
        help='Model for fallback extraction (default: gpt-4o)'
    )

    # Logging options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress all output except errors'
    )

    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.3.0'
    )

    return parser


def setup_progress_callback(total_pages: int, verbose: bool):
    """
    Create progress callback function.

    Args:
        total_pages: Total number of pages
        verbose: Whether verbose mode is enabled

    Returns:
        Progress callback function or None
    """
    if not verbose or tqdm is None:
        return None

    # Create progress bar
    pbar = tqdm(total=total_pages, desc="Processing pages", unit="page")

    def progress_callback(current: int, total: int):
        """Update progress bar."""
        pbar.n = current
        pbar.refresh()

    return progress_callback


def format_output(result, output_format: str, extract_images: bool, extract_tables: bool) -> str:
    """
    Format result for output.

    Args:
        result: Processing result (generator, list, or text)
        output_format: Output format type
        extract_images: Whether images were extracted
        extract_tables: Whether tables were extracted

    Returns:
        Formatted output string
    """
    if output_format == 'text':
        # Already a string
        return result

    elif output_format == 'list':
        # Format list of pages
        output_lines = []

        for page in result:
            output_lines.append(f"=== Page {page.page_number} ===")
            output_lines.append(page.text)

            if extract_images and page.images:
                output_lines.append(f"\n[{len(page.images)} images extracted]")

            if extract_tables and page.metadata.get('tables'):
                tables = page.metadata['tables']
                output_lines.append(f"\n[{len(tables)} tables extracted]")

            output_lines.append("")  # Blank line between pages

        return "\n".join(output_lines)

    else:  # generator
        # Consume generator and format
        output_lines = []

        for page in result:
            output_lines.append(f"=== Page {page.page_number} ===")
            output_lines.append(page.text)

            if extract_images and page.images:
                output_lines.append(f"\n[{len(page.images)} images extracted]")

            if extract_tables and page.metadata.get('tables'):
                tables = page.metadata['tables']
                output_lines.append(f"\n[{len(tables)} tables extracted]")

            output_lines.append("")

        return "\n".join(output_lines)


def main(argv: Optional[list] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command-line arguments (default: sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    log_level = 'ERROR' if args.quiet else ('DEBUG' if args.verbose else 'INFO')
    setup_logging(level=log_level)

    try:
        # Validate PDF file
        pdf_path = Path(args.pdf_path)
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            return 1

        # Log processing start
        logger.info(f"Processing PDF: {pdf_path}")
        logger.info(f"Output format: {args.output_format}")

        if args.extract_images:
            logger.info("Image extraction: enabled")
        if args.extract_tables:
            logger.info("Table extraction: enabled")

        # Process PDF
        result = process_large_pdf(
            pdf_path=pdf_path,
            output_format=args.output_format,
            extract_images=args.extract_images,
            extract_tables=args.extract_tables,
            chunk_size=args.chunk_size,
            fallback_api_key=args.fallback_api_key,
            fallback_model=args.fallback_model,
            progress_callback=None,  # Progress handled separately
            auto_strategy=not args.no_auto_strategy
        )

        # Format output
        output_text = format_output(
            result,
            args.output_format,
            args.extract_images,
            args.extract_tables
        )

        # Write output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_text, encoding='utf-8')
            logger.info(f"Output written to: {output_path}")
        else:
            # Print to stdout (suppress if quiet mode)
            if not args.quiet:
                print(output_text)

        logger.info("Processing complete")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1

    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
