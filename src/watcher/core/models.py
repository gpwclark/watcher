"""Data models for the watcher library."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperRequest:
    """Request object for scraping a URL."""

    url: str
    feed_name: str
    base_url: Optional[str] = None
    min_hours: Optional[float] = None  # Minimum hours between checks


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
