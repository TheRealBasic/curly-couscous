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
    )

    with db._session_maker() as session:
        device = session.get(Device, "ARRJ3290")
        assert device is not None
        assert device.last_result == "PASS"
        assert device.device_type == "Dräger X-am 2500"
        test = session.query(DbTestRecord).one()
        assert test.barcode == "BC-12345"


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
