"""Handles uploading files to the admin OneDrive (local mock)."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from src.cloud.folder_manager import FolderManager
from src.utils.file_validator import validate_file_type
from src.utils.helpers import timestamp_now


class OneDriveUploader:
    def __init__(self, manager: FolderManager | None = None) -> None:
        self.manager = manager or FolderManager()

    def upload_file(self, user_id: str, local_path: Path, notes: str = "") -> dict:
        file_type = validate_file_type(local_path)
        folders = self.manager.ensure_user_folders(user_id)
        target_dir = {
            "CSV": folders["csv"],
            "Image": folders["images"],
            "Excel": folders["excel"],
        }[file_type]
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = target_dir / local_path.name
        shutil.copy2(local_path, destination)
        return {
            "user_id": user_id,
            "file_type": file_type,
            "file_name": local_path.name,
            "size_kb": round(destination.stat().st_size / 1024.0, 2),
            "uploaded_at": timestamp_now(),
            "onedrive_path": str(destination.relative_to(self.manager.connector.base_path())),
            "notes": notes,
        }

    def upload_bytes(self, user_id: str, filename: str, content: bytes) -> dict:
        folders = self.manager.ensure_user_folders(user_id)
        destination = folders["excel"] / filename
        destination.write_bytes(content)
        return {
            "user_id": user_id,
            "file_type": "Excel",
            "file_name": filename,
            "size_kb": round(len(content) / 1024.0, 2),
            "uploaded_at": timestamp_now(),
            "onedrive_path": str(destination.relative_to(self.manager.connector.base_path())),
        }
