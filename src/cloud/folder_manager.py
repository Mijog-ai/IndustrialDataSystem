"""Folder management utilities for OneDrive structure."""
from __future__ import annotations

from pathlib import Path, PurePath
from typing import Dict

from src.cloud.admin_onedrive_connector import AdminOneDriveConnector


class FolderManager:
    def __init__(self, connector: AdminOneDriveConnector | None = None) -> None:
        self.connector = connector or AdminOneDriveConnector()

    def ensure_user_folders(self, user_id: str) -> Dict[str, PurePath]:
        return self.connector.ensure_user_structure(user_id)

    def metadata_folder(self) -> Path:
        return self.connector.metadata_path()

    def templates_folder(self) -> Path:
        return self.connector.templates_path()
