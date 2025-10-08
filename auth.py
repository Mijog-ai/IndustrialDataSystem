"""Authentication helpers for the Industrial Data System application."""
from __future__ import annotations

import hashlib
import os
import secrets
import smtplib
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import List, Optional

import bcrypt
import jwt

from database import (
    UserModel,
    add_user,
    create_reset_token,
    ensure_admin_user,
    get_pending_users,
    get_reset_token_by_hash,
    get_user_by_email,
    get_user_by_username,
    has_admin_user,
    mark_token_used,
    update_user_password,
    update_user_status,
)


class AuthError(Exception):
    """Base class for authentication errors."""


class RegistrationError(AuthError):
    """Raised when a registration attempt fails."""


class LoginError(AuthError):
    """Raised when login fails."""


class SessionError(AuthError):
    """Raised when a JWT session token cannot be validated."""


class PasswordResetError(AuthError):
    """Raised for password reset workflow issues."""


@dataclass
class User:
    id: int
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
    if get_user_by_email(email):
        raise RegistrationError("Email already registered")
    password_hash = hash_password(password)
    add_user(username=username, email=email, password_hash=password_hash)


def authenticate_user(username: str, password: str) -> User:
    username = normalize_username(username)
    record = get_user_by_username(username)
    if not record:
        raise LoginError("Invalid username or password")
    if not verify_password(password, record.password_hash):
        raise LoginError("Invalid username or password")
    return _user_from_model(record)


def list_pending_users() -> List[User]:
    return [
        _user_from_model(row)
        for row in get_pending_users()
    ]


def approve_user(username: str) -> None:
    update_user_status(normalize_username(username), "approved")


def reject_user(username: str) -> None:
    update_user_status(normalize_username(username), "rejected")


def create_session_token(user: User) -> str:
    """Generate a JWT for the authenticated user."""

    secret = os.getenv("IDS_JWT_SECRET")
    if not secret:
        raise SessionError("Missing IDS_JWT_SECRET environment variable.")

    ttl_minutes = int(os.getenv("IDS_SESSION_TTL_MINUTES", "60"))
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        "iat": datetime.now(timezone.utc),
    }
    algorithm = os.getenv("IDS_JWT_ALGORITHM", "HS256")
    return jwt.encode(payload, secret, algorithm=algorithm)


def validate_session_token(token: str) -> dict:
    """Validate a JWT session token and return its payload."""

    secret = os.getenv("IDS_JWT_SECRET")
    if not secret:
        raise SessionError("Missing IDS_JWT_SECRET environment variable.")

    algorithm = os.getenv("IDS_JWT_ALGORITHM", "HS256")
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - environment dependent
        raise SessionError("Session token has expired. Please log in again.") from exc
    except jwt.PyJWTError as exc:  # pragma: no cover - invalid token edge cases
        raise SessionError("Invalid session token.") from exc


def request_password_reset(email: str) -> Optional[str]:
    """Create a password reset token and dispatch it via email.

    Returns the raw token string when email delivery is not configured so that
    developers can complete the flow manually. Otherwise returns ``None``.
    """

    email = email.strip().lower()
    if not email:
        raise PasswordResetError("Email address is required.")

    user = get_user_by_email(email)
    if not user:
        # Intentionally do not disclose that the account is missing.
        return None

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_reset_token(raw_token)
    ttl_minutes = int(os.getenv("IDS_RESET_TOKEN_TTL_MINUTES", "30"))
    create_reset_token(user, token_hash, ttl_minutes)

    email_sent = _send_password_reset_email(email, raw_token)
    return None if email_sent else raw_token


def reset_password(token: str, new_password: str) -> None:
    """Reset a user's password if the provided token is valid."""

    if not token:
        raise PasswordResetError("A reset token is required.")
    if not new_password:
        raise PasswordResetError("New password must not be empty.")

    token_hash = _hash_reset_token(token)
    reset_record = get_reset_token_by_hash(token_hash)
    if not reset_record or reset_record.used:
        raise PasswordResetError("Invalid or already used password reset token.")

    if reset_record.expires_at < datetime.now(timezone.utc):
        raise PasswordResetError("Password reset token has expired.")

    user = reset_record.user
    password_hash = hash_password(new_password)
    update_user_password(user, password_hash)
    mark_token_used(reset_record.id)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_password_reset_email(recipient: str, token: str) -> bool:
    host = os.getenv("SMTP_HOST")
    if not host:
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    sender = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@example.com")

    message = EmailMessage()
    message["Subject"] = "Industrial Data System Password Reset"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        (
            "You requested a password reset for the Industrial Data System application.\n\n"
            f"Use the following token within the next {os.getenv('IDS_RESET_TOKEN_TTL_MINUTES', '30')} minutes:\n"
            f"{token}\n\n"
            "If you did not request this change you can ignore this email."
        )
    )

    try:
        if use_tls:
            with smtplib.SMTP(host, port) as smtp:
                smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port) as smtp:
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(message)
    except Exception:  # pragma: no cover - network dependent
        return False
    return True


def _user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        username=model.username,
        email=model.email,
        role=model.role,
        status=model.status,
    )


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
