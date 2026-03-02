"""FastAPI dashboard and reporting endpoints."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.config import AppConfig
from app.database import Database
from app.models import Device, TestRecord


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
            },
        }

    @app.get("/", response_class=HTMLResponse)
    def index(
        request: Request,
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        db: Session = Depends(get_db),
    ) -> HTMLResponse:
        dashboard_data = get_dashboard_data(db, serial, result, date_from, date_to)

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
        db: Session = Depends(get_db),
    ) -> dict:
        dashboard_data = get_dashboard_data(db, serial, result, date_from, date_to)

        return {
            "stats": dashboard_data["stats"],
            "failures_last_7_days": dashboard_data["failures_last_7_days"],
            "filters": dashboard_data["filters"],
            "devices": [
                {
                    "serial": device.serial,
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

    @app.get("/export.csv")
    def export_csv(
        serial: str | None = Query(default=None),
        result: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
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

        rows = db.scalars(query.order_by(desc(TestRecord.tested_at))).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "serial", "barcode", "device_type", "tested_at", "result", "file_path", "imported_at", "parse_status", "parse_error"])
        for row in rows:
            writer.writerow(
                [row.id, row.serial, row.barcode, row.device_type, row.tested_at, row.result, row.file_path, row.imported_at, row.parse_status, row.parse_error]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gasdock_report.csv"},
        )

    return app
