import logging
import threading

from app.netflix_fetcher import fetch_netflix_top_10_for_countries
from app.radarr_client import RadarrClient
from app.settings import SettingsStore
from app.sonarr_client import SonarrClient
from app.tautulli_client import TautulliClient

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings
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
        protected_titles: list[str] | set[str] = (
            self.tautulli.fetch_protected_titles() if tautulli_mode in ("read", "enabled") else []
        )

        added_movies: list[str] = []
        radarr_mode = self.settings.get("radarr_mode", "disabled")
        if radarr_mode == "enabled":
            for title in netflix_movies:
                if self.radarr.add_movie(title):
                    added_movies.append(title)
        else:
            logger.info("Radarr mode is %s, skipping movie import", radarr_mode)

        added_series: list[str] = []
        sonarr_mode = self.settings.get("sonarr_mode", "disabled")
        if sonarr_mode == "enabled":
            for title in netflix_series:
                if self.sonarr.add_series(title):
                    added_series.append(title)
        else:
            logger.info("Sonarr mode is %s, skipping series import", sonarr_mode)

        if tautulli_mode in ("read", "enabled"):
            logger.info("Tautulli %s — protected media count: %d", tautulli_mode, len(protected_titles))
        else:
            logger.info("Tautulli disabled, skipping protection check")

        return {
            "added_movies": added_movies,
            "added_series": added_series,
            "protected": sorted(protected_titles),
        }
