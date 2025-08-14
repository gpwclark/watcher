# Website Change Tracker

Automatically track changes to websites and get a beautiful, hosted changelog - all within your existing GitHub repository.

## What You Get

- 📊 A hosted webpage showing all changes to tracked websites
- 📰 RSS feeds for each tracked site
- 🔍 Visual diffs showing exactly what changed
- 📅 Complete history of all changes
- 🚀 Zero infrastructure - runs entirely on GitHub Actions

View live example: [https://gpwclark.github.io/watcher/](https://gpwclark.github.io/watcher/)

## Quick Start (3 Steps)

### 1. Add Your Sites to Track

Create `sites.toml` in your repository root:

```toml
[[site]]
url = "https://example.com"        # URL to track
name = "Example Site"              # Display name
selector = "article"               # CSS selector (optional)
```

### 2. Copy the Workflow

Copy [`.github/workflows/tracker.yml`](.github/workflows/tracker.yml) to your repository's `.github/workflows/` directory.

The workflow will:
- Run every 6 hours (customizable)
- Track all sites in your `sites.toml`
- Automatically deploy to GitHub Pages
- Preserve history across runs

That's it! Your tracker will run automatically and publish to `https://your-username.github.io/your-repo/`

## Customization

### Change Update Frequency

Edit the cron schedule in your workflow:
- `'0 * * * *'` - Every hour
- `'0 */6 * * *'` - Every 6 hours
- `'0 0 * * *'` - Daily at midnight
- `'0 0 * * 0'` - Weekly on Sunday

### Track Multiple Sites

Add more entries to `sites.toml`:

```toml
[[site]]
url = "https://example.com"
name = "Example Site"

[[site]]
url = "https://another-site.com"
name = "Another Site"
selector = ".main-content"  # Track only specific content
min_hours = 24  # if desired frequency of checking is > 6 hours or w/e time is set in the GitHub Actions.
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
