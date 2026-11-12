import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

MASK = "***"


def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.field_encrypt_key
    if not key:
        # Deterministic fallback from jwt secret so dev/test still encrypts.
        digest = hashlib.sha256((settings.jwt_secret + ":field").encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    if len(key) != 44:
        digest = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_field(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def mask_secret(_value: str | None = None) -> str:
    return MASK
