import os
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin, auth, billing, projects
from .database import init_db

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
_cors_env = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
_cors_kwargs = ({"allow_origins": _cors_env} if _cors_env
                else {"allow_origins": ["http://127.0.0.1:3000", "http://localhost:3000"]})
_allowed_origins = set(_cors_kwargs["allow_origins"])

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


@app.middleware("http")
async def cookie_origin_guard(request: Request, call_next):
    if (request.url.path.startswith("/api/")
            and request.method.upper() not in {"GET", "HEAD", "OPTIONS"}
            and request.cookies.get("sb_session")):
        origin = request.headers.get("origin") or _origin_from_referer(
            request.headers.get("referer", ""))
        if origin and origin.rstrip("/") not in _allowed_origins:
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
app.include_router(projects.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "swarmbuild-api"}
