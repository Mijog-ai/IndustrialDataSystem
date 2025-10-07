"""User management logic."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import bcrypt

from config.settings import CONFIG_DIR, load_app_config


@dataclass
class User:
    user_id: str
    name: str
    password_hash: str
    quota_mb: int

    def verify_password(self, password: str | None) -> bool:
        if not self.password_hash:
            return True  # passwordless user
        if password is None:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))


class UserManager:
    """Loads and validates users from the local registry."""

    def __init__(self, db_file: Path | None = None) -> None:
        self.db_file = db_file or CONFIG_DIR / "users_db.json"
        self._users: Dict[str, User] = {}
        self._load()

    def _load(self) -> None:
        if not self.db_file.exists():
            raise FileNotFoundError("User database not found.")
        data = json.loads(self.db_file.read_text(encoding="utf-8"))
        for entry in data.get("users", []):
            user = User(
                user_id=entry["user_id"],
                name=entry.get("name", entry["user_id"]),
                password_hash=entry.get("password_hash", ""),
                quota_mb=int(entry.get("quota_mb", load_app_config().default_user_quota_mb)),
            )
            self._users[user.user_id] = user

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def authenticate(self, user_id: str, password: str | None = None) -> Optional[User]:
        user = self.get_user(user_id)
        if not user:
            return None
        if not user.verify_password(password):
            return None
        return user
