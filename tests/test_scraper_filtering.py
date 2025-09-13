"""Tests for the enhanced content filtering features in ContentScraper."""

import pytest
from unittest.mock import Mock, patch
from watcher.core.scraper import ContentScraper


class TestContentScraperFiltering:
    """Test the new filtering capabilities."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock response with test HTML."""
        response = Mock()
        response.status_code = 200
        response.text = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
        </head>
        <body>
            <nav id="main-nav" class="navigation">Navigation content</nav>
            <header class="site-header">Header content</header>
            
            <article id="main-content" class="article-content">
                <h1>Main Article Title</h1>
                <p>This is the main content.</p>
                <div class="sidebar">Sidebar content</div>
            </article>
            
            <section id="comments" class="comments-section">
                <h2>Comments</h2>
                <p>Comment content here.</p>
            </section>
            
            <footer id="footer">Footer content</footer>
            
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
        </body>
        </html>
        """
        return response

    def test_mutual_exclusivity_validation(self):
        """Test that include/exclude options are mutually exclusive."""
        # Should not raise
        ContentScraper("http://example.com", exclude_tags=["nav"])
        ContentScraper("http://example.com", include_tags=["article"])

        # Should raise ValueError
        with pytest.raises(
            ValueError, match="Cannot use both exclude_tags and include_tags"
        ):
            ContentScraper(
                "http://example.com", exclude_tags=["nav"], include_tags=["article"]
            )

        with pytest.raises(
            ValueError, match="Cannot use both exclude_ids and include_ids"
        ):
            ContentScraper(
                "http://example.com", exclude_ids=["nav"], include_ids=["content"]
            )

        with pytest.raises(
            ValueError, match="Cannot use both exclude_classes and include_classes"
        ):
            ContentScraper(
                "http://example.com",
                exclude_classes=["nav"],
                include_classes=["content"],
            )

    @patch("requests.get")
    def test_include_tags(self, mock_get, mock_response):
        """Test including only specific tags."""
        mock_get.return_value = mock_response

        scraper = ContentScraper(
            "http://example.com", include_tags=["article", "section"]
        )
        result = scraper.fetch_content()

        assert result is not None
        assert "error" not in result
        content = result["content"]

        # Should include article and section content
        assert "Main Article Title" in content
        assert "Comments" in content

        # Should exclude other content
        assert "Navigation content" not in content
        assert "Header content" not in content
        assert "Footer content" not in content

    @patch("requests.get")
    def test_exclude_tags_default(self, mock_get, mock_response):
        """Test default exclude tags behavior."""
        mock_get.return_value = mock_response

        scraper = ContentScraper("http://example.com")
        result = scraper.fetch_content()

        content = result["content"]

        # Should include main content
        assert "Main Article Title" in content
        assert "Comments" in content

        # Should exclude default tags
        assert "Navigation content" not in content
        assert "Header content" not in content
        assert "Footer content" not in content
        assert "console.log" not in content

    @patch("requests.get")
    def test_include_ids(self, mock_get, mock_response):
        """Test including only elements with specific IDs."""
        mock_get.return_value = mock_response

        scraper = ContentScraper(
            "http://example.com", include_ids=["main-content", "comments"]
        )
        result = scraper.fetch_content()

        content = result["content"]

        # Should include specified IDs
        assert "Main Article Title" in content
        assert "Comments" in content

        # Should exclude other content
        assert "Navigation content" not in content
        assert "Footer content" not in content

    @patch("requests.get")
    def test_exclude_ids(self, mock_get, mock_response):
        """Test excluding elements with specific IDs."""
        mock_get.return_value = mock_response

        # Note: Default exclude_tags still applies, so header is excluded
        scraper = ContentScraper(
            "http://example.com",
            exclude_ids=["main-nav", "footer", "comments"],
            exclude_tags=[],
        )
        result = scraper.fetch_content()

        content = result["content"]

        # Should include non-excluded content
        assert "Main Article Title" in content

        # Should exclude specified IDs
        assert "Navigation content" not in content
        assert "Footer content" not in content
        assert "Comment content" not in content

    @patch("requests.get")
    def test_include_classes(self, mock_get, mock_response):
        """Test including only elements with specific classes."""
        mock_get.return_value = mock_response

        scraper = ContentScraper(
            "http://example.com", include_classes=["article-content"]
        )
        result = scraper.fetch_content()

        content = result["content"]

        # Should include specified class
        assert "Main Article Title" in content
        assert "main content" in content

        # Should exclude other content
        assert "Navigation content" not in content
        assert "Comments" not in content
        assert "Footer content" not in content

    @patch("requests.get")
    def test_exclude_classes(self, mock_get, mock_response):
        """Test excluding elements with specific classes."""
        mock_get.return_value = mock_response

        scraper = ContentScraper(
            "http://example.com",
            exclude_classes=["navigation", "sidebar", "comments-section"],
        )
        result = scraper.fetch_content()

        content = result["content"]

        # Should include non-excluded content
        assert "Main Article Title" in content
        assert "main content" in content

        # Should exclude specified classes
        assert "Navigation content" not in content
        assert "Sidebar content" not in content
        assert "Comment content" not in content

    @patch("requests.get")
    def test_combined_filtering(self, mock_get, mock_response):
        """Test combining different filtering options."""
        mock_get.return_value = mock_response

        # Include specific tags and exclude certain classes within them
        scraper = ContentScraper(
            "http://example.com", include_tags=["article"], exclude_classes=["sidebar"]
        )
        result = scraper.fetch_content()

        content = result["content"]

        # Should include article content
        assert "Main Article Title" in content
        assert "main content" in content

        # Should exclude sidebar even though it's within article
        assert "Sidebar content" not in content

        # Should exclude everything outside article tag
        assert "Comments" not in content
        assert "Navigation content" not in content

    @patch("requests.get")
    def test_empty_result_with_strict_filtering(self, mock_get, mock_response):
        """Test that overly strict filtering doesn't break."""
        mock_get.return_value = mock_response

        # Include only non-existent ID
        scraper = ContentScraper("http://example.com", include_ids=["non-existent-id"])
        result = scraper.fetch_content()

        # Should still return a valid result, just with empty content
        assert result is not None
        assert "hash" in result
        assert "content" in result
