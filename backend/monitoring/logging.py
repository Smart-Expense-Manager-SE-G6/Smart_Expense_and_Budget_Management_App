import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Serialize log records as one searchable JSON object per line."""

    _EXTRA_FIELDS = (
        "http_method",
        "path",
        "status_code",
        "duration_ms",
        "request_count",
        "error_count",
        "error_rate_percent",
        "slow_request_count",
        "window_seconds",
        "failure_id",
        "failure_reason",
        "email_subject",
    )

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "severity": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for field in self._EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)
