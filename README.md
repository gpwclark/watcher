# Watcher - Git-Scraping RSS Feed Generator

inspire by: https://github.com/simonw/ca-fires-history

does something similar except a bit more opinionated and distributes updates thru rss feeds.

A powerful tool that monitors websites for changes and generates RSS feeds with **git diffs**, leveraging Git for version control and GitHub Actions for automation. Perfect for tracking updates on sites that don't provide RSS feeds.

## Deploy to GitHub Pages

**Now with GitHub Pages support!** Deploy your RSS tracker to GitHub Pages without touching your main branch. Perfect for:
- Adding tracking to existing repositories
- Keeping your main branch clean
- Professional URLs like `username.github.io/repo/watcher/`
- Interactive history explorer with diffs
- j

[Jump to GitHub Pages Setup →](#-github-pages-deployment)

## Key Features

- = **Automatic Change Detection**: Only creates new RSS entries when content actually changes
- =� **Git Diffs in RSS**: Each RSS entry includes the actual changes (diff) in the description
- =� **RSS Feed Generation**: Creates standard RSS 2.0 feeds compatible with any RSS reader
- =� **Full Content Storage**: Stores complete page content for each update
- = **Git Integration**: Leverages Git history for tracking changes over time
- =� **GitHub Actions Automation**: Runs entirely in GitHub Actions - no server needed
- <� **Multi-Site Support**: Track as many sites as you want with separate feeds
- >� **Clean Content Extraction**: Uses Trafilatura for high-quality content extraction

## What Makes This Different

Unlike traditional RSS scrapers, Watcher includes the **actual changes** in each RSS entry. When content changes, you'll see exactly what was added or removed right in your RSS reader - no need to visit the site to understand what changed!

## GitHub Pages Deployment

Deploy your RSS tracker to GitHub Pages in minutes! This is the **easiest way** to get started - no commits to main branch, professional URLs, and includes an interactive history explorer.

### Quick Start

### Step 1: Choose an existing repository or create a new one.

### Step 2: Add these two files to your repository

#### File 1: `sites.toml`
This tells the tracker what websites to monitor:

```toml
# sites.toml - Put this in your repository root
[[sites]]
url = "https://example.com/blog"
feed_name = "example-blog"

[[sites]]
url = "https://news.ycombinator.com"
feed_name = "hackernews"

# Add as many sites as you want!
```

#### File 2: `.github/workflows/tracker.yml`
This is the GitHub Action that does the tracking:

.github/workflows/tracker.yml - This runs the tracker
```yaml
```

### Step 3: Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** (in the top menu)
3. Scroll down to **Pages** (in the left sidebar)
4. Under **Source**, select **GitHub Actions**
5. Click **Save**

### Step 4: Run the workflow

1. Go to the **Actions** tab in your repository
2. Click on "Track Websites" workflow
3. Click "Run workflow" button
4. Wait about 2 minutes for it to complete

### ✅ That's it!

Your RSS feeds are now live at:
- Homepage: `https://YOUR-USERNAME.github.io/YOUR-REPO/`
- RSS feeds: `https://YOUR-USERNAME.github.io/YOUR-REPO/feeds/example-blog.xml`
- History viewer: `https://YOUR-USERNAME.github.io/YOUR-REPO/history-explorer.html`

### What happens next?

- The tracker will run automatically every 6 hours
- When sites change, the RSS feeds update with diffs showing exactly what changed
- You can add these RSS feeds to any RSS reader (Feedly, Inoreader, etc.)
- All history is preserved - you can browse past changes anytime

### Customization

#### Change how often it runs
Edit the `cron` line in the workflow:
- `'0 */6 * * *'` = every 6 hours
- `'0 */12 * * *'` = every 12 hours
- `'0 9 * * *'` = daily at 9 AM
- `'*/30 * * * *'` = every 30 minutes

#### Add more websites
Just edit `sites.toml` and add more entries:
```toml
[[sites]]
url = "https://another-site.com/breaking-news"
feed_name = "another-site"
```

### Troubleshooting

**Workflow fails?**
- Check the Actions tab for error messages
- Make sure the URLs in sites.toml are accessible
- Some sites block automated access - try finding an alternative URL

**Don't see your feeds?**
- Wait for the workflow to complete (check Actions tab)
- Make sure GitHub Pages is enabled with "GitHub Actions" source
- Check that your repository is public (or you have GitHub Pro for private Pages)

**Want to track JavaScript-heavy sites?**
- This tool works best with static content
- For JavaScript-heavy sites, look for a `/print` or text-only version
- Many sites have hidden RSS feeds - try adding `/feed` or `/rss` to the URL first

### Examples of what to track

- Blog posts and news sites
- Documentation and API changes
- Government announcements
- Product changelogs
- Status pages
- Job boards
- Price changes
- Legal/terms of service updates
- Information about live events, e.g. natural disasters, FEMA sites.

### Features of GitHub Pages Deployment

- **📊 Beautiful Dashboard** - Auto-generated index page showing all your feeds
- **📜 History Explorer** - Interactive tool to browse changes with diffs
- **🔗 Clean URLs** - Professional GitHub Pages URLs for all feeds
- **🌿 Clean Branches** - Uses GitHub Actions artifacts, no gh-pages branch needed
- **♻️ Non-Disruptive** - Deploys to `/watcher` subdirectory, won't affect existing Pages
- **🔄 Preserves History** - Maintains complete change history across deployments

### Advanced: Using in Existing GitHub Pages Sites

If you already have a GitHub Pages site, watcher deploys to the `/watcher` subdirectory by default, so it won't interfere:

- Your site: `username.github.io/repo/`
- Watcher: `username.github.io/repo/watcher/`

To deploy to a different path, modify the workflow:
```yaml
# Deploy to /rss instead of /watcher
BASE_URL="https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}/rss"
```

## 🚀 Traditional Setup (Commits to Main Branch)

### Option 1: Use as a Library (Recommended for Simple Setup)

Create your own repository that uses Watcher as a dependency:

#### 1. Create Your Repository

```bash
# Create a new repo for your RSS feeds
mkdir my-rss-tracker && cd my-rss-tracker
git init
```

#### 2. Create `sites.toml`

```toml
# sites.toml - List all the sites you want to track
[[sites]]
url = "https://example.com/blog"
feed_name = "example-blog"
min_hours = 12  # Optional: Only check every 12 hours

[[sites]]
url = "https://news.site.com"
feed_name = "news-site"
# No min_hours = check every time the action runs

[[sites]]
url = "https://changelog.app.com"
feed_name = "app-changelog"
min_hours = 168  # Check weekly (168 hours)

# Status pages might need more frequent checks
[[sites]]
url = "https://status.service.com"
feed_name = "service-status"
min_hours = 0.5  # Check every 30 minutes (if action runs that often)
```

**Note about `min_hours`**: This sets the minimum time between checks for each site. If your GitHub Action runs every 4 hours but a site has `min_hours = 24`, it will only be checked once per day. Sites without `min_hours` are checked every time the action runs.

#### 3. Create GitHub Workflow

Create `.github/workflows/update-feeds.yml`:

```yaml
name: Update RSS Feeds

on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:  # Manual trigger button

jobs:
  update-feeds:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Flox
        uses: flox/install-flox-action@v3

#flox activate -- uv python install 3.13
      - name: Setup environment and install watcher
        run: |
          flox init
          flox install uv
          flox activate -- uv pip install git+https://github.com/gpwclark/watcher.git

      - name: Update feeds
        run: |
          BASE_URL="https://github.com/${{ github.repository }}/blob/${{ github.ref_name }}"
          flox activate -- watcher-batch --config sites.toml --base-url "$BASE_URL"

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add feeds/ content/ || true
          if git diff --staged --quiet; then
            echo "No changes"
          else
            git commit -m "Update feeds: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
            git push
          fi
```

#### 4. Push and Enable Actions

```bash
git add .
git commit -m "Initial setup"
git remote add origin https://github.com/yourusername/my-rss-tracker.git
git push -u origin main
```

Your RSS feeds will be available at:
- `https://raw.githubusercontent.com/yourusername/my-rss-tracker/main/feeds/example-blog.xml`
- `https://raw.githubusercontent.com/yourusername/my-rss-tracker/main/feeds/news-site.xml`
- etc.

The content files are viewable at:
- `https://github.com/yourusername/my-rss-tracker/blob/main/content/example-blog/20250111-123456.html`

### Option 2: Fork This Repository

For development or if you want to customize the code:

### 2. Create Your Tracker Workflow

Create `.github/workflows/track-sites.yml`:

```yaml
name: Track Sites

on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:  # Manual trigger

jobs:
  scrape-sites:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    strategy:
      matrix:
        include:
          - url: https://example.com/updates
            feed_name: example-updates
          - url: https://blog.site.com
            feed_name: blog-site
          # Add more sites here

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Flox
        uses: flox/install-flox-action@v3

      - name: Setup environment with Flox
        run: |
          flox init
          flox install uv

      - name: Install dependencies
        run: flox activate -- uv sync

      - name: Scrape ${{ matrix.feed_name }}
        run: |
          BASE_URL="https://github.com/${{ github.repository }}/blob/${{ github.ref_name }}"
          flox activate -- uv run watcher "${{ matrix.url }}" "${{ matrix.feed_name }}" --base-url "$BASE_URL"

      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add feeds/ content/ || true
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "Update ${{ matrix.feed_name }}: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
            git push
          fi
```

### 3. Understanding Base URLs

The action automatically detects the base URL for content links in your RSS feeds:

**Default (automatic)**: GitHub blob URLs
- Format: `https://github.com/owner/repo/blob/main/content/...`
- Works immediately, no setup required
- HTML files render nicely on GitHub

**With GitHub Pages**: Use your Pages URL for cleaner links
```yaml
# In the scrape step:
BASE_URL="https://${{ github.repository_owner }}.github.io/${{ github.event.repository.name }}"
uv run watcher "${{ matrix.url }}" "${{ matrix.feed_name }}" --base-url "$BASE_URL"
```

### 4. Enable GitHub Pages (Optional but Recommended)

1. Go to Settings � Pages
2. Source: Deploy from branch
3. Branch: main, folder: / (root)
4. Save

Your RSS feeds will be available at:
- `https://yourusername.github.io/my-rss-feeds/feeds/example-updates.xml`

## 📁 Repository Structure

After running, your repository will contain:

```
my-rss-feeds/
   feeds/
      example-updates.xml       # RSS feed with diffs
      another-site.xml
      ...
   content/
      example-updates/
         20250111-120000.html  # Full content snapshots
         20250112-060000.html
         .metadata.json
      another-site/
          ...
   .github/workflows/
       track-example.yml
       track-another.yml
       ...
```

## <� Tracking Multiple Sites

### Option 1: Separate Workflow Files (Recommended for Different Schedules)

Create a separate workflow for each site with its own schedule:

**`.github/workflows/track-blog.yml`:**
```yaml
name: Track Tech Blog

on:
  schedule:
    - cron: '0 8,20 * * *'  # 8 AM and 8 PM
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: ./
        with:
          url: https://techblog.example.com
          feed_name: techblog
```

**`.github/workflows/track-news.yml`:**
```yaml
name: Track News Site

on:
  schedule:
    - cron: '*/30 * * * *'  # Every 30 minutes
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: ./
        with:
          url: https://news.example.com/latest
          feed_name: news-latest
```

### Option 2: Matrix Strategy (Efficient for Similar Schedules)

Track multiple sites in one workflow:

**`.github/workflows/track-all.yml`:**
```yaml
name: Track All Sites

on:
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    strategy:
      matrix:
        include:
          - url: https://blog1.example.com
            feed_name: blog1
          - url: https://blog2.example.com/posts
            feed_name: blog2-posts
          - url: https://status.service.com
            feed_name: service-status
          - url: https://changelog.app.com
            feed_name: app-changelog
      max-parallel: 2  # Limit concurrent runs

    steps:
      - uses: actions/checkout@v4
      - uses: ./
        with:
          url: ${{ matrix.url }}
          feed_name: ${{ matrix.feed_name }}
```

## 📊 Understanding the Git Diffs

Each RSS entry includes the **complete, untruncated diff** showing exactly what changed. The diff is automatically wrapped in CDATA sections for proper XML escaping. For example:

```xml
<description><![CDATA[
Update from https://example.com/changelog

<pre><code>
@@ -10,7 +10,7 @@
 <h2>Latest Updates</h2>
-<p>Version 2.0.1 - Bug fixes</p>
+<p>Version 2.0.2 - New features and improvements</p>

+<h3>What's New:</h3>
+<ul>
+  <li>Added dark mode support</li>
+  <li>Improved performance by 50%</li>
+  <li>Fixed login issues</li>
+</ul>
</code></pre>
]]></description>
```

The diff shows:
- Lines starting with `-` were removed
- Lines starting with `+` were added
- Context lines show unchanged content around the changes
- **No truncation** - the complete diff is included in every RSS entry
- Diffs are cleaned to remove unnecessary git headers for better readability

## 🔧 Advanced Configuration

### Organizing Feeds by Category

Create a hierarchical structure:

```yaml
- uses: ./
  with:
    url: https://example.com
    feed_name: tech/blogs/example  # Creates nested directories
```

Results in:
```
feeds/tech/blogs/example.xml
content/tech/blogs/example/...
```

### Custom Update Frequencies

Different sites need different monitoring frequencies:

```yaml
# High-frequency (News, Status Pages)
- cron: '*/15 * * * *'  # Every 15 minutes

# Medium-frequency (Blogs, Documentation)
- cron: '0 */6 * * *'   # Every 6 hours

# Low-frequency (Changelogs, Archives)
- cron: '0 9 * * 1'     # Weekly on Mondays

# Business hours only
- cron: '0 9-17 * * 1-5'  # Hourly, 9-5 Mon-Fri
```

### Recommended Schedules by Content Type

| Content Type | Suggested Frequency | Cron Expression |
|-------------|-------------------|-----------------|
| Breaking News | Every 15-30 min | `*/30 * * * *` |
| Blog Posts | Every 6-12 hours | `0 */12 * * *` |
| Documentation | Daily | `0 9 * * *` |
| Status Pages | Every 30 min | `*/30 * * * *` |
| Changelogs | Weekly | `0 9 * * 1` |
| Job Boards | Every 4 hours | `0 */4 * * *` |

## 📱 Using the RSS Feeds

### Popular RSS Readers

Add your feeds to any RSS reader:

- **Feedly**: Click + � Add Content � By URL
- **Inoreader**: Add Feed � By URL
- **NewsBlur**: + Add Site � Add Site Address
- **Thunderbird**: File � New � Feed Account
- **NetNewsWire**: File � Add Feed
- **Miniflux**: Feeds � Add Feed � Feed URL

### Feed URLs

With GitHub Pages enabled:
```
https://yourusername.github.io/my-rss-feeds/feeds/[feed-name].xml
```

Without GitHub Pages (raw GitHub):
```
https://raw.githubusercontent.com/yourusername/my-rss-feeds/main/feeds/[feed-name].xml
```

## 💻 Local Development

### CLI Usage

For local testing and development:

```bash
# Install the package
pip install -e .

# Run locally
watcher https://example.com/page my-test-feed

# With custom base URL
watcher https://example.com/page my-test-feed --base-url https://mysite.com
```

### Python Library Usage

```python
from watcher import scrape_and_update_feed, ScraperRequest

# Create a request
request = ScraperRequest(
    url="https://example.com/updates",
    feed_name="example-updates",
    base_url="https://github.com/user/repo/blob/main"
)/

# Scrape and update
result = scrape_and_update_feed(request)

if result.success and result.changed:
    print(f"New content saved: {result.filename}")
    print(f"RSS feed updated: {result.feed_path}")
elif result.success and not result.changed:
    print("No changes detected")
else:
    print(f"Error: {result.error_message}")
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=watcher
```

## =� Best Practices

### 1. GitHub Actions Limits

Be mindful of GitHub's free tier limits:
- **Public repos**: Unlimited Actions minutes
- **Private repos**: 2,000 minutes/month

Calculate your usage:
```
Minutes = (Runs per day � 30 days � ~2 min per run)

Example: Every 6 hours = 4 � 30 � 2 = 240 minutes/month
```

### 2. Respectful Scraping

- Don't poll more frequently than necessary
- Check if the site offers an API first
- Respect robots.txt
- Consider adding delays between requests if tracking many pages from the same site

### 3. Feed Management

- Keep descriptions concise (diffs are truncated at 2000 chars)
- Archive old content periodically to keep repos manageable
- Use meaningful feed names for easy identification

### 4. Error Handling

Add notifications for failures:

```yaml
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v6
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'Scraping failed for ${{ matrix.feed_name }}',
        body: 'Check the Actions logs for details.'
      })
```

## = Troubleshooting

### Feed Not Updating?

1. **Check Actions tab** for error messages
2. **Verify URL accessibility** - some sites block GitHub IPs
3. **Check for JavaScript** - sites requiring JS won't work
4. **Try manual run** - use workflow_dispatch

### Content Looks Wrong?

- Some sites need JavaScript (not supported)
- Try finding a `/text` or `/print` version
- Check if the site has an API or existing RSS feed
- Consider using the site's sitemap.xml

### Very Large Diffs?

Full diffs are always included in the RSS feed. RSS readers will handle the display appropriately. For extremely large changes, you can always visit the linked content file to view the content in your browser.

## > Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## =� License

This project is licensed under the MIT License - see the LICENSE file for details.

## =O Acknowledgments

Built with excellent open-source tools:
- [Trafilatura](https://trafilatura.readthedocs.io/) - Web scraping and content extraction
- [feedgenerator](https://github.com/getpelican/feedgenerator) - RSS feed generation
- [GitPython](https://gitpython.readthedocs.io/) - Git integration

Inspired by Simon Willison's [git-scraping](https://simonwillison.net/2020/Oct/9/git-scraping/) technique.

## =� Example Use Cases

- **Track competitor blog posts** with diffs showing new content
- **Monitor documentation changes** to stay updated on API changes
- **Follow government notices** with full change history
- **Watch product changelogs** across multiple services
- **Track job postings** with instant notifications of new posts
- **Monitor status pages** for service disruptions

---

<p align="center">
  Made with d for the RSS community
</p>
