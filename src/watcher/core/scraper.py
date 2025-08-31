import requests
from inscriptis import get_text
from inscriptis.css_profiles import CSS_PROFILES
from inscriptis.model.config import ParserConfig
from typing import Optional, Dict, List
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup


class ContentScraper:
    def __init__(
        self,
        url: str,
        exclude_tags: Optional[List[str]] = None,
        include_tags: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
        include_ids: Optional[List[str]] = None,
        exclude_classes: Optional[List[str]] = None,
        include_classes: Optional[List[str]] = None,
    ):
        self.url = url
        
        # Validate mutual exclusivity
        if exclude_tags and include_tags:
            raise ValueError("Cannot use both exclude_tags and include_tags")
        if exclude_ids and include_ids:
            raise ValueError("Cannot use both exclude_ids and include_ids")
        if exclude_classes and include_classes:
            raise ValueError("Cannot use both exclude_classes and include_classes")
        
        self.exclude_tags = exclude_tags or (
            ["script", "style", "nav", "header", "footer"] if not include_tags else []
        )
        self.include_tags = include_tags
        self.exclude_ids = exclude_ids or []
        self.include_ids = include_ids
        self.exclude_classes = exclude_classes or []
        self.include_classes = include_classes

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

            # Apply filtering based on configuration
            body = soup.find("body") or soup
            
            # If include_tags is specified, keep only those tags
            if self.include_tags:
                # Create a new soup with only included elements
                included_elements = []
                for tag in self.include_tags:
                    included_elements.extend(body.find_all(tag))
                
                # Create new body with only included elements
                new_body = BeautifulSoup("<body></body>", "html.parser").body
                for elem in included_elements:
                    new_body.append(elem.extract())
                body = new_body
            else:
                # Otherwise, remove excluded tags
                for element in body.find_all(self.exclude_tags):
                    element.decompose()
            
            # Handle ID-based filtering
            if self.include_ids:
                # Keep only elements with specified IDs
                included_elements = []
                for id_name in self.include_ids:
                    elem = body.find(id=id_name)
                    if elem:
                        included_elements.append(elem)
                
                # Create new body with only included elements
                new_body = BeautifulSoup("<body></body>", "html.parser").body
                for elem in included_elements:
                    new_body.append(elem.extract())
                body = new_body
            elif self.exclude_ids:
                # Remove elements with specified IDs
                for id_name in self.exclude_ids:
                    elem = body.find(id=id_name)
                    if elem:
                        elem.decompose()
            
            # Handle class-based filtering
            if self.include_classes:
                # Keep only elements with specified classes
                included_elements = []
                for class_name in self.include_classes:
                    included_elements.extend(body.find_all(class_=class_name))
                
                # Create new body with only included elements
                new_body = BeautifulSoup("<body></body>", "html.parser").body
                for elem in included_elements:
                    new_body.append(elem.extract())
                body = new_body
            elif self.exclude_classes:
                # Remove elements with specified classes
                for class_name in self.exclude_classes:
                    for elem in body.find_all(class_=class_name):
                        elem.decompose()

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
