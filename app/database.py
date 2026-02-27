"""Database service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Device, TestRecord


class Database:
    """Wraps SQLite access and common operations."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        self._session_maker = sessionmaker(bind=self.engine, expire_on_commit=False, class_=Session)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        """Yield DB session for dependency usage."""

        with self._session_maker() as session:
            yield session

    def add_test_record(
        self,
        serial: str,
        tested_at: datetime,
        result: str,
        file_path: str,
        device_type: Optional[str] = None,
        parse_status: str = "ok",
        parse_error: Optional[str] = None,
    ) -> TestRecord:
        """Insert test and update device latest snapshot."""

        with self._session_maker() as session:
            test = TestRecord(
                serial=serial,
                device_type=device_type,
                tested_at=tested_at,
                result=result,
                file_path=file_path,
                parse_status=parse_status,
                parse_error=parse_error,
            )
            session.add(test)

            device = session.get(Device, serial)
            if device is None:
                device = Device(serial=serial)
                session.add(device)

            if device.last_tested_at is None or tested_at >= device.last_tested_at:
                device.last_tested_at = tested_at
                device.last_result = result
                device.device_type = device_type or device.device_type
                device.last_updated = datetime.now(timezone.utc)

            session.commit()
            session.refresh(test)
            return test

    def stats(self) -> dict[str, int]:
        """Return dashboard counters."""

        with self._session_maker() as session:
            total_devices = session.scalar(select(func.count(Device.serial))) or 0
            total_tests = session.scalar(select(func.count(TestRecord.id))) or 0
            return {"total_devices": total_devices, "total_tests": total_tests}
