#!/usr/bin/env python3
"""Test the server manually to verify it's working."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import requests
import time
from test_server import TestServer


def test_server_urls():
    """Test that all URLs work correctly."""
    server = TestServer()
    server.start()

    try:
        # Test each cycle
        for cycle in [1, 2, 3]:
            print(f"\n{'=' * 50}")
            print(f"Testing Cycle {cycle}")
            print("=" * 50)

            server.set_cycle(cycle)
            time.sleep(0.1)

            # Test each URL
            for path in ["/static-article", "/dynamic-article-1", "/dynamic-article-2"]:
                url = f"http://localhost:8888{path}"
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        # Extract title from HTML
                        title_start = response.text.find("<title>") + 7
                        title_end = response.text.find("</title>")
                        title = response.text[title_start:title_end]
                        print(f"✓ {path} -> {title}")
                    else:
                        print(f"✗ {path} -> Status {response.status_code}")
                except Exception as e:
                    print(f"✗ {path} -> Error: {e}")

    finally:
        server.stop()


if __name__ == "__main__":
    test_server_urls()
