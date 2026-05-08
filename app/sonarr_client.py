import logging
import time

import requests
from app import tags as _tags
from app.settings import SettingsStore

logger = logging.getLogger(__name__)

_TAG_CACHE_TTL = 30.0  # seconds


class SonarrClient:
    def __init__(self, settings: SettingsStore):
        self.settings = settings
        self._session = requests.Session()
        self._tag_cache: list | None = None
        self._tag_cache_ts: float = 0.0

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
        response = self._session.get(
            f"{self.base_url}{path}",
            params=params or {},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, json_data: dict):
        response = self._session.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json_data,
            timeout=20,
        )
        if not response.ok:
            logger.error("Sonarr API error %s: %s", response.status_code, response.text)
        response.raise_for_status()
        return response.json()

    def _put(self, path: str, json_data: dict):
        response = self._session.put(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json_data,
            timeout=20,
        )
        if not response.ok:
            logger.error("Sonarr PUT error %s: %s", response.status_code, response.text)
        response.raise_for_status()
        return response.json()

    def _delete(self, path: str, params: dict | None = None):
        response = self._session.delete(
            f"{self.base_url}{path}",
            params=params or {},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response

    # ── Tag list cache ──────────────────────────────────────────────────────

    def _get_tag_list(self) -> list:
        now = time.monotonic()
        if self._tag_cache is not None and (now - self._tag_cache_ts) < _TAG_CACHE_TTL:
            return self._tag_cache
        self._tag_cache = self._get("/api/v3/tag")
        self._tag_cache_ts = now
        return self._tag_cache

    def _bust_tag_cache(self) -> None:
        self._tag_cache = None

    # ── Tag helpers ─────────────────────────────────────────────────────────

    def _resolve_tag_ids(self, tag_names: list[str], title: str) -> list[int]:
        ids = []
        for name in tag_names:
            try:
                ids.append(self.ensure_tag(name))
            except Exception:
                logger.warning("Could not create '%s' tag for: %s", name, title)
        return ids

    def ensure_tag(self, name: str) -> int:
        """Return the ID of an existing tag, creating it first if needed."""
        for tag in self._get_tag_list():
            if tag.get("label") == name:
                return tag["id"]
        result = self._post("/api/v3/tag", {"label": name})
        self._bust_tag_cache()
        return result["id"]

    def get_source_tag_map(self) -> dict[int, str]:
        """Return {tag_id: source_key} for all streamarr-src-* tags in Sonarr."""
        try:
            prefix = _tags.TAG_SRC_PREFIX
            return {
                t["id"]: t["label"][len(prefix):].replace("-", "_")
                for t in self._get_tag_list()
                if t.get("id") is not None and t.get("label", "").startswith(prefix)
            }
        except Exception as exc:
            logger.warning("Failed to fetch Sonarr source tag map: %s", exc)
            return {}

    def get_source_tagged_series(self) -> list[dict]:
        """Return all Sonarr series carrying any streamarr-src-* tag (managed or not)."""
        try:
            src_tag_ids = {
                t["id"] for t in self._get_tag_list()
                if t.get("id") is not None and t.get("label", "").startswith(_tags.TAG_SRC_PREFIX)
            }
            if not src_tag_ids:
                return []
            series = self._get("/api/v3/series")
            return [s for s in series if src_tag_ids & set(s.get("tags", []))]
        except Exception as exc:
            logger.warning("Failed to fetch source-tagged series from Sonarr: %s", exc)
            return []

    def merge_series_tags(self, series_id: int, new_tag_names: list[str]) -> None:
        """Add any new_tag_names not already on the series, leaving existing tags intact."""
        try:
            series = self._get(f"/api/v3/series/{series_id}")
            current_ids = set(series.get("tags", []))
            to_add = set(self._resolve_tag_ids(new_tag_names, str(series_id))) - current_ids
            if not to_add:
                return
            series["tags"] = list(current_ids | to_add)
            self._put(f"/api/v3/series/{series_id}", series)
        except Exception as exc:
            logger.warning("Failed to merge tags for Sonarr series id=%d: %s", series_id, exc)

    def get_tagged_series(self) -> list[dict]:
        """Return all Sonarr series carrying the streamarr root tag."""
        try:
            tag_id = next((t["id"] for t in self._get_tag_list() if t.get("label") == _tags.TAG_ROOT), None)
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

    def get_state_protected_tag_id(self) -> int | None:
        try:
            return next((t["id"] for t in self._get_tag_list() if t.get("label") == _tags.TAG_STATE_PROTECTED), None)
        except Exception as exc:
            logger.warning("Failed to fetch state-protected tag id from Sonarr: %s", exc)
            return None

    def set_series_protection(self, series_id: int, protected: bool) -> bool:
        try:
            tag_id = self.ensure_tag(_tags.TAG_STATE_PROTECTED)
            series = self._get(f"/api/v3/series/{series_id}")
            current_tags = series.get("tags", [])
            if protected:
                if tag_id not in current_tags:
                    current_tags = [*current_tags, tag_id]
            else:
                current_tags = [t for t in current_tags if t != tag_id]
            series["tags"] = current_tags
            self._put(f"/api/v3/series/{series_id}", series)
            logger.info("Set protection=%s for series id=%d", protected, series_id)
            return True
        except Exception as exc:
            logger.error("Failed to set protection for series id=%d: %s", series_id, exc)
            return False

    def lookup_series(self, title: str) -> dict | None:
        try:
            results = self._get("/api/v3/series/lookup", {"term": title})
        except Exception as exc:
            logger.warning("Sonarr lookup failed for series: %s (%s)", title, exc)
            return None
        if isinstance(results, list) and results:
            return results[0]
        return None

    def delete_series(self, series_id: int, delete_files: bool = True) -> bool:
        try:
            self._delete(
                f"/api/v3/series/{series_id}",
                params={"deleteFiles": "true" if delete_files else "false"},
            )
            logger.info("Deleted Sonarr series id=%d (deleteFiles=%s)", series_id, delete_files)
            return True
        except Exception as exc:
            logger.error("Failed to delete Sonarr series id=%d: %s", series_id, exc)
            return False

    def add_series(self, title: str, library_cache: dict | None = None, tags: list[str] | None = None) -> bool:
        tag_names = tags if tags is not None else [_tags.TAG_ROOT]

        if library_cache is not None:
            cached = library_cache.get(title.lower())
            if cached and cached.get("id"):
                return False

        details = self.lookup_series(title)
        if not details:
            logger.warning("Sonarr lookup failed for series: %s", title)
            return False

        if details.get("id"):
            return False

        tvdb_id = details.get("tvdbId")
        if not tvdb_id:
            logger.warning("Unable to add series without TVDB ID: %s", title)
            return False

        tag_ids = self._resolve_tag_ids(tag_names, title)
        self._post("/api/v3/series", {
            "title": details.get("title"),
            "tvdbId": tvdb_id,
            "qualityProfileId": self.quality_profile_id,
            "rootFolderPath": self.root_folder,
            "seasonFolder": True,
            "monitored": True,
            "addOptions": {"searchForMissingEpisodes": True},
            "tags": tag_ids,
        })
        logger.info("Added series to Sonarr: %s", title)
        return True
