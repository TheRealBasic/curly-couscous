"""Folder watcher for incoming PDF certificates."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from app.config import AppConfig
from app.database import Database
from app.parser import ParseError, parse_certificate
from app.sorter import move_quarantine, move_sorted
from app.utils import wait_for_stable_file

LOGGER = logging.getLogger(__name__)


class CertificateHandler(FileSystemEventHandler):
    """Watchdog handler for new certificate files."""

    def __init__(self, config: AppConfig, database: Database):
        self.config = config
        self.database = database

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix.lower() != ".pdf":
            return
        self.process_file(path)

    def process_file(self, path: Path) -> None:
        """Parse, persist, and sort a single PDF file."""

        try:
            wait_for_stable_file(path, checks=self.config.stable_checks, interval=self.config.stable_seconds)
            parsed = parse_certificate(path)
            tested = parsed.tested_at
            destination = move_sorted(
                source=path,
                sorted_root=self.config.sorted_folder,
                result=parsed.result,
                tested_path_parts=(tested.strftime("%Y"), tested.strftime("%m"), tested.strftime("%d")),
                serial=parsed.serial,
            )
            self.database.add_test_record(
                serial=parsed.serial,
                device_type=parsed.device_type,
                barcode=None,
                tested_at=parsed.tested_at,
                result=parsed.result,
                file_path=str(destination),
                parse_status="ok",
            )
            LOGGER.info("Processed certificate: %s -> %s", path, destination)
        except (ParseError, Exception) as exc:
            quarantined = move_quarantine(path, self.config.quarantine_folder)
            self.database.add_test_record(
                serial="UNKNOWN",
                device_type=None,
                barcode=None,
                tested_at=datetime.now(timezone.utc),
                result="UNKNOWN",
                file_path=str(quarantined),
                parse_status="parse_error",
                parse_error=str(exc),
            )
            LOGGER.exception("Failed to process %s. Moved to quarantine: %s", path, quarantined)


def start_watcher(config: AppConfig, database: Database) -> Observer:
    """Create and start watchdog observer."""

    config.import_folder.mkdir(parents=True, exist_ok=True)
    observer = Observer()
    handler = CertificateHandler(config, database)
    observer.schedule(handler, str(config.import_folder), recursive=False)
    observer.start()
    LOGGER.info("Watching folder: %s", config.import_folder)
    return observer
