import csv
import io
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


def test_export_csv_includes_fail_reason_column_and_value(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    failed_cert = tmp_path / "failed.pdf"
    failed_cert.write_text("failed")

    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="BC-OLD",
        result="FAIL",
        file_path=str(failed_cert),
        fail_reason="Sensor drift",
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    response = client.get("/export.zip?latest_only=false&include_certificates=false")
    assert response.status_code == 200

    zip_path = tmp_path / "export.zip"
    zip_path.write_bytes(response.content)
    with ZipFile(zip_path) as zipped:
        csv_content = zipped.read("gasdock_report.csv").decode("utf-8")

    rows = list(csv.DictReader(io.StringIO(csv_content)))
    assert rows
    assert "fail_reason" in rows[0]
    assert rows[0]["fail_reason"] == "Sensor drift"


def test_dashboard_recent_failures_include_fail_reason(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="ARRJ3290",
        device_type="Dräger X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="BC-OLD",
        result="FAIL",
        file_path="failed.pdf",
        fail_reason="Pump fault",
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    response = client.get("/api/dashboard")
    assert response.status_code == 200

    payload = response.json()
    assert payload["recent_failures"]
    assert payload["recent_failures"][0]["fail_reason"] == "Pump fault"
    assert payload["totals"]["devices"] == 1
    assert payload["totals"]["recent_failures"] == 1


def test_api_can_delete_test_and_device(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    test = db.add_test_record(
        serial="ARRJ3290",
        device_type="X-am",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="BC-1",
        result="FAIL",
        file_path="failed.pdf",
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    delete_test_response = client.delete(f"/api/tests/{test.id}")
    assert delete_test_response.status_code == 200

    db.add_test_record(
        serial="ARRJ9999",
        device_type="X-am",
        tested_at=datetime(2026, 2, 24, 11, 0, 0),
        barcode="BC-2",
        result="PASS",
        file_path="pass.pdf",
    )
    delete_device_response = client.delete("/api/devices/ARRJ9999")
    assert delete_device_response.status_code == 200


def test_import_folder_once_uses_selected_folder(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    import_dir = tmp_path / "manual"
    import_dir.mkdir()
    first = import_dir / "a.pdf"
    second = import_dir / "b.pdf"
    first.write_text("one")
    second.write_text("two")

    class StubHandler:
        def __init__(self) -> None:
            self.calls = []

        def process_file(self, path: Path) -> bool:
            self.calls.append(path.name)
            return path.name == "a.pdf"

    app = create_app(AppConfig(), db)
    app.state.certificate_handler = StubHandler()
    client = TestClient(app)

    response = client.post(f"/api/import-folder-once?folder_path={import_dir}")
    assert response.status_code == 200

    payload = response.json()
    assert payload["processed"] == 1
    assert payload["failed"] == 1
    assert payload["total"] == 2
    assert sorted(app.state.certificate_handler.calls) == ["a.pdf", "b.pdf"]


def test_print_report_renders_csv_columns_without_truncation(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    db.add_test_record(
        serial="ARRJ1234",
        device_type="Dräger X-am 2500",
        tested_at=datetime(2026, 2, 24, 10, 0, 0),
        barcode="MCA12345678901234567890",
        result="PASS",
        file_path="/tmp/certificates/very/long/path/that/should/be/visible/in/print/layout/file.pdf",
        fail_reason="",
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    response = client.get("/print-report?organization=MCA&latest_only=false&include_csv=true")
    assert response.status_code == 200
    assert "<th>Parse Error</th>" in response.text
    assert "MCA12345678901234567890" in response.text
    assert "very/long/path/that/should/be/visible" in response.text


def test_print_certificate_returns_original_pdf(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.create_tables()

    certificate_path = tmp_path / "source.pdf"
    certificate_bytes = b"%PDF-1.4\n%mock\n"
    certificate_path.write_bytes(certificate_bytes)

    row = db.add_test_record(
        serial="ARRJ9999",
        device_type="Drager",
        tested_at=datetime(2026, 2, 25, 11, 0, 0),
        barcode="MCA111111",
        result="PASS",
        file_path=str(certificate_path),
        fail_reason="",
    )

    app = create_app(AppConfig(), db)
    client = TestClient(app)

    response = client.get(f"/print-certificate/{row.id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content == certificate_bytes
