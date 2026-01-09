"""Local authentication and upload history storage backed by SQLite."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from industrial_data_system.core.db_manager import DatabaseManager, UploadRecord, UserRecord

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class SessionManager:
    """Manage user sessions with timeout and expiry tracking."""

    def __init__(self, timeout_minutes: int = 30):
        self.timeout_minutes = timeout_minutes
        self._sessions: Dict[int, datetime] = {}  # user_id -> last_activity

    def create_session(self, user_id: int) -> None:
        """Create a new session for user."""
        self._sessions[user_id] = datetime.now()

    def update_activity(self, user_id: int) -> None:
        """Update last activity timestamp."""
        if user_id in self._sessions:
            self._sessions[user_id] = datetime.now()

    def is_session_valid(self, user_id: int) -> bool:
        """Check if session is still valid (not timed out)."""
        if user_id not in self._sessions:
            return False

        last_activity = self._sessions[user_id]
        timeout = timedelta(minutes=self.timeout_minutes)
        return datetime.now() - last_activity < timeout

    def invalidate_session(self, user_id: int) -> None:
        """Remove session (logout)."""
        self._sessions.pop(user_id, None)

    def get_remaining_time(self, user_id: int) -> Optional[int]:
        """Get remaining session time in minutes."""
        if user_id not in self._sessions:
            return None

        last_activity = self._sessions[user_id]
        timeout = timedelta(minutes=self.timeout_minutes)
        remaining = timeout - (datetime.now() - last_activity)
        return max(0, int(remaining.total_seconds() / 60))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets minimum security requirements.

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    return True, ""


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

        # ADD THIS PASSWORD VALIDATION
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

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

        # Check for account lockout
        failed_attempts = self.manager.get_failed_login_count(identifier, minutes=15)
        if failed_attempts >= 5:
            # Record this failed attempt
            self.manager.record_login_attempt(identifier, success=False)
            return None  # Account is locked

        record: Optional[UserRecord]
        if "@" in identifier:
            record = self.manager.get_user_by_email(identifier)
        else:
            record = self.manager.get_user_by_username(identifier)
            if record is None:
                record = self.manager.get_user_by_email(identifier)

        if not record:
            # Record failed attempt for non-existent user
            self.manager.record_login_attempt(identifier, success=False)
            return None

        expected = self._hash_password(password, record.salt)
        if secrets.compare_digest(expected, record.password_hash):
            # SUCCESS - clear failed attempts
            self.manager.clear_login_attempts(record.email)
            self.manager.record_login_attempt(record.email, success=True)
            return self._user_from_record(record)
        else:
            # FAILURE - record failed attempt
            self.manager.record_login_attempt(record.email, success=False)
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
        pump_series: Optional[str] = None,
        test_type: str,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> UploadRecord:
        pump_series_value = pump_series.strip() if pump_series else None
        pump_series_record = (
            self.manager.ensure_pump_series(pump_series_value) if pump_series_value else None
        )
        test_type_record = self.manager.ensure_test_type(
            test_type,
            description,
            pump_series=pump_series_value,
        )
        return self.manager.create_upload(
            user_id=user_id,
            filename=filename,
            file_path=file_path,
            pump_series=pump_series_value,
            test_type=test_type,
            file_size=file_size,
            mime_type=mime_type,
            pump_series_id=pump_series_record.id if pump_series_record else None,
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
        pump_series: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = self.manager.list_uploads(
            user_id=user_id,
            test_type=test_type,
            pump_series=pump_series,
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
            "pump_series": record.pump_series,
            "test_type": record.test_type,
            "file_size": record.file_size,
            "mime_type": record.mime_type,
            "created_at": record.created_at,
            "pump_series_id": record.pump_series_id,
            "test_type_id": record.test_type_id,
        }


__all__ = [
    "LocalAuthStore",
    "LocalUser",
    "UploadHistoryStore",
    "default_data_path",
]
