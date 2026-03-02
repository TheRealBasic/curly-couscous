"""Database service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from app.utils import classify_organization

from sqlalchemy import create_engine, func, select, text
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
        self._ensure_tests_barcode_column()
        self._ensure_tests_fail_reason_column()
        self._ensure_devices_barcode_column()
        self._ensure_devices_organization_column()

    def _ensure_tests_barcode_column(self) -> None:
        """Add barcode column for older databases created before this field existed."""

        with self.engine.begin() as connection:
            columns = connection.execute(text("PRAGMA table_info(tests)")).fetchall()
            if any(column[1] == "barcode" for column in columns):
                return
            connection.execute(text("ALTER TABLE tests ADD COLUMN barcode VARCHAR(128)"))


    def _ensure_tests_fail_reason_column(self) -> None:
        """Add fail_reason column for older databases created before this field existed."""

        with self.engine.begin() as connection:
            columns = connection.execute(text("PRAGMA table_info(tests)")).fetchall()
            if any(column[1] == "fail_reason" for column in columns):
                return
            connection.execute(text("ALTER TABLE tests ADD COLUMN fail_reason TEXT"))

    def _ensure_devices_barcode_column(self) -> None:
        """Add barcode column to devices table for older databases."""

        with self.engine.begin() as connection:
            columns = connection.execute(text("PRAGMA table_info(devices)")).fetchall()
            if any(column[1] == "barcode" for column in columns):
                return
            connection.execute(text("ALTER TABLE devices ADD COLUMN barcode VARCHAR(128)"))

    def _ensure_devices_organization_column(self) -> None:
        """Add organization column to devices table for older databases."""

        with self.engine.begin() as connection:
            columns = connection.execute(text("PRAGMA table_info(devices)")).fetchall()
            if any(column[1] == "organization" for column in columns):
                return
            connection.execute(text("ALTER TABLE devices ADD COLUMN organization VARCHAR(32)"))

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
        barcode: Optional[str] = None,
        parse_status: str = "ok",
        parse_error: Optional[str] = None,
        fail_reason: Optional[str] = None,
    ) -> TestRecord:
        """Insert test and update device latest snapshot."""

        with self._session_maker() as session:
            test = TestRecord(
                serial=serial,
                device_type=device_type,
                barcode=barcode,
                tested_at=tested_at,
                result=result,
                file_path=file_path,
                parse_status=parse_status,
                parse_error=parse_error,
                fail_reason=fail_reason,
            )
            session.add(test)

            device = session.get(Device, serial)
            if device is None:
                device = Device(serial=serial)
                session.add(device)

            if barcode:
                device.barcode = barcode
                device.organization = classify_organization(barcode)

            if device.last_tested_at is None or tested_at >= device.last_tested_at:
                device.last_tested_at = tested_at
                device.last_result = result
                device.device_type = device_type or device.device_type
                device.last_updated = datetime.now(timezone.utc)

            session.commit()
            session.refresh(test)
            return test

    def delete_test_record(self, test_id: int) -> bool:
        """Delete a single test record by id and refresh device snapshot."""

        with self._session_maker() as session:
            test = session.get(TestRecord, test_id)
            if test is None:
                return False

            serial = test.serial
            session.delete(test)
            self._refresh_device_snapshot(session, serial)
            session.commit()
            return True

    def delete_device(self, serial: str) -> bool:
        """Delete a device and all related test records."""

        serial_upper = serial.upper()
        with self._session_maker() as session:
            device = session.get(Device, serial_upper)
            tests = session.query(TestRecord).filter(TestRecord.serial == serial_upper).all()
            if device is None and not tests:
                return False

            for test in tests:
                session.delete(test)
            if device is not None:
                session.delete(device)
            session.commit()
            return True

    def _refresh_device_snapshot(self, session: Session, serial: str) -> None:
        """Update device summary fields based on latest remaining test row."""

        serial_upper = serial.upper()
        latest = session.scalars(
            select(TestRecord)
            .where(TestRecord.serial == serial_upper)
            .order_by(TestRecord.tested_at.desc(), TestRecord.id.desc())
            .limit(1)
        ).first()
        device = session.get(Device, serial_upper)

        if latest is None:
            if device is not None:
                session.delete(device)
            return

        if device is None:
            device = Device(serial=serial_upper)
            session.add(device)

        device.last_tested_at = latest.tested_at
        device.last_result = latest.result
        device.device_type = latest.device_type
        device.barcode = latest.barcode
        device.organization = classify_organization(latest.barcode) if latest.barcode else None
        device.last_updated = datetime.now(timezone.utc)

    def stats(self) -> dict[str, int]:
        """Return dashboard counters."""

        with self._session_maker() as session:
            total_devices = session.scalar(select(func.count(Device.serial))) or 0
            total_tests = session.scalar(select(func.count(TestRecord.id))) or 0
            return {"total_devices": total_devices, "total_tests": total_tests}
