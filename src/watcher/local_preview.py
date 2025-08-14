"""Local preview server for watcher GitHub Pages site."""

import argparse
import http.server
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from watcher.static_site import StaticSiteGenerator


class PreviewServer:
    """Manages local preview of the GitHub Pages site."""

    def __init__(self, repo_path: Path, port: int = 8000):
        self.repo_path = Path(repo_path)
        self.port = port
        self.temp_dir = None
        self.server = None
        self.server_thread = None

    def clone_gh_pages(self) -> Path:
        """Clone gh-pages branch to temporary directory."""
        self.temp_dir = tempfile.mkdtemp(prefix="watcher-preview-")
        temp_path = Path(self.temp_dir)

        print(f"Cloning gh-pages branch to {temp_path}...")

        # Check if gh-pages branch exists
        result = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "gh-pages"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )

        if "gh-pages" in result.stdout:
            # Clone only gh-pages branch
            subprocess.run(
                [
                    "git",
                    "clone",
                    "-b",
                    "gh-pages",
                    "--single-branch",
                    str(self.repo_path),
                    "gh-pages",
                ],
                cwd=temp_path,
                check=True,
            )
            return temp_path / "gh-pages"
        else:
            print("No gh-pages branch found. Creating empty directory.")
            gh_pages_dir = temp_path / "gh-pages"
            gh_pages_dir.mkdir()
            return gh_pages_dir

    def run_watcher_batch(self, gh_pages_path: Path, base_url: str) -> None:
        """Run watcher-batch to generate content."""
        print("Running watcher-batch...")

        # Copy existing content/feeds from gh-pages if they exist
        gh_content = gh_pages_path / "content"
        gh_feeds = gh_pages_path / "feeds"

        if gh_content.exists():
            shutil.copytree(gh_content, self.repo_path / "content", dirs_exist_ok=True)
            print(
                f"Copied existing content: {len(list(gh_content.rglob('*.html')))} files"
            )

        if gh_feeds.exists():
            shutil.copytree(gh_feeds, self.repo_path / "feeds", dirs_exist_ok=True)
            print(f"Copied existing feeds: {len(list(gh_feeds.glob('*.xml')))} files")

        # Run watcher-batch
        cmd = [
            sys.executable,
            "-m",
            "watcher.cli_batch",
            "--config",
            "watcher-config.toml",
            "--base-url",
            base_url,
        ]

        # Don't use check=True - we want to continue even if some sites fail
        result = subprocess.run(cmd, cwd=self.repo_path)
        if result.returncode != 0:
            print(
                f"Warning: watcher-batch exited with code {result.returncode} (some sites may have failed)"
            )

    def generate_static_site(self, subdirectory: Optional[str] = None) -> Path:
        """Generate static site files."""
        print("Generating static site...")

        content_dir = self.repo_path / "content"
        feeds_dir = self.repo_path / "feeds"
        deploy_dir = self.repo_path / "deploy"

        # Determine base URL
        base_url = "http://localhost:{}".format(self.port)
        if subdirectory:
            base_url = f"{base_url}/{subdirectory}"

        # Generate site
        generator = StaticSiteGenerator(base_url, deploy_dir)
        generator.generate_site(content_dir, feeds_dir, subdirectory)

        return deploy_dir

    def start_server(self, serve_dir: Path) -> None:
        """Start HTTP server in background thread."""
        os.chdir(serve_dir)

        class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, format, *args):
                # Only log errors
                if args[1] != "200":
                    super().log_message(format, *args)

        def serve():
            with socketserver.TCPServer(
                ("", self.port), QuietHTTPRequestHandler
            ) as httpd:
                self.server = httpd
                print(f"\n🚀 Preview server running at http://localhost:{self.port}")
                print("Press Ctrl+C to stop\n")
                httpd.serve_forever()

        self.server_thread = threading.Thread(target=serve, daemon=True)
        self.server_thread.start()

    def cleanup(self) -> None:
        """Clean up temporary directory."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")

    def run(
        self, subdirectory: Optional[str] = None, skip_watcher: bool = False
    ) -> None:
        """Run the preview server."""
        try:
            # Clone gh-pages branch
            gh_pages_path = self.clone_gh_pages()

            # Run watcher-batch unless skipped
            if not skip_watcher:
                base_url = f"http://localhost:{self.port}"
                if subdirectory:
                    base_url = f"{base_url}/{subdirectory}"
                self.run_watcher_batch(gh_pages_path, base_url)

            # Generate static site
            deploy_dir = self.generate_static_site(subdirectory)

            # Start server
            self.start_server(deploy_dir)

            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down preview server...")

        finally:
            self.cleanup()


def main():
    """Main entry point for preview server."""
    parser = argparse.ArgumentParser(
        description="Preview watcher GitHub Pages site locally"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run server on (default: 8000)"
    )
    parser.add_argument(
        "--subdirectory",
        help="Subdirectory to deploy to (e.g., 'tracker' for /tracker/)",
    )
    parser.add_argument(
        "--skip-watcher",
        action="store_true",
        help="Skip running watcher-batch (use existing content/feeds)",
    )

    args = parser.parse_args()

    # Run from current directory
    server = PreviewServer(Path.cwd(), args.port)
    server.run(args.subdirectory, args.skip_watcher)


if __name__ == "__main__":
    main()
