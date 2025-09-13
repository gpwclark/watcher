"""Manage proxy configurations and URL transformations."""

import os
import base64
from urllib.parse import quote
from typing import Dict, Optional, List, Any


class ProxyConfig:
    """Configuration for a single proxy."""

    def __init__(self, proxy_id: str, config: Dict[str, Any]):
        self.id = proxy_id
        self.type = config.get("type", "url_template")
        self.template = config.get("template", "")
        self.encoding = config.get("encoding", "url")
        self.env_vars = config.get("env_vars", [])
        self._validate()

    def _validate(self):
        """Validate proxy configuration."""
        if not self.template:
            raise ValueError(f"Proxy {self.id} missing template")

        # Check required environment variables
        for env_var in self.env_vars:
            if not os.environ.get(env_var):
                raise ValueError(
                    f"Proxy {self.id} requires environment variable {env_var}"
                )

    def transform_url(self, url: str) -> str:
        """Transform URL according to proxy configuration."""
        # Encode the URL based on encoding type
        if self.encoding == "url":
            encoded_url = quote(url, safe="")
        elif self.encoding == "base64":
            encoded_url = base64.b64encode(url.encode()).decode()
        else:  # none
            encoded_url = url

        # Build the template replacements
        replacements = {"encoded_url": encoded_url, "url": url}

        # Add environment variables
        for env_var in self.env_vars:
            replacements[f"env:{env_var}"] = os.environ.get(env_var, "")

        # Replace placeholders in template
        result = self.template
        for key, value in replacements.items():
            result = result.replace(f"{{{key}}}", value)

        return result


class ProxyManager:
    """Manage multiple proxy configurations."""

    def __init__(self, proxies_config: Optional[Dict[str, Dict]] = None):
        """Initialize proxy manager with configuration."""
        self.proxies: Dict[str, ProxyConfig] = {}
        if proxies_config:
            for proxy_id, config in proxies_config.items():
                try:
                    self.proxies[proxy_id] = ProxyConfig(proxy_id, config)
                except ValueError as e:
                    print(f"Warning: Skipping proxy {proxy_id}: {e}")

    def get_proxy(self, proxy_id: str) -> Optional[ProxyConfig]:
        """Get a specific proxy configuration."""
        return self.proxies.get(proxy_id)

    def transform_url(self, url: str, proxy_id: str) -> Optional[str]:
        """Transform URL using specified proxy."""
        proxy = self.get_proxy(proxy_id)
        if proxy:
            return proxy.transform_url(url)
        return None

    def get_available_proxies(self) -> List[str]:
        """Get list of available proxy IDs."""
        return list(self.proxies.keys())
