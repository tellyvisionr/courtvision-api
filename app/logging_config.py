"""Structured JSON logging configuration."""

from datetime import UTC, datetime
import json
import logging
import sys

from app.middleware import request_id_ctx


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Every line includes: timestamp (ISO 8601 UTC), level, logger name, message,
    and the current request_id from the contextvar (empty string if outside a
    request). If the log record has exc_info, include a formatted traceback in
    the "exception" field.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, str] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_dict["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_dict)


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with JSON output to stdout.

    Call once at app startup. Replaces any existing handlers on the root logger.
    Also quiets noisy third-party loggers (uvicorn.access, httpx) to WARNING.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Suppress noisy loggers — we have our own access log middleware.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
