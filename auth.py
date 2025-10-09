"""Local authentication and upload history storage helpers."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def default_data_path(filename: str) -> Path:
    """Return a path inside the shared data directory."""
    return DATA_DIR / filename


@dataclass
class LocalUser:
    """Simple representation of a locally stored account."""

    id: str
    email: str
    username: Optional[str]
    password_hash: str
    salt: str
    metadata: Dict[str, str]

    def display_name(self) -> str:
        return self.metadata.get("display_name") or (self.username or self.email)


class LocalAuthStore:
    """Store and validate credentials in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict[str, Dict[str, str]]] = {"users": {}}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if self.path.is_file():
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict) and "users" in loaded:
                        self._data = loaded
                        return
            except Exception:
                pass
        self._data = {"users": {}}
        self._save()

    def _save(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2)
        os.replace(tmp_path, self.path)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def _users(self) -> Iterable[LocalUser]:
        for user_id, payload in self._data.get("users", {}).items():
            yield LocalUser(
                id=user_id,
                email=payload.get("email", ""),
                username=payload.get("username"),
                password_hash=payload.get("password_hash", ""),
                salt=payload.get("salt", ""),
                metadata=payload.get("metadata", {}) or {},
            )

    def _get_user_by_email(self, email: str) -> Optional[LocalUser]:
        email = email.strip().lower()
        if not email:
            return None
        for user in self._users():
            if user.email.lower() == email:
                return user
        return None

    def _get_user_by_username(self, username: str) -> Optional[LocalUser]:
        username = username.strip().lower()
        if not username:
            return None
        for user in self._users():
            if (user.username or "").strip().lower() == username:
                return user
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_user(
        self,
        email: str,
        password: str,
        *,
        username: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> LocalUser:
        email = email.strip().lower()
        if self._get_user_by_email(email):
            raise ValueError("An account with that email already exists.")

        normalized_username: Optional[str] = None
        if username:
            normalized_username = username.strip()
            if self._get_user_by_username(normalized_username):
                raise ValueError("That username is already in use.")

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        user_id = secrets.token_hex(12)
        payload = {
            "email": email,
            "username": normalized_username,
            "password_hash": password_hash,
            "salt": salt,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        self._data.setdefault("users", {})[user_id] = payload
        self._save()
        return LocalUser(
            id=user_id,
            email=email,
            username=normalized_username,
            password_hash=password_hash,
            salt=salt,
            metadata=payload["metadata"],
        )

    def authenticate(self, identifier: str, password: str) -> Optional[LocalUser]:
        identifier = identifier.strip()
        if "@" in identifier:
            user = self._get_user_by_email(identifier)
        else:
            user = self._get_user_by_username(identifier)
            if user is None:
                user = self._get_user_by_email(identifier)
        if not user:
            return None
        expected = self._hash_password(password, user.salt)
        if secrets.compare_digest(expected, user.password_hash):
            return user
        return None

    def list_users(self) -> List[LocalUser]:
        return list(self._users())


class UploadHistoryStore:
    """Track uploads performed by local users."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, List[Dict[str, str]]] = {"records": []}
        self._load()

    def _load(self) -> None:
        if self.path.is_file():
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                    if isinstance(loaded, dict) and "records" in loaded:
                        self._data = loaded
                        return
            except Exception:
                pass
        self._data = {"records": []}
        self._save()

    def _save(self) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(self._data, handle, indent=2)
        os.replace(tmp_path, self.path)

    def add_record(
        self,
        *,
        user_id: str,
        filename: str,
        url: str,
        test_type: str,
        created_at: Optional[str] = None,
    ) -> None:
        record = {
            "user_id": user_id,
            "filename": filename,
            "url": url,
            "test_type": test_type,
            "created_at": created_at
            or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        self._data.setdefault("records", []).append(record)
        self._save()

    def get_records_for_user(self, user_id: str) -> List[Dict[str, str]]:
        records = [
            record
            for record in self._data.get("records", [])
            if record.get("user_id") == user_id
        ]
        records.sort(key=lambda rec: rec.get("created_at", ""), reverse=True)
        return records
