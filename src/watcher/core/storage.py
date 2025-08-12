from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Dict, Optional, Tuple
import subprocess
import os
from .diff_utils import DiffUtils

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

    def should_check(self, min_hours: Optional[float] = None) -> bool:
        """Check if enough time has passed since last update."""
        if min_hours is None:
            return True

        metadata = self.load_metadata()
        last_update = metadata.get('last_update')
        if not last_update:
            return True

        try:
            from dateutil import parser
            last_time = parser.parse(last_update)
            current_time = datetime.now(timezone.utc)
            hours_passed = (current_time - last_time).total_seconds() / 3600
            return hours_passed >= min_hours
        except Exception:
            return True

    def get_content_diff(self, new_file_path: Path, old_file_path: Optional[Path] = None) -> Optional[str]:
        """Get git diff between old and new content files."""
        if old_file_path and old_file_path.exists():
            return DiffUtils.generate_unified_diff(old_file_path, new_file_path)
        return None
    
    def extract_html_content_from_file(self, html_path: Path) -> Optional[str]:
        """Extract HTML content from the body of the HTML file."""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract content from the div with class="content"
            import re
            match = re.search(r'<div class="content">\s*(.*?)\s*</div>\s*</body>', content, re.DOTALL)
            if match:
                return match.group(1).strip()
            return None
        except Exception:
            return None
    
    def get_html_diff(self, new_html_path: Path, old_html_path: Path) -> Optional[str]:
        """Generate diff between HTML content embedded in HTML files."""
        new_html = self.extract_html_content_from_file(new_html_path)
        old_html = self.extract_html_content_from_file(old_html_path)
        
        if new_html and old_html:
            # Create temporary files for diffing
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as new_temp:
                new_temp.write(new_html)
                new_temp_path = Path(new_temp.name)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as old_temp:
                old_temp.write(old_html)
                old_temp_path = Path(old_temp.name)
            
            try:
                diff = DiffUtils.generate_unified_diff(old_temp_path, new_temp_path)
                return diff
            finally:
                # Clean up temp files
                new_temp_path.unlink(missing_ok=True)
                old_temp_path.unlink(missing_ok=True)
        
        return None

    def save_content(self, content_data: Dict[str, str]) -> Optional[Tuple[str, Optional[str]]]:
        """Save content to file and return filename if content is new."""
        if not self.has_content_changed(content_data['hash']):
            print(f"No changes detected for {self.feed_name}")
            return None

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        html_filename = f"{timestamp}.html"
        html_filepath = self.content_dir / html_filename

        # Use the HTML content directly from trafilatura
        html_content_body = content_data['content']
        
        # Create static HTML document
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content_data['title']}</title>
    <meta name="source-url" content="{content_data['url']}">
    <meta name="scraped-at" content="{content_data['timestamp']}">
    <meta name="content-hash" content="{content_data['hash']}">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        th {{
            background-color: #f5f5f5;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="metadata">
        <strong>Source:</strong> <a href="{content_data['url']}">{content_data['url']}</a><br>
        <strong>Captured:</strong> {content_data['timestamp']}<br>
        <strong>Title:</strong> {content_data['title']}<br>
        <strong>📜 <a href="../history-explorer.html?feed={self.feed_name}" style="color: #667eea;">View Full History with Diffs</a></strong>
    </div>
    <div class="content">
        {html_content_body}
    </div>
</body>
</html>"""

        # Save static HTML file
        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Get diff with previous version if it exists
        metadata = self.load_metadata()
        diff_content = None
        if 'last_filename' in metadata:
            old_filepath = self.content_dir / metadata['last_filename']
            if old_filepath.exists():
                # Extract HTML content from HTML files for diffing
                diff_content = self.get_html_diff(html_filepath, old_filepath)

        # Update metadata to track HTML file
        metadata['last_hash'] = content_data['hash']
        metadata['last_update'] = content_data['timestamp']
        metadata['last_filename'] = html_filename
        self.save_metadata(metadata)

        print(f"Saved new content to {html_filepath}")
        return html_filename, diff_content