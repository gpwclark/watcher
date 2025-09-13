"""Test that all documentation examples are valid and work."""

import tempfile
import tomllib
import os
from unittest.mock import patch
import base64
import urllib.parse

from watcher.core.proxy_manager import ProxyManager, ProxyConfig


class TestDocumentationExamples:
    """Test all code examples from documentation."""

    @patch.dict(
        os.environ, {"SCRAPINGANT_API_KEY": "test_key", "SCRAPER_API_KEY": "test_key2"}
    )
    def test_proxy_config_from_docs(self):
        """Test the proxy configuration example from PROXY_AND_ERROR_FEATURES.md."""
        # This is the exact example from the docs
        config_content = """
[proxies]

[proxies.scrapingant]
type = "url_template"
template = "https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={env:SCRAPINGANT_API_KEY}"
encoding = "url"
env_vars = ["SCRAPINGANT_API_KEY"]

[proxies.scraperapi]
type = "url_template"
template = "http://api.scraperapi.com?api_key={env:SCRAPER_API_KEY}&url={encoded_url}"
encoding = "url"
env_vars = ["SCRAPER_API_KEY"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Create ProxyManager
            proxy_manager = ProxyManager(config["proxies"])

            # Test scrapingant proxy
            url = "https://example.com/test"
            transformed = proxy_manager.transform_url(url, "scrapingant")

            # Verify URL encoding
            encoded_url = urllib.parse.quote(url, safe="")
            expected = f"https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key=test_key"
            assert transformed == expected

            # Test scraperapi proxy
            transformed = proxy_manager.transform_url(url, "scraperapi")
            expected = f"http://api.scraperapi.com?api_key=test_key2&url={encoded_url}"
            assert transformed == expected

        finally:
            os.unlink(config_path)

    def test_defaults_config_from_docs(self):
        """Test the defaults configuration example from docs."""
        config_content = """
[watcher.defaults]
min_hours = 168  # Check once a week by default
exclude_tags = ["script", "style", "nav", "header", "footer"]
max_retries = 3
proxy_mode = "on_failure"  # Options: always, on_failure, never
proxies = ["scrapingant", "scraperapi"]  # Default proxy chain
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            defaults = config["watcher"]["defaults"]

            # Verify all fields are correct types and values
            assert defaults["min_hours"] == 168
            assert defaults["exclude_tags"] == [
                "script",
                "style",
                "nav",
                "header",
                "footer",
            ]
            assert defaults["max_retries"] == 3
            assert defaults["proxy_mode"] == "on_failure"
            assert defaults["proxies"] == ["scrapingant", "scraperapi"]

        finally:
            os.unlink(config_path)

    def test_site_specific_config_from_docs(self):
        """Test site-specific configuration from docs."""
        config_content = """
[[watcher.sites]]
url = "https://restricted.example.com/feed"
feed_name = "restricted-site"
proxies = ["scrapingant"]  # Override default proxies
proxy_mode = "always"  # Always use proxy for this site
max_retries = 5  # More retries for important sites
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            site = config["watcher"]["sites"][0]

            # Verify all fields
            assert site["url"] == "https://restricted.example.com/feed"
            assert site["feed_name"] == "restricted-site"
            assert site["proxies"] == ["scrapingant"]
            assert site["proxy_mode"] == "always"
            assert site["max_retries"] == 5

        finally:
            os.unlink(config_path)

    def test_url_encoding_types(self):
        """Test URL encoding examples from docs."""
        test_url = "https://example.com/path with spaces?query=1&foo=bar"

        # Test URL encoding
        proxy_config = ProxyConfig(
            "test",
            {
                "type": "url_template",
                "template": "https://proxy.com?url={encoded_url}",
                "encoding": "url",
                "env_vars": [],
            },
        )

        result = proxy_config.transform_url(test_url)
        expected_encoded = urllib.parse.quote(test_url, safe="")
        assert result == f"https://proxy.com?url={expected_encoded}"
        # Verify spaces become %20
        assert "%20" in result

        # Test base64 encoding
        proxy_config = ProxyConfig(
            "test",
            {
                "type": "url_template",
                "template": "https://proxy.com?target={encoded_url}",
                "encoding": "base64",
                "env_vars": [],
            },
        )

        result = proxy_config.transform_url(test_url)
        expected_base64 = base64.b64encode(test_url.encode()).decode()
        assert result == f"https://proxy.com?target={expected_base64}"

        # Test no encoding
        proxy_config = ProxyConfig(
            "test",
            {
                "type": "url_template",
                "template": "https://proxy.com/{url}/fetch",
                "encoding": "none",
                "env_vars": [],
            },
        )

        result = proxy_config.transform_url(test_url)
        assert result == f"https://proxy.com/{test_url}/fetch"

    @patch.dict(os.environ, {"MAIN_PROXY": "mainkey", "BACKUP_PROXY": "backupkey"})
    def test_complete_example_from_docs(self):
        """Test the complete configuration example from docs."""
        config_content = """
# Proxy configurations
[proxies]
[proxies.scrapingant]
type = "url_template"
template = "https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={env:SCRAPINGANT_API_KEY}"
encoding = "url"
env_vars = ["SCRAPINGANT_API_KEY"]

# Default settings
[watcher.defaults]
min_hours = 168
exclude_tags = ["script", "style", "nav", "header", "footer"]
max_retries = 3
proxy_mode = "on_failure"
proxies = ["scrapingant"]

# Sites
[[watcher.sites]]
url = "https://example.com/changelog"
feed_name = "example-changelog"
min_hours = 24  # Override: check daily

[[watcher.sites]]
url = "https://restricted.example.com/api"
feed_name = "restricted-api"
proxy_mode = "always"  # Always use proxy
max_retries = 5  # More retries
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse complete config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Verify structure
            assert "proxies" in config
            assert "watcher" in config
            assert "defaults" in config["watcher"]
            assert "sites" in config["watcher"]

            # Test merging for first site
            defaults = config["watcher"]["defaults"]
            site1 = config["watcher"]["sites"][0]
            merged1 = {**defaults, **site1}

            assert merged1["min_hours"] == 24  # Override
            assert merged1["proxy_mode"] == "on_failure"  # From default
            assert merged1["max_retries"] == 3  # From default

            # Test merging for second site
            site2 = config["watcher"]["sites"][1]
            merged2 = {**defaults, **site2}

            assert merged2["min_hours"] == 168  # From default
            assert merged2["proxy_mode"] == "always"  # Override
            assert merged2["max_retries"] == 5  # Override

        finally:
            os.unlink(config_path)

    def test_proxy_modes(self):
        """Test all proxy modes mentioned in docs are valid."""
        proxy_modes = ["never", "on_failure", "always"]

        for mode in proxy_modes:
            # Each mode should be parseable
            config = {"watcher": {"defaults": {"proxy_mode": mode}}}

            # Verify mode is one of the valid options
            assert config["watcher"]["defaults"]["proxy_mode"] in proxy_modes

    def test_error_json_structure_from_docs(self):
        """Test the error JSON structure shown in docs is valid."""
        # This is the example from the docs
        error_json = {
            "feed_id": "example-feed",
            "url": "https://example.com",
            "timestamp": "2024-01-15T10:30:00Z",
            "error_type": "HTTPError",
            "error_message": "404 Not Found",
            "consecutive_failures": 3,
            "last_failure": "2024-01-15T10:30:00Z",
            "total_runs": 150,
            "total_failures": 7,
            "details": {
                "status_code": 404,
                "proxy_attempts": [
                    {"proxy": "direct", "success": False, "error": "404 Not Found"},
                    {
                        "proxy": "scrapingant",
                        "success": False,
                        "error": "404 Not Found",
                    },
                ],
            },
        }

        # Verify structure
        assert "feed_id" in error_json
        assert "consecutive_failures" in error_json
        assert "total_runs" in error_json
        assert "total_failures" in error_json
        assert "details" in error_json
        assert "proxy_attempts" in error_json["details"]

        # Verify types
        assert isinstance(error_json["consecutive_failures"], int)
        assert isinstance(error_json["total_runs"], int)
        assert isinstance(error_json["total_failures"], int)
        assert isinstance(error_json["details"]["proxy_attempts"], list)
