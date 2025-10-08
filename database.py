"""Database utilities for the Industrial Data System application."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterable, Optional

DEFAULT_DB_PATH = Path(os.getenv("IDS_DB_PATH", "app.db"))


def _ensure_directory(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection(db_path: Path = DEFAULT_DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager returning a SQLite connection with row factory enabled."""
    _ensure_directory(db_path)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.commit()
        connection.close()


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Create the users table if it does not already exist."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )


def add_user(username: str, email: str, password_hash: str, role: str = "user", *, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Insert a new user into the database."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO users (username, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (username.lower(), email, password_hash, role),
        )


def get_user_by_username(username: str, *, db_path: Path = DEFAULT_DB_PATH) -> Optional[sqlite3.Row]:
    """Return a user row by username if it exists."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username.lower(),))
        return cursor.fetchone()


def get_pending_users(*, db_path: Path = DEFAULT_DB_PATH) -> Iterable[sqlite3.Row]:
    """Return an iterable of pending user registrations."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY username ASC")
        return cursor.fetchall()


def update_user_status(username: str, status: str, *, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Update the status of a user (pending/approved/rejected)."""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE users SET status = ? WHERE username = ?", (status, username.lower()))


def set_user_role(username: str, role: str, *, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Change a user's role."""
    with get_connection(db_path) as conn:
        conn.execute("UPDATE users SET role = ? WHERE username = ?", (role, username.lower()))


def ensure_admin_user(username: str, password_hash: str, email: str = "admin@example.com", *, db_path: Path = DEFAULT_DB_PATH) -> None:
    """Ensure that an admin user exists with the provided credentials.

    If the username already exists, its role is promoted to admin but the password is left unchanged.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username.lower(),))
        existing = cursor.fetchone()
        if existing:
            conn.execute("UPDATE users SET role = 'admin', status = 'approved' WHERE username = ?", (username.lower(),))
        else:
            conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role, status)
                VALUES (?, ?, ?, 'admin', 'approved')
                """,
                (username.lower(), email, password_hash),
            )


# Initialize database when the module is imported.
initialize_database()
