"""Allowlisted JSON access events: no request bodies, URLs, headers or secrets."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "route",
            "status",
            "duration_ms",
            "error_type",
            "error_frames",
            "sqlstate",
        ):
            value = getattr(record, key, None)
            if value is not None:
                event[key] = value
        return json.dumps(event, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("smartlibrary")
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False
