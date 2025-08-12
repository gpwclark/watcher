import trafilatura
import requests
from typing import Optional, Dict
import hashlib
from datetime import datetime, timezone

class ContentScraper:
    def __init__(self, url: str):
        self.url = url

    def fetch_content(self) -> Optional[Dict[str, str]]:
        """Fetch and extract content from the URL using trafilatura."""
        try:
            # Download the webpage
            downloaded = trafilatura.fetch_url(self.url)
            if not downloaded:
                return None

            # Extract main content as HTML
            html_content = trafilatura.extract(
                downloaded,
                output_format='html',
                include_comments=False,
                include_tables=True,
                include_images=True,
                include_links=True,
                deduplicate=True
            )

            # Also get metadata
            metadata = trafilatura.extract_metadata(downloaded)

            if not html_content:
                return None

            # Clean up nested HTML/body tags if present
            html_content = html_content.replace('<html>', '').replace('</html>', '')
            html_content = html_content.replace('<body>', '').replace('</body>', '')
            html_content = html_content.strip()

            # Calculate content hash for change detection
            content_hash = hashlib.sha256(html_content.encode('utf-8')).hexdigest()

            return {
                'content': html_content,
                'hash': content_hash,
                'title': metadata.title if metadata else self.url,
                'description': metadata.description if metadata else '',
                'url': self.url,
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            print(f"Error scraping {self.url}: {str(e)}")
            return None