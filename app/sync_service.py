import logging
import threading

from app.netflix_fetcher import fetch_netflix_top_10_for_countries
from app.radarr_client import RadarrClient
from app.settings import SettingsStore
from app.sonarr_client import SonarrClient
from app.sync_log import SyncLog
from app.tautulli_client import TautulliClient

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, settings: SettingsStore, sync_log: SyncLog) -> None:
        self.settings = settings
        self.sync_log = sync_log
        self.radarr = RadarrClient(settings)
        self.sonarr = SonarrClient(settings)
        self.tautulli = TautulliClient(settings)
        self._lock = threading.Lock()

    def run_once(self) -> dict[str, list[str]]:
        with self._lock:
            return self._run()

    def _run(self) -> dict[str, list[str]]:
        countries = self.settings.get("netflix_top_countries", [])
        if isinstance(countries, str):
            countries = [countries.strip().lower()]

        logger.info("Fetching top titles via Trakt (countries: %s)", countries or ["global"])
        netflix_movies, netflix_series = fetch_netflix_top_10_for_countries(
            countries, self.settings.get("trakt_client_id", "")
        )

        logger.info("Top movies: %s", netflix_movies)
        logger.info("Top series: %s", netflix_series)

        tautulli_mode = self.settings.get("tautulli_mode", "disabled")
        protected_titles: list[str] = (
            list(self.tautulli.fetch_protected_titles()) if tautulli_mode in ("read", "enabled") else []
        )

        added_movies: list[str] = []
        would_add_movies: list[str] = []
        already_in_radarr: list[str] = []
        radarr_mode = self.settings.get("radarr_mode", "disabled")
        radarr_cache: dict = {}
        if radarr_mode != "disabled":
            # Fetch the full library once so per-title existence checks need no network calls.
            radarr_cache = {m["title"].lower(): m for m in self.radarr.get_all_movies()}
            logger.info("Radarr library cache: %d records", len(radarr_cache))

        if radarr_mode == "enabled":
            for title in netflix_movies:
                if self.radarr.add_movie(title, library_cache=radarr_cache):
                    added_movies.append(title)
                    self.sync_log.log_add(title, "movie")
        elif radarr_mode == "read":
            for title in netflix_movies:
                cached = radarr_cache.get(title.lower())
                if cached and cached.get("id"):
                    already_in_radarr.append(title)
                else:
                    would_add_movies.append(title)
            logger.info("Radarr read — would add: %s, already exists: %s", would_add_movies, already_in_radarr)
        else:
            logger.info("Radarr mode is %s, skipping movie import", radarr_mode)

        added_series: list[str] = []
        would_add_series: list[str] = []
        already_in_sonarr: list[str] = []
        sonarr_mode = self.settings.get("sonarr_mode", "disabled")
        sonarr_cache: dict = {}
        if sonarr_mode != "disabled":
            # Fetch the full library once so per-title existence checks need no network calls.
            sonarr_cache = {s["title"].lower(): s for s in self.sonarr.get_all_series()}
            logger.info("Sonarr library cache: %d records", len(sonarr_cache))

        if sonarr_mode == "enabled":
            for title in netflix_series:
                if self.sonarr.add_series(title, library_cache=sonarr_cache):
                    added_series.append(title)
                    self.sync_log.log_add(title, "series")
        elif sonarr_mode == "read":
            for title in netflix_series:
                cached = sonarr_cache.get(title.lower())
                if cached and cached.get("id"):
                    already_in_sonarr.append(title)
                else:
                    would_add_series.append(title)
            logger.info("Sonarr read — would add: %s, already exists: %s", would_add_series, already_in_sonarr)
        else:
            logger.info("Sonarr mode is %s, skipping series import", sonarr_mode)

        if tautulli_mode in ("read", "enabled"):
            logger.info("Tautulli %s — protected media count: %d", tautulli_mode, len(protected_titles))
        else:
            logger.info("Tautulli disabled, skipping protection check")

        result = {
            "added_movies": added_movies,
            "added_series": added_series,
            "would_add_movies": would_add_movies,
            "would_add_series": would_add_series,
            "already_in_radarr": already_in_radarr,
            "already_in_sonarr": already_in_sonarr,
            "protected": sorted(protected_titles),
            "top_movies": netflix_movies,
            "top_series": netflix_series,
        }
        self.sync_log.set_last_sync(result)
        return result
