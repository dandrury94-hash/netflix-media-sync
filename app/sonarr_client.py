import logging

import requests
from app.settings import SettingsStore

logger = logging.getLogger(__name__)


class SonarrClient:
    def __init__(self, settings: SettingsStore):
        self.settings = settings

    @property
    def base_url(self) -> str:
        return self.settings.get("sonarr_url", "").rstrip("/")

    @property
    def api_key(self) -> str:
        return self.settings.get("sonarr_api_key", "")

    @property
    def quality_profile_id(self) -> int:
        return int(self.settings.get("sonarr_quality_profile_id", 1))

    @property
    def root_folder(self) -> str:
        return self.settings.get("root_folder_series", "")

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key}

    def _get(self, path: str, params: dict | None = None):
        response = requests.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json_data: dict):
        response = requests.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json_data,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def lookup_series(self, title: str) -> dict | None:
        results = self._get("/api/v3/series/lookup", {"term": title})
        if isinstance(results, list) and results:
            return results[0]
        return None

    def add_series(self, title: str) -> bool:
        details = self.lookup_series(title)
        if not details:
            logger.warning("Sonarr lookup failed for series: %s", title)
            return False

        if details.get("id"):
            logger.info("Series already exists in Sonarr: %s", title)
            return False

        tvdb_id = details.get("tvdbId")
        if not tvdb_id:
            logger.warning("Unable to add series without TVDB ID: %s", title)
            return False

        self._post("/api/v3/series", {
            "title": details.get("title"),
            "tvdbId": tvdb_id,
            "qualityProfileId": self.quality_profile_id,
            "rootFolderPath": self.root_folder,
            "seasonFolder": True,
            "monitored": True,
            "addOptions": {"searchForMissingEpisodes": True},
        })
        logger.info("Added series to Sonarr: %s", title)
        return True
