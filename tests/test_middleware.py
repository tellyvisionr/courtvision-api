"""Tests for request ID and access logging middleware."""

from __future__ import annotations

import json
import logging
import re
import sys

from httpx import ASGITransport, AsyncClient
import pytest

from app.logging_config import JSONFormatter
from app.main import app


async def test_request_id_generated():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
    assert "x-request-id" in r.headers
    # Should look like a UUID4.
    assert re.match(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        r.headers["x-request-id"],
    )


async def test_request_id_passthrough():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health", headers={"X-Request-ID": "custom-id-123"})
    assert r.headers["x-request-id"] == "custom-id-123"


async def test_access_log_emitted(caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="app.access"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            await ac.get("/health")
    assert any(
        "GET" in r.message and "/health" in r.message and "200" in r.message for r in caplog.records
    )


def test_json_formatter_output():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="hello world",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert "timestamp" in parsed
    assert "level" in parsed
    assert "logger" in parsed
    assert "message" in parsed
    assert "request_id" in parsed
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "hello world"
    assert parsed["request_id"] == ""


def test_json_formatter_with_exception():
    formatter = JSONFormatter()

    try:
        raise ValueError("test error")
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="something broke",
        args=(),
        exc_info=exc_info,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert "exception" in parsed
    assert "ValueError" in parsed["exception"]
