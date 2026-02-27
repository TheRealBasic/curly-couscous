from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.api import create_app
from app.config import AppConfig
from app.database import Database
from app.models import TestRecord as DbTestRecord


def test_manual_barcode_update(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()
    created = db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 52, 38),
        result="PASS",
        file_path="file.pdf",
    )

    config = AppConfig(
        db_path=tmp_path / "test.db",
        import_folder=tmp_path / "imports",
        sorted_folder=tmp_path / "sorted",
        quarantine_folder=tmp_path / "quarantine",
        logs_folder=tmp_path / "logs",
    )
    app = create_app(config, db)
    client = TestClient(app)

    response = client.post(
        f"/test/{created.id}/barcode",
        data={"serial": "ARRJ3290", "barcode": "BC-778899"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].endswith("/device/ARRJ3290?barcode_updated=ok")

    with db._session_maker() as session:
        updated = session.get(DbTestRecord, created.id)
        assert updated is not None
        assert updated.barcode == "BC-778899"
