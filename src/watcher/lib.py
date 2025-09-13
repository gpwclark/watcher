"""Main library API for the watcher package."""

from .core.scraper import ContentScraper
from .core.storage import ContentStorage
from .core.rss_manager import RSSManager
from .core.models import ScraperRequest, ScraperResult
from .core.proxy_manager import ProxyManager
from .core.stats_tracker import StatsTracker
from .core.error_feed import ErrorFeedManager
from typing import Optional, List


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
        scraper = ContentScraper(
            request.url,
            exclude_tags=request.exclude_tags,
            include_tags=request.include_tags,
            exclude_ids=request.exclude_ids,
            include_ids=request.include_ids,
            exclude_classes=request.exclude_classes,
            include_classes=request.include_classes,
        )
        storage = ContentStorage(request.feed_name)
        rss_manager = RSSManager(request.feed_name, request.base_url)

        # Check if enough time has passed since last check
        if not storage.should_check(request.min_hours):
            return ScraperResult(
                success=True,
                changed=False,
                skipped=True,
                error_message=f"Skipped - checked too recently (min_hours={request.min_hours})",
            )

        # Fetch content
        content_data = scraper.fetch_content()
        if not content_data:
            return ScraperResult(
                success=False,
                changed=False,
                error_message="Failed to fetch content from URL",
            )

        # Check if it's an error response
        if isinstance(content_data, dict) and content_data.get("error"):
            return ScraperResult(
                success=False,
                changed=False,
                error_message=content_data.get("error_message", "Unknown error"),
                error_details=content_data,  # Pass along all error details
            )

        # Save content if changed
        save_result = storage.save_content(content_data)
        if not save_result:
            return ScraperResult(
                success=True, changed=False, content_hash=content_data["hash"]
            )

        filename, diff_content = save_result

        # Create description with diff if available
        description = content_data.get("description", f"Update from {request.url}")
        if diff_content:
            # Include full diff without truncation, wrapped in pre/code tags
            # The RSS manager will wrap this in CDATA sections
            description = f"{description}\n\n<pre><code>{diff_content}</code></pre>"

        # Update RSS feed
        rss_item = {
            "title": content_data["title"],
            "description": description,
            "timestamp": content_data["timestamp"],
            "hash": content_data["hash"],
            "filename": filename,
        }

        rss_manager.create_or_update_feed(rss_item)

        return ScraperResult(
            success=True,
            changed=True,
            filename=filename,
            feed_path=f"feeds/{request.feed_name}.xml",
            content_hash=content_data["hash"],
        )

    except Exception as e:
        return ScraperResult(success=False, changed=False, error_message=str(e))


def scrape_with_retries(
    request: ScraperRequest,
    proxy_manager: Optional[ProxyManager] = None,
    stats_tracker: Optional[StatsTracker] = None,
    error_feed_manager: Optional[ErrorFeedManager] = None,
    proxies: Optional[List[str]] = None,
    proxy_mode: str = "on_failure",
    max_retries: int = 3,
) -> ScraperResult:
    """
    Scrape with intelligent retry and proxy support.

    Args:
        request: ScraperRequest containing URL and feed configuration
        proxy_manager: Optional ProxyManager for handling proxies
        stats_tracker: Optional StatsTracker for recording statistics
        error_feed_manager: Optional ErrorFeedManager for error reporting
        proxies: List of proxy IDs to use
        proxy_mode: "always", "on_failure", or "never"
        max_retries: Maximum number of retry attempts

    Returns:
        ScraperResult with success status and details
    """
    # Initialize components
    scraper = ContentScraper(
        request.url,
        exclude_tags=request.exclude_tags,
        include_tags=request.include_tags,
        exclude_ids=request.exclude_ids,
        include_ids=request.include_ids,
        exclude_classes=request.exclude_classes,
        include_classes=request.include_classes,
    )
    storage = ContentStorage(request.feed_name)
    rss_manager = RSSManager(request.feed_name, request.base_url)

    # Check if enough time has passed since last check
    if not storage.should_check(request.min_hours):
        if stats_tracker:
            stats_tracker.record_feed_attempt(request.feed_name, success=True)
        return ScraperResult(
            success=True,
            changed=False,
            skipped=True,
            error_message=f"Skipped - checked too recently (min_hours={request.min_hours})",
        )

    # Determine proxy strategy
    use_proxies = proxies if proxy_manager and proxies else []
    attempts = []
    content_data = None
    last_error = None

    # Build retry chain
    retry_chain = []

    if proxy_mode == "always" and use_proxies:
        # Only use proxies
        if stats_tracker:
            # Get best proxy based on history
            best_proxy = stats_tracker.get_best_proxy_for_url(request.url, use_proxies)
            if best_proxy:
                retry_chain.append(("proxy", best_proxy))
                # Add remaining proxies
                for p in use_proxies:
                    if p != best_proxy:
                        retry_chain.append(("proxy", p))
            else:
                retry_chain = [("proxy", p) for p in use_proxies]
        else:
            retry_chain = [("proxy", p) for p in use_proxies]
    elif proxy_mode == "never" or not use_proxies:
        # Only direct attempts
        retry_chain = [("direct", None)] * min(max_retries, 1)
    else:  # on_failure mode
        # Start with direct, then use proxies
        retry_chain.append(("direct", None))
        if use_proxies and stats_tracker:
            best_proxy = stats_tracker.get_best_proxy_for_url(request.url, use_proxies)
            if best_proxy:
                retry_chain.append(("proxy", best_proxy))
                for p in use_proxies:
                    if p != best_proxy:
                        retry_chain.append(("proxy", p))
        elif use_proxies:
            retry_chain.extend([("proxy", p) for p in use_proxies])

    # Limit to max_retries
    retry_chain = retry_chain[:max_retries]

    # Attempt to fetch content
    for attempt_type, proxy_id in retry_chain:
        proxy_url = None
        proxy_used = None

        if attempt_type == "proxy" and proxy_manager:
            proxy_url = proxy_manager.transform_url(request.url, proxy_id)
            proxy_used = proxy_id
            if not proxy_url:
                continue  # Skip if proxy transformation fails

        # Attempt to fetch
        try:
            content_data = scraper.fetch_content(proxy_url=proxy_url)

            if content_data and not content_data.get("error"):
                # Success!
                if stats_tracker:
                    stats_tracker.record_feed_attempt(
                        request.feed_name, success=True, proxy_used=proxy_used
                    )
                    if proxy_used:
                        stats_tracker.record_proxy_attempt(
                            proxy_used, request.url, success=True
                        )
                break  # Success, exit retry loop
            else:
                # Error in response
                last_error = content_data
                attempts.append(
                    {
                        "proxy": proxy_used or "direct",
                        "success": False,
                        "error": content_data.get("error_message", "Unknown error"),
                    }
                )

                if stats_tracker and proxy_used:
                    stats_tracker.record_proxy_attempt(
                        proxy_used,
                        request.url,
                        success=False,
                        error=content_data.get("error_message"),
                    )
        except Exception as e:
            last_error = {
                "error": True,
                "error_message": str(e),
                "error_type": type(e).__name__,
            }
            attempts.append(
                {"proxy": proxy_used or "direct", "success": False, "error": str(e)}
            )

            if stats_tracker and proxy_used:
                stats_tracker.record_proxy_attempt(
                    proxy_used, request.url, success=False, error=str(e)
                )

    # If all attempts failed
    if not content_data or content_data.get("error"):
        # Record failure in stats
        if stats_tracker:
            error_details = last_error or {"error_message": "All attempts failed"}
            error_details["proxy_attempts"] = attempts

            stats_tracker.record_feed_attempt(
                request.feed_name, success=False, error_details=error_details
            )

            # Add to error feed
            if error_feed_manager:
                feed_stats = stats_tracker.get_feed_stats(request.feed_name)
                error_feed_manager.add_error(
                    feed_id=request.feed_name,
                    url=request.url,
                    error_type=error_details.get("error_type", "ScraperError"),
                    error_message=error_details.get("error_message", "Unknown error"),
                    error_details=error_details,
                    feed_stats=feed_stats,
                )

        return ScraperResult(
            success=False,
            changed=False,
            error_message=last_error.get("error_message", "All attempts failed")
            if last_error
            else "Failed to fetch",
            error_details=last_error,
        )

    # Process successful content
    save_result = storage.save_content(content_data)
    if not save_result:
        return ScraperResult(
            success=True, changed=False, content_hash=content_data["hash"]
        )

    filename, diff_content = save_result

    # Create description with diff if available
    description = content_data.get("description", f"Update from {request.url}")
    if diff_content:
        description = f"{description}\n\n<pre><code>{diff_content}</code></pre>"

    # Update RSS feed
    rss_item = {
        "title": content_data["title"],
        "description": description,
        "timestamp": content_data["timestamp"],
        "hash": content_data["hash"],
        "filename": filename,
    }

    rss_manager.create_or_update_feed(rss_item)

    return ScraperResult(
        success=True,
        changed=True,
        filename=filename,
        feed_path=f"feeds/{request.feed_name}.xml",
        content_hash=content_data["hash"],
    )
