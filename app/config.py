"""Application configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Runtime configuration for the certificate manager."""

    db_path: Path = Field(default=Path(r"C:\GasDock\gasdock.db"))
    import_folder: Path = Field(default=Path(r"C:\GasDock\Imports"))
    sorted_folder: Path = Field(default=Path(r"C:\GasDock\Sorted"))
    quarantine_folder: Path = Field(default=Path(r"C:\GasDock\Quarantine"))
    logs_folder: Path = Field(default=Path(r"C:\GasDock\logs"))
    host: str = "127.0.0.1"
    port: int = 8765
    stable_seconds: float = 2.0
    stable_checks: int = 3


DEFAULT_CONFIG_PATH = Path("config.yaml")


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load config from YAML file if present, else return defaults."""

    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        return AppConfig(**raw)
    return AppConfig()
