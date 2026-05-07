import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# FlixPatrol service key → Plex collection display name (excludes trakt)
SERVICE_COLLECTION_NAMES: dict[str, str] = {
    "netflix":       "Netflix",
    "disney_plus":   "Disney+",
    "amazon_prime":  "Amazon Prime",
    "amazon":        "Amazon",
    "apple_tv":      "Apple TV+",
    "apple_tv_store": "Apple TV",
    "paramount_plus": "Paramount+",
    "google":        "Google Play",
    "rakuten_tv":    "Rakuten TV",
    "now":           "NOW",
    "hayu":          "Hayu",
    "chili":         "Chili",
}

MAIN_COLLECTION_NAME = "Streamarr"

_last_sync: dict = {
    "synced_at": None,
    "movie_count": 0,
    "tv_count": 0,
    "added": 0,
    "removed": 0,
    "error": None,
}


def get_plex_sync_status() -> dict:
    return dict(_last_sync)


class PlexError(Exception):
    pass


class PlexClient:
    def __init__(self, url: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._token = token

    def _request(self, method: str, path: str, params: dict | None = None) -> ET.Element | None:
        qs = urllib.parse.urlencode({"X-Plex-Token": self._token, **(params or {})})
        full_url = f"{self._url}{path}?{qs}"
        has_body = method in ("POST", "PUT")
        req = urllib.request.Request(full_url, data=b"" if has_body else None, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                return ET.fromstring(body) if body else None
        except urllib.error.HTTPError as e:
            raise PlexError(f"HTTP {e.code} from Plex at {path}") from e
        except urllib.error.URLError as e:
            raise PlexError(f"Cannot reach Plex: {e.reason}") from e
        except ET.ParseError as e:
            raise PlexError(f"Invalid XML from Plex at {path}: {e}") from e

    def _get(self, path: str, params: dict | None = None) -> ET.Element:
        result = self._request("GET", path, params)
        if result is None:
            raise PlexError(f"Empty response from Plex at {path}")
        return result

    def _put(self, path: str, params: dict | None = None) -> None:
        self._request("PUT", path, params)

    def _delete(self, path: str, params: dict | None = None) -> None:
        self._request("DELETE", path, params)

    def _post(self, path: str, params: dict | None = None) -> ET.Element:
        result = self._request("POST", path, params)
        if result is None:
            raise PlexError(f"Empty response from Plex at {path}")
        return result

    def test_connection(self) -> tuple[bool, str]:
        try:
            root = self._get("/")
            name = root.get("friendlyName") or root.get("machineIdentifier", "Plex")
            return True, f"Connected to {name}"
        except PlexError as e:
            return False, str(e)

    def get_machine_id(self) -> str:
        root = self._get("/")
        mid = root.get("machineIdentifier")
        if not mid:
            raise PlexError("Could not retrieve Plex machine identifier")
        return mid

    def get_library_section_id(self, library_name: str) -> str | None:
        root = self._get("/library/sections")
        for directory in root.findall("Directory"):
            if directory.get("title") == library_name:
                return directory.get("key")
        return None

    def get_library_items(self, section_id: str) -> tuple[dict[str, str], dict[str, str]]:
        """Return (tmdb_map, tvdb_map) where maps are {external_id_str: ratingKey}."""
        root = self._get(f"/library/sections/{section_id}/all", {"includeGuids": "1"})
        tmdb_map: dict[str, str] = {}
        tvdb_map: dict[str, str] = {}
        for item in root:
            rk = item.get("ratingKey")
            if not rk:
                continue
            for guid in item.findall("Guid"):
                gid = guid.get("id", "")
                if gid.startswith("tmdb://"):
                    tmdb_map[gid[7:]] = rk
                elif gid.startswith("tvdb://"):
                    tvdb_map[gid[7:]] = rk
        return tmdb_map, tvdb_map

    def get_collections(self, section_id: str) -> dict[str, str]:
        """Return {title: ratingKey} for all collections in a section."""
        try:
            root = self._get(f"/library/sections/{section_id}/collections")
            return {
                d.get("title"): d.get("ratingKey")
                for d in root.findall("Directory")
                if d.get("title") and d.get("ratingKey")
            }
        except PlexError:
            return {}

    def _create_collection(self, section_id: str, title: str, library_type: int) -> str:
        root = self._post("/library/collections", {
            "type": str(library_type),
            "title": title,
            "smart": "0",
            "sectionId": section_id,
        })
        directory = root.find("Directory")
        if directory is None:
            raise PlexError(f"Failed to create collection '{title}': no Directory in response")
        rk = directory.get("ratingKey")
        if not rk:
            raise PlexError(f"Created collection '{title}' but got no ratingKey")
        logger.info("Plex: created collection '%s' (key=%s) in section %s", title, rk, section_id)
        return rk

    def _ensure_collection(
        self, section_id: str, title: str, library_type: int, existing: dict[str, str]
    ) -> str:
        if title in existing:
            return existing[title]
        rk = self._create_collection(section_id, title, library_type)
        existing[title] = rk
        return rk

    def get_collection_items(self, collection_key: str) -> set[str]:
        try:
            root = self._get(f"/library/collections/{collection_key}/children")
            return {item.get("ratingKey") for item in root if item.get("ratingKey")}
        except PlexError:
            return set()

    def _add_to_collection(self, collection_key: str, item_keys: list[str], machine_id: str) -> None:
        # Batch in groups of 50 to avoid excessively long URIs
        for i in range(0, len(item_keys), 50):
            batch = item_keys[i:i + 50]
            uri = (
                f"server://{machine_id}/com.plexapp.plugins.library"
                f"/library/metadata/{','.join(batch)}"
            )
            self._put(f"/library/collections/{collection_key}/items", {"uri": uri})

    def _remove_from_collection(self, collection_key: str, item_key: str) -> None:
        self._delete(f"/library/collections/{collection_key}/items/{item_key}")

    def sync_collection(
        self,
        section_id: str,
        title: str,
        library_type: int,
        expected_keys: set[str],
        machine_id: str,
        existing_collections: dict[str, str],
    ) -> tuple[int, int]:
        """Ensure a named collection has exactly the expected items. Returns (added, removed)."""
        if not expected_keys:
            return 0, 0
        coll_key = self._ensure_collection(section_id, title, library_type, existing_collections)
        current_keys = self.get_collection_items(coll_key)
        to_add = list(expected_keys - current_keys)
        to_remove = list(current_keys - expected_keys)
        if to_add:
            self._add_to_collection(coll_key, to_add, machine_id)
        for k in to_remove:
            self._remove_from_collection(coll_key, k)
        if to_add or to_remove:
            logger.info(
                "Plex: '%s' — +%d / -%d items", title, len(to_add), len(to_remove)
            )
        return len(to_add), len(to_remove)


def sync_plex_collections(
    plex: PlexClient,
    tagged_movies: list[dict],
    tagged_series: list[dict],
    sync_entries: list[dict],
    movie_library: str,
    tv_library: str,
) -> dict:
    """Sync Plex collections for all Streamarr-managed items.

    Creates/updates:
    - One main 'Streamarr' collection per library
    - One per-service collection per library for each non-trakt source

    Returns summary dict with counts.
    """
    global _last_sync

    try:
        movie_section_id = plex.get_library_section_id(movie_library)
        tv_section_id = plex.get_library_section_id(tv_library)

        if not movie_section_id and not tv_section_id:
            raise PlexError(
                f"Neither '{movie_library}' nor '{tv_library}' found in Plex — "
                "check library names in settings"
            )

        machine_id = plex.get_machine_id()

        movie_tmdb_map: dict[str, str] = {}
        movie_tvdb_map: dict[str, str] = {}
        if movie_section_id:
            movie_tmdb_map, movie_tvdb_map = plex.get_library_items(movie_section_id)

        tv_tmdb_map: dict[str, str] = {}
        tv_tvdb_map: dict[str, str] = {}
        if tv_section_id:
            tv_tmdb_map, tv_tvdb_map = plex.get_library_items(tv_section_id)

        # Build source attribution: title_lower → set of non-trakt sources
        title_sources: dict[str, set[str]] = {}
        for entry in sync_entries:
            tl = entry.get("title", "").lower()
            for src in (entry.get("sources") or []):
                if src != "trakt":
                    title_sources.setdefault(tl, set()).add(src)

        # Resolve movies to Plex ratingKeys
        all_movie_keys: set[str] = set()
        source_movie_keys: dict[str, set[str]] = {}
        for movie in tagged_movies:
            rk = movie_tmdb_map.get(str(movie.get("tmdbId", "")))
            if not rk:
                continue
            all_movie_keys.add(rk)
            for src in title_sources.get(movie.get("title", "").lower(), set()):
                source_movie_keys.setdefault(src, set()).add(rk)

        # Resolve series to Plex ratingKeys (try TMDB first, then TVDB)
        all_tv_keys: set[str] = set()
        source_tv_keys: dict[str, set[str]] = {}
        for series in tagged_series:
            rk = tv_tmdb_map.get(str(series.get("tmdbId", ""))) or \
                 tv_tvdb_map.get(str(series.get("tvdbId", "")))
            if not rk:
                continue
            all_tv_keys.add(rk)
            for src in title_sources.get(series.get("title", "").lower(), set()):
                source_tv_keys.setdefault(src, set()).add(rk)

        total_added = 0
        total_removed = 0

        existing_movie_colls: dict[str, str] = {}
        existing_tv_colls: dict[str, str] = {}

        if movie_section_id:
            existing_movie_colls = plex.get_collections(movie_section_id)
            added, removed = plex.sync_collection(
                movie_section_id, MAIN_COLLECTION_NAME, 1,
                all_movie_keys, machine_id, existing_movie_colls,
            )
            total_added += added
            total_removed += removed

        if tv_section_id:
            existing_tv_colls = plex.get_collections(tv_section_id)
            added, removed = plex.sync_collection(
                tv_section_id, MAIN_COLLECTION_NAME, 2,
                all_tv_keys, machine_id, existing_tv_colls,
            )
            total_added += added
            total_removed += removed

        all_services = set(source_movie_keys) | set(source_tv_keys)
        for service_key in sorted(all_services):
            display_name = SERVICE_COLLECTION_NAMES.get(
                service_key, service_key.replace("_", " ").title()
            )
            if movie_section_id and service_key in source_movie_keys:
                added, removed = plex.sync_collection(
                    movie_section_id, display_name, 1,
                    source_movie_keys[service_key], machine_id, existing_movie_colls,
                )
                total_added += added
                total_removed += removed
            if tv_section_id and service_key in source_tv_keys:
                added, removed = plex.sync_collection(
                    tv_section_id, display_name, 2,
                    source_tv_keys[service_key], machine_id, existing_tv_colls,
                )
                total_added += added
                total_removed += removed

        logger.info(
            "Plex collection sync complete — %d movies, %d TV, +%d/-%d items",
            len(all_movie_keys), len(all_tv_keys), total_added, total_removed,
        )

        result = {
            "synced_at": time.time(),
            "movie_count": len(all_movie_keys),
            "tv_count": len(all_tv_keys),
            "added": total_added,
            "removed": total_removed,
            "error": None,
        }
        _last_sync.update(result)
        return result

    except Exception as exc:
        logger.error("Plex collection sync failed: %s", exc)
        _last_sync["error"] = str(exc)
        raise
