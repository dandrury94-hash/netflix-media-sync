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
        self._data: dict[str, Any] = {"last_sync": None, "entries": [], "pre_deletion_notified": {}, "last_watched": {}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._data = data
                self._data.pop("grace_periods", None)
                if "pre_deletion_notified" not in self._data:
                    self._data["pre_deletion_notified"] = {}
                if "last_watched" not in self._data:
                    self._data["last_watched"] = {}
        except Exception:
            logger.warning("Failed to load sync log from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to save sync log to %s", self.path, exc_info=True)

    def log_add(self, title: str, media_type: str, sources: list[str]) -> None:
        with self._lock:
            if not isinstance(self._data.get("entries"), list):
                self._data["entries"] = []
            self._data["entries"].append({
                "title": title,
                "type": media_type,
                "date_added": datetime.date.today().isoformat(),
                "sources": sources,
            })
            self._save()

    def set_last_sync(self, result: dict) -> None:
        with self._lock:
            self._data["last_sync"] = {
                "timestamp": datetime.datetime.now().strftime("%H:%M %d/%m/%Y"),
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

    def mark_pre_deletion_notified(self, title: str) -> None:
        with self._lock:
            pdn = self._data.setdefault("pre_deletion_notified", {})
            pdn[title] = datetime.date.today().isoformat()
            self._save()

    def get_pre_deletion_notified(self) -> dict[str, str]:
        with self._lock:
            return dict(self._data.get("pre_deletion_notified", {}))

    def clear_pre_deletion_notified(self, title: str) -> None:
        with self._lock:
            pdn = self._data.get("pre_deletion_notified", {})
            if title in pdn:
                del pdn[title]
                self._save()

    def set_last_watched(self, title: str, date_iso: str) -> None:
        with self._lock:
            watches = self._data.setdefault("last_watched", {})
            if title not in watches or date_iso > watches[title]:
                watches[title] = date_iso
                self._save()

    def get_last_watched_all(self) -> dict[str, str]:
        with self._lock:
            return dict(self._data.get("last_watched", {}))

    def merge_sources(self, title: str, new_sources: list[str]) -> None:
        """Add any new_sources not already recorded for this title across all its entries."""
        with self._lock:
            entries = self._data.get("entries", [])
            changed = False
            for entry in entries:
                if not isinstance(entry, dict) or entry.get("title") != title:
                    continue
                existing = entry.get("sources") or []
                to_add = [s for s in new_sources if s not in existing]
                if to_add:
                    entry["sources"] = existing + to_add
                    changed = True
            if changed:
                self._save()

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
