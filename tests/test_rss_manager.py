"""Tests for the RSS manager module."""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from watcher.core.rss_manager import RSSManager
import xml.etree.ElementTree as ET


class TestRSSManager:
    """Test cases for RSSManager class."""

    def test_init_default_base_url(self):
        """Test RSS manager initialization with default base URL."""
        with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'owner/repo'}):
            manager = RSSManager("test-feed")
            assert manager.feed_name == "test-feed"
            assert "owner/repo" in manager.base_url

    def test_init_custom_base_url(self):
        """Test RSS manager initialization with custom base URL."""
        manager = RSSManager("test-feed", "https://custom.example.com")
        assert manager.feed_name == "test-feed"
        assert manager.base_url == "https://custom.example.com"

    @patch('pathlib.Path.exists')
    def test_load_existing_feed_not_exists(self, mock_exists):
        """Test loading feed when it doesn't exist."""
        mock_exists.return_value = False

        manager = RSSManager("test-feed")
        result = manager.load_existing_feed()

        assert result is None

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_or_update_feed_new(self, mock_file, mock_mkdir, mock_exists):
        """Test creating a new RSS feed."""
        mock_exists.return_value = False

        manager = RSSManager("test-feed", "https://example.com")
        new_item = {
            'title': 'Test Update',
            'description': 'Test description',
            'timestamp': '2025-01-11T12:00:00',
            'hash': 'abc123',
            'filename': 'test.html'
        }

        manager.create_or_update_feed(new_item)

        # Check that write was called
        mock_file().write.assert_called()
        written_content = b''.join(call.args[0] for call in mock_file().write.call_args_list)
        written_content = written_content.decode('utf-8')

        # Verify RSS structure
        assert '<rss' in written_content
        assert '<title>Test Update</title>' in written_content
        assert 'test-feed-abc123' in written_content  # unique_id

    @patch('pathlib.Path.exists')
    def test_load_existing_items_empty(self, mock_exists):
        """Test loading items from non-existent feed."""
        mock_exists.return_value = False

        manager = RSSManager("test-feed")
        items = manager._load_existing_items()

        assert items == []

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_existing_items_with_items(self, mock_file, mock_exists):
        """Test loading items from existing feed."""
        mock_exists.return_value = True

        # Create a sample RSS XML
        rss_content = '''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>test-feed Updates</title>
    <item>
      <title>Previous Update</title>
      <link>https://example.com/content/test.html</link>
      <description>Previous description</description>
      <guid>test-feed-xyz789</guid>
      <pubDate>Sat, 11 Jan 2025 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>'''
        mock_file.return_value.read.return_value = rss_content

        # Mock ET.parse to return parsed tree
        with patch('xml.etree.ElementTree.parse') as mock_parse:
            mock_tree = ET.ElementTree(ET.fromstring(rss_content))
            mock_parse.return_value = mock_tree

            manager = RSSManager("test-feed")
            items = manager._load_existing_items()

            assert len(items) == 1
            assert items[0]['title'] == 'Previous Update'
            assert items[0]['unique_id'] == 'test-feed-xyz789'