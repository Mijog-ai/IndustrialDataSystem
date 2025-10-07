"""Session management for logged in users."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR, load_app_config

SESSION_FILE = DATA_DIR / "sessions" / "active_sessions.json"
SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)


class SessionManager:
    def __init__(self) -> None:
        self.config = load_app_config()

    def _load_sessions(self) -> dict:
        if not SESSION_FILE.exists():
            return {}
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))

    def _save_sessions(self, sessions: dict) -> None:
        SESSION_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")

    def create_session(self, user_id: str) -> dict:
        sessions = self._load_sessions()
        expiry = (datetime.utcnow() + timedelta(hours=self.config.session_timeout_hours)).isoformat()
        sessions[user_id] = {"created": datetime.utcnow().isoformat(), "expires": expiry}
        self._save_sessions(sessions)
        return sessions[user_id]

    def is_session_active(self, user_id: str) -> bool:
        sessions = self._load_sessions()
        data = sessions.get(user_id)
        if not data:
            return False
        expires = datetime.fromisoformat(data["expires"])
        if datetime.utcnow() > expires:
            sessions.pop(user_id, None)
            self._save_sessions(sessions)
            return False
        return True

    def purge_expired(self) -> None:
        sessions = self._load_sessions()
        changed = False
        now = datetime.utcnow()
        for key, data in list(sessions.items()):
            if datetime.fromisoformat(data["expires"]) < now:
                sessions.pop(key, None)
                changed = True
        if changed:
            self._save_sessions(sessions)
