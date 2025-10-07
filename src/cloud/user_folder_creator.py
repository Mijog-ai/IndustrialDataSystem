"""Utility to create user folders on demand."""
from __future__ import annotations

from typing import Dict

from src.cloud.folder_manager import FolderManager


class UserFolderCreator:
    def __init__(self, manager: FolderManager | None = None) -> None:
        self.manager = manager or FolderManager()

    def ensure(self, user_id: str) -> Dict[str, str]:
        folders = self.manager.ensure_user_folders(user_id)
        return {name: str(path) for name, path in folders.items()}
