import datetime
import json
import logging
import threading
from pathlib import Path

from app.config import DISMISSED_PATH

logger = logging.getLogger(__name__)


class DismissedTitles:
    def __init__(self, path: Path = DISMISSED_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._data = data
        except Exception:
            logger.warning("Failed to load dismissed titles from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to save dismissed titles to %s", self.path, exc_info=True)

    def dismiss(self, title: str, media_type: str, in_library: bool) -> None:
        with self._lock:
            self._data[title] = {
                "type": media_type,
                "dismissed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "in_library": in_library,
            }
            self._save()

    def undismiss(self, title: str) -> None:
        with self._lock:
            self._data.pop(title, None)
            self._save()

    def get_all(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._data)

    def is_dismissed(self, title: str) -> bool:
        with self._lock:
            return title in self._data

    def get_pending_deletion(self) -> list[dict]:
        grace = datetime.timedelta(minutes=15)
        now = datetime.datetime.now()
        result = []
        with self._lock:
            for title, entry in self._data.items():
                if not entry.get("in_library"):
                    continue
                try:
                    dismissed_at = datetime.datetime.fromisoformat(entry["dismissed_at"])
                except (KeyError, ValueError):
                    continue
                if (now - dismissed_at) >= grace:
                    result.append({"title": title, **entry})
        return result

    def mark_deleted(self, title: str) -> None:
        with self._lock:
            if title in self._data:
                self._data[title]["in_library"] = False
                self._save()
