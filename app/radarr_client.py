import logging

import requests
from app.settings import SettingsStore

logger = logging.getLogger(__name__)

_TAG_NAME = "netflix-sync"


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
            logger.error("Radarr API error %s: %s", response.status_code, response.text)
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

    def get_tagged_movies(self, tag_name: str) -> list[dict]:
        """Return all Radarr movies carrying the named tag."""
        try:
            tags = self._get("/api/v3/tag")
            tag_id = next((t["id"] for t in tags if t.get("label") == tag_name), None)
            if tag_id is None:
                return []
            movies = self._get("/api/v3/movie")
            return [m for m in movies if tag_id in m.get("tags", [])]
        except Exception as exc:
            logger.warning("Failed to fetch tagged movies from Radarr: %s", exc)
            return []

    def get_all_movies(self) -> list[dict]:
        try:
            return self._get("/api/v3/movie")
        except Exception as exc:
            logger.warning("Failed to fetch Radarr library: %s", exc)
            return []

    def get_movie_by_id(self, movie_id: int) -> dict | None:
        try:
            return self._get(f"/api/v3/movie/{movie_id}")
        except Exception as exc:
            logger.warning("Failed to fetch Radarr movie %d: %s", movie_id, exc)
            return None

    def lookup_movie(self, title: str) -> dict | None:
        try:
            results = self._get("/api/v3/movie/lookup", {"term": title})
        except Exception as exc:
            logger.warning("Radarr lookup failed for movie: %s (%s)", title, exc)
            return None
        if isinstance(results, list) and results:
            return results[0]
        return None

    def delete_movie(self, movie_id: int, delete_files: bool = True) -> bool:
        try:
            response = requests.delete(
                f"{self.base_url}/api/v3/movie/{movie_id}",
                params={"deleteFiles": "true" if delete_files else "false"},
                headers=self._headers(),
                timeout=20,
            )
            response.raise_for_status()
            logger.info("Deleted Radarr movie id=%d (deleteFiles=%s)", movie_id, delete_files)
            return True
        except Exception as exc:
            logger.error("Failed to delete Radarr movie id=%d: %s", movie_id, exc)
            return False

    def add_movie(self, title: str, library_cache: dict | None = None) -> bool:
        if library_cache is not None:
            cached = library_cache.get(title.lower())
            if cached and cached.get("id"):
                logger.info("Movie already exists in Radarr (cache): %s", title)
                return False

        details = self.lookup_movie(title)
        if not details:
            logger.warning("Radarr lookup failed for movie: %s", title)
            return False

        if details.get("id"):
            logger.info("Movie already exists in Radarr: %s", title)
            return False

        tmdb_id = details.get("tmdbId")
        if not tmdb_id:
            logger.warning("Unable to add movie without TMDb ID: %s", title)
            return False

        try:
            tag_id = self.ensure_tag(_TAG_NAME)
            tags = [tag_id]
        except Exception:
            logger.warning("Could not create '%s' tag, adding movie without tag: %s", _TAG_NAME, title)
            tags = []

        self._post("/api/v3/movie", {
            "tmdbId": tmdb_id,
            "qualityProfileId": self.quality_profile_id,
            "rootFolderPath": self.root_folder,
            "monitored": True,
            "addOptions": {"searchForMovie": True},
            "tags": tags,
        })
        logger.info("Added movie to Radarr: %s", title)
        return True