from datetime import datetime
from dateutil import parser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional
import os


class RSSManager:
    def __init__(self, feed_name: str, base_url: str = None):
        self.feed_name = feed_name
        self.base_url = (
            base_url
            or f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'owner/repo')}/blob/main"
        )
        self.feeds_dir = Path("feeds")
        self.feeds_dir.mkdir(exist_ok=True)
        self.feed_path = self.feeds_dir / f"{feed_name}.xml"

    def load_existing_feed(self) -> Optional[ET.ElementTree]:
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
        latest_link = (
            f"{self.base_url}/content/{self.feed_name}/{latest_file}"
            if latest_file
            else f"{self.base_url}/feeds/{self.feed_name}.xml"
        )

        # Load existing items if feed exists
        existing_items = self._load_existing_items()

        # Add new item to the beginning
        content_path = f"content/{self.feed_name}/{new_item['filename']}"
        timestamp = parser.parse(new_item["timestamp"])

        # Link directly to static HTML files with date parameter for history viewer
        link = f"{self.base_url}/{content_path}?date={new_item['timestamp']}"

        new_item_dict = {
            "title": new_item["title"],
            "link": link,
            "description": new_item.get("description", "Content update"),
            "pubdate": timestamp,
            "unique_id": f"{self.feed_name}-{new_item['hash'][:8]}",
        }

        # Build items list with new item first
        items = [new_item_dict] + existing_items[:19]  # Keep last 20 items

        # Generate RSS XML with CDATA for descriptions
        self._write_rss_feed(
            title=f"{self.feed_name} Updates",
            link=latest_link,
            description=f"Updates from {self.feed_name}",
            items=items,
        )

    def _load_existing_items(self) -> List[Dict]:
        """Load existing items from the RSS feed."""
        items = []

        if not self.feed_path.exists():
            return items

        try:
            tree = ET.parse(self.feed_path)
            root = tree.getroot()

            for item in root.findall(".//item"):
                item_dict = {
                    "title": item.find("title").text
                    if item.find("title") is not None
                    else "",
                    "link": item.find("link").text
                    if item.find("link") is not None
                    else "",
                    "description": item.find("description").text
                    if item.find("description") is not None
                    else "",
                    "unique_id": item.find("guid").text
                    if item.find("guid") is not None
                    else "",
                }

                # Parse pubDate
                pubdate_elem = item.find("pubDate")
                if pubdate_elem is not None and pubdate_elem.text:
                    item_dict["pubdate"] = parser.parse(pubdate_elem.text)

                items.append(item_dict)

        except Exception as e:
            print(f"Error loading existing feed items: {e}")

        return items

    def _write_rss_feed(
        self, title: str, link: str, description: str, items: List[Dict]
    ) -> None:
        """Write RSS feed XML with CDATA sections for descriptions."""
        # Create RSS root element
        rss = ET.Element(
            "rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"}
        )
        channel = ET.SubElement(rss, "channel")

        # Add channel metadata
        ET.SubElement(channel, "title").text = title
        ET.SubElement(channel, "link").text = link
        ET.SubElement(channel, "description").text = description
        ET.SubElement(channel, "language").text = "en"
        ET.SubElement(channel, "lastBuildDate").text = datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S +0000"
        )

        # Add items
        for item in items:
            item_elem = ET.SubElement(channel, "item")

            # Add simple text elements
            ET.SubElement(item_elem, "title").text = item["title"]
            ET.SubElement(item_elem, "link").text = item["link"]

            # Add description with placeholder for CDATA
            desc_elem = ET.SubElement(item_elem, "description")
            # Store raw content with a unique marker for CDATA replacement
            desc_elem.text = (
                f"__CDATA_START__{item.get('description', '')}__CDATA_END__"
            )

            # Add pubDate
            pubdate = item.get("pubdate")
            if isinstance(pubdate, datetime):
                ET.SubElement(item_elem, "pubDate").text = pubdate.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000"
                )
            elif isinstance(pubdate, str):
                ET.SubElement(item_elem, "pubDate").text = pubdate

            # Add guid
            if "unique_id" in item:
                ET.SubElement(item_elem, "guid").text = item["unique_id"]

        # Write to file with custom CDATA handling
        self._write_xml_with_cdata(rss)

    def _write_xml_with_cdata(self, root: ET.Element) -> None:
        """Write XML with CDATA sections for description elements."""
        # Convert to string first
        xml_str = ET.tostring(root, encoding="unicode", method="xml")

        # Replace our CDATA markers with actual CDATA sections
        import re

        def replace_cdata_markers(match):
            content = match.group(1)
            # Unescape the content that was escaped by ET.tostring
            import html

            unescaped_content = html.unescape(content)
            return f"<description><![CDATA[{unescaped_content}]]></description>"

        # Replace all description elements that have our markers
        xml_str = re.sub(
            r"<description>__CDATA_START__(.*?)__CDATA_END__</description>",
            replace_cdata_markers,
            xml_str,
            flags=re.DOTALL,
        )

        # Add XML declaration and write to file
        xml_final = f'<?xml version="1.0" encoding="utf-8"?>\n{xml_str}'

        with open(self.feed_path, "w", encoding="utf-8") as f:
            f.write(xml_final)
