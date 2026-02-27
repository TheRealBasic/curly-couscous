"""Database models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class TestRecord(Base):
    """Single imported calibration certificate test result."""

    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    serial: Mapped[str] = mapped_column(String(64), index=True)
    barcode: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tested_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    result: Mapped[str] = mapped_column(String(16), index=True)
    file_path: Mapped[str] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    parse_status: Mapped[str] = mapped_column(String(16), default="ok")
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Device(Base):
    """Latest known status per device serial."""

    __tablename__ = "devices"

    serial: Mapped[str] = mapped_column(String(64), primary_key=True)
    device_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_result: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


Index("ix_devices_last_result", Device.last_result)
Index("ix_devices_last_tested_at", Device.last_tested_at)
