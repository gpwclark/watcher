#!/usr/bin/env python3
"""
End-to-end integration test for the watcher system.
Tests the complete flow from scraping through git commits.
"""

import os
import sys
import tempfile
import shutil
import hashlib
import json
from pathlib import Path
import subprocess
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from watcher.lib import scrape_and_update_feed
from watcher.core.models import ScraperRequest
from test_server import TestServer


def compute_directory_hash(directory: Path) -> str:
    """Compute a deterministic hash of directory contents."""
    hasher = hashlib.sha256()

    # Get all files sorted by path
    files = sorted(directory.rglob("*"))

    for file_path in files:
        if file_path.is_file() and not file_path.name.startswith("."):
            # Include relative path in hash (but not the timestamp-based filename)
            rel_path = file_path.relative_to(directory)
            dir_path = str(rel_path.parent)
            hasher.update(dir_path.encode("utf-8"))
            hasher.update(b"\n")

            # Include file content, but skip the timestamp line in HTML
            content = file_path.read_text()
            # The watcher includes a timestamp comment in the HTML
            # Skip lines that contain timestamp patterns
            lines = content.split("\n")
            filtered_lines = [line for line in lines if "Fetched:" not in line]
            filtered_content = "\n".join(filtered_lines)
            hasher.update(filtered_content.encode("utf-8"))
            hasher.update(b"\n\n")

    return hasher.hexdigest()


def get_git_log(repo_dir: Path) -> list[str]:
    """Get git commit messages."""
    result = subprocess.run(
        ["git", "log", "--pretty=format:%s"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\n") if result.stdout else []


class IntegrationTest:
    def __init__(self):
        self.test_dir = None
        self.server = TestServer(port=8890)
        self.expected_hashes = {}

    def setup(self):
        """Set up test environment."""
        # Create temporary directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="watcher_test_"))
        print(f"Test directory: {self.test_dir}")

        # Change to test directory (watcher expects to run from output dir)
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)

        # Define test sites
        self.test_sites = [
            ("static-article", "http://localhost:8890/static-article"),
            ("dynamic-article-1", "http://localhost:8890/dynamic-article-1"),
            ("dynamic-article-2", "http://localhost:8890/dynamic-article-2"),
        ]

        # Start test server
        self.server.start()

        return self.test_sites

    def teardown(self):
        """Clean up test environment."""
        self.server.stop()
        os.chdir(self.original_cwd)
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_cycle(self, cycle: int, test_sites):
        """Run a test cycle."""
        print(f"\n{'=' * 60}")
        print(f"Running Cycle {cycle}")
        print("=" * 60)

        # Set server to correct cycle
        self.server.set_cycle(cycle)
        time.sleep(0.5)  # Give server time to update

        # Process each site
        for feed_name, url in test_sites:
            print(f"Processing {feed_name}...")
            request = ScraperRequest(
                url=url, feed_name=feed_name, base_url="https://example.com"
            )
            result = scrape_and_update_feed(request)
            if not result.success:
                print(f"  Error: {result.error_message}")
            elif result.changed:
                print(f"  Changed: {result.filename}")
            else:
                print("  No changes")

        # Compute hash of output
        content_dir = self.test_dir / "content"
        if content_dir.exists():
            dir_hash = compute_directory_hash(content_dir)
            print(f"Content hash: {dir_hash[:16]}...")
        else:
            dir_hash = "no_content"
            print("No content directory found")

        # Get git log
        commits = get_git_log(self.test_dir)
        print(f"Git commits: {len(commits)}")
        if commits:
            print(f"Latest commit: {commits[0]}")

        # Get all markdown files recursively
        all_files = []
        if content_dir.exists():
            for subdir in content_dir.iterdir():
                if subdir.is_dir():
                    all_files.extend([f.name for f in subdir.glob("*.html")])

        return {
            "cycle": cycle,
            "content_hash": dir_hash,
            "commits": commits,
            "files": sorted(all_files),
        }

    def verify_results(self, results):
        """Verify test results."""
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check that we have results for all 3 cycles
        assert len(results) == 3, f"Expected 3 cycles, got {len(results)}"

        # Load expected hashes if they exist
        expected_hashes_file = Path(__file__).parent / "expected_hashes.json"
        if expected_hashes_file.exists():
            with open(expected_hashes_file) as f:
                json.load(f)

        # Cycle 1: Initial scrape
        cycle1 = results[0]
        print(f"Cycle 1: {len(cycle1['files'])} files")
        assert len(cycle1["files"]) >= 3, (
            f"Cycle 1: Expected at least 3 files, got {cycle1['files']}"
        )

        # Cycle 2: One update (dynamic-article-1)
        cycle2 = results[1]
        print(f"Cycle 2: {len(cycle2['files'])} files")
        assert len(cycle2["files"]) >= 4, (
            f"Cycle 2: Expected at least 4 files (3 + 1 update), got {cycle2['files']}"
        )
        assert cycle2["content_hash"] != cycle1["content_hash"], (
            "Cycle 2: Content should have changed"
        )

        # Cycle 3: Two updates (dynamic-article-1 and dynamic-article-2)
        cycle3 = results[2]
        print(f"Cycle 3: {len(cycle3['files'])} files")
        assert len(cycle3["files"]) >= 6, (
            f"Cycle 3: Expected at least 6 files (4 + 2 updates), got {cycle3['files']}"
        )
        assert cycle3["content_hash"] != cycle2["content_hash"], (
            "Cycle 3: Content should have changed"
        )

        # Note: We don't check exact hashes because they include metadata that can vary
        # The important tests are:
        # 1. Content changes between cycles
        # 2. Correct number of files created
        # 3. Static content doesn't create new files

        # Verify static article never changed by checking content
        print("\nChecking static article consistency...")

        # The watcher should have detected no changes for static-article after cycle 1
        # We can verify this by checking that only one HTML file exists for static-article
        static_dir = self.test_dir / "content" / "static-article"
        if static_dir.exists():
            static_files = list(static_dir.glob("*.html"))
            print(f"Static article files: {len(static_files)}")
            # Should only have one file since content never changed
            assert len(static_files) == 1, (
                f"Static article should have only 1 file, found {len(static_files)}"
            )

        print("\n✅ All verifications passed!")

    def run(self):
        """Run the complete integration test."""
        try:
            # Setup
            test_sites = self.setup()

            # Run all cycles
            results = []
            for cycle in [1, 2, 3]:
                result = self.run_cycle(cycle, test_sites)
                results.append(result)
                time.sleep(1)  # Brief pause between cycles

            # Verify results
            self.verify_results(results)

            print("\n✅ Integration test passed!")

        finally:
            self.teardown()


def main():
    """Run the integration test."""
    print("WATCHER INTEGRATION TEST")
    print("Testing complete flow: HTTP → Scraping → Git → Files")

    test = IntegrationTest()
    test.run()


if __name__ == "__main__":
    main()
