import logging

import requests

from app.settings import SettingsStore

logger = logging.getLogger(__name__)

_PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


class PushoverClient:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings

    def is_enabled(self) -> bool:
        return (
            bool(self.settings.get("pushover_enabled"))
            and bool(self.settings.get("pushover_user_key"))
            and bool(self.settings.get("pushover_api_token"))
        )

    def send(self, title: str, message: str, priority: int = 0) -> None:
        if not self.is_enabled():
            return
        try:
            resp = requests.post(
                _PUSHOVER_URL,
                data={
                    "token": self.settings.get("pushover_api_token"),
                    "user": self.settings.get("pushover_user_key"),
                    "title": title,
                    "message": message,
                    "priority": priority,
                },
                timeout=10,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Pushover notification failed: %s", exc)
