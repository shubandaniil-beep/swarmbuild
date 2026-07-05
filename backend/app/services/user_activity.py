from sqlalchemy.orm import Session

from ..models import User, UserActivity


def log_user_activity(db: Session, user: User | None, action: str,
                      project_id: str | None = None, meta: dict | None = None) -> None:
    db.add(UserActivity(
        user_id=user.id if user else None,
        email=user.email if user else "",
        action=action,
        project_id=project_id,
        meta=meta or {},
    ))
    db.commit()
