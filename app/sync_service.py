import logging
from app.netflix_fetcher import fetch_netflix_top_10_for_countries, fetch_netflix_top_10
from app.radarr_client import RadarrClient
from app.sonarr_client import SonarrClient
from app.tautulli_client import TautulliClient
from app.settings import SettingsStore

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings
        self.radarr = RadarrClient(settings)
        self.sonarr = SonarrClient(settings)
        self.tautulli = TautulliClient(settings)

    def run_once(self) -> dict[str, list[str]]:
        countries = self.settings.get("netflix_top_countries", [])
        if isinstance(countries, str):
            countries = [countries.strip().lower()]

        if countries:
            netflix_movies, netflix_series = fetch_netflix_top_10_for_countries(countries)
            logger.info("Fetching Netflix top titles for countries: %s", countries)
        else:
            netflix_movies, netflix_series = fetch_netflix_top_10(self.settings.get("netflix_top_url"))
            logger.info("Fetching Netflix top titles from URL: %s", self.settings.get("netflix_top_url"))

        logger.info("Netflix top movies: %s", netflix_movies)
        logger.info("Netflix top series: %s", netflix_series)

        tautulli_mode = self.settings.get("tautulli_mode", "disabled")
        protected_titles = self.tautulli.fetch_protected_titles() if tautulli_mode in ("read", "enabled") else []
        movie_retention_days = int(self.settings.get("movie_retention_days", 30))
        series_retention_days = int(self.settings.get("series_retention_days", 30))

        logger.info("Retention settings: movies=%s days, series=%s days", movie_retention_days, series_retention_days)

        added_movies: list[str] = []
        added_series: list[str] = []
        radarr_mode = self.settings.get("radarr_mode", "disabled")
        if radarr_mode == "enabled":
            for title in netflix_movies:
                if self.radarr.add_movie(title):
                    added_movies.append(title)
        else:
            logger.info("Radarr mode is %s, skipping movie import", radarr_mode)

        logger.info("Adding top series to Sonarr")
        sonarr_mode = self.settings.get("sonarr_mode", "disabled")
        if sonarr_mode == "enabled":
            for title in netflix_series:
                if self.sonarr.add_series(title):
                    added_series.append(title)
        else:
            logger.info("Sonarr mode is %s, skipping series import", sonarr_mode)

        if tautulli_mode == "enabled":
            logger.info("Tautulli enabled, cleanup evaluation active. Protected media count: %d", len(protected_titles))
        elif tautulli_mode == "read":
            logger.info("Tautulli read-only, protected media count: %d", len(protected_titles))
        else:
            logger.info("Tautulli disabled, no protection or cleanup evaluated.")

        result = {
            "added_movies": added_movies,
            "added_series": added_series,
            "protected": sorted(protected_titles),
            "movie_retention_days": movie_retention_days,
            "series_retention_days": series_retention_days,
        }
        return result
