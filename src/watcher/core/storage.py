from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Dict, Optional, Tuple
import subprocess
import os

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
        try:
            if old_file_path and old_file_path.exists():
                # Use git diff to compare only the body content
                # This gives us a cleaner diff without the HTML wrapper
                result = subprocess.run(
                    [
                        'git', 'diff',
                        '--no-index',
                        '--no-prefix',
                        '--unified=3',  # Show 3 lines of context
                        '-w',  # Ignore whitespace changes
                        str(old_file_path),
                        str(new_file_path)
                    ],
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd()
                )
                if result.returncode in [0, 1]:  # 0 = no diff, 1 = diff exists
                    diff_text = result.stdout
                    if diff_text:
                        # Clean up the diff header to be more readable
                        lines = diff_text.split('\n')
                        cleaned_lines = []
                        skip_next = False

                        for line in lines:
                            # Skip the diff header lines
                            if line.startswith('diff --git') or line.startswith('index '):
                                skip_next = True
                                continue
                            if skip_next and (line.startswith('---') or line.startswith('+++')):
                                continue
                            skip_next = False

                            # Keep the actual diff content
                            if line.startswith('@@') or line.startswith('+') or line.startswith('-') or line.startswith(' '):
                                cleaned_lines.append(line)

                        return '\n'.join(cleaned_lines)
            return None
        except Exception as e:
            print(f"Error getting diff: {e}")
            return None

    def save_content(self, content_data: Dict[str, str]) -> Optional[Tuple[str, Optional[str]]]:
        """Save content to file and return filename if content is new."""
        if not self.has_content_changed(content_data['hash']):
            print(f"No changes detected for {self.feed_name}")
            return None

        # Generate filename with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
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

        # Get diff with previous version if it exists
        metadata = self.load_metadata()
        diff_content = None
        if 'last_filename' in metadata:
            old_filepath = self.content_dir / metadata['last_filename']
            diff_content = self.get_content_diff(filepath, old_filepath)

        # Update metadata
        metadata['last_hash'] = content_data['hash']
        metadata['last_update'] = content_data['timestamp']
        metadata['last_filename'] = filename
        self.save_metadata(metadata)

        print(f"Saved new content to {filepath}")
        return filename, diff_content