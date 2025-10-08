"""Database utilities using SQLAlchemy for Industrial Data System."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator, Iterable, Optional

from dotenv import load_dotenv
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, joinedload, mapped_column, relationship, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
ENGINE_ECHO = os.getenv("IDS_SQL_ECHO", "false").lower() == "true"

engine = create_engine(DATABASE_URL, echo=ENGINE_ECHO, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class UserModel(Base):
    """SQLAlchemy model representing an authenticated user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    reset_tokens: Mapped[list[PasswordResetTokenModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class PasswordResetTokenModel(Base):
    """Model storing hashed password reset tokens."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="reset_tokens")


def initialize_database() -> None:
    """Create all tables if they do not exist."""

    Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def add_user(
    username: str,
    email: str,
    password_hash: str,
    role: str = "user",
) -> None:
    """Insert a new user record."""

    with get_session() as session:
        session.add(
            UserModel(
                username=username.lower(),
                email=email.lower(),
                password_hash=password_hash,
                role=role,
            )
        )


def get_user_by_username(username: str) -> Optional[UserModel]:
    """Retrieve a user by username."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.username == username.lower())
        return session.scalar(stmt)


def get_user_by_email(email: str) -> Optional[UserModel]:
    """Retrieve a user by email."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.email == email.lower())
        return session.scalar(stmt)


def get_pending_users() -> Iterable[UserModel]:
    """Return all users whose accounts are pending approval."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.status == "pending").order_by(UserModel.username.asc())
        return list(session.scalars(stmt))


def update_user_status(username: str, status: str) -> None:
    """Update a user's status."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.username == username.lower())
        user = session.scalar(stmt)
        if user:
            user.status = status


def has_admin_user() -> bool:
    """Determine if an admin user already exists."""

    with get_session() as session:
        stmt = select(UserModel.id).where(UserModel.role == "admin").limit(1)
        return session.scalar(stmt) is not None


def ensure_admin_user(username: str, password_hash: str, email: str = "admin@example.com") -> None:
    """Ensure an admin user exists or promote an existing user."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.username == username.lower())
        user = session.scalar(stmt)
        if user:
            user.role = "admin"
            user.status = "approved"
        else:
            session.add(
                UserModel(
                    username=username.lower(),
                    email=email.lower(),
                    password_hash=password_hash,
                    role="admin",
                    status="approved",
                )
            )


def set_user_role(username: str, role: str) -> None:
    """Set the role for a given user."""

    with get_session() as session:
        stmt = select(UserModel).where(UserModel.username == username.lower())
        user = session.scalar(stmt)
        if user:
            user.role = role


def create_reset_token(user: UserModel, token_hash: str, ttl_minutes: int) -> PasswordResetTokenModel:
    """Persist a password reset token for the user."""

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    with get_session() as session:
        user_in_session = session.merge(user)
        reset_token = PasswordResetTokenModel(
            user=user_in_session, token_hash=token_hash, expires_at=expires_at
        )
        session.add(reset_token)
        session.flush()
        session.refresh(reset_token)
        session.expunge(reset_token)
        return reset_token


def get_reset_token_by_hash(token_hash: str) -> Optional[PasswordResetTokenModel]:
    """Return a password reset token by its hash."""

    with get_session() as session:
        stmt = (
            select(PasswordResetTokenModel)
            .options(joinedload(PasswordResetTokenModel.user))
            .where(PasswordResetTokenModel.token_hash == token_hash)
        )
        token = session.scalar(stmt)
        if token:
            session.expunge(token)
        return token


def mark_token_used(token_id: int) -> None:
    """Mark a password reset token as used."""

    with get_session() as session:
        stmt = select(PasswordResetTokenModel).where(PasswordResetTokenModel.id == token_id)
        token = session.scalar(stmt)
        if token:
            token.used = True


def update_user_password(user: UserModel, password_hash: str) -> None:
    """Update the stored password hash for a user."""

    with get_session() as session:
        user_in_session = session.merge(user)
        user_in_session.password_hash = password_hash


# Initialize tables when module is imported.
initialize_database()
