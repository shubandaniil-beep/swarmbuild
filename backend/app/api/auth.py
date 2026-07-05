import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..lib import rate_limit
from ..lib.security import TOKEN_TTL_SECONDS, create_token, hash_password, verify_password
from ..models import User
from ..services import credit_pricing
from ..services.settings_service import get_setting
from ..services.token_ledger import ensure_credit_columns
from ..services.user_activity import log_user_activity
from .deps import SESSION_COOKIE, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    fingerprint: str = Field(default="", max_length=128)


def _set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=TOKEN_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")


def _is_loopback_host(value: str) -> bool:
    host = (value or "").strip().lower().strip("[]")
    return host in {"127.0.0.1", "::1", "localhost"}


def _dev_founder_email() -> str:
    return os.getenv("ADMIN_EMAIL") or os.getenv("FOUNDER_EMAIL") or "founder@swarmbuild.ai"


def _dev_founder_password() -> str:
    configured = os.getenv("ADMIN_PASSWORD") or os.getenv("FOUNDER_PASSWORD")
    if configured:
        return configured
    password_file = Path(__file__).resolve().parents[2] / ".founder-password"
    if password_file.exists():
        return password_file.read_text().strip()
    return ""


def _require_local_dev_autofill(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    request_host = request.url.hostname or ""
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    origin_host = urlparse(origin).hostname if origin else ""
    referer_host = urlparse(referer).hostname if referer else ""
    if not _is_loopback_host(client_host):
        raise HTTPException(404, "not found")
    if not _is_loopback_host(request_host):
        raise HTTPException(404, "not found")
    if origin and not _is_loopback_host(origin_host or ""):
        raise HTTPException(404, "not found")
    if referer and not _is_loopback_host(referer_host or ""):
        raise HTTPException(404, "not found")


def _client_ip(request: Request, db: Session) -> str:
    """Client IP for rate-limiting. X-Forwarded-For is client-controllable and
    only trusted when a proxy in front is known to set it (trust_proxy_headers);
    otherwise a caller could spoof it to dodge the per-IP anti-abuse limits."""
    if get_setting(db, "trust_proxy_headers"):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


def _abuse_check(db: Session, email: str, fingerprint: str, ip: str) -> None:
    """Blocks mass-signup abuse from a single device/network (spec: anti-fraud)."""
    fp_limit = get_setting(db, "max_accounts_per_fingerprint")
    if fingerprint and fp_limit is not None:
        existing = db.query(User).filter(User.signup_fingerprint == fingerprint).count()
        if existing >= int(fp_limit):
            log_user_activity(db, None, "signup_blocked", meta={
                "email": email,
                "reason": "fingerprint_limit",
                "fingerprint": fingerprint,
                "ip": ip,
                "existing_accounts": existing,
            })
            raise HTTPException(429, "too many accounts already registered from this device")

    ip_limit = get_setting(db, "max_accounts_per_ip_per_day")
    if ip and ip_limit is not None:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        recent = db.query(User).filter(User.signup_ip == ip, User.created_at >= since).count()
        if recent >= int(ip_limit):
            log_user_activity(db, None, "signup_blocked", meta={
                "email": email,
                "reason": "ip_daily_limit",
                "ip": ip,
                "recent_accounts": recent,
            })
            raise HTTPException(429, "too many accounts registered from this network today")


def _user_out(user: User, db: Session | None = None) -> dict:
    ensure_credit_columns(user)
    credits_per_usd = credit_pricing.tokens_per_usd(db) if db is not None else 100
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "token_balance": user.token_balance,
        "demo_generations_remaining": user.demo_generations_remaining,
        "credits_per_usd": credits_per_usd,
        "credit_value_usd": round(1 / max(credits_per_usd, 1), 4),
    }


@router.post("/register")
def register(body: Credentials, request: Request, response: Response,
             db: Session = Depends(get_db)):
    if not get_setting(db, "public_registration_enabled"):
        raise HTTPException(403, "registration is disabled")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(409, "email already registered")
    ip = _client_ip(request, db)
    _abuse_check(db, body.email, body.fingerprint, ip)
    # Starter grant is the admin-configurable "$1 starter balance" (default 100
    # credits, matching the landing page's "100 credits = $1"). Set it explicitly
    # so the offer never drifts from the model's column default.
    starting_credits = int(get_setting(db, "demo_starting_credits") or 100)
    user = User(email=body.email, password_hash=hash_password(body.password),
                signup_fingerprint=body.fingerprint, signup_ip=ip,
                token_balance=starting_credits,
                lifetime_tokens_granted=starting_credits)
    db.add(user)
    db.commit()
    log_user_activity(db, user, "registered", meta={"token_balance": user.token_balance})
    token = create_token(user.id, user.token_version or 0)
    _set_session_cookie(response, request, token)
    return {"user": _user_out(user, db)}


def _login_guard(db: Session, bucket: str, request: Request, email: str):
    """Sliding-window brute-force guard keyed by IP and by email."""
    max_attempts = int(get_setting(db, "max_login_attempts") or 0)
    window = int(get_setting(db, "login_window_minutes") or 15) * 60
    ip = _client_ip(request, db)
    for identity in (f"ip:{ip}", f"email:{email.lower()}"):
        if not rate_limit.check(bucket, identity, max_attempts, window):
            log_user_activity(db, None, "login_rate_limited",
                              meta={"bucket": bucket, "email": email, "ip": ip})
            raise HTTPException(429, "too many attempts, try again later")
    return ip, window


def _record_login_failure(bucket: str, ip: str, email: str, window: float) -> None:
    rate_limit.record_failure(bucket, f"ip:{ip}", window)
    rate_limit.record_failure(bucket, f"email:{email.lower()}", window)


def _clear_login_failures(bucket: str, ip: str, email: str) -> None:
    rate_limit.clear(bucket, f"ip:{ip}")
    rate_limit.clear(bucket, f"email:{email.lower()}")


@router.post("/login")
def login(body: Credentials, request: Request, response: Response,
          db: Session = Depends(get_db)):
    ip, window = _login_guard(db, "login", request, body.email)
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        _record_login_failure("login", ip, body.email, window)
        raise HTTPException(401, "invalid email or password")
    if user.disabled:
        raise HTTPException(403, "account disabled")
    _clear_login_failures("login", ip, body.email)
    log_user_activity(db, user, "login")
    token = create_token(user.id, user.token_version or 0)
    _set_session_cookie(response, request, token)
    return {"user": _user_out(user, db)}


@router.post("/admin-login")
def admin_login(body: Credentials, request: Request, response: Response,
                db: Session = Depends(get_db)):
    ip, window = _login_guard(db, "admin-login", request, body.email)
    user = db.query(User).filter(User.email == body.email).first()
    if (not user or user.role != "admin" or user.disabled
            or not verify_password(body.password, user.password_hash)):
        _record_login_failure("admin-login", ip, body.email, window)
        raise HTTPException(401, "invalid admin credentials")
    _clear_login_failures("admin-login", ip, body.email)
    log_user_activity(db, user, "admin_login")
    token = create_token(user.id, user.token_version or 0)
    _set_session_cookie(response, request, token)
    return {"user": _user_out(user, db)}


@router.get("/admin-autofill")
def admin_autofill(request: Request):
    _require_local_dev_autofill(request)
    password = _dev_founder_password()
    if not password:
        raise HTTPException(404, "founder autofill is not configured")
    return {
        "email": _dev_founder_email(),
        "password": password,
    }


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_out(user, db)


@router.post("/logout")
def logout(response: Response, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    log_user_activity(db, user, "logout")
    _clear_session_cookie(response)
    return {"ok": True}
