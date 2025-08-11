from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Optional

class ContentStorage:
    def __init__(self, feed_name: str):
        self.feed_name = feed_name
        self.content_dir = Path("content") / feed_name
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.content_dir / ".metadata.json"
        
    def load_metadata(self) -> Dict[str, str]:
        """Load metadata about previously stored content."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_metadata(self, metadata: Dict[str, str]) -> None:
        """Save metadata about stored content."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def has_content_changed(self, content_hash: str) -> bool:
        """Check if content has changed based on hash."""
        metadata = self.load_metadata()
        return metadata.get('last_hash') != content_hash
    
    def save_content(self, content_data: Dict[str, str]) -> Optional[str]:
        """Save content to file and return filename if content is new."""
        if not self.has_content_changed(content_data['hash']):
            print(f"No changes detected for {self.feed_name}")
            return None
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}.html"
        filepath = self.content_dir / filename
        
        # Create HTML document with metadata
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{content_data['title']}</title>
    <meta name="source-url" content="{content_data['url']}">
    <meta name="scraped-at" content="{content_data['timestamp']}">
    <meta name="content-hash" content="{content_data['hash']}">
</head>
<body>
{content_data['content']}
</body>
</html>"""
        
        # Save content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Update metadata
        metadata = self.load_metadata()
        metadata['last_hash'] = content_data['hash']
        metadata['last_update'] = content_data['timestamp']
        metadata['last_filename'] = filename
        self.save_metadata(metadata)
        
        print(f"Saved new content to {filepath}")
        return filename