"""Tests for configuration parsing with new structure."""

import tempfile
import tomllib
from unittest.mock import patch
import os

from watcher.core.proxy_manager import ProxyManager


class TestConfigParsing:
    """Test configuration file parsing with new structure."""

    def test_parse_config_with_defaults(self):
        """Test parsing config with defaults section."""
        config_content = """
[watcher.defaults]
min_hours = 168
exclude_tags = ["script", "style", "nav", "header", "footer"]
max_retries = 3
proxy_mode = "on_failure"
proxies = ["scrapingant", "scraperapi"]

[[watcher.sites]]
url = "https://example.com/feed1"
feed_name = "feed1"
min_hours = 24  # Override default

[[watcher.sites]]
url = "https://example.com/feed2"
feed_name = "feed2"
# Uses all defaults
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse the config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Verify structure
            assert "watcher" in config
            assert "defaults" in config["watcher"]
            assert "sites" in config["watcher"]

            # Check defaults
            defaults = config["watcher"]["defaults"]
            assert defaults["min_hours"] == 168
            assert defaults["max_retries"] == 3
            assert defaults["proxy_mode"] == "on_failure"
            assert defaults["proxies"] == ["scrapingant", "scraperapi"]
            assert defaults["exclude_tags"] == [
                "script",
                "style",
                "nav",
                "header",
                "footer",
            ]

            # Check sites
            sites = config["watcher"]["sites"]
            assert len(sites) == 2
            assert sites[0]["min_hours"] == 24  # Override
            assert sites[1].get("min_hours") is None  # Will use default

        finally:
            os.unlink(config_path)

    def test_parse_proxy_configuration(self):
        """Test parsing proxy configuration."""
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

[proxies.custom_proxy]
type = "url_template"
template = "https://proxy.example.com/fetch?target={encoded_url}&key={env:CUSTOM_PROXY_KEY}"
encoding = "base64"
env_vars = ["CUSTOM_PROXY_KEY"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse the config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Verify proxy structure
            assert "proxies" in config
            assert len(config["proxies"]) == 3

            # Check scrapingant proxy
            scrapingant = config["proxies"]["scrapingant"]
            assert scrapingant["type"] == "url_template"
            assert "{encoded_url}" in scrapingant["template"]
            assert "{env:SCRAPINGANT_API_KEY}" in scrapingant["template"]
            assert scrapingant["encoding"] == "url"
            assert scrapingant["env_vars"] == ["SCRAPINGANT_API_KEY"]

            # Check custom proxy with base64
            custom = config["proxies"]["custom_proxy"]
            assert custom["encoding"] == "base64"
            assert custom["env_vars"] == ["CUSTOM_PROXY_KEY"]

        finally:
            os.unlink(config_path)

    @patch.dict(os.environ, {"TEST_PROXY_KEY": "test_key_123"})
    def test_proxy_manager_with_config(self):
        """Test ProxyManager can load from parsed config."""
        config_content = """
[proxies]

[proxies.test_proxy]
type = "url_template"
template = "https://proxy.test.com?url={encoded_url}&key={env:TEST_PROXY_KEY}"
encoding = "url"
env_vars = ["TEST_PROXY_KEY"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            # Parse and create ProxyManager
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            proxy_manager = ProxyManager(config.get("proxies", {}))

            # Verify proxy was loaded
            assert "test_proxy" in proxy_manager.get_available_proxies()

            # Test URL transformation
            transformed = proxy_manager.transform_url(
                "https://example.com", "test_proxy"
            )
            assert (
                transformed
                == "https://proxy.test.com?url=https%3A%2F%2Fexample.com&key=test_key_123"
            )

        finally:
            os.unlink(config_path)

    def test_complete_example_from_docs(self):
        """Test the complete example from documentation."""
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
            # Parse the complete config
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Verify all sections exist
            assert "proxies" in config
            assert "watcher" in config
            assert "defaults" in config["watcher"]
            assert "sites" in config["watcher"]

            # Verify proxy configuration
            assert "scrapingant" in config["proxies"]

            # Verify defaults
            defaults = config["watcher"]["defaults"]
            assert defaults["min_hours"] == 168
            assert defaults["proxy_mode"] == "on_failure"
            assert defaults["proxies"] == ["scrapingant"]

            # Verify sites with overrides
            sites = config["watcher"]["sites"]
            assert len(sites) == 2

            # First site overrides min_hours
            assert sites[0]["feed_name"] == "example-changelog"
            assert sites[0]["min_hours"] == 24

            # Second site overrides proxy_mode and max_retries
            assert sites[1]["feed_name"] == "restricted-api"
            assert sites[1]["proxy_mode"] == "always"
            assert sites[1]["max_retries"] == 5

        finally:
            os.unlink(config_path)

    def test_merge_defaults_with_site_config(self):
        """Test merging defaults with site-specific config."""
        config_content = """
[watcher.defaults]
min_hours = 168
exclude_tags = ["script", "style"]
max_retries = 3
proxy_mode = "on_failure"
proxies = ["proxy1", "proxy2"]

[[watcher.sites]]
url = "https://example.com"
feed_name = "test"
proxy_mode = "always"  # Override
# min_hours not specified, should use default
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            defaults = config["watcher"]["defaults"]
            site = config["watcher"]["sites"][0]

            # Simulate merging (as done in cli_batch.py)
            site_config = {**defaults, **site}

            # Verify merged config
            assert site_config["min_hours"] == 168  # From defaults
            assert site_config["proxy_mode"] == "always"  # Override
            assert site_config["max_retries"] == 3  # From defaults
            assert site_config["proxies"] == ["proxy1", "proxy2"]  # From defaults
            assert site_config["feed_name"] == "test"  # From site
            assert site_config["url"] == "https://example.com"  # From site

        finally:
            os.unlink(config_path)

    def test_all_proxy_modes(self):
        """Test all proxy mode options are valid."""
        valid_modes = ["always", "on_failure", "never"]

        for mode in valid_modes:
            config_content = f"""
[watcher.defaults]
proxy_mode = "{mode}"

[[watcher.sites]]
url = "https://example.com"
feed_name = "test"
"""

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False
            ) as f:
                f.write(config_content)
                config_path = f.name

            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                assert config["watcher"]["defaults"]["proxy_mode"] == mode

            finally:
                os.unlink(config_path)

    def test_all_encoding_types(self):
        """Test all encoding types are valid."""
        valid_encodings = ["url", "base64", "none"]

        for encoding in valid_encodings:
            config_content = f"""
[proxies]
[proxies.test_proxy]
type = "url_template"
template = "https://proxy.com?url={{encoded_url}}"
encoding = "{encoding}"
env_vars = []
"""

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".toml", delete=False
            ) as f:
                f.write(config_content)
                config_path = f.name

            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                assert config["proxies"]["test_proxy"]["encoding"] == encoding

            finally:
                os.unlink(config_path)

    def test_backwards_compatibility(self):
        """Test that old format still works."""
        old_format = """
[[watcher.sites]]
url = "https://example.com"
feed_name = "test"
min_hours = 24
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(old_format)
            config_path = f.name

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Old format should still parse
            assert "watcher" in config
            assert "sites" in config["watcher"]
            assert len(config["watcher"]["sites"]) == 1
            assert config["watcher"]["sites"][0]["feed_name"] == "test"

        finally:
            os.unlink(config_path)
