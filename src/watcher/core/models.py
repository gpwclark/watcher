"""Data models for the watcher library."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ScraperRequest:
    """Request object for scraping a URL."""

    url: str
    feed_name: str
    base_url: Optional[str] = None
    min_hours: Optional[float] = None  # Minimum hours between checks
    exclude_tags: Optional[List[str]] = None  # Tags to remove during scraping
    include_tags: Optional[List[str]] = (
        None  # Only include these tags (exclusive with exclude_tags)
    )
    exclude_ids: Optional[List[str]] = None  # IDs to exclude
    include_ids: Optional[List[str]] = (
        None  # Only include these IDs (exclusive with exclude_ids)
    )
    exclude_classes: Optional[List[str]] = None  # Classes to exclude
    include_classes: Optional[List[str]] = (
        None  # Only include these classes (exclusive with exclude_classes)
    )


@dataclass
class ScraperResult:
    """Result of a scraping operation."""

    success: bool
    changed: bool
    filename: Optional[str] = None
    feed_path: Optional[str] = None
    error_message: Optional[str] = None
    content_hash: Optional[str] = None
    skipped: bool = False  # True if skipped due to min_hours
    error_details: Optional[dict] = None  # Full error details including stack trace
