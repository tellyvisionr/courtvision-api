"""Auto-instrument FastAPI, httpx, and SQLAlchemy with OpenTelemetry."""

from fastapi import FastAPI


def instrument_app(app: FastAPI) -> None:
    """Attach OpenTelemetry auto-instrumentation to the app and libraries.

    Call after init_telemetry() and after the FastAPI app is created.
    Each instrumentor is wrapped in a try/except so a missing or broken
    instrumentation library doesn't prevent the app from starting.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        from app.db.database import engine

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    except Exception:
        pass
