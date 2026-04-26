import logging
from threading import Event, Thread

from app.settings import SettingsStore
from app.sync_service import SyncService
from app.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_worker(stop_event: Event, settings: SettingsStore) -> None:
    while not stop_event.is_set():
        try:
            SyncService(settings).run_once()
        except Exception as exc:
            logger.exception("Sync run failed: %s", exc)

        interval = settings.get("run_interval_seconds", 86400)
        logger.info("Waiting %s seconds until next sync", interval)
        if stop_event.wait(interval):
            break


def main() -> None:
    logger.info("Starting Netflix Sync service")

    settings = SettingsStore()
    sync_service = SyncService(settings)
    stop_event = Event()

    worker = Thread(target=run_worker, args=(stop_event, settings), daemon=True)
    worker.start()

    app = create_app(settings, sync_service)
    port = settings.get("web_port", 8080)
    logger.info("Opening web interface on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
