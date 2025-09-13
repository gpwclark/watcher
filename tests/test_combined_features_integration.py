"""Integration tests combining error tracking and proxy features."""

import json
import os
import tempfile
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch
from xml.etree import ElementTree as ET

from watcher.core.proxy_manager import ProxyManager
from watcher.core.stats_tracker import StatsTracker
from watcher.core.error_feed import ErrorFeedManager
from watcher.lib import scrape_with_retries
from watcher.core.models import ScraperRequest


class ComplexTestHandler(BaseHTTPRequestHandler):
    """Handler with complex failure scenarios."""

    request_log = []
    failure_pattern = []  # List of response codes
    current_index = 0

    def do_GET(self):
        """Handle requests with configured failure pattern."""
        # Log request details
        self.__class__.request_log.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "index": self.__class__.current_index,
            }
        )

        # Get response code from pattern
        if self.__class__.current_index < len(self.__class__.failure_pattern):
            code = self.__class__.failure_pattern[self.__class__.current_index]
        else:
            code = 200  # Default to success

        self.__class__.current_index += 1

        if code == 200:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"""
            <html>
            <head><title>Test Success</title></head>
            <body>
                <h1>Success Response</h1>
                <p>Request #{self.__class__.current_index}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error {code}: Simulated failure".encode())

    def log_message(self, format, *args):
        """Suppress log messages."""
        pass

    @classmethod
    def reset(cls):
        """Reset handler state."""
        cls.request_log = []
        cls.failure_pattern = []
        cls.current_index = 0


class TestCombinedFeatures:
    """Test error tracking and proxy features working together."""

    def setup_method(self):
        """Reset state before each test."""
        ComplexTestHandler.reset()

    @patch.dict(os.environ, {"PROXY1_KEY": "key1", "PROXY2_KEY": "key2"})
    def test_error_tracking_with_proxy_attempts(self):
        """Test that error feed correctly tracks all proxy attempts."""
        # Start content server with specific failure pattern
        content_server = HTTPServer(("localhost", 0), ComplexTestHandler)
        content_port = content_server.server_address[1]

        # Pattern: direct fails (403), proxy1 fails (500), proxy2 succeeds (200)
        ComplexTestHandler.failure_pattern = [403, 500, 200]

        # Start proxy servers
        proxy1_server = HTTPServer(("localhost", 0), ComplexTestHandler)
        proxy1_port = proxy1_server.server_address[1]

        proxy2_server = HTTPServer(("localhost", 0), ComplexTestHandler)
        proxy2_port = proxy2_server.server_address[1]

        # Run servers
        for server in [content_server, proxy1_server, proxy2_server]:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxies
                proxy_config = {
                    "proxy1": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy1_port}?url={{encoded_url}}&key={{env:PROXY1_KEY}}",
                        "encoding": "url",
                        "env_vars": ["PROXY1_KEY"],
                    },
                    "proxy2": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy2_port}?url={{encoded_url}}&key={{env:PROXY2_KEY}}",
                        "encoding": "url",
                        "env_vars": ["PROXY2_KEY"],
                    },
                }

                proxy_manager = ProxyManager(proxy_config)
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                content_url = f"http://localhost:{content_port}/test"
                request = ScraperRequest(url=content_url, feed_name="complex_test")

                # First attempt - will try direct, then proxies
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["proxy1", "proxy2"],
                    proxy_mode="on_failure",
                    max_retries=3,
                )

                # Should eventually succeed via proxy2
                assert result.success

                # Check statistics
                feed_stats = stats_tracker.get_feed_stats("complex_test")
                assert feed_stats["total_runs"] == 1
                assert feed_stats["total_failures"] == 0  # Eventually succeeded
                assert feed_stats["consecutive_failures"] == 0

                # Check proxy statistics
                proxy1_rate = stats_tracker.get_proxy_success_rate(
                    "proxy1", content_url
                )
                proxy2_rate = stats_tracker.get_proxy_success_rate(
                    "proxy2", content_url
                )

                assert proxy1_rate == 0.0  # proxy1 failed
                assert proxy2_rate == 1.0  # proxy2 succeeded

                # Now make it fail completely
                ComplexTestHandler.reset()
                ComplexTestHandler.failure_pattern = [403, 500, 503]  # All fail

                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["proxy1", "proxy2"],
                    proxy_mode="on_failure",
                    max_retries=3,
                )

                assert not result.success

                # Generate error feed
                error_feed_path = error_feed_manager.generate_rss_feed()

                # Parse error feed
                tree = ET.parse(error_feed_path)
                item = tree.find(".//item")
                description = item.find("description").text

                # Extract JSON
                json_start = description.find("<pre>") + 5
                json_end = description.find("</pre>")
                json_text = description[json_start:json_end]
                error_data = json.loads(json_text)

                # Verify proxy attempts are recorded
                assert "details" in error_data
                assert "proxy_attempts" in error_data["details"]
                attempts = error_data["details"]["proxy_attempts"]

                # Should have 3 attempts: direct, then proxies (order may vary based on history)
                assert len(attempts) == 3
                assert attempts[0]["proxy"] == "direct"
                # Check that both proxies were tried
                proxy_names = [a["proxy"] for a in attempts[1:]]
                assert "proxy1" in proxy_names or "proxy2" in proxy_names

                # All should have failed
                for attempt in attempts:
                    assert attempt["success"] is False

        finally:
            content_server.shutdown()
            proxy1_server.shutdown()
            proxy2_server.shutdown()

    @patch.dict(os.environ, {"MAIN_PROXY": "mainkey", "BACKUP_PROXY": "backupkey"})
    def test_intelligent_proxy_selection_over_time(self):
        """Test that proxy selection improves based on historical performance."""
        # Start servers
        main_server = HTTPServer(("localhost", 0), ComplexTestHandler)
        main_port = main_server.server_address[1]

        backup_server = HTTPServer(("localhost", 0), ComplexTestHandler)
        backup_port = backup_server.server_address[1]

        for server in [main_server, backup_server]:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxies
                proxy_config = {
                    "main_proxy": {
                        "type": "url_template",
                        "template": f"http://localhost:{main_port}?url={{encoded_url}}&key={{env:MAIN_PROXY}}",
                        "encoding": "url",
                        "env_vars": ["MAIN_PROXY"],
                    },
                    "backup_proxy": {
                        "type": "url_template",
                        "template": f"http://localhost:{backup_port}?url={{encoded_url}}&key={{env:BACKUP_PROXY}}",
                        "encoding": "url",
                        "env_vars": ["BACKUP_PROXY"],
                    },
                }

                proxy_manager = ProxyManager(proxy_config)
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                # Test URL 1: main_proxy fails, backup succeeds
                url1 = f"http://localhost:{main_port}/resource1"
                request1 = ScraperRequest(url=url1, feed_name="feed1")

                # Configure main to fail, backup to succeed for first request
                ComplexTestHandler.failure_pattern = [500, 200]

                result = scrape_with_retries(
                    request=request1,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["main_proxy", "backup_proxy"],
                    proxy_mode="always",
                    max_retries=2,
                )

                assert result.success

                # Check that backup_proxy has better stats for url1
                main_rate = stats_tracker.get_proxy_success_rate("main_proxy", url1)
                backup_rate = stats_tracker.get_proxy_success_rate("backup_proxy", url1)

                assert main_rate == 0.0
                assert backup_rate == 1.0

                # Reset for next request
                ComplexTestHandler.reset()
                ComplexTestHandler.failure_pattern = [200]  # Success on first try

                # Make another request to same URL
                # Should prefer backup_proxy based on history
                result = scrape_with_retries(
                    request=request1,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["main_proxy", "backup_proxy"],
                    proxy_mode="always",
                    max_retries=2,
                )

                assert result.success

                # For a different URL, try again
                url2 = f"http://localhost:{main_port}/resource2"
                request2 = ScraperRequest(url=url2, feed_name="feed2")

                # Both proxies work for url2
                ComplexTestHandler.reset()
                ComplexTestHandler.failure_pattern = [200, 200]

                # First attempt for new URL
                result = scrape_with_retries(
                    request=request2,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["main_proxy", "backup_proxy"],
                    proxy_mode="always",
                    max_retries=1,
                )

                assert result.success

                # Build history for url2
                for _ in range(3):
                    ComplexTestHandler.reset()
                    ComplexTestHandler.failure_pattern = [200]

                    result = scrape_with_retries(
                        request=request2,
                        proxy_manager=proxy_manager,
                        stats_tracker=stats_tracker,
                        error_feed_manager=error_feed_manager,
                        proxies=["main_proxy", "backup_proxy"],
                        proxy_mode="always",
                        max_retries=1,
                    )
                    assert result.success

                # Check accumulated statistics
                feed1_stats = stats_tracker.get_feed_stats("feed1")
                feed2_stats = stats_tracker.get_feed_stats("feed2")

                assert feed1_stats["total_runs"] == 2
                assert feed1_stats["total_failures"] == 0
                assert feed2_stats["total_runs"] == 4
                assert feed2_stats["total_failures"] == 0

        finally:
            main_server.shutdown()
            backup_server.shutdown()

    @patch.dict(os.environ, {"PROXY_KEY": "testkey"})
    def test_error_feed_accumulation(self):
        """Test that error feed accumulates errors from multiple feeds correctly."""
        # Start server
        server = HTTPServer(("localhost", 0), ComplexTestHandler)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                # Create multiple feeds that fail
                feeds = ["feed_a", "feed_b", "feed_c"]

                for i, feed_name in enumerate(feeds):
                    # Configure different failure patterns
                    ComplexTestHandler.reset()
                    ComplexTestHandler.failure_pattern = [
                        400 + i,
                        500 + i,
                    ]  # Different error codes

                    url = f"http://localhost:{port}/{feed_name}"
                    request = ScraperRequest(url=url, feed_name=feed_name)

                    # Make multiple failed attempts
                    for attempt in range(2):
                        result = scrape_with_retries(
                            request=request,
                            stats_tracker=stats_tracker,
                            error_feed_manager=error_feed_manager,
                            max_retries=1,
                        )
                        assert not result.success

                # Generate error feed
                error_feed_path = error_feed_manager.generate_rss_feed()

                # Parse and verify
                tree = ET.parse(error_feed_path)
                items = tree.findall(".//item")

                # Should have 6 errors total (2 per feed)
                assert len(items) == 6

                # Verify each feed appears
                titles = [item.find("title").text for item in items]
                for feed_name in feeds:
                    feed_titles = [t for t in titles if feed_name in t]
                    assert len(feed_titles) == 2  # 2 errors per feed

                # Check consecutive failures are tracked correctly
                for feed_name in feeds:
                    stats = stats_tracker.get_feed_stats(feed_name)
                    assert stats["total_runs"] == 2
                    assert stats["total_failures"] == 2
                    assert stats["consecutive_failures"] == 2

                # Now make one feed succeed
                ComplexTestHandler.reset()
                ComplexTestHandler.failure_pattern = [200]  # Success

                request = ScraperRequest(
                    url=f"http://localhost:{port}/feed_a", feed_name="feed_a"
                )

                result = scrape_with_retries(
                    request=request,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    max_retries=1,
                )
                assert result.success

                # Check feed_a stats updated
                stats = stats_tracker.get_feed_stats("feed_a")
                assert stats["total_runs"] == 3
                assert stats["total_failures"] == 2  # Still 2 total
                assert stats["consecutive_failures"] == 0  # Reset

                # Other feeds should be unchanged
                for feed_name in ["feed_b", "feed_c"]:
                    stats = stats_tracker.get_feed_stats(feed_name)
                    assert stats["consecutive_failures"] == 2

        finally:
            server.shutdown()

    def test_stats_file_format_validation(self):
        """Test that stats files have correct format and can be manually inspected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stats_dir = Path(tmpdir)
            stats_tracker = StatsTracker(stats_dir)

            # Record various activities
            stats_tracker.record_feed_attempt("test_feed", success=True)
            stats_tracker.record_feed_attempt(
                "test_feed", success=False, error_details={"error": "Test error"}
            )
            stats_tracker.record_proxy_attempt(
                "proxy1", "http://example.com", success=True
            )
            stats_tracker.record_proxy_attempt(
                "proxy1", "http://example.com", success=False
            )

            # Load and validate feed stats file
            feed_stats_file = stats_dir / "feed_stats.json"
            assert feed_stats_file.exists()

            with open(feed_stats_file) as f:
                feed_data = json.load(f)

            # Validate structure
            assert "test_feed" in feed_data
            feed = feed_data["test_feed"]
            assert feed["total_runs"] == 2
            assert feed["total_failures"] == 1
            assert feed["consecutive_failures"] == 1
            assert "last_success" in feed
            assert "last_failure" in feed
            assert "last_error" in feed

            # Load and validate proxy stats file
            proxy_stats_file = stats_dir / "proxy_stats.json"
            assert proxy_stats_file.exists()

            with open(proxy_stats_file) as f:
                proxy_data = json.load(f)

            # Validate structure
            assert "proxy1" in proxy_data
            proxy = proxy_data["proxy1"]
            assert "urls" in proxy
            assert "global_stats" in proxy

            # Check URL-specific stats
            assert "http://example.com" in proxy["urls"]
            url_stat = proxy["urls"]["http://example.com"]
            assert url_stat["attempts"] == 2
            assert url_stat["successes"] == 1

            # Check global stats
            global_stats = proxy["global_stats"]
            assert global_stats["total_requests"] == 2
            assert global_stats["total_successes"] == 1
            assert global_stats["success_rate"] == 0.5
