"""Comprehensive integration tests for error tracking functionality."""

import json
import tempfile
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from xml.etree import ElementTree as ET

from watcher.core.stats_tracker import StatsTracker
from watcher.core.error_feed import ErrorFeedManager
from watcher.lib import scrape_with_retries
from watcher.core.models import ScraperRequest


class FailingTestHandler(BaseHTTPRequestHandler):
    """HTTP handler that can be configured to fail."""

    failure_count = 0
    max_failures = 0
    failure_codes = []

    def do_GET(self):
        """Handle GET requests with configurable failures."""
        # Track request count
        self.__class__.failure_count += 1

        # Fail if configured to
        if self.__class__.failure_count <= self.__class__.max_failures:
            # Use specific failure code if provided
            if self.__class__.failure_codes:
                code = self.__class__.failure_codes[
                    min(
                        self.__class__.failure_count - 1,
                        len(self.__class__.failure_codes) - 1,
                    )
                ]
            else:
                code = 500

            self.send_response(code)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"Error {code}: Simulated failure".encode())
        else:
            # Success after failures
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """
            <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Success after {failures} failures</h1>
                <p>This content loaded successfully.</p>
            </body>
            </html>
            """.format(failures=self.__class__.failure_count - 1)
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress log messages during tests."""
        pass


class TestErrorTrackingIntegration:
    """Test error tracking with real HTTP server."""

    def setup_method(self):
        """Reset handler state before each test."""
        FailingTestHandler.failure_count = 0
        FailingTestHandler.max_failures = 0
        FailingTestHandler.failure_codes = []

    def test_consecutive_failures_tracking(self):
        """Test that consecutive failures are properly tracked."""
        # Start a failing server
        server = HTTPServer(("localhost", 0), FailingTestHandler)
        port = server.server_address[1]

        # Configure to fail 3 times
        FailingTestHandler.max_failures = 3
        FailingTestHandler.failure_codes = [404, 500, 503]

        # Run server in background
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                url = f"http://localhost:{port}/test"

                # First attempt - should fail with 404
                request = ScraperRequest(url=url, feed_name="test_feed")
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )

                assert not result.success

                # Check stats after first failure
                stats = stats_tracker.get_feed_stats("test_feed")
                assert stats["total_runs"] == 1
                assert stats["total_failures"] == 1
                assert stats["consecutive_failures"] == 1

                # Second attempt - should fail with 500
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )

                assert not result.success

                # Check stats after second failure
                stats = stats_tracker.get_feed_stats("test_feed")
                assert stats["total_runs"] == 2
                assert stats["total_failures"] == 2
                assert stats["consecutive_failures"] == 2

                # Third attempt - should fail with 503
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )

                assert not result.success

                # Check stats after third failure
                stats = stats_tracker.get_feed_stats("test_feed")
                assert stats["total_runs"] == 3
                assert stats["total_failures"] == 3
                assert stats["consecutive_failures"] == 3

                # Fourth attempt - should succeed
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )

                assert result.success

                # Check stats after success
                stats = stats_tracker.get_feed_stats("test_feed")
                assert stats["total_runs"] == 4
                assert stats["total_failures"] == 3  # Still 3 total failures
                assert stats["consecutive_failures"] == 0  # Reset to 0
                assert stats["last_success"] is not None

                # Verify error feed was generated
                error_feed_path = Path(tmpdir) / "errors.xml"
                error_feed_manager.generate_rss_feed()
                assert error_feed_path.exists()

                # Parse and verify error feed content
                tree = ET.parse(error_feed_path)
                items = tree.findall(".//item")
                assert len(items) == 3  # Three failures recorded

                # Check that error details are present
                for item in items:
                    description = item.find("description").text
                    assert "test_feed" in description
                    assert "consecutive_failures" in description

        finally:
            server.shutdown()

    def test_error_feed_json_format(self):
        """Test that error feed contains proper JSON with all required fields."""
        server = HTTPServer(("localhost", 0), FailingTestHandler)
        port = server.server_address[1]

        # Configure to always fail
        FailingTestHandler.max_failures = 999
        FailingTestHandler.failure_codes = [403]

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                url = f"http://localhost:{port}/forbidden"

                # Attempt scraping
                request = ScraperRequest(url=url, feed_name="forbidden_feed")
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=2,  # Will try 2 times
                )

                assert not result.success

                # Generate error feed
                error_feed_path = error_feed_manager.generate_rss_feed()

                # Parse RSS and extract JSON from description
                tree = ET.parse(error_feed_path)
                item = tree.find(".//item")
                description = item.find("description").text

                # Extract JSON from CDATA
                json_start = description.find("<pre>") + 5
                json_end = description.find("</pre>")
                json_text = description[json_start:json_end]

                # Parse and verify JSON structure
                error_data = json.loads(json_text)

                # Verify all required fields
                assert error_data["feed_id"] == "forbidden_feed"
                assert error_data["url"] == url
                assert error_data["consecutive_failures"] == 1
                assert error_data["total_runs"] == 1
                assert error_data["total_failures"] == 1
                assert error_data["error_type"] in ["HTTPError", "ScraperError"]
                assert "timestamp" in error_data
                assert "last_failure" in error_data
                assert "details" in error_data

        finally:
            server.shutdown()

    def test_statistics_persistence_across_runs(self):
        """Test that statistics persist correctly across multiple runs."""
        server = HTTPServer(("localhost", 0), FailingTestHandler)
        port = server.server_address[1]

        # Configure intermittent failures
        FailingTestHandler.max_failures = 2

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stats_dir = Path(tmpdir)
                url = f"http://localhost:{port}/test"

                # First run with tracker
                tracker1 = StatsTracker(stats_dir)
                error_mgr1 = ErrorFeedManager(stats_dir)

                request = ScraperRequest(url=url, feed_name="persist_test")

                # First attempt - will fail
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=tracker1,
                    error_feed_manager=error_mgr1,
                    max_retries=1,
                )
                assert not result.success

                # Check initial stats
                stats = tracker1.get_feed_stats("persist_test")
                assert stats["total_runs"] == 1
                assert stats["total_failures"] == 1

                # Create new tracker instance (simulating new run)
                tracker2 = StatsTracker(stats_dir)
                error_mgr2 = ErrorFeedManager(stats_dir)

                # Verify stats persisted
                stats = tracker2.get_feed_stats("persist_test")
                assert stats["total_runs"] == 1
                assert stats["total_failures"] == 1

                # Second attempt with new tracker - will fail again
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=tracker2,
                    error_feed_manager=error_mgr2,
                    max_retries=1,
                )
                assert not result.success

                # Check updated stats
                stats = tracker2.get_feed_stats("persist_test")
                assert stats["total_runs"] == 2
                assert stats["total_failures"] == 2
                assert stats["consecutive_failures"] == 2

                # Reset server to succeed
                FailingTestHandler.failure_count = 999

                # Third tracker instance
                tracker3 = StatsTracker(stats_dir)

                # Attempt should succeed now
                result = scrape_with_retries(
                    request=request,
                    stats_tracker=tracker3,
                    error_feed_manager=ErrorFeedManager(stats_dir),
                    max_retries=1,
                )
                assert result.success

                # Verify cumulative stats
                stats = tracker3.get_feed_stats("persist_test")
                assert stats["total_runs"] == 3
                assert stats["total_failures"] == 2  # Still 2 total
                assert stats["consecutive_failures"] == 0  # Reset after success

        finally:
            server.shutdown()

    def test_multiple_feeds_independent_tracking(self):
        """Test that multiple feeds are tracked independently."""
        server = HTTPServer(("localhost", 0), FailingTestHandler)
        port = server.server_address[1]

        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                # Create two different feeds
                url1 = f"http://localhost:{port}/feed1"
                url2 = f"http://localhost:{port}/feed2"

                request1 = ScraperRequest(url=url1, feed_name="feed1")
                request2 = ScraperRequest(url=url2, feed_name="feed2")

                # Configure different failure patterns
                FailingTestHandler.max_failures = 1

                # Feed1 - first attempt (will fail)
                result = scrape_with_retries(
                    request=request1,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )
                assert not result.success

                # Feed2 - first attempt (will succeed because failure_count > max_failures)
                result = scrape_with_retries(
                    request=request2,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )
                assert result.success

                # Verify independent tracking
                stats1 = stats_tracker.get_feed_stats("feed1")
                stats2 = stats_tracker.get_feed_stats("feed2")

                assert stats1["total_failures"] == 1
                assert stats1["consecutive_failures"] == 1
                assert stats2["total_failures"] == 0
                assert stats2["consecutive_failures"] == 0

                # Generate error feed
                error_feed_path = error_feed_manager.generate_rss_feed()

                # Verify only feed1 appears in errors
                tree = ET.parse(error_feed_path)
                items = tree.findall(".//item")
                assert len(items) == 1

                item_title = items[0].find("title").text
                assert "feed1" in item_title
                assert "feed2" not in item_title

        finally:
            server.shutdown()
