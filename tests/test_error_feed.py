"""Tests for error feed generation."""

import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from watcher.core.error_feed import ErrorFeedManager


class TestErrorFeedManager:
    """Test ErrorFeedManager class."""

    def test_add_error(self):
        """Test adding an error to the feed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ErrorFeedManager(Path(tmpdir))

            manager.add_error(
                feed_id="test_feed",
                url="https://example.com",
                error_type="HTTPError",
                error_message="404 Not Found",
                error_details={"status_code": 404},
                feed_stats={
                    "consecutive_failures": 3,
                    "total_runs": 100,
                    "total_failures": 5,
                },
            )

            assert len(manager.error_items) == 1
            error = manager.error_items[0]
            assert error["feed_id"] == "test_feed"
            assert error["url"] == "https://example.com"
            assert error["error_type"] == "HTTPError"
            assert error["consecutive_failures"] == 3

    def test_generate_rss_feed(self):
        """Test generating RSS feed from errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ErrorFeedManager(Path(tmpdir))

            # Add multiple errors
            manager.add_error(
                feed_id="feed1",
                url="https://example1.com",
                error_type="TimeoutError",
                error_message="Connection timeout",
                feed_stats={
                    "consecutive_failures": 1,
                    "total_runs": 10,
                    "total_failures": 1,
                },
            )

            manager.add_error(
                feed_id="feed2",
                url="https://example2.com",
                error_type="HTTPError",
                error_message="500 Server Error",
                feed_stats={
                    "consecutive_failures": 2,
                    "total_runs": 20,
                    "total_failures": 3,
                },
            )

            # Generate feed
            feed_path = manager.generate_rss_feed()

            # Verify file was created
            assert feed_path.exists()

            # Parse and verify RSS structure
            tree = ET.parse(feed_path)
            root = tree.getroot()

            assert root.tag == "rss"
            assert root.get("version") == "2.0"

            channel = root.find("channel")
            assert channel is not None

            title = channel.find("title")
            assert title is not None
            assert title.text == "Watcher Error Feed"

            items = channel.findall("item")
            assert len(items) == 2

            # Check first item (should be most recent)
            item = items[0]
            item_title = item.find("title")
            assert "[feed2]" in item_title.text
            assert "HTTPError" in item_title.text

    def test_error_feed_with_proxy_attempts(self):
        """Test error feed with proxy attempt details."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ErrorFeedManager(Path(tmpdir))

            error_details = {
                "proxy_attempts": [
                    {
                        "proxy": "direct",
                        "success": False,
                        "error": "Connection refused",
                    },
                    {"proxy": "proxy1", "success": False, "error": "403 Forbidden"},
                    {"proxy": "proxy2", "success": False, "error": "Timeout"},
                ]
            }

            manager.add_error(
                feed_id="test_feed",
                url="https://example.com",
                error_type="AllAttemptsFailed",
                error_message="All proxy attempts failed",
                error_details=error_details,
                feed_stats={
                    "consecutive_failures": 5,
                    "total_runs": 50,
                    "total_failures": 10,
                },
            )

            # Generate feed
            feed_path = manager.generate_rss_feed()

            # Parse and verify
            tree = ET.parse(feed_path)
            root = tree.getroot()

            items = root.find(".//item")
            description = items.find("description")

            # The description should contain JSON with proxy attempts
            assert "proxy_attempts" in description.text
            assert "direct" in description.text
            assert "proxy1" in description.text
            assert "proxy2" in description.text

    def test_max_items_limit(self):
        """Test that max_items limit is respected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ErrorFeedManager(Path(tmpdir))

            # Add more errors than the limit
            for i in range(10):
                manager.add_error(
                    feed_id=f"feed{i}",
                    url=f"https://example{i}.com",
                    error_type="TestError",
                    error_message=f"Error {i}",
                )

            # Generate with max_items=5
            feed_path = manager.generate_rss_feed(max_items=5)

            # Parse and count items
            tree = ET.parse(feed_path)
            items = tree.findall(".//item")

            assert len(items) == 5  # Should be limited to 5
