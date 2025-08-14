"""Batch CLI for processing multiple sites from a TOML file."""

import argparse
import sys
import tomllib
from pathlib import Path
from .lib import scrape_and_update_feed
from .core.models import ScraperRequest
from .static_site import prepare_github_pages_content


def main():
    """Process multiple sites from a TOML configuration file."""
    parser = argparse.ArgumentParser(
        description='Process multiple sites from a TOML file',
        prog='watcher-batch'
    )
    parser.add_argument(
        '--config',
        default='sites.toml',
        help='Path to TOML configuration file (default: sites.toml)'
    )
    parser.add_argument(
        '--base-url',
        help='Base URL for RSS links (defaults to GitHub repo URL)'
    )
    parser.add_argument(
        '--generate-site',
        action='store_true',
        help='Generate static site files for GitHub Pages'
    )
    parser.add_argument(
        '--output-dir',
        default='deploy',
        help='Output directory for static site (default: deploy)'
    )
    parser.add_argument(
        '--subdirectory',
        help='Subdirectory for deployment (e.g., "tracker" for /tracker/)'
    )

    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file '{config_path}' not found")
        sys.exit(1)

    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
    except Exception as e:
        print(f"Error reading configuration: {e}")
        sys.exit(1)

    sites = config.get('sites', [])
    if not sites:
        print("No sites found in configuration")
        sys.exit(1)

    print(f"Processing {len(sites)} sites from {config_path}")

    # Track results
    total = len(sites)
    changed = 0
    errors = 0

    # Process each site
    for site in sites:
        url = site.get('url')
        feed_name = site.get('feed_name')

        if not url or not feed_name:
            print(f"Skipping invalid site entry: {site}")
            errors += 1
            continue

        print(f"\nProcessing {feed_name} ({url})...")

        # Get optional min_hours from config
        min_hours = site.get('min_hours')

        request = ScraperRequest(
            url=url,
            feed_name=feed_name,
            base_url=args.base_url,
            min_hours=min_hours
        )

        try:
            result = scrape_and_update_feed(request)

            if not result.success:
                print(f"  Error: {result.error_message}")
                errors += 1
            elif result.skipped:
                print(f"  Skipped: {result.error_message}")
            elif result.changed:
                print(f"  Updated: {result.feed_path}")
                changed += 1
            else:
                print(f"  No changes detected")

        except Exception as e:
            print(f"  Unexpected error: {e}")
            errors += 1

    # Summary
    print(f"\nSummary:")
    print(f"  Total sites: {total}")
    print(f"  Updated: {changed}")
    print(f"  Errors: {errors}")
    print(f"  Unchanged: {total - changed - errors}")

    # Generate static site if requested
    if args.generate_site:
        print(f"\nGenerating static site...")
        content_dir = Path("content")
        feeds_dir = Path("feeds")
        output_dir = Path(args.output_dir)

        if not content_dir.exists():
            print("Warning: No content directory found")
        if not feeds_dir.exists():
            print("Warning: No feeds directory found")

        try:
            prepare_github_pages_content(
                content_dir=content_dir,
                feeds_dir=feeds_dir,
                base_url=args.base_url or "",
                output_dir=output_dir,
                subdirectory=args.subdirectory
            )
            print(f"Static site generated in: {output_dir}")
        except Exception as e:
            print(f"Error generating static site: {e}")
            errors += 1

    # Exit with error if any failed
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()