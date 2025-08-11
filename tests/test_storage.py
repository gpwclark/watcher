"""Tests for the storage module."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from watcher.core.storage import ContentStorage


class TestContentStorage:
    """Test cases for ContentStorage class."""

    def test_init(self):
        """Test storage initialization."""
        feed_name = "test-feed"
        storage = ContentStorage(feed_name)
        assert storage.feed_name == feed_name
        assert storage.content_dir == Path("content") / feed_name

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"last_hash": "abc123"}')
    def test_load_metadata_existing(self, mock_file, mock_exists):
        """Test loading existing metadata."""
        mock_exists.return_value = True

        storage = ContentStorage("test-feed")
        metadata = storage.load_metadata()

        assert metadata == {"last_hash": "abc123"}

    @patch('pathlib.Path.exists')
    def test_load_metadata_not_existing(self, mock_exists):
        """Test loading metadata when file doesn't exist."""
        mock_exists.return_value = False

        storage = ContentStorage("test-feed")
        metadata = storage.load_metadata()

        assert metadata == {}

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"last_hash": "abc123"}')
    def test_has_content_changed_no_change(self, mock_file, mock_exists):
        """Test detecting no content change."""
        mock_exists.return_value = True

        storage = ContentStorage("test-feed")
        assert not storage.has_content_changed("abc123")

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"last_hash": "abc123"}')
    def test_has_content_changed_with_change(self, mock_file, mock_exists):
        """Test detecting content change."""
        mock_exists.return_value = True

        storage = ContentStorage("test-feed")
        assert storage.has_content_changed("xyz789")

    @patch('watcher.core.storage.ContentStorage.has_content_changed')
    @patch('watcher.core.storage.ContentStorage.load_metadata')
    @patch('watcher.core.storage.ContentStorage.save_metadata')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_content_new(self, mock_file, mock_mkdir, mock_save_meta, mock_load_meta, mock_changed):
        """Test saving new content."""
        mock_changed.return_value = True
        mock_load_meta.return_value = {}

        content_data = {
            'content': '<p>Test content</p>',
            'hash': 'xyz789',
            'title': 'Test Title',
            'url': 'https://example.com',
            'timestamp': '2025-01-11T12:00:00'
        }

        storage = ContentStorage("test-feed")
        result = storage.save_content(content_data)

        assert result is not None
        filename, diff_content = result
        assert filename is not None
        assert filename.endswith('.html')
        mock_file().write.assert_called_once()

    @patch('watcher.core.storage.ContentStorage.has_content_changed')
    def test_save_content_unchanged(self, mock_changed):
        """Test saving unchanged content."""
        mock_changed.return_value = False

        content_data = {
            'content': '<p>Test content</p>',
            'hash': 'abc123',
            'title': 'Test Title',
            'url': 'https://example.com',
            'timestamp': '2025-01-11T12:00:00'
        }

        storage = ContentStorage("test-feed")
        result = storage.save_content(content_data)

        assert result is None