import json
from pathlib import Path
from typing import Any

from app.config import CONFIG_PATH, DEFAULT_SETTINGS, ENV_VAR_TO_SETTING


class SettingsStore:
    def __init__(self) -> None:
        self.path = CONFIG_PATH
        self.values = DEFAULT_SETTINGS.copy()
        self.load()

    def _load_from_file(self) -> None:
        if not self.path.exists():
            return

        try:
            content = self.path.read_text(encoding="utf-8")
            loaded = json.loads(content)
            if isinstance(loaded, dict):
                self.values.update({k: loaded[k] for k in loaded if k in self.values})
        except Exception:
            pass

    def load(self) -> None:
        self._load_from_file()
        self._apply_environment_overrides()

    def _apply_environment_overrides(self) -> None:
        import os

        for env_key, setting_key in ENV_VAR_TO_SETTING.items():
            if os.getenv(env_key) is None:
                continue
            raw = os.getenv(env_key)
            if raw is None:
                continue
            if isinstance(self.values.get(setting_key), bool):
                self.values[setting_key] = raw.lower() == "true"
            elif isinstance(self.values.get(setting_key), int):
                try:
                    self.values[setting_key] = int(raw)
                except ValueError:
                    pass
            else:
                self.values[setting_key] = raw

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.values, indent=2), encoding="utf-8")

    def update(self, updated: dict[str, Any]) -> None:
        for key, value in updated.items():
            if key in self.values:
                self.values[key] = value
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return self.values.copy()
