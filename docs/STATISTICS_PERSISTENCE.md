 # Statistics Persistence in GitHub Actions

## Overview
The watcher now properly preserves statistics files across GitHub Actions runs, ensuring that error tracking and proxy performance data accumulates over time.

## What's Preserved

The following files are now preserved in the `gh-pages` branch:
- `.watcher_stats/feed_stats.json` - Feed performance statistics
- `.watcher_stats/proxy_stats.json` - Proxy performance statistics
- `content/` - All scraped content history
- `feeds/` - All RSS feeds including error feed
- `errors.json` - Recent error details

## How It Works

1. **Before Each Run**: The workflow fetches the existing `gh-pages` branch and copies back:
   - Previous content files
   - Previous feeds
   - Previous statistics (.watcher_stats directory)

2. **During Execution**: The watcher updates statistics:
   - Increments total_runs for each feed
   - Updates consecutive_failures counter
   - Records proxy success/failure rates
   - Tracks per-URL proxy performance

3. **After Each Run**: The workflow commits back to `gh-pages`:
   - Updated content files
   - Updated feeds
   - Updated statistics
   - Generated static site

## Benefits

### Cumulative Statistics
- Total runs accumulate across all workflow executions
- Total failures are tracked historically
- Consecutive failures persist until a success resets them
- Last failure/success timestamps are preserved

### Intelligent Proxy Selection
- Proxy performance data accumulates over time
- The system learns which proxies work best for specific URLs
- Failed proxies are deprioritized in future attempts

### Error Tracking
- Error patterns become visible over time
- Problematic feeds are easily identified
- Recovery from failures is tracked

## Accessing Statistics

### Via GitHub Pages
After deployment, statistics are available at:
- `https://[username].github.io/[repo]/.watcher_stats/feed_stats.json`
- `https://[username].github.io/[repo]/.watcher_stats/proxy_stats.json`
- `https://[username].github.io/[repo]/errors.json`
- `https://[username].github.io/[repo]/feeds/errors.xml`

### Via gh-pages Branch
You can also check out the `gh-pages` branch locally:
```bash
git fetch origin gh-pages
git checkout gh-pages
cat .watcher_stats/feed_stats.json | jq .
```

## Example Statistics

### feed_stats.json
```json
{
  "example-changelog": {
    "total_runs": 150,
    "total_failures": 7,
    "consecutive_failures": 0,
    "last_failure": "2024-01-14T15:30:00Z",
    "last_success": "2024-01-15T10:00:00Z",
    "first_run": "2024-01-01T00:00:00Z"
  }
}
```

### proxy_stats.json
```json
{
  "scrapingant": {
    "urls": {
      "https://example.com": {
        "attempts": 45,
        "successes": 43,
        "last_success": "2024-01-15T10:00:00Z"
      }
    },
    "global_stats": {
      "total_requests": 1250,
      "total_successes": 1187,
      "success_rate": 0.95
    }
  }
}
```

## Monitoring Feed Health

With persistent statistics, you can:
1. **Identify Failing Feeds**: Check consecutive_failures > threshold
2. **Track Recovery**: Monitor when last_success updates after failures
3. **Measure Reliability**: Calculate success rate from total_runs vs total_failures
4. **Optimize Proxies**: Review proxy_stats to see which work best

## Resetting Statistics

If you need to reset statistics:
1. Delete the `.watcher_stats` directory in the `gh-pages` branch
2. The next run will start fresh statistics

```bash
git checkout gh-pages
rm -rf .watcher_stats
git add -A
git commit -m "Reset statistics"
git push origin gh-pages
```

## Important Notes

- Statistics files use JSON format for easy parsing
- Files are updated atomically to prevent corruption
- Thread-safe locking ensures concurrent updates don't conflict
- Statistics survive even if individual feeds fail