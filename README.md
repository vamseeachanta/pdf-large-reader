# pdf-large-reader

**Memory-efficient PDF processing library for large files (100MB+, 1000+ pages)**

A Python library designed to handle large PDF files with intelligent memory management, streaming capabilities, and automatic strategy selection. Built for production use with comprehensive test coverage (93.58%) and robust error handling.

## Features

- ✅ **Memory-Efficient Processing**: Handles 100MB+ PDFs without memory issues
- ✅ **Multiple Output Formats**: Generator (streaming), List, or Plain Text
- ✅ **Automatic Strategy Selection**: Intelligent chunk size calculation based on file characteristics
- ✅ **Complete Extraction**: Text, images, tables, and metadata
- ✅ **CLI Tool**: Command-line interface for quick PDF processing
- ✅ **Progress Tracking**: Built-in progress callbacks for long operations
- ✅ **AI Fallback**: Claude integration for complex extraction (optional)
- ✅ **Comprehensive Testing**: 215 tests with 93.58% coverage

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/workspace-hub/pdf-large-reader.git
cd pdf-large-reader

# Install in development mode
pip install -e .

# Or install with extras
pip install -e ".[dev,progress]"
```

### Requirements

- Python 3.8+
- PyMuPDF (fitz)
- Pillow (for image handling)

## Quick Start

### Python API

```python
from pdf_large_reader import process_large_pdf, extract_text_only

# Simple text extraction
text = extract_text_only("large_document.pdf")
print(text)

# Process with automatic strategy selection
pages = process_large_pdf(
    "large_document.pdf",
    output_format="list",
    extract_images=True,
    extract_tables=True
)

# Memory-efficient streaming for very large files
for page in process_large_pdf("huge_file.pdf", output_format="generator"):
    print(f"Page {page.page_number}: {len(page.text)} characters")
```

### Command Line

```bash
# Extract text from PDF
pdf-large-reader document.pdf

# Save to file
pdf-large-reader document.pdf --output result.txt

# Extract with images and tables
pdf-large-reader document.pdf --extract-images --extract-tables

# Use generator format for large files
pdf-large-reader huge.pdf --output-format generator

# Verbose output
pdf-large-reader document.pdf --verbose

# Quiet mode (errors only)
pdf-large-reader document.pdf --quiet
```

## Usage Examples

### Example 1: Simple Text Extraction

```python
from pdf_large_reader import extract_text_only

# Extract all text from PDF
text = extract_text_only("document.pdf")
print(text)
```

### Example 2: Extract Everything

```python
from pdf_large_reader import extract_everything

# Extract text, images, tables, and metadata
pages = extract_everything("document.pdf")

for page in pages:
    print(f"Page {page.page_number}")
    print(f"Text: {page.text[:100]}...")
    print(f"Images: {len(page.images)}")
    print(f"Metadata: {page.metadata}")
```

### Example 3: Memory-Efficient Processing

```python
from pdf_large_reader import process_large_pdf

# Process 1000-page PDF with generator (memory-efficient)
generator = process_large_pdf(
    "huge_document.pdf",
    output_format="generator",
    chunk_size=10
)

# Process one chunk at a time
for page in generator:
    # Your processing logic here
    analyze_page(page)
    # Memory is freed after each iteration
```

### Example 4: Custom Configuration

```python
from pdf_large_reader import process_large_pdf

# Manual configuration for specific requirements
pages = process_large_pdf(
    "document.pdf",
    output_format="list",
    chunk_size=20,
    auto_strategy=False,
    extract_images=True,
    extract_tables=True
)
```

### Example 5: Progress Tracking

```python
from pdf_large_reader import process_large_pdf

def progress_callback(current: int, total: int):
    percent = (current / total) * 100
    print(f"Progress: {current}/{total} ({percent:.1f}%)")

# Process with progress updates
text = process_large_pdf(
    "large_document.pdf",
    output_format="text",
    progress_callback=progress_callback
)
```

### Example 6: AI Fallback for Complex Pages

```python
from pdf_large_reader import process_large_pdf

# Use Claude for complex text extraction when standard methods fail
pages = process_large_pdf(
    "scanned_document.pdf",
    output_format="list",
    fallback_api_key="your_claude_api_key",
    fallback_model="claude-3-sonnet-20240229"
)
```

## API Reference

### Main Functions

#### `process_large_pdf(pdf_path, **options) -> Union[str, List[PDFPage], Generator]`

Main entry point for PDF processing with automatic strategy selection.

**Parameters:**
- `pdf_path` (str | Path): Path to PDF file
- `output_format` (str): Output format - "text", "list", or "generator" (default: "text")
- `chunk_size` (int): Pages per chunk (default: auto-calculated)
- `auto_strategy` (bool): Enable automatic strategy selection (default: True)
- `extract_images` (bool): Extract images (default: False)
- `extract_tables` (bool): Extract tables (default: False)
- `fallback_api_key` (str): Claude API key for fallback (optional)
- `fallback_model` (str): Claude model name (default: "claude-3-sonnet-20240229")
- `progress_callback` (Callable): Progress callback function (optional)

**Returns:**
- str: Complete text (if output_format="text")
- List[PDFPage]: List of page objects (if output_format="list")
- Generator[PDFPage]: Page generator (if output_format="generator")

**Example:**
```python
pages = process_large_pdf(
    "document.pdf",
    output_format="list",
    chunk_size=10,
    extract_images=True
)
```

#### `extract_text_only(pdf_path) -> str`

Extract text from PDF using the most efficient method.

**Parameters:**
- `pdf_path` (str | Path): Path to PDF file

**Returns:**
- str: Extracted text from all pages

**Example:**
```python
text = extract_text_only("document.pdf")
```

#### `extract_pages_with_images(pdf_path) -> List[PDFPage]`

Extract pages with images included.

**Parameters:**
- `pdf_path` (str | Path): Path to PDF file

**Returns:**
- List[PDFPage]: Pages with images

**Example:**
```python
pages = extract_pages_with_images("document.pdf")
for page in pages:
    print(f"Page {page.page_number} has {len(page.images)} images")
```

#### `extract_pages_with_tables(pdf_path) -> List[PDFPage]`

Extract pages with table detection.

**Parameters:**
- `pdf_path` (str | Path): Path to PDF file

**Returns:**
- List[PDFPage]: Pages with table metadata

**Example:**
```python
pages = extract_pages_with_tables("document.pdf")
```

#### `extract_everything(pdf_path) -> List[PDFPage]`

Extract text, images, tables, and metadata from PDF.

**Parameters:**
- `pdf_path` (str | Path): Path to PDF file

**Returns:**
- List[PDFPage]: Complete page objects with all extracted data

**Example:**
```python
pages = extract_everything("document.pdf")
```

### PDFPage Data Class

```python
@dataclass
class PDFPage:
    page_number: int
    text: str
    images: List[dict]
    metadata: dict
```

**Attributes:**
- `page_number` (int): Page number (1-indexed)
- `text` (str): Extracted text from page
- `images` (List[dict]): Extracted images with metadata
- `metadata` (dict): Page metadata (dimensions, fonts, etc.)

## CLI Reference

### Basic Usage

```bash
pdf-large-reader <input.pdf> [OPTIONS]
```

### Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--output` | `-o` | Output file path | stdout |
| `--output-format` | | Output format: text, list, generator | text |
| `--extract-images` | | Extract images from PDF | False |
| `--extract-tables` | | Extract tables from PDF | False |
| `--chunk-size` | | Pages per chunk | auto |
| `--no-auto-strategy` | | Disable automatic strategy | False |
| `--verbose` | `-v` | Verbose output | False |
| `--quiet` | `-q` | Quiet mode (errors only) | False |
| `--version` | | Show version | |
| `--help` | `-h` | Show help message | |

### CLI Examples

```bash
# Basic extraction
pdf-large-reader document.pdf

# Save to file
pdf-large-reader document.pdf -o output.txt

# Extract with images and tables
pdf-large-reader document.pdf --extract-images --extract-tables -o result.txt

# Process large file with manual chunk size
pdf-large-reader huge.pdf --chunk-size 5 --output-format generator

# Verbose mode
pdf-large-reader document.pdf -v

# Quiet mode
pdf-large-reader document.pdf -q -o result.txt
```

## Architecture

### Component Overview

```
src/
├── assessment.py      # PDF analysis and strategy selection
├── streaming.py       # Memory-efficient streaming
├── extraction.py      # Text, image, table extraction
├── fallback.py        # Claude AI fallback for complex pages
├── utils.py           # Progress tracking, memory monitoring
├── main.py            # Main API entry point
├── cli.py             # Command-line interface
└── logging_config.py  # Logging configuration
```

### Processing Pipeline

1. **Assessment**: Analyze PDF characteristics (size, pages, complexity)
2. **Strategy Selection**: Choose optimal processing method (stream vs. batch)
3. **Extraction**: Extract text, images, tables based on configuration
4. **Output**: Return results in specified format (text/list/generator)

### Strategy Selection

The library automatically selects the best processing strategy based on:
- File size (bytes)
- Page count
- Estimated memory usage
- Page complexity (fonts, images, etc.)

**Strategies:**
- `stream_pages`: Process one page at a time (large files)
- `batch_all`: Load all pages at once (small files)
- `chunked`: Process in chunks (medium files)

## Performance

### Benchmarks

Tested on Ubuntu 22.04, Python 3.11, 16GB RAM:

| File Size | Pages | Time | Memory | Strategy |
|-----------|-------|------|--------|----------|
| 5 MB | 10 | < 5s | ~50 MB | batch_all |
| 50 MB | 100 | < 30s | ~150 MB | chunked |
| 100 MB | 500 | < 60s | ~200 MB | stream_pages |
| 200 MB | 1000 | < 2min | ~250 MB | stream_pages |

### Memory Efficiency

- **Generator mode**: Processes 1000-page PDFs with < 300 MB RAM
- **Chunked processing**: Reduces peak memory by 50-70%
- **Automatic cleanup**: Frees memory after each chunk

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_extraction.py -v
```

### Test Coverage

- **Total Coverage**: 93.58%
- **Total Tests**: 215 (170 unit + 45 integration)
- **Modules**:
  - extraction.py: 100%
  - utils.py: 98%
  - assessment.py: 96%
  - fallback.py: 96%
  - main.py: 94%
  - streaming.py: 91%

### Development Installation

```bash
# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run linter
flake8 src/ tests/

# Run type checker
mypy src/
```

## Troubleshooting

### Common Issues

**Issue**: "FileNotFoundError: PDF file not found"
```python
# Solution: Use absolute paths or verify file exists
from pathlib import Path
pdf_path = Path("document.pdf").absolute()
```

**Issue**: Memory error with very large PDFs
```python
# Solution: Use generator mode with smaller chunks
for page in process_large_pdf("huge.pdf", output_format="generator", chunk_size=1):
    process_page(page)
```

**Issue**: No text extracted from scanned PDFs
```python
# Solution: Use AI fallback (requires Claude API key)
pages = process_large_pdf(
    "scanned.pdf",
    fallback_api_key="your_api_key"
)
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Changelog

### Version 1.3.0 (Current)
- ✅ Complete test suite (215 tests, 93.58% coverage)
- ✅ Integration tests for end-to-end workflows
- ✅ Performance tests for large files
- ✅ CLI integration tests
- ✅ Comprehensive documentation

### Version 1.2.0
- ✅ CLI tool with argparse
- ✅ Progress callback support
- ✅ Multiple output formats

### Version 1.1.0
- ✅ AI fallback integration
- ✅ Image extraction
- ✅ Table detection

### Version 1.0.0
- ✅ Initial release
- ✅ Memory-efficient streaming
- ✅ Automatic strategy selection
- ✅ Text extraction

## Support

- **Documentation**: [README.md](README.md) (this file)
- **Issues**: [GitHub Issues](https://github.com/workspace-hub/pdf-large-reader/issues)
- **Tests**: See `tests/` directory for comprehensive examples

---

**Built with ❤️ for handling large PDF files efficiently**
