"""Generate RSS feed for errors."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, List
import xml.etree.ElementTree as ET
from xml.dom import minidom


class ErrorFeedManager:
    """Manage RSS feed for errors."""

    def __init__(self, feed_dir: Path = None):
        """Initialize error feed manager."""
        self.feed_dir = feed_dir or Path("feeds")
        self.feed_dir.mkdir(exist_ok=True)
        self.error_feed_path = self.feed_dir / "errors.xml"
        self.error_items: List[Dict] = []

    def add_error(
        self,
        feed_id: str,
        url: str,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict] = None,
        feed_stats: Optional[Dict] = None,
    ):
        """Add an error to the error feed."""
        error_item = {
            "feed_id": feed_id,
            "url": url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "consecutive_failures": feed_stats.get("consecutive_failures", 1)
            if feed_stats
            else 1,
            "last_failure": feed_stats.get("last_failure") if feed_stats else None,
            "total_runs": feed_stats.get("total_runs", 1) if feed_stats else 1,
            "total_failures": feed_stats.get("total_failures", 1) if feed_stats else 1,
            "details": error_details or {},
        }

        self.error_items.append(error_item)

    def generate_rss_feed(self, base_url: Optional[str] = None, max_items: int = 50):
        """Generate RSS feed for errors."""
        # Create RSS root
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")

        # Add channel metadata
        ET.SubElement(channel, "title").text = "Watcher Error Feed"
        ET.SubElement(
            channel, "description"
        ).text = "RSS feed tracking errors from web scraping activities"
        ET.SubElement(channel, "link").text = base_url or "https://example.com"
        ET.SubElement(channel, "lastBuildDate").text = datetime.now(
            timezone.utc
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Sort errors by timestamp (newest first) and limit
        sorted_errors = sorted(
            self.error_items, key=lambda x: x["timestamp"], reverse=True
        )[:max_items]

        # Add error items
        for error in sorted_errors:
            item = ET.SubElement(channel, "item")

            # Title includes feed name and error type
            title = f"[{error['feed_id']}] {error['error_type']}"
            if error["consecutive_failures"] > 1:
                title += f" (Failed {error['consecutive_failures']} times)"
            ET.SubElement(item, "title").text = title

            # Description contains JSON error details
            description_data = json.dumps(error, indent=2, default=str)
            description = ET.SubElement(item, "description")
            description.text = f"<![CDATA[<pre>{description_data}</pre>]]>"

            # Link to the failed URL
            ET.SubElement(item, "link").text = error["url"]

            # Publication date
            try:
                pub_date = datetime.fromisoformat(
                    error["timestamp"].replace("Z", "+00:00")
                )
                ET.SubElement(item, "pubDate").text = pub_date.strftime(
                    "%a, %d %b %Y %H:%M:%S GMT"
                )
            except (ValueError, AttributeError):
                ET.SubElement(item, "pubDate").text = datetime.now(
                    timezone.utc
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")

            # GUID for uniqueness
            guid = f"{error['feed_id']}-{error['timestamp']}"
            ET.SubElement(item, "guid", isPermaLink="false").text = guid

        # Pretty print the XML
        xml_str = ET.tostring(rss, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ", encoding="UTF-8")

        # Save to file
        with open(self.error_feed_path, "wb") as f:
            f.write(pretty_xml)

        return self.error_feed_path

    def load_recent_errors(self, hours: int = 24) -> List[Dict]:
        """Load recent errors from existing feed or stats."""
        # This would parse existing error feed if needed
        # For now, returns current error_items
        return self.error_items
