"""Authentication helpers for the Industrial Data System application."""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass
from typing import List

import bcrypt

from database import (
    add_user,
    ensure_admin_user,
    get_pending_users,
    get_user_by_username,
    has_admin_user,
    update_user_status,
)


class AuthError(Exception):
    """Base class for authentication errors."""


class RegistrationError(AuthError):
    """Raised when a registration attempt fails."""


class LoginError(AuthError):
    """Raised when login fails."""


@dataclass
class User:
    username: str
    email: str
    role: str
    status: str


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def normalize_username(username: str) -> str:
    username = username.strip().lower()
    if not username:
        raise RegistrationError("Username cannot be empty")
    return username


def register_user(username: str, email: str, password: str) -> None:
    username = normalize_username(username)
    email = email.strip()
    if not email:
        raise RegistrationError("Email cannot be empty")
    if get_user_by_username(username):
        raise RegistrationError("Username already exists")
    password_hash = hash_password(password)
    add_user(username=username, email=email, password_hash=password_hash)


def authenticate_user(username: str, password: str) -> User:
    username = normalize_username(username)
    record = get_user_by_username(username)
    if not record:
        raise LoginError("Invalid username or password")
    if not verify_password(password, record["password_hash"]):
        raise LoginError("Invalid username or password")
    return User(
        username=record["username"],
        email=record["email"],
        role=record["role"],
        status=record["status"],
    )


def list_pending_users() -> List[User]:
    return [
        User(username=row["username"], email=row["email"], role=row["role"], status=row["status"])
        for row in get_pending_users()
    ]


def approve_user(username: str) -> None:
    update_user_status(normalize_username(username), "approved")


def reject_user(username: str) -> None:
    update_user_status(normalize_username(username), "rejected")


def bootstrap_default_admin() -> None:
    """Create an admin user from environment variables if configured."""
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")

    if admin_username and admin_password:
        hashed = hash_password(admin_password)
        ensure_admin_user(admin_username, hashed, email=admin_email)
        return

    if has_admin_user():
        return

    default_username = os.getenv("IDS_DEFAULT_ADMIN_USERNAME", "admin")
    default_password = os.getenv("IDS_DEFAULT_ADMIN_PASSWORD", "admin123")
    hashed = hash_password(default_password)
    ensure_admin_user(default_username, hashed, email=admin_email)
    warnings.warn(
        "No admin credentials were configured. A default admin account "
        f"('{default_username}' / '{default_password}') was created. "
        "Update the credentials by setting ADMIN_USERNAME and "
        "ADMIN_PASSWORD environment variables.",
        RuntimeWarning,
        stacklevel=2,
    )

# Automatically bootstrap an admin if environment variables are provided.
bootstrap_default_admin()
