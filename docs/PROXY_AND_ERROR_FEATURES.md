# Proxy and Error Tracking Features

## Overview

The watcher now supports:
1. **Error Tracking**: Comprehensive error tracking with RSS feed generation for failures
2. **Proxy Support**: Configure multiple proxy services with intelligent retry logic
3. **Statistics Tracking**: Track success/failure rates for feeds and proxies
4. **Default Configuration**: Set default values for all watch sites

## Configuration

### Proxy Configuration

Add proxy configurations to your `watcher-config.toml`:

```toml
[proxies]

[proxies.scrapingant]
type = "url_template"
template = "https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={env:SCRAPINGANT_API_KEY}"
encoding = "url"  # Options: url, base64, none
env_vars = ["SCRAPINGANT_API_KEY"]  # Required environment variables

[proxies.scraperapi]
type = "url_template"
template = "http://api.scraperapi.com?api_key={env:SCRAPER_API_KEY}&url={encoded_url}"
encoding = "url"
env_vars = ["SCRAPER_API_KEY"]
```

### Default Configuration

Set defaults for all watch sites:

```toml
[watcher.defaults]
min_hours = 168  # Check once a week by default
exclude_tags = ["script", "style", "nav", "header", "footer"]
max_retries = 3
proxy_mode = "on_failure"  # Options: always, on_failure, never
proxies = ["scrapingant", "scraperapi"]  # Default proxy chain
```

### Site-Specific Configuration

Individual sites inherit defaults and can override them:

```toml
[[watcher.sites]]
url = "https://restricted.example.com/feed"
feed_name = "restricted-site"
proxies = ["scrapingant"]  # Override default proxies
proxy_mode = "always"  # Always use proxy for this site
max_retries = 5  # More retries for important sites
```

## Proxy Modes

- **`never`**: Never use proxies, only direct requests
- **`on_failure`**: Try direct first, then use proxies if it fails (default)
- **`always`**: Always use proxies, never try direct

## URL Encoding Types

- **`url`**: Standard URL encoding (e.g., spaces become %20)
- **`base64`**: Base64 encoding of the URL
- **`none`**: No encoding, use URL as-is

## Template Variables

In proxy templates, you can use:
- `{url}`: The original URL
- `{encoded_url}`: The encoded URL (based on encoding type)
- `{env:VAR_NAME}`: Environment variable value

## Error Tracking

### Error RSS Feed

When errors occur, they are automatically tracked and an error RSS feed is generated at `feeds/errors.xml`. Each error entry includes:

```json
{
  "feed_id": "example-feed",
  "url": "https://example.com",
  "timestamp": "2024-01-15T10:30:00Z",
  "error_type": "HTTPError",
  "error_message": "404 Not Found",
  "consecutive_failures": 3,
  "last_failure": "2024-01-15T10:30:00Z",
  "total_runs": 150,
  "total_failures": 7,
  "details": {
    "status_code": 404,
    "proxy_attempts": [
      {"proxy": "direct", "success": false, "error": "404 Not Found"},
      {"proxy": "scrapingant", "success": false, "error": "404 Not Found"}
    ]
  }
}
```

### Statistics Tracking

The system tracks:
- **Feed Statistics**: Total runs, failures, consecutive failures, success rates
- **Proxy Statistics**: Per-URL and global success rates for intelligent retry ordering

Statistics are stored in `.watcher_stats/` directory:
- `feed_stats.json`: Feed performance metrics
- `proxy_stats.json`: Proxy performance by URL and globally

## Intelligent Retry Logic

The retry system uses historical performance data:

1. **Initial Attempt**: Direct request (unless proxy_mode="always")
2. **First Retry**: Proxy with highest success rate for this specific URL
3. **Subsequent Retries**: Remaining proxies ordered by performance
4. **Smart Selection**: Proxies with URL-specific success history are heavily preferred

## Environment Variables

Set your proxy API keys as environment variables:

```bash
export SCRAPINGANT_API_KEY="your-key-here"
export SCRAPER_API_KEY="your-key-here"
```

## Example: Complete Configuration

```toml
# Proxy configurations
[proxies]
[proxies.scrapingant]
type = "url_template"
template = "https://api.scrapingant.com/v2/general?url={encoded_url}&x-api-key={env:SCRAPINGANT_API_KEY}"
encoding = "url"
env_vars = ["SCRAPINGANT_API_KEY"]

# Default settings
[watcher.defaults]
min_hours = 168
exclude_tags = ["script", "style", "nav", "header", "footer"]
max_retries = 3
proxy_mode = "on_failure"
proxies = ["scrapingant"]

# Sites
[[watcher.sites]]
url = "https://example.com/changelog"
feed_name = "example-changelog"
min_hours = 24  # Override: check daily

[[watcher.sites]]
url = "https://restricted.example.com/api"
feed_name = "restricted-api"
proxy_mode = "always"  # Always use proxy
max_retries = 5  # More retries
```

## Monitoring

- Check `feeds/errors.xml` for error tracking
- Review `.watcher_stats/feed_stats.json` for feed performance
- Monitor `.watcher_stats/proxy_stats.json` for proxy effectiveness
- Check `errors.json` for detailed error information after batch runs