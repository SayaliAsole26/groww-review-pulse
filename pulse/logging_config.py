from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", None) or "-",
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class RunIdFilter(logging.Filter):
    """Attach a correlation run_id to every log record."""

    def __init__(self, run_id: str | None = None) -> None:
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "run_id", None):
            record.run_id = self.run_id or "-"
        return True


def configure_logging(
    *,
    run_id: str | None = None,
    level: int = logging.INFO,
) -> None:
    """Configure structured JSON logging for the pulse process."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RunIdFilter(run_id))
    root.addHandler(handler)

    for noisy in ("urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str, run_id: str | None = None) -> logging.LoggerAdapter:
    """Return a logger adapter that always includes run_id."""
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra={"run_id": run_id or "-"})
