from datetime import datetime, timezone
from pathlib import Path

from app.database import Database
from app.models import Device, TestRecord as DbTestRecord


def test_add_record_updates_device(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 52, 38),
        barcode="BC-12345",
        result="PASS",
        file_path="C:/GasDock/Sorted/PASS/2026/02/24/ARRJ3290/cert.pdf",
        fail_reason=None,
    )

    with db._session_maker() as session:
        device = session.get(Device, "ARRJ3290")
        assert device is not None
        assert device.last_result == "PASS"
        assert device.device_type == "Dräger X-am 2500"
        assert device.barcode == "BC-12345"
        assert device.organization == "OTHER"
        test = session.query(DbTestRecord).one()
        assert test.barcode == "BC-12345"
        assert test.fail_reason is None


def test_stats_counts(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()
    db.add_test_record(
        serial="ABCDEFG1",
        device_type="X-am",
        tested_at=datetime.now(timezone.utc),
        result="FAIL",
        file_path="file.pdf",
    )
    stats = db.stats()
    assert stats["total_devices"] == 1
    assert stats["total_tests"] == 1


def test_add_record_persists_fail_reason(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="FAIL0001",
        device_type="X-am",
        tested_at=datetime(2026, 2, 24, 11, 0, 0),
        barcode="BC-FAIL",
        result="FAIL",
        file_path="file.pdf",
        fail_reason="Sensor out of range",
    )

    with db._session_maker() as session:
        test = session.query(DbTestRecord).filter_by(serial="FAIL0001").one()
        assert test.fail_reason == "Sensor out of range"


def test_delete_test_record_updates_device_snapshot(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="ARRJ3290",
        device_type="X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="BC-OLD",
        result="FAIL",
        file_path="old.pdf",
    )
    latest = db.add_test_record(
        serial="ARRJ3290",
        device_type="X-am 2500",
        tested_at=datetime(2026, 2, 24, 11, 0, 0),
        barcode="BC-NEW",
        result="PASS",
        file_path="new.pdf",
    )

    assert db.delete_test_record(latest.id) is True

    with db._session_maker() as session:
        device = session.get(Device, "ARRJ3290")
        assert device is not None
        assert device.last_result == "FAIL"


def test_delete_device_removes_tests(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="ARRJ3290",
        device_type="X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="BC-OLD",
        result="FAIL",
        file_path="old.pdf",
    )

    assert db.delete_device("arrj3290") is True

    with db._session_maker() as session:
        assert session.get(Device, "ARRJ3290") is None
        assert session.query(DbTestRecord).filter_by(serial="ARRJ3290").count() == 0
