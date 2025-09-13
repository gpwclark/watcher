"""Tests for proxy manager functionality."""

import os
import pytest
from unittest.mock import patch
from watcher.core.proxy_manager import ProxyConfig, ProxyManager


class TestProxyConfig:
    """Test ProxyConfig class."""

    def test_url_encoding(self):
        """Test URL encoding."""
        config = {
            "type": "url_template",
            "template": "https://proxy.com?url={encoded_url}",
            "encoding": "url",
            "env_vars": [],
        }
        proxy = ProxyConfig("test", config)
        result = proxy.transform_url("https://example.com/path?query=1")
        assert (
            result
            == "https://proxy.com?url=https%3A%2F%2Fexample.com%2Fpath%3Fquery%3D1"
        )

    def test_base64_encoding(self):
        """Test base64 encoding."""
        config = {
            "type": "url_template",
            "template": "https://proxy.com?target={encoded_url}",
            "encoding": "base64",
            "env_vars": [],
        }
        proxy = ProxyConfig("test", config)
        result = proxy.transform_url("https://example.com")
        # Base64 of "https://example.com" is "aHR0cHM6Ly9leGFtcGxlLmNvbQ=="
        assert result == "https://proxy.com?target=aHR0cHM6Ly9leGFtcGxlLmNvbQ=="

    def test_no_encoding(self):
        """Test no encoding."""
        config = {
            "type": "url_template",
            "template": "https://proxy.com/{url}/fetch",
            "encoding": "none",
            "env_vars": [],
        }
        proxy = ProxyConfig("test", config)
        result = proxy.transform_url("https://example.com")
        assert result == "https://proxy.com/https://example.com/fetch"

    @patch.dict(os.environ, {"TEST_API_KEY": "secret123"})
    def test_environment_variable_substitution(self):
        """Test environment variable substitution."""
        config = {
            "type": "url_template",
            "template": "https://proxy.com?url={encoded_url}&key={env:TEST_API_KEY}",
            "encoding": "url",
            "env_vars": ["TEST_API_KEY"],
        }
        proxy = ProxyConfig("test", config)
        result = proxy.transform_url("https://example.com")
        assert result == "https://proxy.com?url=https%3A%2F%2Fexample.com&key=secret123"

    def test_missing_environment_variable(self):
        """Test error when required environment variable is missing."""
        config = {
            "type": "url_template",
            "template": "https://proxy.com?key={env:MISSING_KEY}",
            "encoding": "url",
            "env_vars": ["MISSING_KEY"],
        }
        with pytest.raises(
            ValueError, match="requires environment variable MISSING_KEY"
        ):
            ProxyConfig("test", config)

    def test_missing_template(self):
        """Test error when template is missing."""
        config = {"type": "url_template", "encoding": "url", "env_vars": []}
        with pytest.raises(ValueError, match="missing template"):
            ProxyConfig("test", config)


class TestProxyManager:
    """Test ProxyManager class."""

    @patch.dict(os.environ, {"API_KEY1": "key1", "API_KEY2": "key2"})
    def test_multiple_proxies(self):
        """Test managing multiple proxies."""
        config = {
            "proxy1": {
                "type": "url_template",
                "template": "https://proxy1.com?url={encoded_url}&key={env:API_KEY1}",
                "encoding": "url",
                "env_vars": ["API_KEY1"],
            },
            "proxy2": {
                "type": "url_template",
                "template": "https://proxy2.com?target={encoded_url}&auth={env:API_KEY2}",
                "encoding": "base64",
                "env_vars": ["API_KEY2"],
            },
        }

        manager = ProxyManager(config)
        assert len(manager.proxies) == 2
        assert "proxy1" in manager.proxies
        assert "proxy2" in manager.proxies

    @patch.dict(os.environ, {"API_KEY": "testkey"})
    def test_transform_url(self):
        """Test URL transformation through manager."""
        config = {
            "test_proxy": {
                "type": "url_template",
                "template": "https://proxy.com?url={encoded_url}&key={env:API_KEY}",
                "encoding": "url",
                "env_vars": ["API_KEY"],
            }
        }

        manager = ProxyManager(config)
        result = manager.transform_url("https://example.com", "test_proxy")
        assert result == "https://proxy.com?url=https%3A%2F%2Fexample.com&key=testkey"

    def test_transform_url_invalid_proxy(self):
        """Test transformation with invalid proxy ID."""
        manager = ProxyManager({})
        result = manager.transform_url("https://example.com", "nonexistent")
        assert result is None

    def test_get_available_proxies(self):
        """Test getting list of available proxies."""
        config = {
            "proxy1": {
                "type": "url_template",
                "template": "https://proxy1.com?url={url}",
                "encoding": "none",
                "env_vars": [],
            },
            "proxy2": {
                "type": "url_template",
                "template": "https://proxy2.com?url={url}",
                "encoding": "none",
                "env_vars": [],
            },
        }

        manager = ProxyManager(config)
        available = manager.get_available_proxies()
        assert len(available) == 2
        assert "proxy1" in available
        assert "proxy2" in available

    @patch.dict(os.environ, {"GOOD_KEY": "key1"})
    def test_skip_invalid_proxy(self):
        """Test that invalid proxies are skipped."""
        config = {
            "good_proxy": {
                "type": "url_template",
                "template": "https://proxy.com?key={env:GOOD_KEY}",
                "encoding": "url",
                "env_vars": ["GOOD_KEY"],
            },
            "bad_proxy": {
                "type": "url_template",
                "template": "https://proxy.com?key={env:MISSING_KEY}",
                "encoding": "url",
                "env_vars": ["MISSING_KEY"],  # This env var doesn't exist
            },
        }

        manager = ProxyManager(config)
        # Should only load the good proxy
        assert len(manager.proxies) == 1
        assert "good_proxy" in manager.proxies
        assert "bad_proxy" not in manager.proxies
