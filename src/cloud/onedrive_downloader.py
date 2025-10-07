"""Download helper for Excel files."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.cloud.folder_manager import FolderManager


class OneDriveDownloader:
    def __init__(self, manager: FolderManager | None = None) -> None:
        self.manager = manager or FolderManager()

    def download_excel(self, user_id: str, filename: str) -> Optional[Path]:
        folders = self.manager.ensure_user_folders(user_id)
        target = folders["excel"] / filename
        connector = self.manager.connector

        if connector.is_cloud_mode:
            return connector.download_to_cache(target)

        local_path = Path(target)
        return local_path if local_path.exists() else None
