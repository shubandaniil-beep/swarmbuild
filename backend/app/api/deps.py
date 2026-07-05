from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..lib.security import token_version, verify_token
from ..models import User


SESSION_COOKIE = "sb_session"


def get_current_user(authorization: str = Header(default=""),
                     sb_session: str = Cookie(default=""),
                     db: Session = Depends(get_db)) -> User:
    raw = sb_session or ""
    if not raw and authorization.startswith("Bearer "):
        raw = authorization.removeprefix("Bearer ").strip()
    if not raw:
        raise HTTPException(401, "not authenticated")
    user_id = verify_token(raw)
    if not user_id:
        raise HTTPException(401, "invalid or expired token")
    user = db.get(User, user_id)
    if not user or user.disabled:
        raise HTTPException(401, "account unavailable")
    if token_version(raw) != (user.token_version or 0):
        raise HTTPException(401, "session revoked")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "admin only")
    return user
