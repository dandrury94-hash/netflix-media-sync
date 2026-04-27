import datetime
import logging
from logging.handlers import RotatingFileHandler
from threading import Event, Thread

from waitress import serve

from app.config import LOG_PATH
from app.manual_overrides import ManualOverrides
from app.removal_history import RemovalHistory
from app.settings import SettingsStore
from app.sync_log import SyncLog
from app.sync_service import SyncService
from app.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_file_handler = RotatingFileHandler(
    LOG_PATH,
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
logging.getLogger().addHandler(_file_handler)

logger = logging.getLogger(__name__)


def run_worker(stop_event: Event, sync_service: SyncService) -> None:
    while not stop_event.is_set():
        try:
            sync_service.run_once()
        except Exception as exc:
            logger.exception("Sync run failed: %s", exc)

        # Interval is read after each run so UI changes take effect on the next cycle without restart.
        interval = sync_service.settings.get("run_interval_seconds", 86400)
        logger.info("Waiting %s seconds until next sync", interval)
        if stop_event.wait(interval):
            break


def run_weekly_preview(
    stop_event: Event,
    sync_service: SyncService,
    sync_log: SyncLog,
    manual_overrides: ManualOverrides,
    settings: SettingsStore,
) -> None:
    while not stop_event.is_set():
        now = datetime.datetime.now()
        # Saturday is weekday 5; compute days until next Saturday 05:00
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.hour >= 5:
            days_until_saturday = 7
        next_run = now.replace(hour=5, minute=0, second=0, microsecond=0) + datetime.timedelta(
            days=days_until_saturday
        )
        wait_seconds = (next_run - now).total_seconds()
        if stop_event.wait(wait_seconds):
            break

        if not sync_service.pushover.is_enabled():
            continue

        today = datetime.date.today()
        in_7_days = today + datetime.timedelta(days=7)
        movie_retention = int(settings.get("movie_retention_days", 30))
        series_retention = int(settings.get("series_retention_days", 30))

        last_sync = sync_log.get_last_sync() or {}
        tautulli_protected = set(last_sync.get("protected", []))
        all_protected = tautulli_protected | manual_overrides.to_set()

        upcoming: list[str] = []

        radarr_mode = settings.get("radarr_mode", "disabled")
        if radarr_mode != "disabled":
            for movie in sync_service.radarr.get_tagged_movies("netflix-sync"):
                title = movie.get("title", "")
                if not title or title in all_protected:
                    continue
                date_added_str = sync_log.get_date_added(title)
                date_added = today
                if date_added_str:
                    try:
                        date_added = datetime.date.fromisoformat(date_added_str)
                    except ValueError:
                        pass
                removal_date = date_added + datetime.timedelta(days=movie_retention)
                if today <= removal_date <= in_7_days:
                    upcoming.append(f"🎬 {title} (removes {removal_date})")

        sonarr_mode = settings.get("sonarr_mode", "disabled")
        if sonarr_mode != "disabled":
            for series in sync_service.sonarr.get_tagged_series("netflix-sync"):
                title = series.get("title", "")
                if not title or title in all_protected:
                    continue
                date_added_str = sync_log.get_date_added(title)
                date_added = today
                if date_added_str:
                    try:
                        date_added = datetime.date.fromisoformat(date_added_str)
                    except ValueError:
                        pass
                removal_date = date_added + datetime.timedelta(days=series_retention)
                if today <= removal_date <= in_7_days:
                    upcoming.append(f"📺 {title} (removes {removal_date})")

        if upcoming:
            sync_service.pushover.send(
                "Netflix Sync — Weekly Preview",
                "Titles due for removal in the next 7 days:\n" + "\n".join(upcoming),
            )


def main() -> None:
    logger.info("Starting Netflix Sync service")

    settings = SettingsStore()
    sync_log = SyncLog()
    manual_overrides = ManualOverrides()
    removal_history = RemovalHistory()
    sync_service = SyncService(settings, sync_log, manual_overrides, removal_history)
    stop_event = Event()

    worker = Thread(target=run_worker, args=(stop_event, sync_service), daemon=True)
    worker.start()

    weekly = Thread(
        target=run_weekly_preview,
        args=(stop_event, sync_service, sync_log, manual_overrides, settings),
        daemon=True,
    )
    weekly.start()

    app = create_app(settings, sync_service, sync_log, manual_overrides, removal_history)
    port = settings.get("web_port", 8080)
    logger.info("Opening web interface on port %s", port)
    serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
