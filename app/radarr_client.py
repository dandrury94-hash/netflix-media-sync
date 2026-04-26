import logging

import requests
from app.settings import SettingsStore

logger = logging.getLogger(__name__)


class RadarrClient:
    def __init__(self, settings: SettingsStore):
        self.settings = settings

    @property
    def base_url(self) -> str:
        return self.settings.get("radarr_url", "").rstrip("/")

    @property
    def api_key(self) -> str:
        return self.settings.get("radarr_api_key", "")

    @property
    def quality_profile_id(self) -> int:
        return int(self.settings.get("radarr_quality_profile_id", 1))

    @property
    def root_folder(self) -> str:
        return self.settings.get("root_folder_movies", "")

    def _get(self, path: str, params: dict | None = None):
        response = requests.get(
            f"{self.base_url}{path}",
            params={**(params or {}), "apikey": self.api_key},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json_data: dict):
        response = requests.post(
            f"{self.base_url}{path}",
            params={"apikey": self.api_key},
            json=json_data,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _movie_exists(self, title: str) -> bool:
        movies = self._get("/api/v3/movie")
        return any(movie.get("title", "").strip().lower() == title.strip().lower() for movie in movies)

    def lookup_movie(self, title: str) -> dict | None:
        results = self._get("/api/v3/movie/lookup", {"term": title})
        if isinstance(results, list) and results:
            return results[0]
        return None

    def add_movie(self, title: str) -> bool:
        if self._movie_exists(title):
            logger.info("Movie already exists in Radarr: %s", title)
            return False

        details = self.lookup_movie(title)
        if not details:
            logger.warning("Radarr lookup failed for movie: %s", title)
            return False

        payload = {
            "tmdbId": details.get("tmdbId"),
            "qualityProfileId": self.quality_profile_id,
            "rootFolderPath": self.root_folder,
            "monitored": True,
            "addOptions": {"searchForMovie": True},
        }
        if not payload["tmdbId"]:
            logger.warning("Unable to add movie without TMDb ID: %s", title)
            return False

        self._post("/api/v3/movie", payload)
        logger.info("Added movie to Radarr: %s", title)
        return True
