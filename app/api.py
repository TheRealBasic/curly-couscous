"""FastAPI dashboard and reporting endpoints."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.config import AppConfig
from app.database import Database
from app.models import Device, TestRecord
from app.utils import classify_organization, normalize_barcode


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

    @app.get("/export.zip")
    def export_zip(
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        organization: str | None = Query(default=None),
        db: Session = Depends(get_db),
    ) -> StreamingResponse:
        query = select(TestRecord)
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

        rows = db.scalars(query.order_by(desc(TestRecord.tested_at))).all()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            csv_output = io.StringIO()
            writer = csv.writer(csv_output)
            writer.writerow(["id", "serial", "barcode", "device_type", "tested_at", "result", "file_path", "imported_at", "parse_status", "parse_error"])
            for row in rows:
                writer.writerow(
                    [row.id, row.serial, row.barcode, row.device_type, row.tested_at, row.result, row.file_path, row.imported_at, row.parse_status, row.parse_error]
                )
            zip_file.writestr("gasdock_report.csv", csv_output.getvalue())

            for row in rows:
                file_path = Path(row.file_path)
                if not file_path.exists() or row.result not in {"PASS", "FAIL"}:
                    continue
                archive_name = f"{row.result}/{file_path.name}"
                zip_file.write(file_path, archive_name)

        zip_buffer.seek(0)
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=gasdock_export.zip"},
        )

    return app
