from datetime import datetime
from pathlib import Path

import pytest

from app import parser
from app.parser import ParseError, parse_certificate, parse_filename


def test_parse_filename_success() -> None:
    tested_at, serial = parse_filename("20260224_10_52_38_8323918ARRJ3290_Calibration_EN.pdf")
    assert tested_at == datetime(2026, 2, 24, 10, 52, 38)
    assert serial == "ARRJ3290"


def test_parse_filename_invalid() -> None:
    with pytest.raises(ParseError):
        parse_filename("invalid.pdf")


def test_parse_certificate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "20260224_10_52_38_8323918ARRJ3290_Calibration_EN.pdf"
    file_path.write_text("dummy")

    monkeypatch.setattr(parser, "parse_pdf_text", lambda _: ("Dräger X-am 2500", "BC-12345", "PASS", None, "text"))

    parsed = parse_certificate(file_path)
    assert parsed.serial == "ARRJ3290"
    assert parsed.result == "PASS"
    assert parsed.device_type == "Dräger X-am 2500"
    assert parsed.barcode == "BC-12345"
    assert parsed.fail_reason is None


def test_parse_certificate_fail_reason(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "20260224_10_52_38_8323918ARRJ3290_Calibration_EN.pdf"
    file_path.write_text("dummy")

    monkeypatch.setattr(
        parser,
        "parse_pdf_text",
        lambda _: ("Dräger X-am 2500", "BC-12345", "FAIL", "Bump test expired", "text"),
    )

    parsed = parse_certificate(file_path)
    assert parsed.result == "FAIL"
    assert parsed.fail_reason == "Bump test expired"


def test_extract_span_calibration_fail_reason_detects_failed_gas() -> None:
    text = """
Results of span calibration
ch4 O2 H2S CO
Test result Failed Passed Passed Passed
Overall result Failed
"""

    reason = parser._extract_span_calibration_fail_reason(text)
    assert reason == "Span calibration failed for CH4"


def test_extract_span_calibration_fail_reason_requires_table_context() -> None:
    text = """
Results of span calibration
Something unrelated Failed
Overall result Failed
"""

    reason = parser._extract_span_calibration_fail_reason(text)
    assert reason is None


def test_parse_certificate_span_failure_maps_expected_fail_reason(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "20260224_10_52_38_8323918ARRJ3290_Calibration_EN.pdf"
    file_path.write_text("dummy")

    sample_text = """
Results of span calibration
ch4 O2 H2S CO
Test result Failed Passed Passed Passed
Overall result Failed
"""
    monkeypatch.setattr(
        parser,
        "parse_pdf_text",
        lambda _: ("Dräger X-am 2500", "BC-12345", "FAIL", "Generic failure", sample_text),
    )

    parsed = parse_certificate(file_path)
    assert parsed.result == "FAIL"
    assert parsed.fail_reason == "Generic failure"
