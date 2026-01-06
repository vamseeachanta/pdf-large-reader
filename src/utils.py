"""
ABOUTME: Utility functions for large PDF reader
ABOUTME: Provides progress tracking, memory monitoring, error handling, and logging
"""

import logging
import psutil
import time
from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict
from pathlib import Path
from tqdm import tqdm

# Setup module logger
logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    current_mb: float
    peak_mb: float
    available_mb: float
    percent_used: float
    timestamp: float


@dataclass
class ErrorResponse:
    """Error handling response."""
    error_type: str
    error_message: str
    is_critical: bool
    should_continue: bool
    recovery_suggestion: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ProgressTracker:
    """Progress tracking with tqdm."""

    def __init__(
        self,
        total: int,
        description: str = "Processing",
        unit: str = "pages",
        disable: bool = False
    ):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
            description: Description shown in progress bar
            unit: Unit name for items (e.g., "pages", "files")
            disable: Disable progress bar if True
        """
        self.total = total
        self.description = description
        self.unit = unit
        self.disable = disable
        self._pbar: Optional[tqdm] = None
        self._start_time: Optional[float] = None

    def __enter__(self):
        """Context manager entry."""
        self._start_time = time.time()
        self._pbar = tqdm(
            total=self.total,
            desc=self.description,
            unit=self.unit,
            disable=self.disable,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._pbar:
            self._pbar.close()
        return False

    def update(self, n: int = 1, description: Optional[str] = None):
        """
        Update progress bar.

        Args:
            n: Number of items completed
            description: Optional new description
        """
        if self._pbar:
            if description:
                self._pbar.set_description(description)
            self._pbar.update(n)

    def set_postfix(self, **kwargs):
        """Set postfix values (e.g., current_file='example.pdf')."""
        if self._pbar:
            self._pbar.set_postfix(**kwargs)

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time:
            return time.time() - self._start_time
        return 0.0


def track_progress(
    total: int,
    description: str = "Processing",
    unit: str = "pages",
    disable: bool = False
) -> ProgressTracker:
    """
    Create a progress tracker context manager.

    Args:
        total: Total number of items to process
        description: Description shown in progress bar
        unit: Unit name for items
        disable: Disable progress bar if True

    Returns:
        ProgressTracker instance for use with 'with' statement

    Example:
        with track_progress(100, "Processing pages") as progress:
            for i in range(100):
                # Do work
                progress.update(1)
    """
    return ProgressTracker(total, description, unit, disable)


def monitor_memory() -> MemoryStats:
    """
    Monitor current memory usage.

    Returns:
        MemoryStats object with current memory information

    Example:
        stats = monitor_memory()
        if stats.percent_used > 80:
            logger.warning("High memory usage: %.1f%%", stats.percent_used)
    """
    process = psutil.Process()
    memory_info = process.memory_info()
    virtual_memory = psutil.virtual_memory()

    current_mb = memory_info.rss / 1024 / 1024
    available_mb = virtual_memory.available / 1024 / 1024
    percent_used = virtual_memory.percent

    # Track peak memory (stored as process attribute)
    if not hasattr(process, '_peak_memory_mb'):
        process._peak_memory_mb = current_mb
    else:
        process._peak_memory_mb = max(process._peak_memory_mb, current_mb)

    return MemoryStats(
        current_mb=current_mb,
        peak_mb=process._peak_memory_mb,
        available_mb=available_mb,
        percent_used=percent_used,
        timestamp=time.time()
    )


def handle_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    is_critical: bool = False
) -> ErrorResponse:
    """
    Handle errors with logging and recovery suggestions.

    Args:
        error: The exception that occurred
        context: Additional context information
        is_critical: Whether this is a critical error that should stop processing

    Returns:
        ErrorResponse with error details and recovery suggestion

    Example:
        try:
            process_pdf(file_path)
        except FileNotFoundError as e:
            response = handle_error(e, context={"file": file_path})
            if not response.should_continue:
                raise
    """
    error_type = type(error).__name__
    error_message = str(error)

    # Determine if we should continue based on error type
    recoverable_errors = (
        FileNotFoundError,
        PermissionError,
        ValueError,
        KeyError,
    )

    should_continue = not is_critical and isinstance(error, recoverable_errors)

    # Generate recovery suggestion
    recovery_suggestion = None
    if isinstance(error, FileNotFoundError):
        recovery_suggestion = "Check that the file path is correct and the file exists"
    elif isinstance(error, PermissionError):
        recovery_suggestion = "Check file permissions or try running with appropriate access"
    elif isinstance(error, ValueError):
        recovery_suggestion = "Validate input data format and try again"
    elif isinstance(error, MemoryError):
        recovery_suggestion = "Reduce chunk size or increase available memory"
        is_critical = True
        should_continue = False

    # Log the error
    log_level = logging.ERROR if is_critical else logging.WARNING
    logger.log(
        log_level,
        "%s: %s (context: %s)",
        error_type,
        error_message,
        context or {}
    )

    return ErrorResponse(
        error_type=error_type,
        error_message=error_message,
        is_critical=is_critical,
        should_continue=should_continue,
        recovery_suggestion=recovery_suggestion,
        context=context
    )


@dataclass
class OperationMetrics:
    """Metrics for an operation."""
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    memory_start_mb: Optional[float] = None
    memory_end_mb: Optional[float] = None
    memory_peak_mb: Optional[float] = None
    items_processed: int = 0
    errors_encountered: int = 0
    success: bool = False
    additional_data: Optional[Dict[str, Any]] = None


class OperationLogger:
    """Context manager for logging operation metrics."""

    def __init__(self, operation_name: str, log_memory: bool = True):
        """
        Initialize operation logger.

        Args:
            operation_name: Name of the operation to log
            log_memory: Whether to track memory usage
        """
        self.metrics = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time()
        )
        self.log_memory = log_memory

        if self.log_memory:
            mem_stats = monitor_memory()
            self.metrics.memory_start_mb = mem_stats.current_mb

    def __enter__(self):
        """Context manager entry."""
        logger.info("Starting operation: %s", self.metrics.operation_name)
        return self.metrics

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.metrics.end_time = time.time()
        self.metrics.duration_seconds = self.metrics.end_time - self.metrics.start_time

        if self.log_memory:
            mem_stats = monitor_memory()
            self.metrics.memory_end_mb = mem_stats.current_mb
            self.metrics.memory_peak_mb = mem_stats.peak_mb

        self.metrics.success = exc_type is None

        # Log the metrics
        if self.metrics.success:
            logger.info(
                "Completed operation: %s (duration: %.2fs, items: %d)",
                self.metrics.operation_name,
                self.metrics.duration_seconds,
                self.metrics.items_processed
            )
            if self.log_memory:
                logger.info(
                    "Memory usage: start=%.1fMB, end=%.1fMB, peak=%.1fMB",
                    self.metrics.memory_start_mb or 0,
                    self.metrics.memory_end_mb or 0,
                    self.metrics.memory_peak_mb or 0
                )
        else:
            logger.error(
                "Failed operation: %s (duration: %.2fs, error: %s)",
                self.metrics.operation_name,
                self.metrics.duration_seconds,
                exc_type.__name__ if exc_type else "Unknown"
            )

        return False


def log_operation(operation_name: str, log_memory: bool = True) -> OperationLogger:
    """
    Create an operation logger context manager.

    Args:
        operation_name: Name of the operation
        log_memory: Whether to track memory usage

    Returns:
        OperationLogger instance for use with 'with' statement

    Example:
        with log_operation("PDF Processing") as metrics:
            # Do work
            metrics.items_processed = 100
            metrics.additional_data = {"file_size_mb": 50}
    """
    return OperationLogger(operation_name, log_memory)


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes to human-readable string.

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60

    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}h {remaining_minutes}m"


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path

    Returns:
        Path object to the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
