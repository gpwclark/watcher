"""Tests for the scraper module."""

from unittest.mock import patch, MagicMock
from watcher.core.scraper import ContentScraper


class TestContentScraper:
    """Test cases for ContentScraper class."""

    def test_init(self):
        """Test scraper initialization."""
        url = "https://example.com"
        scraper = ContentScraper(url)
        assert scraper.url == url

    @patch("watcher.core.scraper.trafilatura.fetch_url")
    @patch("watcher.core.scraper.trafilatura.extract")
    @patch("watcher.core.scraper.trafilatura.extract_metadata")
    def test_fetch_content_success(self, mock_metadata, mock_extract, mock_fetch):
        """Test successful content fetching."""
        # Setup mocks
        mock_fetch.return_value = "<html>Test content</html>"
        mock_extract.return_value = "<p>Extracted content</p>"
        mock_metadata.return_value = MagicMock(
            title="Test Title", description="Test Description"
        )

        # Test
        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        # Assertions
        assert result is not None
        assert result["content"] == "<p>Extracted content</p>"
        assert result["title"] == "Test Title"
        assert result["description"] == "Test Description"
        assert result["url"] == "https://example.com"
        assert "hash" in result
        assert "timestamp" in result

    @patch("watcher.core.scraper.trafilatura.fetch_url")
    def test_fetch_content_download_failure(self, mock_fetch):
        """Test handling of download failure."""
        mock_fetch.return_value = None

        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        assert result is None

    @patch("watcher.core.scraper.trafilatura.fetch_url")
    @patch("watcher.core.scraper.trafilatura.extract")
    def test_fetch_content_extract_failure(self, mock_extract, mock_fetch):
        """Test handling of extraction failure."""
        mock_fetch.return_value = "<html>Test</html>"
        mock_extract.return_value = None

        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        assert result is None
