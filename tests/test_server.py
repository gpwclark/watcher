#!/usr/bin/env python3
"""
Test HTTP server for integration tests.
Serves different versions of pages based on the current test cycle.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from pathlib import Path


class CycleAwareHandler(BaseHTTPRequestHandler):
    """HTTP handler that serves different content based on test cycle."""

    current_cycle = 1

    def do_GET(self):
        """Handle GET requests with cycle-aware routing."""
        # Map URLs to files based on current cycle
        cycle_routes = {
            1: {
                "/static-article": "static-article.html",
                "/dynamic-article-1": "dynamic-article-1-v1.html",
                "/dynamic-article-2": "dynamic-article-2-v1.html",
            },
            2: {
                "/static-article": "static-article.html",
                "/dynamic-article-1": "dynamic-article-1-v2.html",
                "/dynamic-article-2": "dynamic-article-2-v1.html",
            },
            3: {
                "/static-article": "static-article.html",
                "/dynamic-article-1": "dynamic-article-1-v3.html",
                "/dynamic-article-2": "dynamic-article-2-v2.html",
            },
        }

        # Get the appropriate file for this cycle
        routes = cycle_routes.get(self.current_cycle, {})
        file_name = routes.get(self.path)

        if file_name:
            # Serve the HTML file
            file_path = Path(__file__).parent / "fixtures" / "html_pages" / file_name
            try:
                if file_path.exists():
                    with open(file_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    print(
                        f"[Cycle {self.current_cycle}] Served {self.path} -> {file_name}"
                    )
                else:
                    print(f"[Cycle {self.current_cycle}] File not found: {file_path}")
                    self.send_error(404, f"File not found: {file_path}")
            except Exception as e:
                print(f"[Cycle {self.current_cycle}] Error serving {self.path}: {e}")
                self.send_error(500, str(e))
        else:
            # 404 for unknown paths
            self.send_error(404, f"Not found: {self.path}")

    def log_message(self, format, *args):
        """Override to add cycle info to logs."""
        print(f"[Cycle {self.current_cycle}] {format % args}")


class TestServer:
    """Test server that can be controlled programmatically."""

    def __init__(self, port=8888):
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the server in a background thread."""
        self.server = HTTPServer(("localhost", self.port), CycleAwareHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print(f"Test server started on http://localhost:{self.port}")
        time.sleep(0.5)  # Give server time to start

    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.thread.join()
            print("Test server stopped")

    def set_cycle(self, cycle):
        """Set the current test cycle (1, 2, or 3)."""
        CycleAwareHandler.current_cycle = cycle
        print(f"Test server now serving cycle {cycle} content")


if __name__ == "__main__":
    # For manual testing
    server = TestServer()
    server.start()

    try:
        print("\nTest URLs:")
        print("  http://localhost:8888/static-article")
        print("  http://localhost:8888/dynamic-article-1")
        print("  http://localhost:8888/dynamic-article-2")
        print("\nPress Enter to advance to next cycle, or Ctrl+C to exit")

        for cycle in [1, 2, 3]:
            server.set_cycle(cycle)
            input(f"\nServing cycle {cycle} content. Press Enter to continue...")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop()
