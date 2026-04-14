"""Tests for OpenTelemetry bootstrap and instrumentation."""

from __future__ import annotations

import os

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.instrumentation import instrument_app
from app.main import app
from app.telemetry import init_telemetry


def _reset_tracer() -> None:
    """Reset the global tracer provider to a clean SDK provider."""
    trace.set_tracer_provider(TracerProvider())


def test_init_telemetry_no_exporter():
    init_telemetry()
    assert isinstance(trace.get_tracer_provider(), TracerProvider)
    _reset_tracer()


def test_init_telemetry_console_exporter():
    os.environ["OTEL_TRACES_CONSOLE"] = "true"
    try:
        init_telemetry()  # Should not raise.
    finally:
        del os.environ["OTEL_TRACES_CONSOLE"]
        _reset_tracer()


def test_instrument_app_does_not_raise():
    fresh_app = FastAPI()
    instrument_app(fresh_app)  # Should not raise even if already instrumented.


async def test_request_creates_trace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
