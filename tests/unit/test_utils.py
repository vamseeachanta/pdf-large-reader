"""
ABOUTME: Unit tests for utilities module
ABOUTME: Tests progress tracking, memory monitoring, error handling, and logging
"""

import pytest
import time
import psutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.utils import (
    MemoryStats,
    ErrorResponse,
    ProgressTracker,
    track_progress,
    monitor_memory,
    handle_error,
    log_operation,
    format_bytes,
    format_duration,
    ensure_directory,
    OperationMetrics
)


class TestMemoryStats:
    """Tests for MemoryStats dataclass."""

    def test_memory_stats_creation(self):
        """Test creating MemoryStats object."""
        stats = MemoryStats(
            current_mb=100.5,
            peak_mb=150.0,
            available_mb=2048.0,
            percent_used=45.5,
            timestamp=time.time()
        )

        assert stats.current_mb == 100.5
        assert stats.peak_mb == 150.0
        assert stats.available_mb == 2048.0
        assert stats.percent_used == 45.5
        assert stats.timestamp > 0


class TestErrorResponse:
    """Tests for ErrorResponse dataclass."""

    def test_error_response_creation(self):
        """Test creating ErrorResponse object."""
        response = ErrorResponse(
            error_type="ValueError",
            error_message="Invalid input",
            is_critical=False,
            should_continue=True,
            recovery_suggestion="Check input format"
        )

        assert response.error_type == "ValueError"
        assert response.error_message == "Invalid input"
        assert not response.is_critical
        assert response.should_continue
        assert response.recovery_suggestion == "Check input format"

    def test_error_response_with_context(self):
        """Test ErrorResponse with context dictionary."""
        context = {"file": "test.pdf", "page": 5}
        response = ErrorResponse(
            error_type="IOError",
            error_message="File read failed",
            is_critical=True,
            should_continue=False,
            context=context
        )

        assert response.context == context
        assert response.context["file"] == "test.pdf"


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    def test_progress_tracker_creation(self):
        """Test creating ProgressTracker."""
        tracker = ProgressTracker(
            total=100,
            description="Test progress",
            unit="items"
        )

        assert tracker.total == 100
        assert tracker.description == "Test progress"
        assert tracker.unit == "items"

    def test_progress_tracker_context_manager(self):
        """Test ProgressTracker as context manager."""
        with track_progress(10, "Testing") as progress:
            assert progress.elapsed_time >= 0
            time.sleep(0.01)  # Small delay
            assert progress.elapsed_time > 0

    def test_progress_tracker_update(self):
        """Test updating progress."""
        with track_progress(100, "Test", disable=True) as progress:
            progress.update(10)
            progress.update(20, description="Updated")
            # No assertion needed - just verify no exceptions

    def test_progress_tracker_postfix(self):
        """Test setting postfix values."""
        with track_progress(50, "Test", disable=True) as progress:
            progress.set_postfix(current_file="test.pdf", page=5)
            # No assertion needed - just verify no exceptions

    def test_progress_tracker_disabled(self):
        """Test progress tracker in disabled mode."""
        with track_progress(100, "Test", disable=True) as progress:
            progress.update(50)
            assert progress.elapsed_time >= 0


class TestMonitorMemory:
    """Tests for memory monitoring function."""

    def test_monitor_memory_returns_stats(self):
        """Test that monitor_memory returns MemoryStats."""
        stats = monitor_memory()

        assert isinstance(stats, MemoryStats)
        assert stats.current_mb > 0
        assert stats.peak_mb > 0
        assert stats.available_mb > 0
        assert 0 <= stats.percent_used <= 100
        assert stats.timestamp > 0

    def test_monitor_memory_tracks_peak(self):
        """Test that peak memory is tracked correctly."""
        stats1 = monitor_memory()
        initial_peak = stats1.peak_mb

        # Allocate some memory
        _ = bytearray(10 * 1024 * 1024)  # 10MB

        stats2 = monitor_memory()
        # Peak should be at least as high as before
        assert stats2.peak_mb >= initial_peak

    def test_monitor_memory_multiple_calls(self):
        """Test calling monitor_memory multiple times."""
        stats1 = monitor_memory()
        time.sleep(0.01)
        stats2 = monitor_memory()

        assert stats2.timestamp > stats1.timestamp
        assert stats2.peak_mb >= stats1.peak_mb


class TestHandleError:
    """Tests for error handling function."""

    def test_handle_file_not_found_error(self):
        """Test handling FileNotFoundError."""
        error = FileNotFoundError("test.pdf not found")
        response = handle_error(error, context={"file": "test.pdf"})

        assert response.error_type == "FileNotFoundError"
        assert "not found" in response.error_message
        assert not response.is_critical
        assert response.should_continue
        assert response.recovery_suggestion is not None
        assert "file path" in response.recovery_suggestion.lower()

    def test_handle_permission_error(self):
        """Test handling PermissionError."""
        error = PermissionError("Access denied")
        response = handle_error(error)

        assert response.error_type == "PermissionError"
        assert response.should_continue
        assert "permission" in response.recovery_suggestion.lower()

    def test_handle_value_error(self):
        """Test handling ValueError."""
        error = ValueError("Invalid data format")
        response = handle_error(error)

        assert response.error_type == "ValueError"
        assert response.should_continue
        assert "validate" in response.recovery_suggestion.lower()

    def test_handle_memory_error(self):
        """Test handling MemoryError (critical)."""
        error = MemoryError("Out of memory")
        response = handle_error(error)

        assert response.error_type == "MemoryError"
        assert response.is_critical
        assert not response.should_continue
        assert "memory" in response.recovery_suggestion.lower()

    def test_handle_critical_error(self):
        """Test handling error marked as critical."""
        error = ValueError("Critical validation error")
        response = handle_error(error, is_critical=True)

        assert response.is_critical
        assert not response.should_continue

    def test_handle_error_with_context(self):
        """Test error handling with context."""
        error = FileNotFoundError("test.pdf")
        context = {"file": "test.pdf", "operation": "read"}
        response = handle_error(error, context=context)

        assert response.context == context

    @patch('src.utils.logger')
    def test_handle_error_logs_warning(self, mock_logger):
        """Test that recoverable errors are logged as warnings."""
        error = ValueError("Recoverable error")
        handle_error(error, is_critical=False)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Should log at WARNING level (30)
        assert call_args[0][0] == 30  # logging.WARNING

    @patch('src.utils.logger')
    def test_handle_error_logs_error(self, mock_logger):
        """Test that critical errors are logged as errors."""
        error = MemoryError("Critical error")
        handle_error(error)

        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Should log at ERROR level (40)
        assert call_args[0][0] == 40  # logging.ERROR


class TestLogOperation:
    """Tests for operation logging."""

    def test_log_operation_success(self):
        """Test logging successful operation."""
        with log_operation("Test Operation") as metrics:
            time.sleep(0.01)
            metrics.items_processed = 100

        assert metrics.success
        assert metrics.duration_seconds > 0
        assert metrics.items_processed == 100
        assert metrics.memory_start_mb is not None
        assert metrics.memory_end_mb is not None

    def test_log_operation_failure(self):
        """Test logging failed operation."""
        try:
            with log_operation("Test Operation") as metrics:
                metrics.items_processed = 50
                raise ValueError("Test error")
        except ValueError:
            pass

        assert not metrics.success
        assert metrics.items_processed == 50
        assert metrics.duration_seconds > 0

    def test_log_operation_without_memory_tracking(self):
        """Test operation logging without memory tracking."""
        with log_operation("Test", log_memory=False) as metrics:
            time.sleep(0.01)

        assert metrics.success
        assert metrics.memory_start_mb is None
        assert metrics.memory_end_mb is None

    def test_log_operation_with_additional_data(self):
        """Test operation with additional data."""
        with log_operation("Test") as metrics:
            metrics.additional_data = {
                "file_size_mb": 50,
                "pages": 100
            }

        assert metrics.additional_data["file_size_mb"] == 50
        assert metrics.additional_data["pages"] == 100

    @patch('src.utils.logger')
    def test_log_operation_logs_start(self, mock_logger):
        """Test that operation start is logged."""
        with log_operation("Test Operation"):
            pass

        # Check if info was called with operation start
        calls = [call for call in mock_logger.info.call_args_list
                if "Starting operation" in str(call)]
        assert len(calls) > 0

    @patch('src.utils.logger')
    def test_log_operation_logs_completion(self, mock_logger):
        """Test that operation completion is logged."""
        with log_operation("Test Operation"):
            time.sleep(0.01)

        # Check if info was called with completion
        calls = [call for call in mock_logger.info.call_args_list
                if "Completed operation" in str(call)]
        assert len(calls) > 0


class TestFormatBytes:
    """Tests for byte formatting function."""

    def test_format_bytes_small(self):
        """Test formatting small byte values."""
        assert format_bytes(500) == "500.0 B"

    def test_format_bytes_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1536) == "1.5 KB"

    def test_format_bytes_megabytes(self):
        """Test formatting megabytes."""
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 2.5) == "2.5 MB"

    def test_format_bytes_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"

    def test_format_bytes_terabytes(self):
        """Test formatting terabytes."""
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"


class TestFormatDuration:
    """Tests for duration formatting function."""

    def test_format_duration_seconds(self):
        """Test formatting seconds."""
        assert format_duration(5.5) == "5.5s"
        assert format_duration(45) == "45.0s"

    def test_format_duration_minutes(self):
        """Test formatting minutes."""
        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(125) == "2m 5s"

    def test_format_duration_hours(self):
        """Test formatting hours."""
        assert format_duration(3600) == "1h 0m"
        assert format_duration(3660) == "1h 1m"
        assert format_duration(7200) == "2h 0m"


class TestEnsureDirectory:
    """Tests for directory creation function."""

    def test_ensure_directory_creates_new(self, tmp_path):
        """Test creating new directory."""
        new_dir = tmp_path / "test_dir"
        assert not new_dir.exists()

        result = ensure_directory(new_dir)

        assert result.exists()
        assert result.is_dir()
        assert result == new_dir

    def test_ensure_directory_existing(self, tmp_path):
        """Test with existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = ensure_directory(existing_dir)

        assert result.exists()
        assert result.is_dir()

    def test_ensure_directory_nested(self, tmp_path):
        """Test creating nested directories."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"

        result = ensure_directory(nested_dir)

        assert result.exists()
        assert result.is_dir()
        assert (tmp_path / "level1").exists()
        assert (tmp_path / "level1" / "level2").exists()


class TestOperationMetrics:
    """Tests for OperationMetrics dataclass."""

    def test_operation_metrics_creation(self):
        """Test creating OperationMetrics."""
        metrics = OperationMetrics(
            operation_name="Test",
            start_time=time.time(),
            items_processed=100,
            success=True
        )

        assert metrics.operation_name == "Test"
        assert metrics.items_processed == 100
        assert metrics.success

    def test_operation_metrics_with_memory(self):
        """Test OperationMetrics with memory tracking."""
        metrics = OperationMetrics(
            operation_name="Test",
            start_time=time.time(),
            end_time=time.time() + 1,
            duration_seconds=1.0,
            memory_start_mb=100.0,
            memory_end_mb=150.0,
            memory_peak_mb=160.0
        )

        assert metrics.memory_start_mb == 100.0
        assert metrics.memory_end_mb == 150.0
        assert metrics.memory_peak_mb == 160.0
