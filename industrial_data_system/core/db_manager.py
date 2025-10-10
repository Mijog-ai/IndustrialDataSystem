"""Database manager wrapping SQLite queries with retry logic."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from industrial_data_system.core.database import SQLiteDatabase, get_database


@dataclass
class UserRecord:
    id: int
    email: str
    username: Optional[str]
    password_hash: str
    salt: str
    metadata: Dict[str, Any]
    created_at: str


@dataclass
class UploadRecord:
    id: int
    user_id: int
    filename: str
    file_path: str
    pump_series: Optional[str]
    test_type: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: str
    pump_series_id: Optional[int]
    test_type_id: Optional[int]


@dataclass
class TestTypeRecord:
    id: int
    name: str
    description: Optional[str]
    created_at: str
    pump_series: Optional[str]
    pump_series_id: Optional[int]


@dataclass
class PumpSeriesRecord:
    id: int
    name: str
    description: Optional[str]
    created_at: str


class DatabaseManager:
    """High-level interface for all database operations."""

    def __init__(self, database: Optional[SQLiteDatabase] = None, *, max_retries: int = 5) -> None:
        self.database = database or get_database()
        self.database.initialise()
        self.max_retries = max_retries

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Provide a transaction context with retry handling."""

        attempts = 0
        while True:
            try:
                with self.database.connection() as connection:
                    yield connection
                    break
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc).lower() and attempts < self.max_retries:
                    time.sleep(0.2 * (attempts + 1))
                    attempts += 1
                    continue
                raise

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _execute(
        self,
        query: str,
        parameters: Sequence[Any] = (),
        *,
        fetchone: bool = False,
        fetchall: bool = False,
    ) -> Any:
        attempts = 0
        while True:
            try:
                with self.database.connection() as connection:
                    cursor = connection.cursor()
                    cursor.execute(query, parameters)
                    if fetchone:
                        row = cursor.fetchone()
                    elif fetchall:
                        row = cursor.fetchall()
                    else:
                        row = None
                    cursor.close()
                    return row
            except sqlite3.OperationalError as exc:
                if "database is locked" in str(exc).lower() and attempts < self.max_retries:
                    time.sleep(0.2 * (attempts + 1))
                    attempts += 1
                    continue
                raise

    def _row_to_user(self, row: sqlite3.Row) -> UserRecord:
        metadata_raw = row["metadata"] if "metadata" in row.keys() else row[5]
        metadata: Dict[str, Any]
        if isinstance(metadata_raw, (bytes, bytearray)):
            metadata_raw = metadata_raw.decode("utf-8")
        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata = {}
        else:
            metadata = {}
        return UserRecord(
            id=row["id"],
            email=row["email"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            metadata=metadata,
            created_at=row["created_at"],
        )

    def _row_to_upload(self, row: sqlite3.Row) -> UploadRecord:
        pump_series = row["pump_series"] if "pump_series" in row.keys() else None
        pump_series_id = row["pump_series_id"] if "pump_series_id" in row.keys() else None
        return UploadRecord(
            id=row["id"],
            user_id=row["user_id"],
            filename=row["filename"],
            file_path=row["file_path"],
            pump_series=pump_series,
            test_type=row["test_type"],
            file_size=row["file_size"],
            mime_type=row["mime_type"],
            created_at=row["created_at"],
            pump_series_id=pump_series_id,
            test_type_id=row["test_type_id"],
        )

    def _row_to_test_type(self, row: sqlite3.Row) -> TestTypeRecord:
        pump_series = row["pump_series"] if "pump_series" in row.keys() else None
        pump_series_id = row["pump_series_id"] if "pump_series_id" in row.keys() else None
        return TestTypeRecord(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
            pump_series=pump_series,
            pump_series_id=pump_series_id,
        )

    def _row_to_pump_series(self, row: sqlite3.Row) -> PumpSeriesRecord:
        return PumpSeriesRecord(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # User operations
    # ------------------------------------------------------------------
    def create_user(
        self,
        *,
        email: str,
        username: Optional[str],
        password_hash: str,
        salt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRecord:
        metadata_json = json.dumps(metadata or {})
        self._execute(
            """
            INSERT INTO users (email, username, password_hash, salt, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, username, password_hash, salt, metadata_json),
        )
        row = self._execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
            fetchone=True,
        )
        assert row is not None
        return self._row_to_user(row)

    def update_user(
        self,
        user_id: int,
        *,
        email: Optional[str] = None,
        username: Optional[str] = None,
        password_hash: Optional[str] = None,
        salt: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        fields: List[str] = []
        parameters: List[Any] = []
        if email is not None:
            fields.append("email = ?")
            parameters.append(email)
        if username is not None:
            fields.append("username = ?")
            parameters.append(username)
        if password_hash is not None:
            fields.append("password_hash = ?")
            parameters.append(password_hash)
        if salt is not None:
            fields.append("salt = ?")
            parameters.append(salt)
        if metadata is not None:
            fields.append("metadata = ?")
            parameters.append(json.dumps(metadata))
        if not fields:
            return
        parameters.append(user_id)
        query = "UPDATE users SET " + ", ".join(fields) + " WHERE id = ?"
        self._execute(query, parameters)

    def delete_user(self, user_id: int) -> None:
        self._execute("DELETE FROM users WHERE id = ?", (user_id,))

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        row = self._execute(
            "SELECT * FROM users WHERE lower(email) = lower(?)",
            (email,),
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_user(row)

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        row = self._execute(
            "SELECT * FROM users WHERE lower(username) = lower(?)",
            (username,),
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_user(row)

    def get_user_by_id(self, user_id: int) -> Optional[UserRecord]:
        row = self._execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_user(row)

    def list_users(self) -> List[UserRecord]:
        rows = self._execute("SELECT * FROM users ORDER BY created_at DESC", fetchall=True)
        if not rows:
            return []
        return [self._row_to_user(row) for row in rows]

    # ------------------------------------------------------------------
    # Pump series
    # ------------------------------------------------------------------
    def create_pump_series(
        self,
        *,
        name: str,
        description: Optional[str] = None,
    ) -> PumpSeriesRecord:
        self._execute(
            "INSERT OR IGNORE INTO pump_series (name, description) VALUES (?, ?)",
            (name, description),
        )
        row = self._execute(
            "SELECT * FROM pump_series WHERE lower(name) = lower(?)",
            (name,),
            fetchone=True,
        )
        assert row is not None
        return self._row_to_pump_series(row)

    def ensure_pump_series(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> PumpSeriesRecord:
        existing = self.get_pump_series_by_name(name)
        if existing:
            if description and not existing.description:
                self.update_pump_series(existing.id, description=description)
                existing = self.get_pump_series_by_name(name)
            assert existing is not None
            return existing
        return self.create_pump_series(name=name, description=description)

    def get_pump_series_by_name(self, name: str) -> Optional[PumpSeriesRecord]:
        row = self._execute(
            "SELECT * FROM pump_series WHERE lower(name) = lower(?)",
            (name,),
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_pump_series(row)

    def list_pump_series(self) -> List[PumpSeriesRecord]:
        rows = self._execute(
            "SELECT * FROM pump_series ORDER BY name COLLATE NOCASE ASC",
            fetchall=True,
        )
        if not rows:
            return []
        return [self._row_to_pump_series(row) for row in rows]

    def update_pump_series(
        self,
        pump_series_id: int,
        *,
        description: Optional[str] = None,
    ) -> None:
        if description is None:
            return
        self._execute(
            "UPDATE pump_series SET description = ? WHERE id = ?",
            (description, pump_series_id),
        )

    # ------------------------------------------------------------------
    # Test types
    # ------------------------------------------------------------------
    def create_test_type(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        pump_series: Optional[str] = None,
    ) -> TestTypeRecord:
        pump_series_name = pump_series.strip() if pump_series else None
        pump_series_id: Optional[int] = None
        if pump_series_name:
            pump_record = self.ensure_pump_series(pump_series_name)
            pump_series_id = pump_record.id
        self._execute(
            """
            INSERT OR IGNORE INTO test_types (name, description, pump_series, pump_series_id)
            VALUES (?, ?, ?, ?)
            """,
            (name, description, pump_series_name, pump_series_id),
        )
        row = self._execute(
            "SELECT * FROM test_types WHERE lower(name) = lower(?)",
            (name,),
            fetchone=True,
        )
        assert row is not None
        return self._row_to_test_type(row)

    def ensure_test_type(
        self,
        name: str,
        description: Optional[str] = None,
        pump_series: Optional[str] = None,
    ) -> TestTypeRecord:
        existing = self.get_test_type_by_name(name, pump_series=pump_series)
        if existing:
            needs_description_update = description and not existing.description
            needs_series_update = pump_series and not existing.pump_series
            if needs_description_update or needs_series_update:
                self.update_test_type(
                    existing.id,
                    description=description if needs_description_update else None,
                    pump_series=pump_series if needs_series_update else None,
                )
                existing = self.get_test_type_by_name(name, pump_series=pump_series)
            assert existing is not None
            return existing
        return self.create_test_type(name=name, description=description, pump_series=pump_series)

    def get_test_type_by_name(
        self,
        name: str,
        *,
        pump_series: Optional[str] = None,
    ) -> Optional[TestTypeRecord]:
        query = "SELECT * FROM test_types WHERE lower(name) = lower(?)"
        params: List[Any] = [name]
        if pump_series:
            query += " AND lower(pump_series) = lower(?)"
            params.append(pump_series)
        row = self._execute(
            query,
            params,
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_test_type(row)

    def list_test_types(
        self,
        *,
        pump_series: Optional[str] = None,
    ) -> List[TestTypeRecord]:
        query = "SELECT * FROM test_types"
        params: List[Any] = []
        if pump_series:
            query += " WHERE lower(pump_series) = lower(?)"
            params.append(pump_series)
        query += " ORDER BY name COLLATE NOCASE ASC"
        rows = self._execute(
            query,
            params,
            fetchall=True,
        )
        if not rows:
            return []
        return [self._row_to_test_type(row) for row in rows]

    def update_test_type(
        self,
        test_type_id: int,
        *,
        description: Optional[str] = None,
        pump_series: Optional[str] = None,
    ) -> None:
        fields: List[str] = []
        params: List[Any] = []
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if pump_series is not None:
            pump_record = self.ensure_pump_series(pump_series)
            fields.append("pump_series = ?")
            params.append(pump_series)
            fields.append("pump_series_id = ?")
            params.append(pump_record.id)
        if not fields:
            return
        params.append(test_type_id)
        query = "UPDATE test_types SET " + ", ".join(fields) + " WHERE id = ?"
        self._execute(query, params)

    # ------------------------------------------------------------------
    # Uploads
    # ------------------------------------------------------------------
    def create_upload(
        self,
        *,
        user_id: int,
        filename: str,
        file_path: str,
        pump_series: Optional[str],
        test_type: str,
        file_size: Optional[int],
        mime_type: Optional[str],
        pump_series_id: Optional[int],
        test_type_id: Optional[int],
    ) -> UploadRecord:
        self._execute(
            """
            INSERT INTO uploads (
                user_id,
                filename,
                file_path,
                pump_series,
                test_type,
                file_size,
                mime_type,
                pump_series_id,
                test_type_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                filename,
                file_path,
                pump_series,
                test_type,
                file_size,
                mime_type,
                pump_series_id,
                test_type_id,
            ),
        )
        row = self._execute(
            """
            SELECT * FROM uploads
            WHERE user_id = ? AND file_path = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, file_path),
            fetchone=True,
        )
        assert row is not None
        return self._row_to_upload(row)

    def find_upload(
        self,
        *,
        user_id: int,
        filename: str,
        test_type: str,
        pump_series: Optional[str] = None,
    ) -> Optional[UploadRecord]:
        query = (
            """
            SELECT * FROM uploads
            WHERE user_id = ? AND filename = ? AND test_type = ?
            """
        )
        params: List[Any] = [user_id, filename, test_type]
        if pump_series:
            query += " AND pump_series = ?"
            params.append(pump_series)
        query += " ORDER BY datetime(created_at) DESC LIMIT 1"
        row = self._execute(
            query,
            params,
            fetchone=True,
        )
        if row is None:
            return None
        return self._row_to_upload(row)

    def update_upload(
        self,
        upload_id: int,
        *,
        filename: Optional[str] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
    ) -> None:
        fields: List[str] = []
        params: List[Any] = []
        if filename is not None:
            fields.append("filename = ?")
            params.append(filename)
        if file_path is not None:
            fields.append("file_path = ?")
            params.append(file_path)
        if file_size is not None:
            fields.append("file_size = ?")
            params.append(file_size)
        if mime_type is not None:
            fields.append("mime_type = ?")
            params.append(mime_type)
        if not fields:
            return
        params.append(upload_id)
        query = "UPDATE uploads SET " + ", ".join(fields) + " WHERE id = ?"
        self._execute(query, params)

    def list_uploads(
        self,
        *,
        user_id: Optional[int] = None,
        test_type: Optional[str] = None,
        pump_series: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[UploadRecord]:
        query = "SELECT * FROM uploads WHERE 1=1"
        params: List[Any] = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        if test_type:
            query += " AND test_type = ?"
            params.append(test_type)
        if pump_series:
            query += " AND pump_series = ?"
            params.append(pump_series)
        if start_date:
            query += " AND datetime(created_at) >= datetime(?)"
            params.append(start_date)
        if end_date:
            query += " AND datetime(created_at) <= datetime(?)"
            params.append(end_date)
        query += " ORDER BY datetime(created_at) DESC"
        rows = self._execute(query, params, fetchall=True)
        if not rows:
            return []
        return [self._row_to_upload(row) for row in rows]

    def delete_upload(self, upload_id: int) -> None:
        self._execute("DELETE FROM uploads WHERE id = ?", (upload_id,))

    def prune_missing_uploads(self, base_path: Path) -> int:
        """Remove upload records that no longer have files on disk.

        Parameters
        ----------
        base_path:
            Root directory where uploaded files are stored.

        Returns
        -------
        int
            Number of records removed from the database.
        """

        base_path = Path(base_path)
        if not base_path.exists():
            return 0

        removed = 0
        for record in self.list_uploads():
            file_path = record.file_path
            candidate = Path(file_path) if file_path else None
            if candidate and not candidate.is_absolute():
                candidate = base_path / candidate

            if not candidate or not candidate.exists():
                self.delete_upload(record.id)
                removed += 1

        return removed

    def get_storage_usage(self) -> int:
        row = self._execute("SELECT COALESCE(SUM(file_size), 0) AS usage FROM uploads", fetchone=True)
        if row is None:
            return 0
        return int(row[0])


__all__ = [
    "DatabaseManager",
    "UserRecord",
    "UploadRecord",
    "TestTypeRecord",
    "PumpSeriesRecord",
]
