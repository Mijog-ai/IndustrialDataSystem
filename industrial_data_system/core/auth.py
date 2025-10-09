"""Local authentication and upload history storage backed by SQLite."""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from industrial_data_system.core.db_manager import (
    DatabaseManager,
    UploadRecord,
    UserRecord,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def default_data_path(filename: str) -> Path:
    """Return a path inside the legacy shared data directory."""

    return DATA_DIR / filename


@dataclass
class LocalUser:
    """Representation of a locally stored account fetched from SQLite."""

    id: int
    email: str
    username: Optional[str]
    password_hash: str
    salt: str
    metadata: Dict[str, Any]
    created_at: str

    def display_name(self) -> str:
        return self.metadata.get("display_name") or (self.username or self.email)


class LocalAuthStore:
    """Store and validate credentials against the SQLite database."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or DatabaseManager()

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    def _user_from_record(self, record: UserRecord) -> LocalUser:
        return LocalUser(
            id=record.id,
            email=record.email,
            username=record.username,
            password_hash=record.password_hash,
            salt=record.salt,
            metadata=record.metadata,
            created_at=record.created_at,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def create_user(
        self,
        email: str,
        password: str,
        *,
        username: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LocalUser:
        email = email.strip().lower()
        if self.manager.get_user_by_email(email):
            raise ValueError("An account with that email already exists.")

        normalized_username: Optional[str] = None
        if username:
            normalized_username = username.strip()
            if self.manager.get_user_by_username(normalized_username):
                raise ValueError("That username is already in use.")

        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        record = self.manager.create_user(
            email=email,
            username=normalized_username,
            password_hash=password_hash,
            salt=salt,
            metadata=metadata or {},
        )
        return self._user_from_record(record)

    def authenticate(self, identifier: str, password: str) -> Optional[LocalUser]:
        identifier = identifier.strip()
        record: Optional[UserRecord]
        if "@" in identifier:
            record = self.manager.get_user_by_email(identifier)
        else:
            record = self.manager.get_user_by_username(identifier)
            if record is None:
                record = self.manager.get_user_by_email(identifier)
        if not record:
            return None

        expected = self._hash_password(password, record.salt)
        if secrets.compare_digest(expected, record.password_hash):
            return self._user_from_record(record)
        return None

    def list_users(self) -> List[LocalUser]:
        return [self._user_from_record(record) for record in self.manager.list_users()]


class UploadHistoryStore:
    """Track uploads performed by local users in SQLite."""

    def __init__(self, manager: Optional[DatabaseManager] = None) -> None:
        self.manager = manager or DatabaseManager()

    def add_record(
        self,
        *,
        user_id: int,
        filename: str,
        file_path: str,
        test_type: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UploadRecord:
        test_type_record = self.manager.ensure_test_type(test_type, description)
        return self.manager.create_upload(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            test_type=test_type,
            file_size=file_size,
            mime_type=mime_type,
            test_type_id=test_type_record.id if test_type_record else None,
        )

    def get_records_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        records = self.manager.list_uploads(user_id=user_id)
        return [self._record_to_dict(record) for record in records]

    def query(
        self,
        *,
        user_id: Optional[int] = None,
        test_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = self.manager.list_uploads(
            user_id=user_id,
            test_type=test_type,
            start_date=start_date,
            end_date=end_date,
        )
        return [self._record_to_dict(record) for record in records]

    def _record_to_dict(self, record: UploadRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "user_id": record.user_id,
            "filename": record.filename,
            "file_path": record.file_path,
            "test_type": record.test_type,
            "file_size": record.file_size,
            "mime_type": record.mime_type,
            "created_at": record.created_at,
            "test_type_id": record.test_type_id,
        }


__all__ = [
    "LocalAuthStore",
    "LocalUser",
    "UploadHistoryStore",
    "default_data_path",
]
