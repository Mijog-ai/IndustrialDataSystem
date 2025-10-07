"""Abstraction layer for OneDrive operations."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from config.settings import DATA_DIR, load_app_config
from src.auth.admin_onedrive_auth import AdminOneDriveAuth
from src.utils.helpers import ensure_directory

logger = logging.getLogger(__name__)


class AdminOneDriveConnector:
    """Simplified connector storing files locally while mimicking OneDrive structure."""

    def __init__(self) -> None:
        self.config = load_app_config()
        self.auth = AdminOneDriveAuth()
        self.root = DATA_DIR / "mock_onedrive" / self.config.onedrive_root_folder
        ensure_directory(self.root)
        self._token: Optional[str] = None

    def ensure_authenticated(self) -> Optional[str]:
        if self._token:
            return self._token
        token = self.auth.acquire_token()
        if token:
            logger.info("Admin authenticated successfully.")
            self._token = token
        else:
            logger.warning("Running in offline mode without OneDrive token.")
        return self._token

    def base_path(self) -> Path:
        ensure_directory(self.root)
        return self.root
