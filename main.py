import argparse
import sys
import os
from scraper import ContentScraper
from storage import ContentStorage
from rss_manager import RSSManager

def main():
    parser = argparse.ArgumentParser(description='Git-scraping tool with RSS feed generation')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('feed_name', help='Name for the RSS feed (e.g., "jank-progress")')
    parser.add_argument('--base-url', help='Base URL for RSS links (defaults to GitHub repo URL)')
    
    args = parser.parse_args()
    
    # Initialize components
    scraper = ContentScraper(args.url)
    storage = ContentStorage(args.feed_name)
    rss_manager = RSSManager(args.feed_name, args.base_url)
    
    print(f"Scraping {args.url} for feed '{args.feed_name}'...")
    
    # Fetch content
    content_data = scraper.fetch_content()
    if not content_data:
        print("Failed to fetch content")
        sys.exit(1)
    
    # Save content if changed
    filename = storage.save_content(content_data)
    if not filename:
        print("No changes detected - skipping RSS update")
        sys.exit(0)
    
    # Update RSS feed
    rss_item = {
        'title': content_data['title'],
        'description': content_data.get('description', f'Update from {args.url}'),
        'timestamp': content_data['timestamp'],
        'hash': content_data['hash'],
        'filename': filename,
    }
    
    rss_manager.create_or_update_feed(rss_item)
    print(f"Updated RSS feed: feeds/{args.feed_name}.xml")
    
    # Set output for GitHub Actions
    if os.environ.get('GITHUB_ACTIONS'):
        print(f"::set-output name=changed::true")
        print(f"::set-output name=filename::{filename}")
        print(f"::set-output name=feed_path::feeds/{args.feed_name}.xml")


if __name__ == "__main__":
    main()
