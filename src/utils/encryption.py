"""Simple encryption helpers using Fernet for token storage."""
from __future__ import annotations

import json
from typing import Optional

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config.settings import DATA_DIR, load_app_config

SECRET_FILE = DATA_DIR / "admin_tokens.json"
SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)


def _get_cipher() -> Fernet:
    config = load_app_config()
    raw = config.encryption_key.encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(text: str) -> str:
    return _get_cipher().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str) -> Optional[str]:
    try:
        return _get_cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None


def store_encrypted_payload(name: str, payload: str) -> None:
    data: dict[str, str] = {}
    if SECRET_FILE.exists():
        raw = SECRET_FILE.read_text(encoding="utf-8")
        data = json.loads(raw) if raw else {}
    data[name] = encrypt_text(payload)
    SECRET_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_encrypted_payload(name: str) -> Optional[str]:
    if not SECRET_FILE.exists():
        return None
    data = json.loads(SECRET_FILE.read_text(encoding="utf-8"))
    encrypted = data.get(name)
    if not encrypted:
        return None
    return decrypt_text(encrypted)
