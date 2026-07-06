"""Background project runner.

MVP uses a daemon thread per project; the interface matches an RQ/Celery job
(`run_project_job(project_id)`), so swapping in Redis-backed workers later is a
one-line change in `enqueue`.
"""
import threading

from ..database import SessionLocal
from ..models import Project
from ..services.event_log import log_event
from ..services.phase_orchestrator import run_project
from ..services.project_intake import workspace_path

_running: set[str] = set()
_lock = threading.Lock()


def run_project_job(project_id: str) -> None:
    db = SessionLocal()
    try:
        try:
            run_project(db, project_id)
        except Exception as exc:
            project = db.get(Project, project_id)
            if project:
                project.status = "failed"
                project.current_phase = None
                db.commit()
                log_event(db, project_id, "worker_failed",
                          f"Worker failed: {exc}", {}, workspace_path(project_id))
    finally:
        db.close()
        with _lock:
            _running.discard(project_id)


def enqueue(project_id: str) -> bool:
    with _lock:
        if project_id in _running:
            return False
        _running.add(project_id)
    threading.Thread(target=run_project_job, args=(project_id,), daemon=True).start()
    return True


def is_running(project_id: str) -> bool:
    with _lock:
        return project_id in _running
