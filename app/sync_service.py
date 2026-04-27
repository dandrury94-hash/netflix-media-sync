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

        protected_titles = self.tautulli.fetch_protected_titles()
        movie_retention_days = int(self.settings.get("movie_retention_days", 30))
        series_retention_days = int(self.settings.get("series_retention_days", 30))

        logger.info("Retention settings: movies=%s days, series=%s days", movie_retention_days, series_retention_days)

        added_movies: list[str] = []
        added_series: list[str] = []
        for title in netflix_movies:
            if self.radarr.add_movie(title):
                added_movies.append(title)

        logger.info("Adding top series to Sonarr")
        for title in netflix_series:
            if self.sonarr.add_series(title):
                added_series.append(title)

        if self.settings.get("delete_old_media"):
            logger.info("DELETE_OLD_MEDIA=true, cleanup evaluation is enabled.")
            logger.info("Protected media count: %d", len(protected_titles))
        else:
            logger.info("DELETE_OLD_MEDIA=false, no removals will be performed.")

        result = {
            "added_movies": added_movies,
            "added_series": added_series,
            "protected": sorted(protected_titles),
            "movie_retention_days": movie_retention_days,
            "series_retention_days": series_retention_days,
        }
        return result
