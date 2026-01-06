"""
Large PDF Reader - Memory-efficient PDF processing library.

This package provides tools for processing large PDF files (100MB+, 1000+ pages)
with minimal memory usage and high performance.
"""

__version__ = "1.3.0"
__author__ = "Workspace Hub"

from . import utils
from . import logging_config
from . import assessment
from . import streaming
from . import extraction
from . import fallback
from . import main

# Import main API functions for convenient access
from .main import (
    process_large_pdf,
    extract_text_only,
    extract_pages_with_images,
    extract_pages_with_tables,
    extract_everything
)

__all__ = [
    "utils", "logging_config", "assessment", "streaming", "extraction", "fallback", "main",
    # Main API functions
    "process_large_pdf",
    "extract_text_only",
    "extract_pages_with_images",
    "extract_pages_with_tables",
    "extract_everything"
]
