import requests
from inscriptis import get_text
from inscriptis.css_profiles import CSS_PROFILES
from inscriptis.model.config import ParserConfig
from typing import Optional, Dict, List
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup


class ContentScraper:
    def __init__(self, url: str, exclude_tags: Optional[List[str]] = None):
        self.url = url
        self.exclude_tags = exclude_tags or ["script", "style", "nav", "header", "footer"]

    def fetch_content(self) -> Optional[Dict[str, str]]:
        """Fetch and extract content from the URL using inscriptis."""
        try:
            # Download the webpage
            response = requests.get(
                self.url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; Watcher/1.0)"},
            )
            response.raise_for_status()
            html = response.text

            # Use BeautifulSoup to extract metadata
            soup = BeautifulSoup(html, "html.parser")

            # Get title
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else self.url

            # Get description
            desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            description = desc_tag.get("content", "").strip() if desc_tag else ""

            # Remove unwanted elements
            for element in soup.find_all(self.exclude_tags):
                element.decompose()

            # Get the body or main content
            body = soup.find("body") or soup

            # Extract text using inscriptis with custom config
            # Using 'strict' profile as base, which preserves tables well
            config = ParserConfig(
                css=CSS_PROFILES["strict"],
                display_links=True,
                display_anchors=False,
            )

            text_content = get_text(str(body), config)

            # Convert text to HTML while preserving structure
            # This maintains tables and formatting from inscriptis
            html_lines = []

            for line in text_content.split("\n"):
                line = line.rstrip()
                if not line:
                    html_lines.append("<br>")
                    continue

                # Simple heuristic for table detection based on multiple spaces/tabs
                if "    " in line or "\t" in line:
                    # This likely contains tabular data
                    # Convert to preformatted text to preserve spacing
                    html_lines.append(f"<pre>{line}</pre>")
                else:
                    # Regular paragraph
                    html_lines.append(f"<p>{line}</p>")

            html_content = "\n".join(html_lines)

            # For storage and comparison, use the text for hashing (more stable)
            content_hash = hashlib.sha256(text_content.encode("utf-8")).hexdigest()

            return {
                "content": html_content,
                "hash": content_hash,
                "title": title,
                "description": description,
                "url": self.url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            import traceback

            print(f"Error scraping {self.url}: {str(e)}")
            # Return error details instead of None
            return {
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "error_module": type(e).__module__,
                "stack_trace": traceback.format_exc(),
                "url": self.url,
            }
