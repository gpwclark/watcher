# Content Filtering Options

The watcher tool provides powerful filtering options to extract only the content you need from web pages. You can filter by HTML tags, element IDs, and CSS classes.

## Configuration

All filtering options can be specified in your `watcher-config.toml` file for each site:

```toml
[[watcher.sites]]
url = "https://example.com/page"
feed_name = "example-site"
# Add filtering options here
```

## Filtering Options

### Tag-based Filtering

#### exclude_tags (default behavior)
Removes specified HTML tags from the content. By default, the following tags are excluded:
- `script`
- `style`
- `nav`
- `header`
- `footer`

```toml
# Custom exclude tags
exclude_tags = ["div", "aside", "nav", "footer"]
```

#### include_tags (exclusive with exclude_tags)
Only keeps content from specified tags. Everything else is removed.

```toml
# Only keep article and section content
include_tags = ["article", "section", "main"]
```

**Note:** You cannot use both `exclude_tags` and `include_tags` for the same site.

### ID-based Filtering

#### exclude_ids
Removes elements with specific IDs.

```toml
# Remove elements by ID
exclude_ids = ["sidebar", "ads", "cookie-banner"]
```

#### include_ids (exclusive with exclude_ids)
Only keeps elements with specified IDs.

```toml
# Only keep specific content areas
include_ids = ["main-content", "article-body"]
```

### Class-based Filtering

#### exclude_classes
Removes elements with specific CSS classes.

```toml
# Remove elements by class
exclude_classes = ["advertisement", "popup", "social-share"]
```

#### include_classes (exclusive with exclude_classes)
Only keeps elements with specified CSS classes.

```toml
# Only keep specific content classes
include_classes = ["article-content", "post-body", "main-text"]
```

## Examples

### Example 1: News Article Extraction
Extract only the main article content, excluding navigation and ads:

```toml
[[watcher.sites]]
url = "https://news-site.com/article"
feed_name = "news-articles"
include_tags = ["article"]
exclude_classes = ["ad-container", "related-articles", "comments"]
```

### Example 2: Documentation Site
Track only the documentation content area:

```toml
[[watcher.sites]]
url = "https://docs.example.com/guide"
feed_name = "docs-updates"
include_ids = ["docs-content"]
exclude_tags = []  # Disable default excludes
```

### Example 3: Blog with Specific Content
Monitor blog posts but exclude sidebars and comments:

```toml
[[watcher.sites]]
url = "https://blog.example.com"
feed_name = "blog-posts"
include_classes = ["post-content", "entry-content"]
exclude_ids = ["comments", "sidebar"]
```

### Example 4: Forum Thread
Track forum discussions but exclude signatures and ads:

```toml
[[watcher.sites]]
url = "https://forum.example.com/thread/123"
feed_name = "forum-thread"
include_classes = ["post-message"]
exclude_classes = ["signature", "user-stats", "ad-block"]
```

## Important Notes

1. **Mutual Exclusivity**: Include and exclude options for the same filter type (tags, IDs, or classes) cannot be used together. Choose one approach per filter type.

2. **Order of Operations**: Filters are applied in this order:
   - Tag filtering (include/exclude)
   - ID filtering (include/exclude)
   - Class filtering (include/exclude)

3. **Empty Results**: If your filters are too restrictive, you might get empty content. Start with broader filters and refine as needed.

4. **Default Behavior**: If no filtering options are specified, the default `exclude_tags` list is applied (removing script, style, nav, header, and footer tags).

5. **Performance**: Include filters are generally more efficient than exclude filters when you know exactly what content you want.

## Testing Your Filters

Before deploying, test your filtering configuration:

1. Run the watcher on a single site:
   ```bash
   watcher-batch --config your-config.toml
   ```

2. Check the generated content in `content/[feed-name]/` to ensure you're capturing the right elements.

3. Adjust your filters based on the results.