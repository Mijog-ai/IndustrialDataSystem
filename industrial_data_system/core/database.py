"""SQLite database helpers for the Industrial Data System."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from industrial_data_system.core.config import get_config

_LOCK = threading.Lock()


class DatabaseInitialisationError(RuntimeError):
    """Raised when the database cannot be initialised."""


def _apply_pragma(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.close()


@dataclass
class SQLiteDatabase:
    """A thin wrapper that manages database creation and connections."""

    path: Path
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialise(self) -> None:
        with self.connection() as connection:
            _apply_pragma(connection)
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS pump_series (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS test_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    pump_series TEXT,
                    pump_series_id INTEGER REFERENCES pump_series(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    pump_series TEXT,
                    test_type TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    pump_series_id INTEGER REFERENCES pump_series(id) ON DELETE SET NULL,
                    test_type_id INTEGER REFERENCES test_types(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS dataset_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pump_series TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    checksum TEXT,
                    processed_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS model_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pump_series TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    model_path TEXT NOT NULL,
                    scaler_path TEXT,
                    metadata_path TEXT,
                    trained_at TEXT DEFAULT (datetime('now')),
                    file_count INTEGER DEFAULT 0,
                    input_dim INTEGER NOT NULL,
                    metrics TEXT DEFAULT '{}',
                    UNIQUE(pump_series, test_type, file_type, version)
                );
                 -- Add these indexes at the end:
                CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
                CREATE INDEX IF NOT EXISTS idx_uploads_test_type ON uploads(test_type);
                CREATE INDEX IF NOT EXISTS idx_uploads_pump_series ON uploads(pump_series);
                CREATE INDEX IF NOT EXISTS idx_uploads_created_at ON uploads(created_at);
                CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(LOWER(email));
                CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(username));
                CREATE INDEX IF NOT EXISTS idx_test_types_name ON test_types(name);
                CREATE INDEX IF NOT EXISTS idx_pump_series_name ON pump_series(name);
                
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    ip_address TEXT,
                    attempted_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
                );
                
                CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email);
                CREATE INDEX IF NOT EXISTS idx_login_attempts_attempted_at ON login_attempts(attempted_at);
            """

            )
            cursor = connection.cursor()
            for statement in (
                "ALTER TABLE test_types ADD COLUMN pump_series TEXT",
                "ALTER TABLE test_types ADD COLUMN pump_series_id INTEGER REFERENCES pump_series(id) ON DELETE SET NULL",
                "ALTER TABLE uploads ADD COLUMN pump_series TEXT",
                "ALTER TABLE uploads ADD COLUMN pump_series_id INTEGER REFERENCES pump_series(id) ON DELETE SET NULL",
            ):
                try:
                    cursor.execute(statement)
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise
            cursor.close()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        attempts = 0
        while True:
            try:
                connection = sqlite3.connect(
                    str(self.path),
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    timeout=self.timeout,
                    isolation_level=None,
                )
                connection.row_factory = sqlite3.Row
                _apply_pragma(connection)
                break
            except sqlite3.OperationalError as exc:
                if "unable to open database file" in str(exc).lower():
                    raise DatabaseInitialisationError(str(exc)) from exc
                if "database is locked" in str(exc).lower() and attempts < 5:
                    time.sleep(0.2 * (attempts + 1))
                    attempts += 1
                    continue
                raise

        try:
            yield connection
            connection.commit()
        finally:
            try:
                connection.rollback()
            except sqlite3.ProgrammingError:
                pass
            connection.close()


def get_database() -> SQLiteDatabase:
    """Return a shared :class:`SQLiteDatabase` instance."""

    config = get_config()
    with _LOCK:
        return SQLiteDatabase(config.database_path)


def migrate_from_json(
    *,
    upload_users_path: Optional[Path] = None,
    reader_users_path: Optional[Path] = None,
    upload_history_path: Optional[Path] = None,
) -> Dict[str, int]:
    """Migrate historical JSON data into the SQLite database."""

    database = get_database()
    database.initialise()
    counts = {"users": 0, "reader_users": 0, "uploads": 0}
    legacy_to_new_ids: Dict[str, int] = {}

    with database.connection() as connection:
        cursor = connection.cursor()

        def _insert_user(payload: Dict[str, Any], legacy_id: Optional[str]) -> None:
            metadata = payload.get("metadata") or {}
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (email, username, password_hash, salt, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
                """,
                (
                    payload.get("email"),
                    payload.get("username"),
                    payload.get("password_hash"),
                    payload.get("salt"),
                    json.dumps(metadata),
                    payload.get("created_at"),
                ),
            )
            cursor.execute(
                "SELECT id FROM users WHERE email = ?",
                (payload.get("email"),),
            )
            row = cursor.fetchone()
            if row and legacy_id:
                legacy_to_new_ids[legacy_id] = int(row["id"])

        if upload_users_path and upload_users_path.is_file():
            data = json.loads(upload_users_path.read_text(encoding="utf-8"))
            for legacy_id, user_payload in data.get("users", {}).items():
                _insert_user(user_payload, legacy_id)
                counts["users"] += 1

        if reader_users_path and reader_users_path.is_file():
            data = json.loads(reader_users_path.read_text(encoding="utf-8"))
            for legacy_id, user_payload in data.get("users", {}).items():
                _insert_user(user_payload, legacy_id)
                counts["reader_users"] += 1

        if upload_history_path and upload_history_path.is_file():
            data = json.loads(upload_history_path.read_text(encoding="utf-8"))
            for record in data.get("records", []):
                legacy_user_id = record.get("user_id")
                new_user_id = legacy_to_new_ids.get(str(legacy_user_id)) if legacy_user_id else None
                if new_user_id is None:
                    continue
                test_type = record.get("test_type") or "General"
                filename = record.get("filename") or "unknown.dat"
                cursor.execute(
                    """
                    INSERT INTO uploads (user_id, filename, file_path, test_type, created_at)
                    VALUES (?, ?, ?, ?, COALESCE(?, datetime('now')))
                    """,
                    (
                        new_user_id,
                        filename,
                        f"tests/{test_type}/{filename}",
                        test_type,
                        record.get("created_at"),
                    ),
                )
                counts["uploads"] += 1

        cursor.close()

    return counts


__all__ = [
    "SQLiteDatabase",
    "get_database",
    "migrate_from_json",
    "DatabaseInitialisationError",
]
