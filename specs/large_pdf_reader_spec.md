# Large PDF Reader - Technical Specification

> Version: 1.0.0
> Created: 2026-01-04
> Target: PDF Skill v1.3.0

## Executive Summary

Memory-efficient solution for processing large PDF files (100MB+, 1000+ pages) that integrates with existing PDF skill v1.2.2. Uses streaming, chunking, and intelligent fallback strategies to maintain ≤512MB RAM usage while processing files in <5 minutes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Large PDF Reader v1.3.0                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Assessment  │───▶│  Streaming   │───▶│ Extraction   │  │
│  │    Module    │    │    Module    │    │   Module     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Utilities Module                        │  │
│  │  (Progress, Memory Monitor, Error Recovery)          │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│                  ┌─────────────────┐                        │
│                  │ Fallback Module │                        │
│                  │ (OpenAI Codex)  │                        │
│                  │ (Use < 1%)      │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Module Specifications

### 1. Assessment Module (`src/assessment.py`)

**Purpose**: Analyze PDF structure and estimate processing requirements without loading into memory.

**Key Functions**:

```python
def assess_pdf(file_path: Path) -> PDFAnalysis:
    """
    Analyze PDF file and determine optimal processing strategy.

    Args:
        file_path: Path to PDF file

    Returns:
        PDFAnalysis object with:
        - file_size: Size in bytes
        - page_count: Number of pages
        - estimated_memory: RAM estimate for processing
        - complexity_score: 0-100 (higher = more complex)
        - recommended_strategy: 'full_load' | 'stream_pages' | 'chunk_batch'
        - issues: List[str] (corruption, encryption, etc.)
    """

def estimate_memory_usage(file_path: Path) -> MemoryEstimate:
    """
    Estimate memory requirements for processing.

    Returns:
        MemoryEstimate with:
        - min_memory: Minimum RAM needed
        - recommended_memory: Recommended RAM
        - peak_memory: Peak usage estimate
    """

def detect_pdf_issues(file_path: Path) -> List[PDFIssue]:
    """
    Detect potential processing issues.

    Returns:
        List of issues (encryption, corruption, missing fonts, etc.)
    """
```

**Data Structures**:

```python
@dataclass
class PDFAnalysis:
    file_size: int
    page_count: int
    estimated_memory: int
    complexity_score: float
    recommended_strategy: str
    issues: List[str]
    metadata: Dict[str, Any]

@dataclass
class MemoryEstimate:
    min_memory: int
    recommended_memory: int
    peak_memory: int
    per_page_avg: int
```

### 2. Streaming Module (`src/streaming.py`)

**Purpose**: Stream PDF pages efficiently without loading entire file into memory.

**Key Functions**:

```python
def stream_pdf_pages(
    file_path: Path,
    chunk_size: int = 1,
    progress_callback: Optional[Callable] = None
) -> Iterator[PDFPage]:
    """
    Stream PDF pages one at a time or in small chunks.

    Args:
        file_path: Path to PDF file
        chunk_size: Number of pages per chunk (default: 1)
        progress_callback: Optional progress update function

    Yields:
        PDFPage objects with text, images, metadata
    """

def chunk_pdf(
    file_path: Path,
    chunk_pages: int = 10,
    overlap: int = 0
) -> Iterator[List[PDFPage]]:
    """
    Process PDF in multi-page chunks with optional overlap.

    Args:
        file_path: Path to PDF file
        chunk_pages: Pages per chunk
        overlap: Overlap pages between chunks

    Yields:
        Lists of PDFPage objects
    """

def select_strategy(pdf_analysis: PDFAnalysis) -> ProcessingStrategy:
    """
    Select optimal processing strategy based on PDF analysis.

    Returns:
        ProcessingStrategy with:
        - strategy_type: 'full_load' | 'stream_pages' | 'chunk_batch'
        - chunk_size: Pages per chunk (if applicable)
        - memory_limit: RAM limit for operation
    """
```

**Processing Strategies**:

| Strategy | Trigger | Chunk Size | Memory Usage | Speed |
|----------|---------|------------|--------------|-------|
| **full_load** | < 10MB | All pages | ~2x file size | Fastest |
| **stream_pages** | 10-100MB | 1 page | ~5MB/page | Fast |
| **chunk_batch** | ≥ 100MB | 5-10 pages | ~25-50MB/chunk | Moderate |

**Data Structures**:

```python
@dataclass
class PDFPage:
    page_number: int
    text: str
    images: List[Image.Image]
    metadata: Dict[str, Any]
    layout: Optional[Dict]

@dataclass
class ProcessingStrategy:
    strategy_type: str
    chunk_size: int
    memory_limit: int
    estimated_time: float
```

### 3. Extraction Module (`src/extraction.py`)

**Purpose**: Extract text, images, and tables from PDF pages with layout preservation.

**Key Functions**:

```python
def extract_text(page: fitz.Page, preserve_layout: bool = True) -> str:
    """
    Extract text from PDF page with optional layout preservation.

    Args:
        page: PyMuPDF page object
        preserve_layout: Maintain text positioning

    Returns:
        Extracted text string
    """

def extract_images(page: fitz.Page) -> List[Image.Image]:
    """
    Extract images from PDF page.

    Returns:
        List of PIL Image objects
    """

def extract_tables(page: fitz.Page) -> List[pd.DataFrame]:
    """
    Extract tables from PDF page as DataFrames.

    Returns:
        List of pandas DataFrames
    """

def extract_page_full(
    page: fitz.Page,
    extract_images: bool = True,
    extract_tables: bool = False
) -> PDFPage:
    """
    Complete page extraction with all content types.

    Returns:
        PDFPage object with text, images, tables, metadata
    """
```

### 4. Fallback Module (`src/fallback.py`)

**Purpose**: Handle complex layouts using OpenAI Codex when necessary (target: <1% usage).

**Key Functions**:

```python
def should_use_fallback(page: fitz.Page, complexity_score: float) -> bool:
    """
    Determine if fallback AI processing is needed.

    Args:
        page: PyMuPDF page object
        complexity_score: Page complexity (0-100)

    Returns:
        True if fallback needed, False otherwise

    Criteria:
    - Scanned PDF without OCR
    - Complex multi-column layouts
    - Heavy use of custom fonts
    - Complexity score > 85
    """

def extract_with_codex(
    page: fitz.Page,
    api_key: str,
    model: str = "gpt-4o"
) -> str:
    """
    Extract content using OpenAI Codex API.

    Args:
        page: PyMuPDF page object
        api_key: OpenAI API key
        model: Model to use

    Returns:
        Extracted text from Codex

    Usage tracking:
    - Logs each usage
    - Reports % of pages using fallback
    - Target: < 1% of total pages
    """

def extract_with_chrome(page_image: bytes) -> str:
    """
    Extract content using Chrome Claude extension (last resort).

    Args:
        page_image: Page rendered as image bytes

    Returns:
        Extracted text from Claude extension
    """
```

**Fallback Decision Tree**:

```
Page → Assess Complexity → Score < 85? → Use PyMuPDF
                              ↓ No
                         Scanned PDF? → Yes → Use Codex OCR
                              ↓ No
                      Complex Layout? → Yes → Use Codex
                              ↓ No
                         Use PyMuPDF
```

### 5. Utilities Module (`src/utils.py`)

**Purpose**: Progress tracking, memory monitoring, and error recovery.

**Key Functions**:

```python
def track_progress(
    total: int,
    desc: str = "Processing"
) -> tqdm:
    """
    Create progress bar for long operations.

    Args:
        total: Total items to process
        desc: Progress bar description

    Returns:
        tqdm progress bar object
    """

def monitor_memory() -> MemoryStats:
    """
    Monitor current memory usage.

    Returns:
        MemoryStats with:
        - current_mb: Current RAM usage
        - peak_mb: Peak RAM usage
        - available_mb: Available RAM
        - percent_used: Percentage used
    """

def handle_error(
    error: Exception,
    context: str,
    critical: bool = False
) -> ErrorResponse:
    """
    Handle errors with logging and recovery.

    Args:
        error: Exception raised
        context: Error context description
        critical: Whether error is critical

    Returns:
        ErrorResponse with:
        - should_continue: Whether to continue processing
        - error_message: Logged error message
        - recovery_action: Suggested recovery
    """

def log_operation(
    operation: str,
    file_path: Path,
    duration: float,
    memory_used: int
) -> None:
    """
    Log operation metrics for performance tracking.
    """
```

**Data Structures**:

```python
@dataclass
class MemoryStats:
    current_mb: float
    peak_mb: float
    available_mb: float
    percent_used: float

@dataclass
class ErrorResponse:
    should_continue: bool
    error_message: str
    recovery_action: str
```

## Main Module API (`src/large_pdf_reader.py`)

**Public Functions**:

```python
def process_large_pdf(
    file_path: Path,
    output_dir: Path,
    preserve_layout: bool = True,
    extract_images: bool = True,
    extract_tables: bool = False,
    use_fallback: bool = True,
    max_memory_mb: int = 512
) -> ProcessingResult:
    """
    Process large PDF file with automatic strategy selection.

    Args:
        file_path: Path to PDF file
        output_dir: Output directory for results
        preserve_layout: Maintain text layout
        extract_images: Extract images from PDF
        extract_tables: Extract tables as DataFrames
        use_fallback: Allow OpenAI Codex fallback
        max_memory_mb: Maximum RAM usage allowed

    Returns:
        ProcessingResult with:
        - success: bool
        - output_files: List[Path]
        - pages_processed: int
        - fallback_used: int (count)
        - processing_time: float
        - memory_peak: float
    """

def stream_pdf_pages(file_path: Path, **kwargs) -> Iterator[PDFPage]:
    """Exposed streaming function for custom processing."""

def chunk_pdf(file_path: Path, **kwargs) -> Iterator[List[PDFPage]]:
    """Exposed chunking function for batch processing."""
```

## CLI Tool (`pdf-large-reader`)

**Usage**:

```bash
# Process single PDF
pdf-large-reader input.pdf --output ./output/

# Batch processing
pdf-large-reader *.pdf --output ./batch_output/ --parallel 4

# With options
pdf-large-reader large.pdf \
    --output ./results/ \
    --max-memory 512 \
    --no-fallback \
    --extract-images \
    --progress

# Resume interrupted processing
pdf-large-reader input.pdf --resume checkpoint.pkl
```

**CLI Arguments**:

```
positional arguments:
  files                 PDF file(s) to process

options:
  -o, --output DIR      Output directory (default: ./output)
  --max-memory MB       Max RAM usage in MB (default: 512)
  --no-fallback         Disable OpenAI Codex fallback
  --extract-images      Extract images from PDF
  --extract-tables      Extract tables as CSV
  --preserve-layout     Preserve text layout
  --parallel N          Parallel processing (batch mode)
  --progress            Show progress bars
  --resume FILE         Resume from checkpoint
  --verbose             Verbose logging
```

## Performance Requirements

### Memory Constraints

| PDF Size | Strategy | Target Memory | Actual Limit |
|----------|----------|---------------|--------------|
| < 10MB | Full load | ~20MB | 512MB |
| 10-50MB | Stream pages | ~5MB/page | 512MB |
| 50-100MB | Stream pages | ~5MB/page | 512MB |
| 100MB+ | Chunk batch | ~50MB/chunk | 512MB |

### Processing Speed

| Metric | Target | Measurement |
|--------|--------|-------------|
| 1000-page PDF | < 5 minutes | Total processing time |
| Page processing | < 0.3 sec/page | Average per page |
| Memory overhead | < 50MB | Base memory usage |
| Fallback usage | < 1% | % of pages using Codex |

### Error Recovery

- **Never crash** - All errors handled gracefully
- **Continue on page errors** - Skip problematic pages, continue processing
- **Checkpoint support** - Resume interrupted processing
- **Detailed logging** - All errors logged with context

## Integration with PDF Skill v1.2.2

### Backward Compatibility

Existing PDF skill functions remain unchanged:
- `pdf_to_text()` - Still works for small PDFs
- `batch_pdf_to_markdown()` - Uses Codex for batch processing
- `pdf_to_markdown_codex()` - Codex integration unchanged

### New Functions Added (v1.3.0)

```python
# In ~/.claude/skills/document-handling/pdf/SKILL.md

def process_large_pdf(file_path: str, **kwargs) -> Dict:
    """Process large PDF efficiently (new in v1.3.0)."""
    from large_pdf_reader import process_large_pdf
    return process_large_pdf(Path(file_path), **kwargs)

def stream_pdf_pages_skill(file_path: str, **kwargs) -> Iterator:
    """Stream PDF pages for custom processing (new in v1.3.0)."""
    from large_pdf_reader import stream_pdf_pages
    return stream_pdf_pages(Path(file_path), **kwargs)
```

### Usage in Skill

```python
# Small PDFs (< 10MB) - use existing functions
text = pdf_to_text("small_document.pdf")

# Large PDFs (100MB+) - use new functions
result = process_large_pdf(
    "large_report.pdf",
    output_dir="./output",
    max_memory_mb=512
)

# Streaming for custom processing
for page in stream_pdf_pages_skill("massive.pdf"):
    # Custom page processing
    process_page(page)
```

## Testing Strategy

### Unit Tests (Target: 90% coverage)

```
tests/unit/
├── test_assessment.py     # PDF analysis functions
├── test_streaming.py      # Streaming and chunking
├── test_extraction.py     # Content extraction
├── test_fallback.py       # Codex integration
└── test_utils.py          # Utilities
```

### Integration Tests

```
tests/integration/
├── test_end_to_end.py     # Full pipeline tests
├── test_large_files.py    # Tests with 100MB+ PDFs
└── test_error_recovery.py # Error handling
```

### Performance Tests

```
tests/performance/
├── test_memory_limits.py  # Verify ≤512MB usage
├── test_processing_speed.py # Verify <5min for 1000 pages
└── test_fallback_usage.py # Verify <1% Codex usage
```

### Test Data

```
tests/fixtures/
├── small.pdf              # 1MB, 10 pages
├── medium.pdf             # 25MB, 250 pages
├── large.pdf              # 100MB, 1000 pages
├── corrupted.pdf          # Test error handling
└── scanned.pdf            # Test fallback
```

## Logging and Monitoring

### Log Levels

```python
import logging

# DEBUG: Detailed progress, page-by-page processing
logger.debug("Processing page %d/%d", page_num, total_pages)

# INFO: Major milestones, strategy selection
logger.info("Selected strategy: %s", strategy_type)

# WARNING: Fallback usage, memory warnings
logger.warning("Using Codex fallback for page %d", page_num)

# ERROR: Processing errors, but continue
logger.error("Failed to extract page %d: %s", page_num, error)

# CRITICAL: Fatal errors, cannot continue
logger.critical("Out of memory, aborting")
```

### Metrics Collection

```python
metrics = {
    "total_pages": 1000,
    "pages_processed": 1000,
    "pages_fallback": 8,      # 0.8% - meets <1% target
    "processing_time_sec": 287,  # 4.78 minutes - meets <5min target
    "memory_peak_mb": 487,    # Meets ≤512MB target
    "errors": 0
}
```

## Deployment

### Installation

```bash
# Install in PDF skill directory
cd ~/.claude/skills/document-handling/pdf/
git clone <repo> large_pdf_reader/
cd large_pdf_reader/
pip install -r requirements.txt

# Or use UV
uv pip install -r requirements.txt
```

### Configuration

```python
# config.yaml
large_pdf_reader:
  max_memory_mb: 512
  fallback_enabled: true
  openai_api_key: ${OPENAI_API_KEY}
  fallback_model: "gpt-4o"
  log_level: "INFO"
  checkpoint_dir: "./checkpoints"
```

## Success Criteria Validation

| Requirement | Target | Validation Method |
|-------------|--------|-------------------|
| Memory usage | ≤ 512MB | `psutil` monitoring in tests |
| Processing speed | < 5 min / 1000 pages | Performance tests with timer |
| Error recovery | 100% (never crash) | Try/except all operations |
| Fallback usage | < 1% | Count Codex API calls |
| Integration | Backward compatible | All existing tests pass |
| Test coverage | 85%+ | pytest-cov report |

---

**End of Technical Specification**
