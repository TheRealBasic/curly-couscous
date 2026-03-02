"""FastAPI dashboard and reporting endpoints."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.config import AppConfig
from app.database import Database
from app.models import Device, TestRecord
from app.watcher import CertificateHandler
from app.utils import classify_organization, normalize_barcode


def _safe_filename_part(value: str | None, fallback: str) -> str:
    """Return a filesystem-safe filename token."""

    if value is None or not value.strip():
        return fallback
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or fallback


def latest_test_per_device(rows: list[TestRecord]) -> list[TestRecord]:
    """Keep only the newest test row per serial."""

    latest_rows_by_device: list[TestRecord] = []
    seen_serials: set[str] = set()
    for row in rows:
        serial_key = row.serial.upper()
        if serial_key in seen_serials:
            continue
        seen_serials.add(serial_key)
        latest_rows_by_device.append(row)
    return latest_rows_by_device


def export_archive_name(row: TestRecord, source_file: Path) -> str:
    """Build export archive filename from serial, barcode, and result."""

    serial_part = _safe_filename_part(row.serial, "UNKNOWN_SERIAL")
    barcode_part = _safe_filename_part(row.barcode, "NO_BARCODE")
    result_part = _safe_filename_part(row.result, "UNKNOWN")
    return f"{row.result}/{serial_part}_{barcode_part}_{result_part}{source_file.suffix}"


def apply_export_filters(
    query,
    serial: str | None,
    result: str | None,
    date_from: str | None,
    date_to: str | None,
    organization: str | None,
):
    """Apply shared export/report filters to a TestRecord query."""

    if serial:
        query = query.where(TestRecord.serial.contains(serial.upper()))
    if result in {"PASS", "FAIL", "UNKNOWN"}:
        query = query.where(TestRecord.result == result)
    if date_from:
        query = query.where(TestRecord.tested_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(TestRecord.tested_at <= datetime.fromisoformat(date_to))
    if organization in {"AMBIPAR", "MCA", "OTHER", "UNKNOWN"}:
        if organization == "UNKNOWN":
            query = query.where(TestRecord.barcode.is_(None))
        elif organization == "AMBIPAR":
            query = query.where(TestRecord.barcode.ilike("AR %"))
        elif organization == "MCA":
            query = query.where(
                TestRecord.barcode.ilike("MCA%")
                | TestRecord.barcode.ilike("011%")
                | TestRecord.barcode.ilike("012%")
                | TestRecord.barcode.ilike("013%")
            )
        elif organization == "OTHER":
            query = query.where(TestRecord.barcode.is_not(None))
    return query


def create_app(config: AppConfig, database: Database) -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(title="GasDock Certificate Manager", version="1.0.0")

    templates = Jinja2Templates(directory=str(Path("templates")))
    app.mount("/static", StaticFiles(directory="static"), name="static")

    def get_db() -> Session:
        with database._session_maker() as session:  # internal helper for FastAPI dependency
            yield session

    def get_dashboard_data(
        db: Session,
        serial: str | None,
        result: str | None,
        date_from: str | None,
        date_to: str | None,
        organization: str | None,
    ) -> dict:
        stats = database.stats()

        failures_last_7_days = db.scalar(
            select(func.count(TestRecord.id)).where(
                and_(TestRecord.result == "FAIL", TestRecord.tested_at >= datetime.now(timezone.utc) - timedelta(days=7))
            )
        ) or 0

        query = select(Device)
        if serial:
            query = query.where(Device.serial.contains(serial.upper()))
        if result in {"PASS", "FAIL", "UNKNOWN"}:
            query = query.where(Device.last_result == result)
        if date_from:
            query = query.where(Device.last_tested_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.where(Device.last_tested_at <= datetime.fromisoformat(date_to))
        if organization in {"AMBIPAR", "MCA", "OTHER", "UNKNOWN"}:
            if organization == "UNKNOWN":
                query = query.where(Device.organization.is_(None))
            else:
                query = query.where(Device.organization == organization)
        devices = db.scalars(query.order_by(desc(Device.last_tested_at))).all()

        recent_failures = db.scalars(
            select(TestRecord)
            .where(TestRecord.result == "FAIL")
            .order_by(desc(TestRecord.tested_at))
            .limit(25)
        ).all()

        return {
            "stats": stats,
            "failures_last_7_days": failures_last_7_days,
            "devices": devices,
            "recent_failures": recent_failures,
            "filters": {
                "serial": serial or "",
                "result": result or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "organization": organization or "",
            },
        }

    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        organization: str | None = Query(default=None),
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        dashboard_data = get_dashboard_data(db, serial, result, date_from, date_to, organization)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                **dashboard_data,
            },
        )

    @app.get("/api/dashboard", response_class=JSONResponse)
    def dashboard_api(
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        organization: str | None = Query(default=None),
        db: Session = Depends(get_db),
    ) -> dict:
        dashboard_data = get_dashboard_data(db, serial, result, date_from, date_to, organization)

        return {
            "stats": dashboard_data["stats"],
            "failures_last_7_days": dashboard_data["failures_last_7_days"],
            "filters": dashboard_data["filters"],
            "devices": [
                {
                    "serial": device.serial,
                    "barcode": device.barcode,
                    "organization": device.organization,
                    "device_type": device.device_type,
                    "last_tested_at": device.last_tested_at.isoformat() if device.last_tested_at else None,
                    "last_result": device.last_result,
                }
                for device in dashboard_data["devices"]
            ],
            "recent_failures": [
                {
                    "id": failure.id,
                    "serial": failure.serial,
                    "barcode": failure.barcode,
                    "device_type": failure.device_type,
                    "fail_reason": failure.fail_reason,
                    "tested_at": failure.tested_at.isoformat() if failure.tested_at else None,
                    "result": failure.result,
                }
                for failure in dashboard_data["recent_failures"]
            ],
        }

    @app.get("/device/{serial}", response_class=HTMLResponse)
    def device_detail(request: Request, serial: str, db: Session = Depends(get_db)) -> HTMLResponse:
        device = db.get(Device, serial.upper())
        tests = db.scalars(
            select(TestRecord).where(TestRecord.serial == serial.upper()).order_by(desc(TestRecord.tested_at))
        ).all()
        return templates.TemplateResponse(
            "device.html",
            {"request": request, "device": device, "tests": tests, "serial": serial.upper()},
        )

    @app.get("/device/{serial}/barcode")
    def update_device_barcode(
        serial: str,
        barcode: str = Query(...),
        db: Session = Depends(get_db),
    ) -> RedirectResponse:
        normalized = normalize_barcode(barcode)
        device = db.get(Device, serial.upper())
        if device is not None:
            device.barcode = normalized or None
            device.organization = classify_organization(normalized) if normalized else None

            if normalized:
                latest = db.scalars(
                    select(TestRecord)
                    .where(TestRecord.serial == serial.upper())
                    .order_by(desc(TestRecord.tested_at))
                    .limit(1)
                ).first()
                if latest is not None:
                    latest.barcode = normalized
            db.commit()

        return RedirectResponse(url=f"/device/{serial.upper()}", status_code=303)

    @app.delete("/api/tests/{test_id}", response_class=JSONResponse)
    def delete_test(test_id: int) -> dict:
        deleted = database.delete_test_record(test_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Test record not found")
        return {"ok": True}

    @app.delete("/api/devices/{serial}", response_class=JSONResponse)
    def delete_device(serial: str) -> dict:
        deleted = database.delete_device(serial)
        if not deleted:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"ok": True}

    @app.post("/api/import-folder-once", response_class=JSONResponse)
    def import_folder_once(folder_path: str = Query(..., min_length=1)) -> dict:
        candidate = Path(folder_path).expanduser()
        if not candidate.exists() or not candidate.is_dir():
            raise HTTPException(status_code=400, detail="Selected folder does not exist")

        handler = getattr(app.state, "certificate_handler", None)
        if handler is None:
            handler = CertificateHandler(config, database)

        processed = 0
        failed = 0
        for file_path in sorted(candidate.glob("*.pdf")):
            if handler.process_file(file_path):
                processed += 1
            else:
                failed += 1

        return {
            "ok": True,
            "folder": str(candidate),
            "processed": processed,
            "failed": failed,
            "total": processed + failed,
        }

    @app.get("/export.zip")
    def export_zip(
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        organization: str | None = Query(default=None),
        latest_only: bool = Query(default=True),
        include_csv: bool = Query(default=True),
        include_certificates: bool = Query(default=True),
        db: Session = Depends(get_db),
    ) -> StreamingResponse:
        query = apply_export_filters(select(TestRecord), serial, result, date_from, date_to, organization)

        filtered_rows = db.scalars(query.order_by(desc(TestRecord.tested_at), desc(TestRecord.id))).all()
        export_rows = latest_test_per_device(filtered_rows) if latest_only else filtered_rows

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            csv_output = io.StringIO()
            if include_csv:
                writer = csv.writer(csv_output)
                writer.writerow([
                    "id",
                    "serial",
                    "barcode",
                    "device_type",
                    "tested_at",
                    "result",
                    "fail_reason",
                    "file_path",
                    "imported_at",
                    "parse_status",
                    "parse_error",
                ])
                for row in export_rows:
                    writer.writerow(
                        [
                            row.id,
                            row.serial,
                            row.barcode,
                            row.device_type,
                            row.tested_at,
                            row.result,
                            row.fail_reason,
                            row.file_path,
                            row.imported_at,
                            row.parse_status,
                            row.parse_error,
                        ]
                    )
                zip_file.writestr("gasdock_report.csv", csv_output.getvalue())

            if include_certificates:
                for row in export_rows:
                    file_path = Path(row.file_path)
                    if not file_path.exists() or row.result not in {"PASS", "FAIL"}:
                        continue
                    archive_name = export_archive_name(row, file_path)
                    zip_file.write(file_path, archive_name)

        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=gasdock_export.zip"},
        )

    @app.get("/print-report", response_class=HTMLResponse)
    def print_report(
        request: Request,
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        organization: str | None = Query(default=None),
        latest_only: bool = Query(default=True),
        include_csv: bool = Query(default=True),
        include_certificates: bool = Query(default=True),
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        query = apply_export_filters(select(TestRecord), serial, result, date_from, date_to, organization)

        filtered_rows = db.scalars(query.order_by(desc(TestRecord.tested_at), desc(TestRecord.id))).all()
        export_rows = latest_test_per_device(filtered_rows) if latest_only else filtered_rows

        return templates.TemplateResponse(
            "print_report.html",
            {
                "request": request,
                "rows": export_rows,
                "organization": organization or "ALL",
                "include_csv": include_csv,
                "include_certificates": include_certificates,
            },
        )

    return app
