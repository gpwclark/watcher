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

    @patch("watcher.core.scraper.get_text")
    @patch("watcher.core.scraper.BeautifulSoup")
    @patch("watcher.core.scraper.requests.get")
    def test_fetch_content_success(self, mock_get, mock_bs, mock_get_text):
        """Test successful content fetching."""
        # Setup request mock
        mock_response = MagicMock()
        mock_response.text = "<html><head><title>Test Title</title></head><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Setup BeautifulSoup mock
        mock_soup = MagicMock()
        mock_title_tag = MagicMock()
        mock_title_tag.text = "Test Title"
        mock_soup.find.side_effect = lambda tag, **kwargs: {
            "title": mock_title_tag,
            "meta": MagicMock(
                get=lambda key, default: "Test Description"
                if key == "content"
                else default
            ),
            "body": MagicMock(),
        }.get(tag)
        mock_soup.find_all.return_value = []
        mock_bs.return_value = mock_soup

        # Setup inscriptis mock
        mock_get_text.return_value = "Extracted content"

        # Test
        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        # Assertions
        assert result is not None
        assert "<p>Extracted content</p>" in result["content"]
        assert result["title"] == "Test Title"
        assert result["description"] == "Test Description"
        assert result["url"] == "https://example.com"
        assert "hash" in result
        assert "timestamp" in result

    @patch("watcher.core.scraper.requests.get")
    def test_fetch_content_download_failure(self, mock_get):
        """Test handling of download failure."""
        mock_get.side_effect = Exception("Connection error")

        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        assert result is not None
        assert result.get("error") is True
        assert "Connection error" in result.get("error_message", "")

    @patch("watcher.core.scraper.get_text")
    @patch("watcher.core.scraper.BeautifulSoup")
    @patch("watcher.core.scraper.requests.get")
    def test_fetch_content_extract_failure(self, mock_get, mock_bs, mock_get_text):
        """Test handling of extraction failure."""
        # Setup request mock
        mock_response = MagicMock()
        mock_response.text = "<html>Test</html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Setup inscriptis to fail
        mock_get_text.side_effect = Exception("Extraction failed")

        scraper = ContentScraper("https://example.com")
        result = scraper.fetch_content()

        assert result is not None
        assert result.get("error") is True
        assert "Extraction failed" in result.get("error_message", "")
