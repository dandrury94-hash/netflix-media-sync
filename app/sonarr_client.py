import logging

import requests
from app.settings import SettingsStore

logger = logging.getLogger(__name__)

_TAG_NAME = "netflix-sync"


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
        if not response.ok:
            logger.error("Sonarr API error %s: %s", response.status_code, response.text)
        response.raise_for_status()
        return response.json()

    def ensure_tag(self, name: str) -> int:
        """Return the ID of an existing tag, creating it first if needed."""
        tags = self._get("/api/v3/tag")
        for tag in tags:
            if tag.get("label") == name:
                return tag["id"]
        result = self._post("/api/v3/tag", {"label": name})
        return result["id"]

    def get_tagged_series(self, tag_name: str) -> list[dict]:
        """Return all Sonarr series carrying the named tag."""
        try:
            tags = self._get("/api/v3/tag")
            tag_id = next((t["id"] for t in tags if t.get("label") == tag_name), None)
            if tag_id is None:
                return []
            series = self._get("/api/v3/series")
            return [s for s in series if tag_id in s.get("tags", [])]
        except Exception as exc:
            logger.warning("Failed to fetch tagged series from Sonarr: %s", exc)
            return []

    def get_all_series(self) -> list[dict]:
        try:
            return self._get("/api/v3/series")
        except Exception as exc:
            logger.warning("Failed to fetch Sonarr library: %s", exc)
            return []

    def get_series_by_id(self, series_id: int) -> dict | None:
        try:
            return self._get(f"/api/v3/series/{series_id}")
        except Exception as exc:
            logger.warning("Failed to fetch Sonarr series %d: %s", series_id, exc)
            return None

    def lookup_series(self, title: str) -> dict | None:
        results = self._get("/api/v3/series/lookup", {"term": title})
        if isinstance(results, list) and results:
            return results[0]
        return None

    def add_series(self, title: str, library_cache: dict | None = None) -> bool:
        if library_cache is not None:
            cached = library_cache.get(title.lower())
            if cached and cached.get("id"):
                logger.info("Series already exists in Sonarr (cache): %s", title)
                return False

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

        try:
            tag_id = self.ensure_tag(_TAG_NAME)
            tags = [tag_id]
        except Exception:
            logger.warning("Could not create '%s' tag, adding series without tag: %s", _TAG_NAME, title)
            tags = []

        self._post("/api/v3/series", {
            "title": details.get("title"),
            "tvdbId": tvdb_id,
            "qualityProfileId": self.quality_profile_id,
            "rootFolderPath": self.root_folder,
            "seasonFolder": True,
            "monitored": True,
            "addOptions": {"searchForMissingEpisodes": True},
            "tags": tags,
        })
        logger.info("Added series to Sonarr: %s", title)
        return True
