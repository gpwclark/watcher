"""Tests for stats tracker functionality."""

import tempfile
from pathlib import Path
import pytest
from watcher.core.stats_tracker import StatsTracker


class TestStatsTracker:
    """Test StatsTracker class."""

    def test_record_feed_success(self):
        """Test recording successful feed attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            tracker.record_feed_attempt("test_feed", success=True)

            stats = tracker.get_feed_stats("test_feed")
            assert stats is not None
            assert stats["total_runs"] == 1
            assert stats["total_failures"] == 0
            assert stats["consecutive_failures"] == 0
            assert stats["last_success"] is not None
            assert stats["last_failure"] is None

    def test_record_feed_failure(self):
        """Test recording failed feed attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            error_details = {
                "error_message": "Connection timeout",
                "error_type": "TimeoutError",
            }
            tracker.record_feed_attempt(
                "test_feed", success=False, error_details=error_details
            )

            stats = tracker.get_feed_stats("test_feed")
            assert stats is not None
            assert stats["total_runs"] == 1
            assert stats["total_failures"] == 1
            assert stats["consecutive_failures"] == 1
            assert stats["last_failure"] is not None
            assert stats["last_success"] is None
            assert stats["last_error"] == error_details

    def test_consecutive_failures(self):
        """Test tracking consecutive failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            # Record 3 failures
            for i in range(3):
                tracker.record_feed_attempt("test_feed", success=False)

            stats = tracker.get_feed_stats("test_feed")
            assert stats["total_runs"] == 3
            assert stats["total_failures"] == 3
            assert stats["consecutive_failures"] == 3

            # Record a success
            tracker.record_feed_attempt("test_feed", success=True)

            stats = tracker.get_feed_stats("test_feed")
            assert stats["total_runs"] == 4
            assert stats["total_failures"] == 3
            assert stats["consecutive_failures"] == 0  # Reset

    def test_record_proxy_success(self):
        """Test recording successful proxy attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            tracker.record_proxy_attempt("proxy1", "https://example.com", success=True)

            # Check global success rate
            rate = tracker.get_proxy_success_rate("proxy1")
            assert rate == 1.0

            # Check URL-specific success rate
            url_rate = tracker.get_proxy_success_rate("proxy1", "https://example.com")
            assert url_rate == 1.0

    def test_record_proxy_failure(self):
        """Test recording failed proxy attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            tracker.record_proxy_attempt(
                "proxy1", "https://example.com", success=False, error="403 Forbidden"
            )

            rate = tracker.get_proxy_success_rate("proxy1")
            assert rate == 0.0

    def test_proxy_success_rate_calculation(self):
        """Test proxy success rate calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            # Record mixed results
            tracker.record_proxy_attempt("proxy1", "https://example.com", success=True)
            tracker.record_proxy_attempt("proxy1", "https://example.com", success=False)
            tracker.record_proxy_attempt("proxy1", "https://example.com", success=True)

            rate = tracker.get_proxy_success_rate("proxy1")
            assert rate == pytest.approx(2 / 3)

            url_rate = tracker.get_proxy_success_rate("proxy1", "https://example.com")
            assert url_rate == pytest.approx(2 / 3)

    def test_get_best_proxy_for_url(self):
        """Test getting best proxy for a URL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            # Set up proxy history
            # proxy1: 80% success for this URL
            for _ in range(4):
                tracker.record_proxy_attempt(
                    "proxy1", "https://example.com", success=True
                )
            tracker.record_proxy_attempt("proxy1", "https://example.com", success=False)

            # proxy2: 40% success for this URL
            for _ in range(2):
                tracker.record_proxy_attempt(
                    "proxy2", "https://example.com", success=True
                )
            for _ in range(3):
                tracker.record_proxy_attempt(
                    "proxy2", "https://example.com", success=False
                )

            # proxy3: No history for this URL but 90% global success
            for _ in range(9):
                tracker.record_proxy_attempt(
                    "proxy3", "https://other.com", success=True
                )
            tracker.record_proxy_attempt("proxy3", "https://other.com", success=False)

            best = tracker.get_best_proxy_for_url(
                "https://example.com", ["proxy1", "proxy2", "proxy3"]
            )
            assert best == "proxy1"  # Best success rate for this specific URL

    def test_get_best_proxy_no_history(self):
        """Test getting best proxy when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = StatsTracker(Path(tmpdir))

            best = tracker.get_best_proxy_for_url(
                "https://example.com", ["proxy1", "proxy2"]
            )
            assert best == "proxy1"  # Returns first when no history

    def test_persistence(self):
        """Test that stats persist across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_dir = Path(tmpdir)

            # First tracker instance
            tracker1 = StatsTracker(stats_dir)
            tracker1.record_feed_attempt("test_feed", success=True)
            tracker1.record_proxy_attempt("proxy1", "https://example.com", success=True)

            # Second tracker instance
            tracker2 = StatsTracker(stats_dir)

            # Should see stats from first instance
            feed_stats = tracker2.get_feed_stats("test_feed")
            assert feed_stats["total_runs"] == 1

            proxy_rate = tracker2.get_proxy_success_rate("proxy1")
            assert proxy_rate == 1.0

            # Add more data
            tracker2.record_feed_attempt("test_feed", success=False)

            # Third instance should see all data
            tracker3 = StatsTracker(stats_dir)
            feed_stats = tracker3.get_feed_stats("test_feed")
            assert feed_stats["total_runs"] == 2
            assert feed_stats["total_failures"] == 1
