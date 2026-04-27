import datetime
import json
import logging
import threading
from pathlib import Path
from typing import Any

from app.config import SYNC_LOG_PATH

logger = logging.getLogger(__name__)


class SyncLog:
    def __init__(self, path: Path = SYNC_LOG_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {"last_sync": None, "entries": []}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._data = data
        except Exception:
            logger.warning("Failed to load sync log from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to save sync log to %s", self.path, exc_info=True)

    def log_add(self, title: str, media_type: str, source: str = "trakt") -> None:
        with self._lock:
            if not isinstance(self._data.get("entries"), list):
                self._data["entries"] = []
            self._data["entries"].append({
                "title": title,
                "type": media_type,
                "date_added": datetime.date.today().isoformat(),
                "source": source,
            })
            self._save()

    def set_last_sync(self, result: dict) -> None:
        with self._lock:
            self._data["last_sync"] = {
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                **{k: list(v) if isinstance(v, (set, list)) else v for k, v in result.items()},
            }
            self._save()

    def get_last_sync(self) -> dict | None:
        with self._lock:
            return self._data.get("last_sync")

    def get_entries(self) -> list[dict]:
        with self._lock:
            entries = self._data.get("entries", [])
            return list(entries) if isinstance(entries, list) else []

    def get_date_added(self, title: str) -> str | None:
        """Return the earliest date_added recorded for a title."""
        with self._lock:
            entries = self._data.get("entries", [])
            dates = [
                e["date_added"]
                for e in entries
                if isinstance(e, dict) and e.get("title") == title and e.get("date_added")
            ]
            return min(dates) if dates else None
