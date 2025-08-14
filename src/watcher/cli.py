"""Command-line interface for the watcher tool."""

import argparse
import sys
import os
from .lib import scrape_and_update_feed
from .core.models import ScraperRequest


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Git-scraping tool with RSS feed generation", prog="watcher"
    )
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument(
        "feed_name", help='Name for the RSS feed (e.g., "jank-progress")'
    )
    parser.add_argument(
        "--base-url", help="Base URL for RSS links (defaults to GitHub repo URL)"
    )

    args = parser.parse_args()

    # Create request object
    request = ScraperRequest(
        url=args.url, feed_name=args.feed_name, base_url=args.base_url
    )

    print(f"Scraping {request.url} for feed '{request.feed_name}'...")

    # Call library function
    result = scrape_and_update_feed(request)

    if not result.success:
        print(f"Error: {result.error_message}")
        sys.exit(1)

    if not result.changed:
        print("No changes detected - skipping RSS update")
        sys.exit(0)

    print(f"Saved new content to: content/{request.feed_name}/{result.filename}")
    print(f"Updated RSS feed: {result.feed_path}")

    # Set output for GitHub Actions
    if os.environ.get("GITHUB_ACTIONS"):
        print("::set-output name=changed::true")
        print(f"::set-output name=filename::{result.filename}")
        print(f"::set-output name=feed_path::{result.feed_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
