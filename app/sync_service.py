import datetime
import logging
import threading
import time

from app import tags as _tags
from app.manual_overrides import ManualOverrides
from app.netflix_fetcher import fetch_from_sources
from app.pushover_client import PushoverClient
from app.radarr_client import RadarrClient
from app.removal_history import RemovalHistory
from app.settings import SettingsStore
from app.sonarr_client import SonarrClient
from app.sync_log import SyncLog
from app.tautulli_client import TautulliClient

logger = logging.getLogger(__name__)


def _resolve_date(
    log_date: str | None,
    api_added: str | None,
    fallback: datetime.date,
) -> datetime.date:
    if log_date:
        try:
            return datetime.date.fromisoformat(log_date)
        except ValueError:
            pass
    if api_added:
        try:
            return datetime.datetime.fromisoformat(
                api_added.replace("Z", "+00:00")
            ).date()
        except ValueError:
            pass
    return fallback


class SyncService:
    def __init__(
        self,
        settings: SettingsStore,
        sync_log: SyncLog,
        manual_overrides: ManualOverrides,
        removal_history: RemovalHistory,
    ) -> None:
        self.settings = settings
        self.sync_log = sync_log
        self.manual_overrides = manual_overrides
        self.removal_history = removal_history
        self.radarr = RadarrClient(settings)
        self.sonarr = SonarrClient(settings)
        self.tautulli = TautulliClient(settings)
        self.pushover = PushoverClient(settings)
        self._lock = threading.Lock()

    def run_once(self) -> dict:
        with self._lock:
            _start = time.monotonic()
            try:
                result = self._run()
            except Exception as exc:
                self.pushover.send(
                    "Streamarr — Error",
                    f"Sync failed: {exc}",
                    priority=1,
                )
                raise
            result["duration_seconds"] = int(time.monotonic() - _start)
            self.sync_log.set_last_sync(result)
            _t = time.monotonic()
            self.run_deletions()
            logger.info("[timing] deletion_run: %.1fs", time.monotonic() - _t)
            return result

    def _run(self) -> dict:
        countries = self.settings.get("netflix_top_countries", [])
        if isinstance(countries, str):
            countries = [countries.strip().lower()]

        sources = self.settings.get("sources", ["trakt"])
        if isinstance(sources, str):
            sources = [sources]

        flixpatrol_country = self.settings.get("flixpatrol_country", "United Kingdom")
        flixpatrol_services = self.settings.get("flixpatrol_services", [])
        if isinstance(flixpatrol_services, str):
            flixpatrol_services = [s.strip() for s in flixpatrol_services.split(",") if s.strip()]
        flixpatrol_service_types = self.settings.get("flixpatrol_service_types", {})
        if not isinstance(flixpatrol_service_types, dict):
            flixpatrol_service_types = {}
        flixpatrol_cache_hours = int(self.settings.get("flixpatrol_cache_hours", 6))

        logger.info("Fetching top titles from sources: %s (countries: %s)", sources, countries or ["global"])
        _t = time.monotonic()
        trending = fetch_from_sources(
            sources,
            countries,
            self.settings.get("trakt_client_id", ""),
            flixpatrol_country=flixpatrol_country,
            flixpatrol_services=flixpatrol_services,
            flixpatrol_service_types=flixpatrol_service_types,
            flixpatrol_cache_hours=flixpatrol_cache_hours,
        )
        logger.info("[timing] source_fetch: %.1fs", time.monotonic() - _t)

        movie_items = [i for i in trending if i["type"] == "movie"]
        series_items = [i for i in trending if i["type"] == "series"]
        netflix_movies = [i["title"] for i in movie_items]
        netflix_series = [i["title"] for i in series_items]

        top_by_source: dict[str, dict] = {}
        for item in trending:
            src = item["source"]
            if src not in top_by_source:
                top_by_source[src] = {"movie": [], "series": []}
            top_by_source[src][item["type"]].append(item["title"])

        logger.info("Top movies: %s", netflix_movies)
        logger.info("Top series: %s", netflix_series)

        tautulli_mode = self.settings.get("tautulli_mode", "disabled")
        protected_titles: list[str] = []
        if tautulli_mode in ("read", "enabled"):
            _t = time.monotonic()
            protected_titles = list(self.tautulli.fetch_protected_titles())
            logger.info("[timing] tautulli_fetch: %.1fs", time.monotonic() - _t)

        added_movies: list[str] = []
        would_add_movies: list[str] = []
        already_in_radarr: list[str] = []
        radarr_mode = self.settings.get("radarr_mode", "disabled")
        radarr_cache: dict = {}
        if radarr_mode != "disabled":
            _t = time.monotonic()
            radarr_cache = {m["title"].lower(): m for m in self.radarr.get_all_movies()}
            logger.info("[timing] radarr_bulk_fetch: %.1fs (%d records)", time.monotonic() - _t, len(radarr_cache))

        if radarr_mode == "enabled":
            _t = time.monotonic()
            for item in movie_items:
                if self.radarr.add_movie(item["title"], library_cache=radarr_cache, tags=_tags.all_tags_for(item["source"], "movie")):
                    added_movies.append(item["title"])
                    self.sync_log.log_add(item["title"], "movie")
            logger.info("[timing] radarr_add_loop: %.1fs", time.monotonic() - _t)
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
            _t = time.monotonic()
            sonarr_cache = {s["title"].lower(): s for s in self.sonarr.get_all_series()}
            logger.info("[timing] sonarr_bulk_fetch: %.1fs (%d records)", time.monotonic() - _t, len(sonarr_cache))

        if sonarr_mode == "enabled":
            _t = time.monotonic()
            for item in series_items:
                if self.sonarr.add_series(item["title"], library_cache=sonarr_cache, tags=_tags.all_tags_for(item["source"], "series")):
                    added_series.append(item["title"])
                    self.sync_log.log_add(item["title"], "series")
            logger.info("[timing] sonarr_add_loop: %.1fs", time.monotonic() - _t)
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
            "top_by_source": top_by_source,
        }
        if added_movies or added_series:
            lines = [f"🎬 {t}" for t in added_movies] + [f"📺 {t}" for t in added_series]
            self.pushover.send("Streamarr — Added", "\n".join(lines))

        return result

    def run_deletions(self) -> dict:
        if not self.settings.get("deletion_enabled", False):
            return {"deleted_movies": [], "deleted_series": [], "grace_started": []}

        grace_period_days = int(self.settings.get("grace_period_days", 7))
        movie_retention = int(self.settings.get("movie_retention_days", 30))
        series_retention = int(self.settings.get("series_retention_days", 30))

        last_sync = self.sync_log.get_last_sync() or {}
        tautulli_protected = set(last_sync.get("protected", []))
        all_protected = tautulli_protected | self.manual_overrides.to_set()

        today = datetime.date.today()
        deleted_movies: list[str] = []
        deleted_series: list[str] = []
        grace_started: list[str] = []

        radarr_mode = self.settings.get("radarr_mode", "disabled")
        if radarr_mode != "disabled":
            for movie in self.radarr.get_tagged_movies():
                title = movie.get("title", "")
                movie_id = movie.get("id")
                if not title or not movie_id or title in all_protected:
                    continue

                date_added = _resolve_date(
                    self.sync_log.get_date_added(title), movie.get("added"), today
                )
                removal_date = date_added + datetime.timedelta(days=movie_retention)
                if today < removal_date:
                    continue

                self.sync_log.start_grace_period(title, "movie")
                grace_info = self.sync_log.get_grace_periods().get(title, {})
                try:
                    grace_start = datetime.date.fromisoformat(grace_info["started"])
                except (KeyError, ValueError):
                    grace_started.append(title)
                    continue

                grace_expires = grace_start + datetime.timedelta(days=grace_period_days)
                if today < grace_expires:
                    grace_started.append(title)
                    continue

                was_watched = title in tautulli_protected
                if self.radarr.delete_movie(movie_id):
                    deleted_movies.append(title)
                    self.removal_history.log_removal(title, "movie", reason="retention", was_watched=was_watched)
                    self.sync_log.clear_grace_period(title)
                    self.pushover.send("Streamarr — Deleted", f"🎬 {title}")

        sonarr_mode = self.settings.get("sonarr_mode", "disabled")
        if sonarr_mode != "disabled":
            for series in self.sonarr.get_tagged_series():
                title = series.get("title", "")
                series_id = series.get("id")
                if not title or not series_id or title in all_protected:
                    continue

                date_added = _resolve_date(
                    self.sync_log.get_date_added(title), series.get("added"), today
                )
                removal_date = date_added + datetime.timedelta(days=series_retention)
                if today < removal_date:
                    continue

                self.sync_log.start_grace_period(title, "series")
                grace_info = self.sync_log.get_grace_periods().get(title, {})
                try:
                    grace_start = datetime.date.fromisoformat(grace_info["started"])
                except (KeyError, ValueError):
                    grace_started.append(title)
                    continue

                grace_expires = grace_start + datetime.timedelta(days=grace_period_days)
                if today < grace_expires:
                    grace_started.append(title)
                    continue

                was_watched = title in tautulli_protected
                if self.sonarr.delete_series(series_id):
                    deleted_series.append(title)
                    self.removal_history.log_removal(title, "series", reason="retention", was_watched=was_watched)
                    self.sync_log.clear_grace_period(title)
                    self.pushover.send("Streamarr — Deleted", f"📺 {title}")

        if deleted_movies or deleted_series:
            logger.info(
                "Deletions complete — movies: %s, series: %s",
                deleted_movies,
                deleted_series,
            )

        return {
            "deleted_movies": deleted_movies,
            "deleted_series": deleted_series,
            "grace_started": grace_started,
        }
