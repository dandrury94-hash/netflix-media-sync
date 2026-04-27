import datetime
import json
import logging
import threading
from pathlib import Path

from app.config import REMOVAL_HISTORY_PATH

logger = logging.getLogger(__name__)


class RemovalHistory:
    def __init__(self, path: Path = REMOVAL_HISTORY_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._entries = data
        except Exception:
            logger.warning("Failed to load removal history from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            cutoff = (datetime.date.today() - datetime.timedelta(days=180)).isoformat()
            self._entries = [e for e in self._entries if e.get("date_removed", "") >= cutoff]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._entries, indent=2), encoding="utf-8")
        except Exception:
            logger.warning("Failed to save removal history to %s", self.path, exc_info=True)

    def log_removal(
        self,
        title: str,
        media_type: str,
        reason: str = "retention",
        was_watched: bool = False,
    ) -> None:
        with self._lock:
            self._entries.append({
                "title": title,
                "type": media_type,
                "date_removed": datetime.date.today().isoformat(),
                "reason": reason,
                "was_watched": was_watched,
            })
            self._save()

    def get_recent(self, days: int = 180) -> list[dict]:
        with self._lock:
            cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
            return [e for e in self._entries if e.get("date_removed", "") >= cutoff]
