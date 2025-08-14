"""Watcher - A git-scraping tool with RSS feed generation."""

from .lib import scrape_and_update_feed
from .core.models import ScraperRequest, ScraperResult

__version__ = "0.1.0"
__all__ = ["scrape_and_update_feed", "ScraperRequest", "ScraperResult"]
