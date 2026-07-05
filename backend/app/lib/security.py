"""Password hashing (PBKDF2) and stateless signed session tokens.

Tokens are HMAC-signed and survive backend restarts (no in-memory session
store on purpose).
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path

_SECRET_FILE = Path(__file__).resolve().parent.parent.parent / ".secret"


def _secret() -> bytes:
    env = os.getenv("ENCRYPTION_SECRET", "")
    if env:
        return env.encode()
    if not _SECRET_FILE.exists():
        _SECRET_FILE.write_text(secrets.token_hex(32))
    return _SECRET_FILE.read_text().strip().encode()


# --- passwords --------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"pbkdf2${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, expected = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(digest.hex(), expected)


# --- tokens -----------------------------------------------------------------

TOKEN_TTL_SECONDS = 7 * 24 * 3600


def create_token(user_id: str, token_version: int = 0) -> str:
    payload = f"{user_id}.{int(time.time()) + TOKEN_TTL_SECONDS}.{token_version}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload.encode()).decode() + "." + sig


def _decode_payload(token: str) -> str | None:
    try:
        payload_b64, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return payload
    except Exception:
        return None


def verify_token(token: str) -> str | None:
    """Return user_id if the token is valid and unexpired, else None."""
    try:
        payload = _decode_payload(token)
        if not payload:
            return None
        parts = payload.rsplit(".", 2)
        user_id, exp = parts[0], parts[1] if len(parts) == 3 else parts[-1]
        if int(exp) < time.time():
            return None
        return user_id
    except Exception:
        return None


def token_version(token: str) -> int:
    """Return the embedded session version; legacy two-part payloads are version 0."""
    payload = _decode_payload(token)
    if not payload:
        return -1
    parts = payload.rsplit(".", 2)
    if len(parts) != 3:
        return 0
    try:
        return int(parts[2])
    except ValueError:
        return -1
