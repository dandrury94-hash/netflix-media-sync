import datetime
import logging

import requests
from app.settings import SettingsStore

logger = logging.getLogger(__name__)


def _parse_timestamp(value):
    try:
        if isinstance(value, (int, float)):
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc).replace(tzinfo=None)
        if isinstance(value, str) and value.isdigit():
            return datetime.datetime.fromtimestamp(int(value), tz=datetime.timezone.utc).replace(tzinfo=None)
        dt = datetime.datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


class TautulliClient:
    def __init__(self, settings: SettingsStore):
        self.settings = settings

    @property
    def base_url(self) -> str:
        return self.settings.get("tautulli_url", "").rstrip("/")

    @property
    def api_key(self) -> str:
        return self.settings.get("tautulli_api_key", "")

    @property
    def lookback_days(self) -> int:
        return int(self.settings.get("tautulli_lookback_days", 30))

    def _request(self, cmd: str, params: dict | None = None):
        params = params or {}
        default = {"apikey": self.api_key, "cmd": cmd}
        response = requests.get(self.base_url + "/api/v2", params={**default, **params}, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return data.get("response", {})

    def fetch_protected_titles(self) -> set[str]:
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        cutoff = now - datetime.timedelta(days=self.lookback_days)
        protected_titles: set[str] = set()

        logger.info("Fetching Tautulli history to protect watched media")
        history = self._request("get_history", {"length": 200})
        items = history.get("data", [])
        if not isinstance(items, list):
            items = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if not title:
                continue
            watched_at = _parse_timestamp(item.get("last_viewed_at") or item.get("date"))
            if watched_at and watched_at >= cutoff:
                protected_titles.add(title.strip())
                continue
            progress = item.get("progress", 0)
            try:
                progress = float(progress)
            except Exception:
                progress = 0.0
            if progress > 0 and progress < 100:
                protected_titles.add(title.strip())

        activity = self._request("get_activity")
        sessions = activity.get("sessions", [])
        if not isinstance(sessions, list):
            sessions = []
        for item in sessions:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            if title:
                protected_titles.add(title.strip())

        logger.info("Protected titles from Tautulli: %s", list(protected_titles)[:10])
        return protected_titles
