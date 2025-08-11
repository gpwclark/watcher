"""Main library API for the watcher package."""

from .core.scraper import ContentScraper
from .core.storage import ContentStorage
from .core.rss_manager import RSSManager
from .core.models import ScraperRequest, ScraperResult


def scrape_and_update_feed(request: ScraperRequest) -> ScraperResult:
    """
    Scrape a URL and update the RSS feed if content has changed.

    Args:
        request: ScraperRequest containing URL, feed name, and optional base URL

    Returns:
        ScraperResult indicating success, whether content changed, and file paths
    """
    try:
        # Initialize components
        scraper = ContentScraper(request.url)
        storage = ContentStorage(request.feed_name)
        rss_manager = RSSManager(request.feed_name, request.base_url)

        # Check if enough time has passed since last check
        if not storage.should_check(request.min_hours):
            return ScraperResult(
                success=True,
                changed=False,
                skipped=True,
                error_message=f"Skipped - checked too recently (min_hours={request.min_hours})"
            )

        # Fetch content
        content_data = scraper.fetch_content()
        if not content_data:
            return ScraperResult(
                success=False,
                changed=False,
                error_message="Failed to fetch content from URL"
            )

        # Save content if changed
        save_result = storage.save_content(content_data)
        if not save_result:
            return ScraperResult(
                success=True,
                changed=False,
                content_hash=content_data['hash']
            )

        filename, diff_content = save_result

        # Create description with diff if available
        description = content_data.get('description', f'Update from {request.url}')
        if diff_content:
            # Include full diff without truncation
            # The RSS manager will handle CDATA wrapping
            description = f"{description}\n\n{diff_content}"

        # Update RSS feed
        rss_item = {
            'title': content_data['title'],
            'description': description,
            'timestamp': content_data['timestamp'],
            'hash': content_data['hash'],
            'filename': filename,
        }

        rss_manager.create_or_update_feed(rss_item)

        return ScraperResult(
            success=True,
            changed=True,
            filename=filename,
            feed_path=f"feeds/{request.feed_name}.xml",
            content_hash=content_data['hash']
        )

    except Exception as e:
        return ScraperResult(
            success=False,
            changed=False,
            error_message=str(e)
        )