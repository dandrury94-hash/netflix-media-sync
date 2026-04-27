import json
import logging
import threading
from pathlib import Path

from app.config import MANUAL_OVERRIDES_PATH

logger = logging.getLogger(__name__)


class ManualOverrides:
    def __init__(self, path: Path = MANUAL_OVERRIDES_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._protected: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("protected"), list):
                self._protected = set(data["protected"])
        except Exception:
            logger.warning("Failed to load manual overrides from %s", self.path, exc_info=True)

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"protected": sorted(self._protected)}, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.warning("Failed to save manual overrides to %s", self.path, exc_info=True)

    def set_override(self, title: str, protected: bool) -> None:
        with self._lock:
            if protected:
                self._protected.add(title)
            else:
                self._protected.discard(title)
            self._save()

    def to_set(self) -> set[str]:
        with self._lock:
            return set(self._protected)
