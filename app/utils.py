"""Utility helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path


def setup_logging(log_file: Path) -> None:
    """Configure app logging to file and console."""

    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def wait_for_stable_file(path: Path, checks: int = 3, interval: float = 1.0) -> None:
    """Wait until file size remains stable for N checks."""

    stable_count = 0
    last_size = -1
    while stable_count < checks:
        size = path.stat().st_size
        if size == last_size and size > 0:
            stable_count += 1
        else:
            stable_count = 0
            last_size = size
        time.sleep(interval)


def normalize_barcode(value: str) -> str:
    """Normalize barcode user input."""

    return " ".join(value.strip().upper().split())


def classify_organization(barcode: str | None) -> str | None:
    """Classify barcode by customer organization."""

    if not barcode:
        return None

    normalized = normalize_barcode(barcode)
    compact = normalized.replace(" ", "")

    if normalized.startswith("AR "):
        return "AMBIPAR"

    if compact.startswith(("MCA", "011", "012", "013")):
        return "MCA"

    return "OTHER"
