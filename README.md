# Website Change Tracker

Automatically track changes to websites and generate RSS feeds with a beautiful GitHub Pages site.

## What You Get

- 📊 A hosted webpage showing all changes to tracked websites
- 📰 RSS feeds for each tracked site
- 🔍 Visual diffs showing exactly what changed
- 📅 Complete history of all changes
- 🚀 Zero infrastructure - runs entirely on GitHub Actions

View live example: [https://gpwclark.github.io/watcher/](https://gpwclark.github.io/watcher/)

## Quick Start (2 Minutes)

### 1. Create Your Repository

Use this repository as a template or create your own with these two files:

**`sites.toml`** - List the websites you want to track:
```toml
[[sites]]
url = "https://example.com/changelog"
feed_name = "example-changelog"

[[sites]]
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
    paths: [ 'sites.toml' ]

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

### 3. That's It!

Push your files and the action will:
- Run automatically every 6 hours
- Track changes to all your sites
- Generate RSS feeds
- Deploy a beautiful site to GitHub Pages

Your site will be live at: `https://YOUR-USERNAME.github.io/YOUR-REPO/`

## Configuration

### sites.toml Format

```toml
[[sites]]
url = "https://example.com/changelog"  # Required: URL to track
feed_name = "example-changelog"        # Required: Name for the feed (alphanumeric + hyphens)
min_hours = 1.0                        # Optional: Minimum hours between checks (default: no limit)
```

### Action Options

The action supports these inputs (all have sensible defaults):

```yaml
- uses: gpwclark/watcher@main
  with:
    sites-config: sites.toml    # Path to config file
    subdirectory: /             # Deploy to root or subdirectory like /tracker
    generate-site: true         # Generate the GitHub Pages site
    deploy-to-pages: true       # Deploy to GitHub Pages
    commit-to-gh-pages: true    # Save history to gh-pages branch
```

### Update Frequency

Change the cron schedule in your workflow:
```yaml
on:
  schedule:
    - cron: '0 * * * *'     # Every hour
    - cron: '0 */6 * * *'   # Every 6 hours (default)
    - cron: '0 0 * * *'     # Daily at midnight
    - cron: '0 0 * * 0'     # Weekly on Sunday
```
## Examples of What to Track

- Product prices and availability
- Job postings
- News headlines
- Documentation updates
- Competition websites
- Government announcements
- Event schedules
- API documentation
