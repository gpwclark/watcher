"""Comprehensive integration tests for proxy functionality."""

import os
import tempfile
import threading
import urllib.parse
import base64
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from unittest.mock import patch

from watcher.core.proxy_manager import ProxyManager
from watcher.core.stats_tracker import StatsTracker
from watcher.core.error_feed import ErrorFeedManager
from watcher.lib import scrape_with_retries
from watcher.core.models import ScraperRequest


class ContentServerHandler(BaseHTTPRequestHandler):
    """Handler for the actual content server."""

    response_count = 0
    fail_direct_requests = False

    def do_GET(self):
        """Handle GET requests to content server."""
        self.__class__.response_count += 1

        # Check if this is a direct request (not through proxy)
        is_direct = "proxy-forwarded" not in self.headers

        if is_direct and self.__class__.fail_direct_requests:
            # Fail direct requests if configured
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Direct access forbidden")
        else:
            # Success response
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"""
            <html>
            <head><title>Content Server</title></head>
            <body>
                <h1>Content from origin server</h1>
                <p>Request count: {self.__class__.response_count}</p>
                <p>Via proxy: {not is_direct}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress log messages during tests."""
        pass


class ProxyServerHandler(BaseHTTPRequestHandler):
    """Handler for the proxy server."""

    request_count = 0
    api_key_received = None
    target_urls = []
    fail_count = 0
    max_failures = 0

    def do_GET(self):
        """Handle GET requests to proxy server."""
        self.__class__.request_count += 1

        # Parse query parameters
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Extract API key
        if "api_key" in params:
            self.__class__.api_key_received = params["api_key"][0]
        elif "key" in params:
            self.__class__.api_key_received = params["key"][0]

        # Extract target URL
        if "url" in params:
            target_url = params["url"][0]
            # URL might be encoded
            target_url = urllib.parse.unquote(target_url)
        elif "target" in params:
            # Might be base64 encoded
            target_url = base64.b64decode(params["target"][0]).decode()
        else:
            target_url = None

        if target_url:
            self.__class__.target_urls.append(target_url)

        # Simulate failures if configured
        if self.__class__.fail_count < self.__class__.max_failures:
            self.__class__.fail_count += 1
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Proxy server error")
            return

        # Make request to origin server (in real scenario)
        # For testing, we'll just return success
        if target_url:
            # In a real proxy, we'd fetch from target_url
            # For testing, we'll simulate a successful proxy response
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("X-Proxy-Used", "true")
            self.end_headers()

            # Simulate fetching from the content server
            # We'll make an actual request to test the full flow
            import requests

            try:
                # Extract port from target URL if it's our test server
                if "localhost" in target_url:
                    # Add header to indicate this is via proxy
                    response = requests.get(
                        target_url, headers={"proxy-forwarded": "true"}, timeout=1
                    )
                    self.wfile.write(response.content)
                else:
                    # For non-localhost URLs, return mock content
                    html = f"""
                    <html>
                    <head><title>Proxied Content</title></head>
                    <body>
                        <h1>Content via Proxy</h1>
                        <p>Target: {target_url}</p>
                        <p>API Key: {self.__class__.api_key_received}</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode())
            except Exception as e:
                self.wfile.write(f"Proxy fetch error: {e}".encode())
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing target URL")

    def log_message(self, format, *args):
        """Suppress log messages during tests."""
        pass


class TestProxyIntegration:
    """Test proxy functionality with real HTTP servers."""

    def setup_method(self):
        """Reset handler state before each test."""
        ContentServerHandler.response_count = 0
        ContentServerHandler.fail_direct_requests = False
        ProxyServerHandler.request_count = 0
        ProxyServerHandler.api_key_received = None
        ProxyServerHandler.target_urls = []
        ProxyServerHandler.fail_count = 0
        ProxyServerHandler.max_failures = 0

    @patch.dict(os.environ, {"TEST_PROXY_KEY": "secret123", "BACKUP_KEY": "backup456"})
    def test_proxy_with_environment_variables(self):
        """Test that environment variables are properly substituted in proxy URLs."""
        # Start content server
        content_server = HTTPServer(("localhost", 0), ContentServerHandler)
        content_port = content_server.server_address[1]

        # Start proxy server
        proxy_server = HTTPServer(("localhost", 0), ProxyServerHandler)
        proxy_port = proxy_server.server_address[1]

        # Run servers in background
        content_thread = threading.Thread(target=content_server.serve_forever)
        content_thread.daemon = True
        content_thread.start()

        proxy_thread = threading.Thread(target=proxy_server.serve_forever)
        proxy_thread.daemon = True
        proxy_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxy with environment variable
                proxy_config = {
                    "test_proxy": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy_port}?url={{encoded_url}}&api_key={{env:TEST_PROXY_KEY}}",
                        "encoding": "url",
                        "env_vars": ["TEST_PROXY_KEY"],
                    }
                }

                proxy_manager = ProxyManager(proxy_config)
                stats_tracker = StatsTracker(Path(tmpdir))

                content_url = f"http://localhost:{content_port}/test"
                request = ScraperRequest(url=content_url, feed_name="proxy_test")

                # Make request through proxy
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    proxies=["test_proxy"],
                    proxy_mode="always",
                    max_retries=1,
                )

                assert result.success

                # Verify environment variable was received by proxy
                assert ProxyServerHandler.api_key_received == "secret123"

                # Verify target URL was properly encoded
                assert len(ProxyServerHandler.target_urls) == 1
                assert ProxyServerHandler.target_urls[0] == content_url

        finally:
            content_server.shutdown()
            proxy_server.shutdown()

    @patch.dict(os.environ, {"PROXY_KEY": "test_key"})
    def test_proxy_fallback_on_direct_failure(self):
        """Test that proxy is used when direct request fails."""
        # Start content server that blocks direct access
        content_server = HTTPServer(("localhost", 0), ContentServerHandler)
        content_port = content_server.server_address[1]
        ContentServerHandler.fail_direct_requests = True

        # Start proxy server
        proxy_server = HTTPServer(("localhost", 0), ProxyServerHandler)
        proxy_port = proxy_server.server_address[1]

        content_thread = threading.Thread(target=content_server.serve_forever)
        content_thread.daemon = True
        content_thread.start()

        proxy_thread = threading.Thread(target=proxy_server.serve_forever)
        proxy_thread.daemon = True
        proxy_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxy
                proxy_config = {
                    "fallback_proxy": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy_port}?url={{encoded_url}}&key={{env:PROXY_KEY}}",
                        "encoding": "url",
                        "env_vars": ["PROXY_KEY"],
                    }
                }

                proxy_manager = ProxyManager(proxy_config)
                stats_tracker = StatsTracker(Path(tmpdir))
                error_feed_manager = ErrorFeedManager(Path(tmpdir))

                content_url = f"http://localhost:{content_port}/restricted"
                request = ScraperRequest(url=content_url, feed_name="fallback_test")

                # Try with on_failure mode (default)
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    error_feed_manager=error_feed_manager,
                    proxies=["fallback_proxy"],
                    proxy_mode="on_failure",
                    max_retries=2,
                )

                # Should succeed via proxy after direct failure
                assert result.success

                # Verify proxy was used
                assert ProxyServerHandler.request_count == 1
                assert ProxyServerHandler.api_key_received == "test_key"

                # Check statistics
                proxy_stats = stats_tracker.get_proxy_success_rate(
                    "fallback_proxy", content_url
                )
                assert proxy_stats == 1.0  # Proxy succeeded

        finally:
            content_server.shutdown()
            proxy_server.shutdown()

    @patch.dict(os.environ, {"PROXY1_KEY": "key1", "PROXY2_KEY": "key2"})
    def test_multiple_proxy_retry_chain(self):
        """Test intelligent retry with multiple proxies."""
        # Start content server
        content_server = HTTPServer(("localhost", 0), ContentServerHandler)
        content_port = content_server.server_address[1]

        # Start first proxy server (will fail initially)
        proxy1_server = HTTPServer(("localhost", 0), ProxyServerHandler)
        proxy1_port = proxy1_server.server_address[1]

        # Start second proxy server (will succeed)
        class SuccessProxyHandler(BaseHTTPRequestHandler):
            """Always successful proxy."""

            request_count = 0

            def do_GET(self):
                self.__class__.request_count += 1
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = "<html><body>Success from proxy2</body></html>"
                self.wfile.write(html.encode())

            def log_message(self, format, *args):
                pass

        proxy2_server = HTTPServer(("localhost", 0), SuccessProxyHandler)
        proxy2_port = proxy2_server.server_address[1]

        # Configure first proxy to fail once
        ProxyServerHandler.max_failures = 1

        # Start all servers
        for server in [content_server, proxy1_server, proxy2_server]:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure multiple proxies
                proxy_config = {
                    "proxy1": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy1_port}?url={{encoded_url}}&key={{env:PROXY1_KEY}}",
                        "encoding": "url",
                        "env_vars": ["PROXY1_KEY"],
                    },
                    "proxy2": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy2_port}?url={{encoded_url}}&key={{env:PROXY2_KEY}}",
                        "encoding": "url",
                        "env_vars": ["PROXY2_KEY"],
                    },
                }

                proxy_manager = ProxyManager(proxy_config)
                stats_tracker = StatsTracker(Path(tmpdir))

                content_url = f"http://localhost:{content_port}/test"
                request = ScraperRequest(url=content_url, feed_name="multi_proxy_test")

                # Attempt with both proxies
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    proxies=["proxy1", "proxy2"],
                    proxy_mode="always",
                    max_retries=3,
                )

                # Should eventually succeed
                assert result.success

                # Verify both proxies were tried
                assert ProxyServerHandler.request_count == 1  # First proxy tried
                assert SuccessProxyHandler.request_count == 1  # Second proxy succeeded

                # Check statistics
                proxy1_stats = stats_tracker.get_proxy_success_rate(
                    "proxy1", content_url
                )
                proxy2_stats = stats_tracker.get_proxy_success_rate(
                    "proxy2", content_url
                )

                assert proxy1_stats == 0.0  # First proxy failed
                assert proxy2_stats == 1.0  # Second proxy succeeded

                # Next request should prefer proxy2 based on history
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=stats_tracker,
                    proxies=["proxy1", "proxy2"],
                    proxy_mode="always",
                    max_retries=3,
                )

                # Should use proxy2 first this time (intelligent retry)
                assert result.success
                assert SuccessProxyHandler.request_count == 2  # Proxy2 used again

        finally:
            content_server.shutdown()
            proxy1_server.shutdown()
            proxy2_server.shutdown()

    @patch.dict(os.environ, {"PROXY_KEY": "base64_test"})
    def test_base64_encoding(self):
        """Test proxy with base64 URL encoding."""
        # Start servers
        content_server = HTTPServer(("localhost", 0), ContentServerHandler)
        content_port = content_server.server_address[1]

        proxy_server = HTTPServer(("localhost", 0), ProxyServerHandler)
        proxy_port = proxy_server.server_address[1]

        for server in [content_server, proxy_server]:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxy with base64 encoding
                proxy_config = {
                    "base64_proxy": {
                        "type": "url_template",
                        "template": f"http://localhost:{proxy_port}?target={{encoded_url}}&key={{env:PROXY_KEY}}",
                        "encoding": "base64",
                        "env_vars": ["PROXY_KEY"],
                    }
                }

                proxy_manager = ProxyManager(proxy_config)

                content_url = f"http://localhost:{content_port}/test"

                # Transform URL
                transformed = proxy_manager.transform_url(content_url, "base64_proxy")

                # Verify base64 encoding
                expected_base64 = base64.b64encode(content_url.encode()).decode()
                assert f"target={expected_base64}" in transformed
                assert "key=base64_test" in transformed

                # Make actual request
                request = ScraperRequest(url=content_url, feed_name="base64_test")
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=StatsTracker(Path(tmpdir)),
                    proxies=["base64_proxy"],
                    proxy_mode="always",
                    max_retries=1,
                )

                assert result.success

                # Verify proxy received base64-encoded URL
                assert ProxyServerHandler.target_urls[0] == content_url

        finally:
            content_server.shutdown()
            proxy_server.shutdown()

    def test_proxy_never_mode(self):
        """Test that proxy_mode='never' bypasses all proxies."""
        # Start only content server
        content_server = HTTPServer(("localhost", 0), ContentServerHandler)
        content_port = content_server.server_address[1]

        content_thread = threading.Thread(target=content_server.serve_forever)
        content_thread.daemon = True
        content_thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Configure proxy (that doesn't actually exist)
                proxy_config = {
                    "unused_proxy": {
                        "type": "url_template",
                        "template": "http://nonexistent:9999?url={encoded_url}",
                        "encoding": "url",
                        "env_vars": [],
                    }
                }

                proxy_manager = ProxyManager(proxy_config)

                content_url = f"http://localhost:{content_port}/direct"
                request = ScraperRequest(url=content_url, feed_name="never_mode_test")

                # Request with proxy_mode="never"
                result = scrape_with_retries(
                    request=request,
                    proxy_manager=proxy_manager,
                    stats_tracker=StatsTracker(Path(tmpdir)),
                    proxies=["unused_proxy"],
                    proxy_mode="never",
                    max_retries=1,
                )

                # Should succeed with direct request
                assert result.success

                # Verify only direct request was made
                assert ContentServerHandler.response_count == 1

        finally:
            content_server.shutdown()
