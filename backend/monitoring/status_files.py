import json
from datetime import datetime, timezone

from django.conf import settings


def read_job_status(name, max_age_seconds):
    """Read a job's shared status file without treating missing data as healthy."""
    path = settings.MONITORING_STATE_DIR / f"{name}.json"
    try:
        with path.open(encoding="utf-8") as status_file:
            payload = json.load(status_file)
    except FileNotFoundError:
        return {"status": "unknown", "message": "No job status has been recorded."}
    except (OSError, ValueError):
        return {"status": "unknown", "message": "Job status could not be read."}
    if not isinstance(payload, dict):
        return {"status": "unknown", "message": "Job status has an invalid format."}

    updated_at = payload.get("updated_at")
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - updated).total_seconds()
    except (AttributeError, TypeError, ValueError):
        return {"status": "unknown", "message": "Job status timestamp is invalid."}

    payload["age_seconds"] = max(0, int(age_seconds))
    if age_seconds > max_age_seconds:
        payload["status"] = "stale"
        payload.setdefault("message", "The last job status is older than its freshness limit.")
    return payload
