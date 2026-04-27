import logging
from threading import Event, Thread

from waitress import serve

from app.manual_overrides import ManualOverrides
from app.settings import SettingsStore
from app.sync_log import SyncLog
from app.sync_service import SyncService
from app.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_worker(stop_event: Event, sync_service: SyncService) -> None:
    while not stop_event.is_set():
        try:
            sync_service.run_once()
        except Exception as exc:
            logger.exception("Sync run failed: %s", exc)

        interval = sync_service.settings.get("run_interval_seconds", 86400)
        logger.info("Waiting %s seconds until next sync", interval)
        if stop_event.wait(interval):
            break


def main() -> None:
    logger.info("Starting Netflix Sync service")

    settings = SettingsStore()
    sync_log = SyncLog()
    manual_overrides = ManualOverrides()
    sync_service = SyncService(settings, sync_log)
    stop_event = Event()

    worker = Thread(target=run_worker, args=(stop_event, sync_service), daemon=True)
    worker.start()

    app = create_app(settings, sync_service, sync_log, manual_overrides)
    port = settings.get("web_port", 8080)
    logger.info("Opening web interface on port %s", port)
    serve(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
