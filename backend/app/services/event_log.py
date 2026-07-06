import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..lib.redact import redact_text
from ..models import Event


def log_event(db: Session, project_id: str, event_type: str, message: str,
              metadata: dict | None = None, workspace: Path | None = None) -> Event:
    """Write an event to the DB and, when a workspace is given, to logs/events.jsonl."""
    message = redact_text(message)  # never let a secret land in the event log
    event = Event(project_id=project_id, event_type=event_type, message=message,
                  meta=metadata or {})
    db.add(event)
    db.commit()

    if workspace is not None:
        logs_dir = workspace / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        with open(logs_dir / "events.jsonl", "a") as f:
            f.write(json.dumps({
                "type": event_type,
                "message": message,
                "metadata": metadata or {},
                "created_at": datetime.now(UTC).isoformat(),
            }, ensure_ascii=False) + "\n")
    return event
