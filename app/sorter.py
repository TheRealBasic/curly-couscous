"""File sorting and quarantine handling."""

from __future__ import annotations

import shutil
from pathlib import Path


def move_sorted(source: Path, sorted_root: Path, result: str, tested_path_parts: tuple[str, str, str], serial: str) -> Path:
    """Move file to structured sorted destination."""

    yyyy, mm, dd = tested_path_parts
    destination = sorted_root / result / yyyy / mm / dd / serial
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / source.name
    shutil.move(str(source), str(target))
    return target


def move_quarantine(source: Path, quarantine_root: Path) -> Path:
    """Move file to quarantine folder on parsing error."""

    quarantine_root.mkdir(parents=True, exist_ok=True)
    target = quarantine_root / source.name
    shutil.move(str(source), str(target))
    return target
