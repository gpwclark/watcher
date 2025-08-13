from feedgenerator import Rss201rev2Feed
from datetime import datetime
from dateutil import parser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import os
import glob

class RSSManager:
    def __init__(self, feed_name: str, base_url: str = None):
        self.feed_name = feed_name
        self.base_url = base_url or f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'owner/repo')}/blob/main"
        self.feeds_dir = Path("feeds")
        self.feeds_dir.mkdir(exist_ok=True)
        self.feed_path = self.feeds_dir / f"{feed_name}.xml"

    def load_existing_feed(self) -> Optional[Rss201rev2Feed]:
        """Load existing RSS feed if it exists."""
        if not self.feed_path.exists():
            return None

        try:
            tree = ET.parse(self.feed_path)
            return tree
        except Exception:
            return None

    def get_latest_content_file(self) -> Optional[str]:
        """Get the latest content file for this feed."""
        content_dir = Path("content") / self.feed_name
        if not content_dir.exists():
            return None

        # Look for HTML files
        html_files = list(content_dir.glob("*.html"))
        
        if not html_files:
            return None

        # Sort by filename (which includes timestamp)
        latest = sorted(html_files)[-1]
        return latest.name

    def create_or_update_feed(self, new_item: Dict[str, str]) -> None:
        """Add a new item to the RSS feed or create a new feed."""
        # Get latest file for feed link
        latest_file = self.get_latest_content_file()
        latest_link = f"{self.base_url}/content/{self.feed_name}/{latest_file}" if latest_file else f"{self.base_url}/feeds/{self.feed_name}.xml"

        # Create feed object
        feed = Rss201rev2Feed(
            title=f"{self.feed_name} Updates",
            link=latest_link,  # Link to latest content file
            description=f"Updates from {self.feed_name}",
            language="en",
        )

        # Load existing items if feed exists
        existing_items = self._load_existing_items()

        # Add new item
        content_path = f"content/{self.feed_name}/{new_item['filename']}"
        timestamp = parser.parse(new_item['timestamp'])
        
        # Link directly to static HTML files with date parameter for history viewer
        link = f"{self.base_url}/{content_path}?date={new_item['timestamp']}"

        # Use description as-is (feedgenerator will handle escaping)
        description = new_item.get('description', 'Content update')

        feed.add_item(
            title=new_item['title'],
            link=link,
            description=description,
            pubdate=timestamp,
            unique_id=f"{self.feed_name}-{new_item['hash'][:8]}",
        )

        # Add existing items (limit to last 20)
        for item in existing_items[:19]:
            feed.add_item(**item)

        # Write feed to file
        with open(self.feed_path, 'w', encoding='utf-8') as f:
            feed.write(f, 'utf-8')

    def _load_existing_items(self) -> List[Dict]:
        """Load existing items from the RSS feed."""
        items = []

        if not self.feed_path.exists():
            return items

        try:
            tree = ET.parse(self.feed_path)
            root = tree.getroot()

            for item in root.findall('.//item'):
                item_dict = {
                    'title': item.find('title').text if item.find('title') is not None else '',
                    'link': item.find('link').text if item.find('link') is not None else '',
                    'description': item.find('description').text if item.find('description') is not None else '',
                    'unique_id': item.find('guid').text if item.find('guid') is not None else '',
                }

                # Parse pubDate
                pubdate_elem = item.find('pubDate')
                if pubdate_elem is not None and pubdate_elem.text:
                    item_dict['pubdate'] = parser.parse(pubdate_elem.text)

                items.append(item_dict)

        except Exception as e:
            print(f"Error loading existing feed items: {e}")

        return items