"""Test that the actual watcher-config.toml files are valid."""

import tomllib
from pathlib import Path
import pytest


class TestActualConfigs:
    """Test actual configuration files in the repository."""

    def test_main_watcher_config(self):
        """Test the main watcher-config.toml is valid."""
        config_path = Path("watcher-config.toml")
        if not config_path.exists():
            pytest.skip("watcher-config.toml not found")

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Check structure
        assert "watcher" in config
        assert "sites" in config["watcher"]

        # Check defaults if present
        if "defaults" in config["watcher"]:
            defaults = config["watcher"]["defaults"]

            # Verify default values are valid types
            if "min_hours" in defaults:
                assert isinstance(defaults["min_hours"], (int, float))
                assert defaults["min_hours"] > 0

            if "max_retries" in defaults:
                assert isinstance(defaults["max_retries"], int)
                assert defaults["max_retries"] > 0

            if "proxy_mode" in defaults:
                assert defaults["proxy_mode"] in ["always", "on_failure", "never"]

            if "proxies" in defaults:
                assert isinstance(defaults["proxies"], list)

            if "exclude_tags" in defaults:
                assert isinstance(defaults["exclude_tags"], list)

        # Check each site
        for site in config["watcher"]["sites"]:
            # Required fields
            assert "url" in site
            assert "feed_name" in site

            # URL should be valid
            assert site["url"].startswith(("http://", "https://"))

            # feed_name should be a string
            assert isinstance(site["feed_name"], str)
            assert len(site["feed_name"]) > 0

            # Optional fields should have correct types if present
            if "min_hours" in site:
                assert isinstance(site["min_hours"], (int, float))
                assert site["min_hours"] > 0

            if "proxy_mode" in site:
                assert site["proxy_mode"] in ["always", "on_failure", "never"]

            if "max_retries" in site:
                assert isinstance(site["max_retries"], int)
                assert site["max_retries"] > 0

            if "proxies" in site:
                assert isinstance(site["proxies"], list)

            if "exclude_tags" in site:
                assert isinstance(site["exclude_tags"], list)

    def test_example_watcher_config(self):
        """Test the example watcher-config.example.toml is valid."""
        config_path = Path("watcher-config.example.toml")
        if not config_path.exists():
            pytest.skip("watcher-config.example.toml not found")

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Check proxy section if present
        if "proxies" in config:
            for proxy_name, proxy_config in config["proxies"].items():
                # Required fields for proxy
                assert "type" in proxy_config
                assert "template" in proxy_config
                assert "encoding" in proxy_config
                assert "env_vars" in proxy_config

                # Validate values
                assert proxy_config["type"] == "url_template"
                assert proxy_config["encoding"] in ["url", "base64", "none"]
                assert isinstance(proxy_config["env_vars"], list)

                # Template should contain placeholders
                template = proxy_config["template"]
                assert "{encoded_url}" in template or "{url}" in template

                # If env_vars specified, they should be in template
                for env_var in proxy_config["env_vars"]:
                    assert f"{{env:{env_var}}}" in template

        # Check watcher section
        assert "watcher" in config

        # Check defaults if present
        if "defaults" in config["watcher"]:
            defaults = config["watcher"]["defaults"]

            # All values should be valid
            if "proxy_mode" in defaults:
                assert defaults["proxy_mode"] in ["always", "on_failure", "never"]

            if "proxies" in defaults:
                # If proxies are specified in defaults, they should exist in proxy section
                if "proxies" in config:
                    for proxy_name in defaults["proxies"]:
                        if proxy_name:  # Skip empty strings
                            assert proxy_name in config["proxies"], (
                                f"Proxy '{proxy_name}' referenced but not defined"
                            )

        # Check sites
        assert "sites" in config["watcher"]
        for site in config["watcher"]["sites"]:
            assert "url" in site
            assert "feed_name" in site

            # If site references proxies, they should exist
            if "proxies" in site and "proxies" in config:
                for proxy_name in site["proxies"]:
                    if proxy_name:  # Skip empty strings
                        assert proxy_name in config["proxies"], (
                            f"Proxy '{proxy_name}' referenced but not defined"
                        )

    def test_config_merging_simulation(self):
        """Test that config merging works as expected."""
        config_path = Path("watcher-config.toml")
        if not config_path.exists():
            pytest.skip("watcher-config.toml not found")

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Get defaults if they exist
        defaults = {}
        if "watcher" in config and "defaults" in config["watcher"]:
            defaults = config["watcher"]["defaults"]

        # Simulate merging for each site
        for site in config["watcher"]["sites"]:
            # Merge defaults with site config
            merged = {**defaults, **site}

            # Verify merged config has all necessary fields
            assert "url" in merged
            assert "feed_name" in merged

            # If defaults had values, they should be in merged unless overridden
            for key, value in defaults.items():
                if key not in site:
                    assert merged[key] == value, f"Default {key} not properly merged"

            # Site-specific values should override defaults
            for key, value in site.items():
                assert merged[key] == value, (
                    f"Site value {key} not properly overriding default"
                )
