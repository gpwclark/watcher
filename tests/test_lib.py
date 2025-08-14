"""Tests for the main library API."""

from unittest.mock import patch, MagicMock
from watcher import scrape_and_update_feed, ScraperRequest


class TestLibraryAPI:
    """Test cases for the main library API."""

    @patch("watcher.lib.ContentScraper")
    @patch("watcher.lib.ContentStorage")
    @patch("watcher.lib.RSSManager")
    def test_scrape_and_update_feed_success(self, mock_rss, mock_storage, mock_scraper):
        """Test successful scraping and feed update."""
        # Setup mocks
        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_content.return_value = {
            "content": "<p>Test</p>",
            "hash": "abc123",
            "title": "Test Title",
            "description": "Test Description",
            "url": "https://example.com",
            "timestamp": "2025-01-11T12:00:00",
        }

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save_content.return_value = ("20250111-120000.html", None)

        mock_rss_instance = MagicMock()
        mock_rss.return_value = mock_rss_instance

        # Test
        request = ScraperRequest(url="https://example.com", feed_name="test-feed")
        result = scrape_and_update_feed(request)

        # Assertions
        assert result.success is True
        assert result.changed is True
        assert result.filename == "20250111-120000.html"
        assert result.feed_path == "feeds/test-feed.xml"
        assert result.content_hash == "abc123"

        # Verify calls
        mock_scraper_instance.fetch_content.assert_called_once()
        mock_storage_instance.save_content.assert_called_once()
        mock_rss_instance.create_or_update_feed.assert_called_once()

    @patch("watcher.lib.ContentScraper")
    def test_scrape_and_update_feed_fetch_failure(self, mock_scraper):
        """Test handling of content fetch failure."""
        # Setup mocks
        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_content.return_value = None

        # Test
        request = ScraperRequest(url="https://example.com", feed_name="test-feed")
        result = scrape_and_update_feed(request)

        # Assertions
        assert result.success is False
        assert result.changed is False
        assert result.error_message == "Failed to fetch content from URL"

    @patch("watcher.lib.ContentScraper")
    @patch("watcher.lib.ContentStorage")
    def test_scrape_and_update_feed_no_change(self, mock_storage, mock_scraper):
        """Test handling when content hasn't changed."""
        # Setup mocks
        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_content.return_value = {
            "content": "<p>Test</p>",
            "hash": "abc123",
            "title": "Test Title",
            "description": "Test Description",
            "url": "https://example.com",
            "timestamp": "2025-01-11T12:00:00",
        }

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save_content.return_value = None  # No change

        # Test
        request = ScraperRequest(url="https://example.com", feed_name="test-feed")
        result = scrape_and_update_feed(request)

        # Assertions
        assert result.success is True
        assert result.changed is False
        assert result.content_hash == "abc123"

    @patch("watcher.lib.ContentScraper")
    def test_scrape_and_update_feed_exception(self, mock_scraper):
        """Test handling of unexpected exceptions."""
        # Setup mocks
        mock_scraper.side_effect = Exception("Test error")

        # Test
        request = ScraperRequest(url="https://example.com", feed_name="test-feed")
        result = scrape_and_update_feed(request)

        # Assertions
        assert result.success is False
        assert result.changed is False
        assert "Test error" in result.error_message

    @patch("watcher.lib.ContentScraper")
    @patch("watcher.lib.ContentStorage")
    @patch("watcher.lib.RSSManager")
    def test_scrape_and_update_feed_with_diff(
        self, mock_rss, mock_storage, mock_scraper
    ):
        """Test successful scraping with diff included."""
        # Setup mocks
        mock_scraper_instance = MagicMock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.fetch_content.return_value = {
            "content": "<p>Updated content</p>",
            "hash": "def456",
            "title": "Test Title",
            "description": "Test Description",
            "url": "https://example.com",
            "timestamp": "2025-01-11T14:00:00",
        }

        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        diff_content = "- <p>Old content</p>\n+ <p>Updated content</p>"
        mock_storage_instance.save_content.return_value = (
            "20250111-140000.html",
            diff_content,
        )

        mock_rss_instance = MagicMock()
        mock_rss.return_value = mock_rss_instance

        # Test
        request = ScraperRequest(url="https://example.com", feed_name="test-feed")
        result = scrape_and_update_feed(request)

        # Assertions
        assert result.success is True
        assert result.changed is True

        # Verify RSS item includes diff in description
        call_args = mock_rss_instance.create_or_update_feed.call_args[0][0]
        assert "<pre><code>" in call_args["description"]
        assert diff_content in call_args["description"]
