import logging
import os
import re
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, billing, projects, telegram
from .database import init_db

# AI-call diagnostics (provider, model, status, redacted errors). Uvicorn owns
# the root logger config, so the app namespace gets its own handler.
_ai_log = logging.getLogger("swarmbuild")
if not _ai_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"))
    _ai_log.addHandler(_handler)
    _ai_log.setLevel(os.getenv("SWARMBUILD_LOG_LEVEL", "INFO").upper())
    _ai_log.propagate = False

_enable_docs = os.getenv("ENABLE_API_DOCS", "").lower() in {"1", "true", "yes"}

app = FastAPI(
    title="SwarmBuild API",
    version="0.1.0",
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
    openapi_url="/openapi.json" if _enable_docs else None,
)

# Production origins come from CORS_ALLOW_ORIGINS (comma-separated). With none
# set we fall back to localhost only — never a wildcard, since credentials are
# allowed. Auth is primarily an HttpOnly cookie, with Bearer kept only for
# CLI/API compatibility, so a tight allowlist is required.
_cors_env = [o.strip().rstrip("/") for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
             if o.strip()]
_local_dev_origins = ["http://127.0.0.1:3000", "http://localhost:3000"]
_private_lan_origin_pattern = (
    r"^http://("
    r"10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|"
    r"172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}"
    r"):3000$"
)
_cors_kwargs = (
    {"allow_origins": _cors_env}
    if _cors_env
    else {"allow_origins": _local_dev_origins,
          "allow_origin_regex": _private_lan_origin_pattern}
)
_allowed_origins = set(_cors_env or _local_dev_origins)
_allowed_origin_regex = None if _cors_env else re.compile(_private_lan_origin_pattern)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    **_cors_kwargs,
)

init_db()


def _origin_from_referer(referer: str) -> str:
    parsed = urlparse(referer)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_allowed_origin(origin: str) -> bool:
    normalized = (origin or "").rstrip("/")
    if not normalized:
        return False
    return normalized in _allowed_origins or bool(
        _allowed_origin_regex and _allowed_origin_regex.match(normalized)
    )


@app.middleware("http")
async def cookie_origin_guard(request: Request, call_next):
    if (request.url.path.startswith("/api/")
            and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}
            and request.cookies.get("sb_session")):
        origin = request.headers.get("origin") or _origin_from_referer(
            request.headers.get("referer", ""))
        if origin and not _is_allowed_origin(origin):
            return JSONResponse({"detail": "origin not allowed"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "cross-site request blocked"}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(telegram.router)
app.include_router(projects.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "swarmbuild-api"}
