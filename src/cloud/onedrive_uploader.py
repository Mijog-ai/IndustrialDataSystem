"""Handles uploading files to OneDrive storage."""
from __future__ import annotations

import shutil
from pathlib import Path

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
        connector = self.manager.connector

        if connector.is_cloud_mode:
            destination = target_dir / local_path.name
            upload_result = connector.upload_to_drive(destination, local_path=local_path)
            size_bytes = upload_result.get("size", local_path.stat().st_size)
            return {
                "user_id": user_id,
                "file_type": file_type,
                "file_name": local_path.name,
                "size_kb": round(size_bytes / 1024.0, 2),
                "uploaded_at": timestamp_now(),
                "onedrive_path": connector.drive_relative_string(destination),
                "onedrive_url": upload_result.get("webUrl", ""),
                "notes": notes,
            }

        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        destination = target_path / local_path.name
        shutil.copy2(local_path, destination)
        return {
            "user_id": user_id,
            "file_type": file_type,
            "file_name": local_path.name,
            "size_kb": round(destination.stat().st_size / 1024.0, 2),
            "uploaded_at": timestamp_now(),
            "onedrive_path": str(destination.relative_to(connector.base_path())),
            "onedrive_url": "",
            "notes": notes,
        }

    def upload_bytes(self, user_id: str, filename: str, content: bytes) -> dict:
        folders = self.manager.ensure_user_folders(user_id)
        destination = folders["excel"] / filename
        connector = self.manager.connector

        if connector.is_cloud_mode:
            upload_result = connector.upload_to_drive(destination, data=content)
            size_bytes = upload_result.get("size", len(content))
            return {
                "user_id": user_id,
                "file_type": "Excel",
                "file_name": filename,
                "size_kb": round(size_bytes / 1024.0, 2),
                "uploaded_at": timestamp_now(),
                "onedrive_path": connector.drive_relative_string(destination),
                "onedrive_url": upload_result.get("webUrl", ""),
            }

        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
        return {
            "user_id": user_id,
            "file_type": "Excel",
            "file_name": filename,
            "size_kb": round(len(content) / 1024.0, 2),
            "uploaded_at": timestamp_now(),
            "onedrive_path": str(target_path.relative_to(connector.base_path())),
            "onedrive_url": "",
        }
