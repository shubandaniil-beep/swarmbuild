"""Encryption service for provider API keys.

Provider keys are encrypted with AES-256-GCM using a key derived from
ENCRYPTION_SECRET (or the local development secret). New ciphertexts use the
`v2:` prefix. The legacy v1 decrypt path is retained so existing local provider
records remain readable after the upgrade. Keys must never be logged or returned
by the API; only mask_key() output is exposed.
"""
import base64
import hashlib
import hmac
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .security import _secret

_AAD = b"swarmbuild-provider-key-v2"


def _aes_key() -> bytes:
    return hashlib.sha256(_secret() + b":swarmbuild-provider-keys:v2").digest()


def encrypt_key(plaintext: str) -> str:
    nonce = secrets.token_bytes(12)
    cipher = AESGCM(_aes_key()).encrypt(nonce, plaintext.encode(), _AAD)
    return "v2:" + base64.b64encode(nonce + cipher).decode()


def decrypt_key(token: str) -> str:
    if token.startswith("v2:"):
        raw = base64.b64decode(token.removeprefix("v2:").encode())
        nonce, cipher = raw[:12], raw[12:]
        return AESGCM(_aes_key()).decrypt(nonce, cipher, _AAD).decode()
    return _decrypt_legacy_key(token)


def _legacy_keystream(nonce: bytes, length: int) -> bytes:
    key = hashlib.pbkdf2_hmac("sha256", _secret(), b"swarmbuild-provider-keys", 100_000)
    out = b""
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:length]


def _decrypt_legacy_key(token: str) -> str:
    raw = base64.b64decode(token.encode())
    nonce, mac, cipher = raw[:16], raw[16:32], raw[32:]
    expected = hmac.new(_secret(), nonce + cipher, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(mac, expected):
        raise ValueError("provider key integrity check failed")
    return bytes(a ^ b for a, b in zip(cipher, _legacy_keystream(nonce, len(cipher)), strict=True)).decode()


def mask_key(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "•" * len(plaintext)
    return f"{plaintext[:3]}…{plaintext[-4:]}"
