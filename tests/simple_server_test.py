#!/usr/bin/env python3
"""Simple test to debug server issues."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests


class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Hello World</body></html>")

    def log_message(self, format, *args):
        print(f"[Server] {format % args}")


# Start server
server = HTTPServer(("localhost", 9999), SimpleHandler)
thread = threading.Thread(target=server.serve_forever)
thread.daemon = True
thread.start()
print("Server started on http://localhost:9999")
time.sleep(0.5)

# Test it
try:
    response = requests.get("http://localhost:9999/", timeout=5)
    print(f"Response: {response.status_code}")
    print(f"Content: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Stop server
server.shutdown()
print("Server stopped")
