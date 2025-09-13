"""Track statistics for feeds and proxies."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional
import threading


class StatsTracker:
    """Track statistics for feeds and proxies."""

    def __init__(self, stats_dir: Path = None):
        """Initialize the stats tracker."""
        self.stats_dir = stats_dir or Path(".watcher_stats")
        self.stats_dir.mkdir(exist_ok=True)
        self.feed_stats_file = self.stats_dir / "feed_stats.json"
        self.proxy_stats_file = self.stats_dir / "proxy_stats.json"
        self._lock = threading.Lock()

    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file or return empty dict."""
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
        return {}

    def _save_json(self, file_path: Path, data: Dict):
        """Save data to JSON file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def record_feed_attempt(
        self,
        feed_id: str,
        success: bool,
        error_details: Optional[Dict] = None,
        proxy_used: Optional[str] = None,
    ):
        """Record a feed scraping attempt."""
        with self._lock:
            stats = self._load_json(self.feed_stats_file)

            if feed_id not in stats:
                stats[feed_id] = {
                    "total_runs": 0,
                    "total_failures": 0,
                    "consecutive_failures": 0,
                    "last_failure": None,
                    "last_success": None,
                    "first_run": datetime.now(timezone.utc).isoformat(),
                }

            feed_stats = stats[feed_id]
            feed_stats["total_runs"] += 1
            now = datetime.now(timezone.utc).isoformat()

            if success:
                feed_stats["consecutive_failures"] = 0
                feed_stats["last_success"] = now
            else:
                feed_stats["total_failures"] += 1
                feed_stats["consecutive_failures"] += 1
                feed_stats["last_failure"] = now
                feed_stats["last_error"] = error_details

            self._save_json(self.feed_stats_file, stats)

    def record_proxy_attempt(
        self, proxy_id: str, url: str, success: bool, error: Optional[str] = None
    ):
        """Record a proxy usage attempt."""
        with self._lock:
            stats = self._load_json(self.proxy_stats_file)

            if proxy_id not in stats:
                stats[proxy_id] = {
                    "urls": {},
                    "global_stats": {
                        "total_requests": 0,
                        "total_successes": 0,
                        "success_rate": 0.0,
                    },
                }

            proxy_stats = stats[proxy_id]
            global_stats = proxy_stats["global_stats"]
            url_stats = proxy_stats["urls"]

            # Update global stats
            global_stats["total_requests"] += 1
            if success:
                global_stats["total_successes"] += 1
            global_stats["success_rate"] = (
                global_stats["total_successes"] / global_stats["total_requests"]
            )

            # Update URL-specific stats
            if url not in url_stats:
                url_stats[url] = {
                    "attempts": 0,
                    "successes": 0,
                    "last_success": None,
                    "last_failure": None,
                }

            url_stat = url_stats[url]
            url_stat["attempts"] += 1
            now = datetime.now(timezone.utc).isoformat()

            if success:
                url_stat["successes"] += 1
                url_stat["last_success"] = now
            else:
                url_stat["last_failure"] = now
                url_stat["last_error"] = error

            self._save_json(self.proxy_stats_file, stats)

    def get_feed_stats(self, feed_id: str) -> Optional[Dict]:
        """Get statistics for a specific feed."""
        stats = self._load_json(self.feed_stats_file)
        return stats.get(feed_id)

    def get_proxy_success_rate(self, proxy_id: str, url: Optional[str] = None) -> float:
        """Get success rate for a proxy, optionally for a specific URL."""
        stats = self._load_json(self.proxy_stats_file)
        if proxy_id not in stats:
            return 0.0

        proxy_stats = stats[proxy_id]

        if url and url in proxy_stats["urls"]:
            url_stat = proxy_stats["urls"][url]
            if url_stat["attempts"] > 0:
                return url_stat["successes"] / url_stat["attempts"]

        return proxy_stats["global_stats"].get("success_rate", 0.0)

    def get_best_proxy_for_url(
        self, url: str, available_proxies: list
    ) -> Optional[str]:
        """Get the best performing proxy for a specific URL."""
        if not available_proxies:
            return None

        proxy_scores = []
        for proxy_id in available_proxies:
            # Get URL-specific success rate
            stats = self._load_json(self.proxy_stats_file)
            url_attempts = 0
            if proxy_id in stats and url in stats[proxy_id]["urls"]:
                url_stat = stats[proxy_id]["urls"][url]
                url_attempts = url_stat["attempts"]

            url_rate = self.get_proxy_success_rate(proxy_id, url)
            global_rate = self.get_proxy_success_rate(proxy_id)

            # Weighted score: heavily prefer URL-specific if we have data
            if url_attempts > 0:
                # If we have URL-specific data, use it primarily
                score = url_rate * 0.9 + global_rate * 0.1
            else:
                # No URL-specific data, use global rate
                score = global_rate * 0.3  # Lower weight for non-specific

            proxy_scores.append((proxy_id, score))

        # Sort by score descending
        proxy_scores.sort(key=lambda x: x[1], reverse=True)

        # Return best proxy if it has any successful history
        if proxy_scores and proxy_scores[0][1] > 0:
            return proxy_scores[0][0]

        # If no proxy has success history, return first available
        return available_proxies[0]
