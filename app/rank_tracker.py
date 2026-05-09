import datetime
import json
import logging
import threading
from pathlib import Path

from app.config import RANK_TRACKER_PATH

logger = logging.getLogger(__name__)


class RankTracker:
    def __init__(self, path: Path = RANK_TRACKER_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._data = data
        except Exception:
            logger.warning("Failed to load rank tracker from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to save rank tracker to %s", self.path, exc_info=True)

    def update(self, source: str, media_type: str, ranked_titles: list[str]) -> None:
        """Update today's snapshot. Only rotates the baseline when the calendar date changes,
        so multiple syncs on the same day always compare against the previous day's rankings."""
        today = datetime.date.today().isoformat()
        with self._lock:
            src = self._data.setdefault(source, {})
            bucket = src.get(media_type, {})

            # Migrate old per-title format (no "today_ranks" key present)
            if bucket and "today_ranks" not in bucket:
                bucket = {}
            src[media_type] = bucket

            today_ranks: dict[str, int] = {t: idx + 1 for idx, t in enumerate(ranked_titles)}

            if bucket.get("today") != today:
                # New calendar day — rotate current snapshot → baseline
                bucket["baseline_date"] = bucket.get("today")
                bucket["baseline_ranks"] = bucket.get("today_ranks", {})
                bucket["today"] = today

            bucket["today_ranks"] = today_ranks

            first_seen: dict[str, str] = bucket.get("first_seen", {})
            for title in ranked_titles:
                if title not in first_seen:
                    first_seen[title] = today
            bucket["first_seen"] = first_seen

            self._save()

    def get_all(self) -> dict:
        """Return rank data in the same shape the rest of the app expects:
        {source: {media_type: {title: {rank, previous_rank, first_seen}}}}"""
        with self._lock:
            result: dict = {}
            for source, types in self._data.items():
                result[source] = {}
                for media_type, bucket in types.items():
                    if not isinstance(bucket, dict) or "today_ranks" not in bucket:
                        continue
                    baseline = bucket.get("baseline_ranks", {})
                    first_seen = bucket.get("first_seen", {})
                    result[source][media_type] = {
                        title: {
                            "rank": rank,
                            "previous_rank": baseline.get(title),
                            "first_seen": first_seen.get(title),
                        }
                        for title, rank in bucket["today_ranks"].items()
                    }
            return result
