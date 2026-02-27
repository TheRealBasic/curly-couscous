"""Run GasDock certificate manager web app and watcher."""

from __future__ import annotations

import signal
import threading

import uvicorn

from app.api import create_app
from app.config import load_config
from app.database import Database
from app.utils import setup_logging
from app.watcher import start_watcher


def main() -> None:
    """Application entrypoint."""

    config = load_config()
    setup_logging(config.logs_folder / "app.log")

    db = Database(config.db_path)
    db.create_tables()

    observer = start_watcher(config, db)
    app = create_app(config, db)

    stop_event = threading.Event()

    def shutdown_handler(*_: object) -> None:
        if observer.is_alive():
            observer.stop()
            observer.join(timeout=5)
        stop_event.set()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    main()
