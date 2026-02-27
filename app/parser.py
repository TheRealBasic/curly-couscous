"""PDF certificate parsing logic."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pdfplumber

FILENAME_PATTERN = re.compile(
    r"^(?P<date>\d{8})_(?P<hour>\d{2})_(?P<minute>\d{2})_(?P<second>\d{2})_(?P<serial>[A-Za-z0-9]+?)_Calibration",
    re.IGNORECASE,
)
DEVICE_TYPE_PATTERN = re.compile(r"^\s*Device\s*type\s*[:\-]?\s*(?P<value>.+?)\s*$", re.IGNORECASE | re.MULTILINE)
OVERALL_RESULT_PATTERN = re.compile(
    r"Overall\s*result\s*[:\-]?\s*(?P<value>Passed|Failed)",
    re.IGNORECASE,
)
SERIAL_FALLBACK_PATTERN = re.compile(r"\b([A-Z0-9]{8})\b")


@dataclass(slots=True)
class ParsedCertificate:
    """Parsed fields from a certificate file."""

    serial: str
    tested_at: datetime
    device_type: str | None
    result: str


class ParseError(RuntimeError):
    """Raised when required fields cannot be parsed."""


def parse_filename(file_name: str) -> tuple[datetime, str]:
    """Extract tested datetime and serial from expected X-dock filename."""

    match = FILENAME_PATTERN.search(file_name)
    if not match:
        raise ParseError(f"Unsupported filename format: {file_name}")

    tested_at = datetime.strptime(
        f"{match.group('date')}{match.group('hour')}{match.group('minute')}{match.group('second')}",
        "%Y%m%d%H%M%S",
    )
    serial = match.group("serial")[-8:].upper()
    return tested_at, serial


def parse_pdf_text(file_path: Path) -> tuple[str | None, str | None, str]:
    """Extract device type, result and full text from the PDF."""

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    full_text = "\n".join(text_parts)

    device_match = DEVICE_TYPE_PATTERN.search(full_text)
    device_type = device_match.group("value").strip() if device_match else None

    result_match = OVERALL_RESULT_PATTERN.search(full_text)
    result = result_match.group("value").upper() if result_match else None
    if result == "PASSED":
        result = "PASS"
    elif result == "FAILED":
        result = "FAIL"

    return device_type, result, full_text


def parse_certificate(file_path: Path) -> ParsedCertificate:
    """Parse certificate fields from filename and PDF content."""

    tested_at, serial = parse_filename(file_path.name)

    try:
        device_type, result, full_text = parse_pdf_text(file_path)
    except Exception as exc:  # pdf library level exceptions
        raise ParseError(f"PDF parsing failed: {exc}") from exc

    if not serial:
        serial_match = SERIAL_FALLBACK_PATTERN.search(full_text)
        if not serial_match:
            raise ParseError("Serial not found in filename or PDF")
        serial = serial_match.group(1)

    if result not in {"PASS", "FAIL"}:
        result = "UNKNOWN"

    return ParsedCertificate(serial=serial, tested_at=tested_at, device_type=device_type, result=result)
