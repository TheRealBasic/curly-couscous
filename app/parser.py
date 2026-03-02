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
BARCODE_PATTERN = re.compile(r"^\s*Barcode\s*[:\-]?\s*(?P<value>.+?)\s*$", re.IGNORECASE | re.MULTILINE)
FAIL_REASON_PATTERN = re.compile(r"^\s*Fail\s*reason\s*[:\-]?\s*(?P<value>.+?)\s*$", re.IGNORECASE | re.MULTILINE)
SERIAL_FALLBACK_PATTERN = re.compile(r"\b([A-Z0-9]{8})\b")
SPAN_SECTION_PATTERN = re.compile(
    r"Results\s+of\s+span\s+calibration(?P<section>.*?)(?:\n\s*Overall\s*result|\Z)",
    re.IGNORECASE | re.DOTALL,
)
SPAN_HEADER_PATTERN = re.compile(r"\b(?:ch4|o2|h2s|co)\b", re.IGNORECASE)
FAILED_GAS_PATTERN = re.compile(r"\b(ch4|o2|h2s|co)\b[^\n]*?\bfailed\b", re.IGNORECASE)


@dataclass(slots=True)
class ParsedCertificate:
    """Parsed fields from a certificate file."""

    serial: str
    tested_at: datetime
    device_type: str | None
    barcode: str | None
    result: str
    fail_reason: str | None


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


def parse_pdf_text(file_path: Path) -> tuple[str | None, str | None, str | None, str | None, str]:
    """Extract device type, barcode, result, fail reason and full text from the PDF."""

    text_parts: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    full_text = "\n".join(text_parts)

    device_match = DEVICE_TYPE_PATTERN.search(full_text)
    device_type = device_match.group("value").strip() if device_match else None

    barcode_match = BARCODE_PATTERN.search(full_text)
    barcode = barcode_match.group("value").strip() if barcode_match else None

    result_match = OVERALL_RESULT_PATTERN.search(full_text)
    result = result_match.group("value").upper() if result_match else None

    fail_reason_match = FAIL_REASON_PATTERN.search(full_text)
    fail_reason = fail_reason_match.group("value").strip() if fail_reason_match else None
    span_fail_reason = _extract_span_calibration_fail_reason(full_text)
    if span_fail_reason:
        fail_reason = span_fail_reason
    if result == "PASSED":
        result = "PASS"
    elif result == "FAILED":
        result = "FAIL"

    return device_type, barcode, result, fail_reason, full_text


def _extract_span_calibration_fail_reason(full_text: str) -> str | None:
    """Extract normalized fail reason from the span calibration results table."""

    section_match = SPAN_SECTION_PATTERN.search(full_text)
    if not section_match:
        return None

    section = section_match.group("section")
    if not SPAN_HEADER_PATTERN.search(section) or "test result" not in section.lower():
        return None

    lines = [line.strip() for line in section.splitlines() if line.strip()]
    lowered_lines = [line.lower() for line in lines]

    try:
        test_result_index = next(i for i, line in enumerate(lowered_lines) if line.startswith("test result"))
    except StopIteration:
        test_result_index = -1

    if test_result_index > 0:
        gas_tokens = re.findall(r"\b(ch4|o2|h2s|co)\b", lines[test_result_index - 1], re.IGNORECASE)
        status_tokens = re.findall(r"\b(passed|failed)\b", lines[test_result_index], re.IGNORECASE)
        if gas_tokens and len(gas_tokens) == len(status_tokens):
            for gas, status in zip(gas_tokens, status_tokens):
                if status.lower() == "failed":
                    return f"Span calibration failed for {gas.upper()}"

    failed_gas_match = FAILED_GAS_PATTERN.search(section)
    if failed_gas_match:
        gas = failed_gas_match.group(1).upper()
        return f"Span calibration failed for {gas}"

    return None


def parse_certificate(file_path: Path) -> ParsedCertificate:
    """Parse certificate fields from filename and PDF content."""

    tested_at, serial = parse_filename(file_path.name)

    try:
        device_type, barcode, result, fail_reason, full_text = parse_pdf_text(file_path)
    except Exception as exc:  # pdf library level exceptions
        raise ParseError(f"PDF parsing failed: {exc}") from exc

    if not serial:
        serial_match = SERIAL_FALLBACK_PATTERN.search(full_text)
        if not serial_match:
            raise ParseError("Serial not found in filename or PDF")
        serial = serial_match.group(1)

    if result not in {"PASS", "FAIL"}:
        result = "UNKNOWN"

    if result != "FAIL":
        fail_reason = None

    return ParsedCertificate(serial=serial, tested_at=tested_at, device_type=device_type, barcode=barcode, result=result, fail_reason=fail_reason)
