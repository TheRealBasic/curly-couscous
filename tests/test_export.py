from datetime import datetime, timedelta
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import desc, select

from app.api import create_app, export_archive_name, latest_test_per_device
from app.config import AppConfig
from app.database import Database
from app.models import TestRecord as DbTestRecord


def test_export_uses_latest_test_per_device_and_new_file_name(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    older_cert = tmp_path / "older.pdf"
    latest_cert = tmp_path / "latest.pdf"
    older_cert.write_text("older")
    latest_cert.write_text("latest")

    base = datetime(2026, 2, 24, 10, 0, 0)
    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=base,
        barcode="BC-OLD",
        result="FAIL",
        file_path=str(older_cert),
    )
    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=base + timedelta(hours=1),
        barcode="BC-NEW",
        result="PASS",
        file_path=str(latest_cert),
    )

    with db._session_maker() as session:
        rows = session.scalars(select(DbTestRecord).order_by(desc(DbTestRecord.tested_at), desc(DbTestRecord.id))).all()

    latest = latest_test_per_device(rows)
    assert len(latest) == 1
    assert latest[0].barcode == "BC-NEW"

    archive_name = export_archive_name(latest[0], Path(latest[0].file_path))
    assert archive_name == "PASS/ARRJ3290_BC-NEW_PASS.pdf"


def test_export_can_include_all_rows_and_skip_csv(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    older_cert = tmp_path / "older.pdf"
    latest_cert = tmp_path / "latest.pdf"
    older_cert.write_text("older")
    latest_cert.write_text("latest")

    base = datetime(2026, 2, 24, 10, 0, 0)
    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=base,
        barcode="BC-OLD",
        result="FAIL",
        file_path=str(older_cert),
    )
    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=base + timedelta(hours=1),
        barcode="BC-NEW",
        result="PASS",
        file_path=str(latest_cert),
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    response = client.get("/export.zip?latest_only=false&include_csv=false")
    assert response.status_code == 200

    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(response.content)
    with ZipFile(zip_path) as zipped:
        names = sorted(zipped.namelist())

    assert names == [
        "FAIL/ARRJ3290_BC-OLD_FAIL.pdf",
        "PASS/ARRJ3290_BC-NEW_PASS.pdf",
    ]
