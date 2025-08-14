"""Static site generation for watcher - extracted from GitHub Actions workflow."""

import json
import shutil
from pathlib import Path
from typing import Optional


class StaticSiteGenerator:
    """Generates static site files for GitHub Pages deployment."""

    def __init__(self, base_url: str, output_dir: Path = Path("deploy")):
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)

    def generate_site(
        self, content_dir: Path, feeds_dir: Path, subdirectory: str,
    ) -> None:
        """Generate complete static site with all necessary files."""
        # Create deployment directory
        self.output_dir.mkdir(exist_ok=True)

        # Determine deployment path
        # Treat "/" as root (no subdirectory)
        if subdirectory and subdirectory != "/":
            deploy_path = self.output_dir / subdirectory
            deploy_path.mkdir(parents=True, exist_ok=True)
        else:
            deploy_path = self.output_dir

        # Copy content and feeds preserving structure
        if content_dir.exists():
            shutil.copytree(content_dir, deploy_path / "content", dirs_exist_ok=True)

        if feeds_dir.exists():
            shutil.copytree(feeds_dir, deploy_path / "feeds", dirs_exist_ok=True)

        # Copy history explorer files to deployment root
        history_files = [
            "history-explorer.html",
            "history-viewer.js",
            "feed-viewer.html",
        ]
        for file in history_files:
            src_file = content_dir / file
            if src_file.exists():
                shutil.copy2(src_file, deploy_path / file)

        # Generate JSON indices
        self._generate_feeds_json(feeds_dir, deploy_path)
        self._generate_file_listings(content_dir, deploy_path)

        # Generate index.html
        self._generate_index_html(deploy_path)

    def _generate_feeds_json(self, feeds_dir: Path, deploy_path: Path) -> None:
        """Create JSON index of available feeds."""
        feeds = []
        if feeds_dir.exists():
            feeds = [f.name for f in feeds_dir.glob("*.xml")]

        with open(deploy_path / "feeds.json", "w") as f:
            json.dump(feeds, f, indent=2)

    def _generate_file_listings(self, content_dir: Path, deploy_path: Path) -> None:
        """Create files.json for each feed directory."""
        if not content_dir.exists():
            return

        for feed_dir in content_dir.iterdir():
            if feed_dir.is_dir():
                files = [f.name for f in feed_dir.glob("*.html")]
                files_json_path = deploy_path / "content" / feed_dir.name / "files.json"
                files_json_path.parent.mkdir(parents=True, exist_ok=True)
                with open(files_json_path, "w") as f:
                    json.dump(files, f, indent=2)

    def _generate_index_html(self, deploy_path: Path) -> None:
        """Generate the main index.html page."""
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Change Tracker</title>
    <link rel="alternate" type="application/rss+xml" title="All Feeds" href="feeds/">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            font-size: 1.1em;
        }
        .feeds-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .feed-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .feed-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }
        .feed-name {
            font-weight: 600;
            font-size: 1.2em;
            margin-bottom: 10px;
            color: #333;
        }
        .feed-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .feed-link {
            display: inline-block;
            padding: 6px 12px;
            background: #f0f0f0;
            color: #333;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.2s;
        }
        .feed-link:hover {
            background: #667eea;
            color: white;
        }
        .feed-link.rss {
            background: #ff9500;
            color: white;
        }
        .feed-link.rss:hover {
            background: #e88600;
        }
        .explorer-banner {
            background: white;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .explorer-button {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            margin-top: 15px;
            transition: transform 0.2s;
        }
        .explorer-button:hover {
            transform: scale(1.05);
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: white;
        }
        .last-updated {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📡 Website Change Tracker</h1>
            <p class="subtitle">Monitoring websites for updates via RSS feeds</p>
        </div>

        <div id="feedsContainer" class="feeds-grid">
            <div class="loading">Loading feeds...</div>
        </div>

        <div class="explorer-banner">
            <h2>📜 Explore Change History</h2>
            <p>View detailed diffs and navigate through the complete history of tracked websites</p>
            <a href="history-explorer.html" class="explorer-button">Open History Explorer</a>
        </div>

        <div class="last-updated">
            Last updated: <span id="lastUpdated"></span>
        </div>
    </div>

    <script>
        // Set last updated time
        document.getElementById('lastUpdated').textContent = new Date().toLocaleString();

        // Load feeds dynamically
        async function loadFeeds() {
            const container = document.getElementById('feedsContainer');

            try {
                // Fetch the feeds JSON index
                const response = await fetch('feeds.json');
                const feeds = await response.json();

                if (feeds.length === 0) {
                    container.innerHTML = '<div class="loading">No feeds found yet. They will appear after the first run.</div>';
                    return;
                }

                container.innerHTML = feeds.map(filename => {
                    const feedName = filename.replace('.xml', '');
                    const displayName = feedName.replace(/-/g, ' ')
                        .replace(/\\b\\w/g, l => l.toUpperCase());

                    return `
                        <div class="feed-card">
                            <div class="feed-name">${displayName}</div>
                            <div class="feed-links">
                                <a href="feeds/${filename}" class="feed-link rss">📡 RSS</a>
                                <a href="history-explorer.html?feed=${feedName}" class="feed-link">📜 History</a>
                                <a href="feed-viewer.html?feed=${feedName}" class="feed-link">📄 Feed</a>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (error) {
                console.error('Error loading feeds:', error);
                container.innerHTML = `
                    <div class="loading">
                        <p>Feeds will appear here after the workflow runs.</p>
                        <p style="margin-top: 10px; font-size: 0.9em;">
                            If you just set this up, trigger the workflow manually or wait for the schedule.
                        </p>
                    </div>
                `;
            }
        }

        loadFeeds();
    </script>
</body>
</html>"""

        with open(deploy_path / "index.html", "w") as f:
            f.write(html_content)


def prepare_github_pages_content(
    content_dir: Path,
    feeds_dir: Path,
    base_url: str,
    subdirectory: str,
    output_dir: Path = Path("deploy"),
) -> None:
    """Convenience function to generate static site for GitHub Pages."""
    generator = StaticSiteGenerator(base_url, output_dir)
    generator.generate_site(content_dir, feeds_dir, subdirectory)
