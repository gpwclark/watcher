"""Tests for history reconstruction functionality."""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime, timezone, timedelta
from watcher.core.storage import ContentStorage
from watcher.core.rss_manager import RSSManager
from watcher.lib import scrape_and_update_feed
from watcher.core.models import ScraperRequest


class TestHistoryReconstruction:
    def test_html_includes_history_viewer_script(self):
        """Test that generated HTML includes the history viewer script."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                storage = ContentStorage("test-feed")

                content_data = {
                    'content': '<p>Test content</p>',
                    'hash': 'abc123',
                    'title': 'Test Page',
                    'url': 'https://example.com',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }

                filename, _ = storage.save_content(content_data)

                # Read saved file
                saved_file = Path("content/test-feed") / filename
                html_content = saved_file.read_text()

                # Check for history viewer script
                assert '<script src="../../history-viewer.js"></script>' in html_content
                assert '<meta name="rss-feed-url"' in html_content

            finally:
                os.chdir(old_cwd)

    def test_rss_links_include_date_parameter(self):
        """Test that RSS feed links include date query parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                rss_manager = RSSManager("test-feed", "https://example.com")

                # Create a test item
                timestamp = datetime.now(timezone.utc)
                rss_item = {
                    'title': 'Test Update',
                    'description': 'Test description with diff\n@@ -1,3 +1,3 @@\n-old\n+new',
                    'timestamp': timestamp.isoformat(),
                    'hash': 'abc123',
                    'filename': '20250811-120000.html',
                }

                rss_manager.create_or_update_feed(rss_item)

                # Read the RSS feed
                feed_content = Path("feeds/test-feed.xml").read_text()

                # Check that link includes date parameter
                assert '?date=' in feed_content
                assert timestamp.isoformat() in feed_content

                # Check that diff is wrapped in CDATA
                assert '<![CDATA[' in feed_content

            finally:
                os.chdir(old_cwd)

    def test_diff_generation_between_versions(self):
        """Test that diffs are generated correctly between versions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                storage = ContentStorage("test-feed")

                # Save first version
                content_data1 = {
                    'content': '<p>Original content</p>',
                    'hash': 'hash1',
                    'title': 'Test Page',
                    'url': 'https://example.com',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                }

                filename1, diff1 = storage.save_content(content_data1)
                assert diff1 is None  # No diff for first version

                # Save second version
                content_data2 = {
                    'content': '<p>Modified content</p>',
                    'hash': 'hash2',
                    'title': 'Test Page',
                    'url': 'https://example.com',
                    'timestamp': (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
                }

                filename2, diff2 = storage.save_content(content_data2)
                assert diff2 is not None
                assert '-<p>Original content</p>' in diff2
                assert '+<p>Modified content</p>' in diff2

            finally:
                os.chdir(old_cwd)

    def test_latest_file_link_in_rss(self):
        """Test that RSS feed links to latest content file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Create content directory and file
                content_dir = Path("content/test-feed")
                content_dir.mkdir(parents=True)

                # Create a dummy HTML file
                html_file = content_dir / "20250811-120000.html"
                html_file.write_text("<html><body>Test</body></html>")

                rss_manager = RSSManager("test-feed", "https://example.com")

                # Get latest file
                latest = rss_manager.get_latest_content_file()
                assert latest == "20250811-120000.html"

                # Create feed
                rss_item = {
                    'title': 'Test',
                    'description': 'Test',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'hash': 'abc123',
                    'filename': '20250811-120000.html',
                }

                rss_manager.create_or_update_feed(rss_item)

                # Check feed content
                feed_content = Path("feeds/test-feed.xml").read_text()
                assert "content/test-feed/20250811-120000.html" in feed_content

            finally:
                os.chdir(old_cwd)