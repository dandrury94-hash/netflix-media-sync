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
        today = datetime.date.today().isoformat()
        with self._lock:
            source_data = self._data.setdefault(source, {})
            prev_type_data: dict[str, dict] = source_data.get(media_type, {})
            new_type_data: dict[str, dict] = {}
            for idx, title in enumerate(ranked_titles):
                prev = prev_type_data.get(title, {})
                new_type_data[title] = {
                    "rank": idx + 1,
                    "previous_rank": prev.get("rank"),
                    "first_seen": prev.get("first_seen") or today,
                }
            source_data[media_type] = new_type_data
            self._save()

    def get_all(self) -> dict:
        with self._lock:
            return dict(self._data)
