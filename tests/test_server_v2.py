#!/usr/bin/env python3
"""Simplified test server."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from pathlib import Path

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Simple static mapping for now
        pages = {
            '/test': '<html><body>Test Page</body></html>',
            '/static-article': self.load_file('static-article.html'),
            '/dynamic-article-1': self.load_file('dynamic-article-1-v1.html'),
            '/dynamic-article-2': self.load_file('dynamic-article-2-v1.html'),
        }
        
        content = pages.get(self.path)
        if content:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(404)
    
    def load_file(self, filename):
        file_path = Path(__file__).parent / 'fixtures' / 'html_pages' / filename
        if file_path.exists():
            return file_path.read_text()
        return f"<html><body>File not found: {filename}</body></html>"
    
    def log_message(self, format, *args):
        print(f"[Server] {format % args}")

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8889), TestHandler)
    print("Server running on http://localhost:8889")
    print("Test URLs:")
    print("  http://localhost:8889/test")
    print("  http://localhost:8889/static-article")
    print("  http://localhost:8889/dynamic-article-1")
    print("  http://localhost:8889/dynamic-article-2")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")