"""Folder management utilities for OneDrive structure."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.cloud.admin_onedrive_connector import AdminOneDriveConnector
from src.utils.helpers import build_user_structure


class FolderManager:
    def __init__(self, connector: AdminOneDriveConnector | None = None) -> None:
        self.connector = connector or AdminOneDriveConnector()

    def ensure_user_folders(self, user_id: str) -> Dict[str, Path]:
        base = self.connector.base_path()
        return build_user_structure(base, user_id)

    def metadata_folder(self) -> Path:
        base = self.connector.base_path()
        return base / "Metadata"

    def templates_folder(self) -> Path:
        base = self.connector.base_path()
        return base / "Templates"
