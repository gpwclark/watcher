# Website Change Tracker

Automatically track changes to websites and generate RSS feeds with a GitHub Pages site.

## Features

- 📡 **RSS Feeds** - Automatic RSS feed generation for each tracked site
- 🔍 **Visual Diffs** - See exactly what changed between versions
- 📊 **Complete History** - All changes preserved with timestamps
- 🌐 **GitHub Pages** - Zero infrastructure, runs entirely on GitHub
- 🛡️ **Proxy Support** - Configure multiple proxy services with intelligent retry
- ⚠️ **Error Tracking** - Comprehensive error reporting with RSS feed
- 📈 **Statistics** - Track success rates and performance over time
- 🎯 **Content Filtering** - Extract only the content you need

View live example: [https://gpwclark.github.io/watcher/](https://gpwclark.github.io/watcher/)

## Quick Start

### 1. Create Your Repository

Use this repository as a template or create your own with these two files:

**`watcher-config.toml`** - List the websites you want to track:
```toml
[watcher]

[[watcher.sites]]
url = "https://example.com/changelog"
feed_name = "example-changelog"

[[watcher.sites]]
url = "https://news.site.com"
feed_name = "news-site"
```

**`.github/workflows/tracker.yml`** - The GitHub Action that does everything:
```yaml
name: Track Website Changes

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:       # Manual trigger
  push:
    branches: [ main ]
    paths: [ 'watcher-config.toml' ]

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  track:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.tracker.outputs.deployment-url }}
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Track websites and deploy
        id: tracker
        uses: gpwclark/watcher@main
```

### 2. Enable GitHub Pages

1. Go to Settings → Pages
2. Set Source to "GitHub Actions"
3. Save

### 3. Deploy!

Push your files and the action will:
- Run automatically on your schedule
- Generate RSS feeds when changes are detected
- Deploy everything to GitHub Pages

Your site will be live at: `https://YOUR-USERNAME.github.io/YOUR-REPO/`

## Configuration

### Basic Site Configuration

```toml
[[watcher.sites]]
url = "https://example.com/page"       # Required: URL to track
feed_name = "example-site"             # Required: Feed identifier (alphanumeric + hyphens)
min_hours = 24                         # Optional: Minimum hours between checks
```

### Default Settings

Set defaults that all sites inherit:

```toml
[watcher.defaults]
min_hours = 168                        # Check weekly by default
max_retries = 3                        # Retry failed requests
proxy_mode = "on_failure"              # Use proxies when direct fails
exclude_tags = ["script", "style", "nav", "header", "footer"]
```

### Content Filtering

Extract only the content you need:

```toml
[[watcher.sites]]
url = "https://news-site.com/article"
feed_name = "news-articles"

# Tag-based filtering
include_tags = ["article", "main"]     # Only keep these tags
# OR
exclude_tags = ["nav", "footer", "aside"]  # Remove these tags

# ID-based filtering  
include_ids = ["main-content", "post"]  # Only keep these IDs
# OR
exclude_ids = ["sidebar", "ads"]        # Remove these IDs

# Class-based filtering
include_classes = ["article-body", "content"]  # Only keep these classes
# OR
exclude_classes = ["advertisement", "popup"]   # Remove these classes
```

**Note:** Include and exclude options for the same filter type cannot be used together.

### Proxy Configuration

Add proxy services for sites that block direct access:

```toml
[proxies]

[proxies.scrapingant]
type = "url_template"
template = "https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={env:SCRAPINGANT_API_KEY}"
encoding = "url"  # Options: url, base64, none
env_vars = ["SCRAPINGANT_API_KEY"]

[watcher.defaults]
proxy_mode = "on_failure"  # Options: always, on_failure, never
proxies = ["scrapingant"]  # Proxy services to use

[[watcher.sites]]
url = "https://restricted.site.com"
feed_name = "restricted"
proxy_mode = "always"      # Always use proxy for this site
```

Set API keys as GitHub secrets or environment variables:
```bash
export SCRAPINGANT_API_KEY="your-key-here"
```

### Update Frequency

Adjust the cron schedule in your workflow:

```yaml
- cron: '0 * * * *'     # Every hour
- cron: '0 */6 * * *'   # Every 6 hours (default)
- cron: '0 0 * * *'     # Daily at midnight
- cron: '0 0 * * 0'     # Weekly on Sunday
```

## Monitoring

### Error Tracking

Errors are tracked and available at:
- **RSS Feed**: `feeds/errors.xml`
- **JSON Details**: `errors.json`
- **Web Interface**: Displayed on your GitHub Pages site

### Statistics

Performance metrics are preserved across runs:
- **Feed Stats**: `.watcher_stats/feed_stats.json`
- **Proxy Stats**: `.watcher_stats/proxy_stats.json`

Access via GitHub Pages:
```
https://[username].github.io/[repo]/.watcher_stats/feed_stats.json
```

## Action Options

Configure the GitHub Action with these inputs:

```yaml
- uses: gpwclark/watcher@main
  with:
    sites-config: watcher-config.toml    # Config file path
    subdirectory: /                      # Deploy location
    generate-site: true                  # Generate GitHub Pages site
    deploy-to-pages: true                # Deploy to GitHub Pages
    commit-to-gh-pages: true             # Save history to gh-pages branch
```

## Examples

### News Site with Content Filtering
```toml
[[watcher.sites]]
url = "https://news.example.com"
feed_name = "news"
include_tags = ["article"]
exclude_classes = ["ads", "comments", "related"]
min_hours = 6
```

### Documentation with Proxy
```toml
[[watcher.sites]]
url = "https://docs.example.com/api"
feed_name = "api-docs"
proxy_mode = "always"
proxies = ["scrapingant"]
include_ids = ["content", "main"]
```

### Price Tracking
```toml
[[watcher.sites]]
url = "https://store.example.com/product/12345"
feed_name = "product-price"
include_classes = ["price", "availability"]
min_hours = 1
```

## Local Development

Test locally with:
```bash
flox activate -- uv run watcher-preview
```

## What to Track

- Product prices and availability
- Job postings
- Documentation updates
- Government announcements
- News headlines
- API changes
- Event schedules
- Competition websites
- Any webpage that changes over time

## Advanced Examples

For more complex configurations, see:
- [examples/multi-proxy.toml](examples/multi-proxy.toml) - Multiple proxy setup
- [examples/filtering.toml](examples/filtering.toml) - Advanced content filtering
- [examples/complete.toml](examples/complete.toml) - Full configuration with all features

## License

MIT