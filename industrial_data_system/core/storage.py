"""Local file storage management for the shared drive."""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from industrial_data_system.core.config import AppConfig, get_config
from industrial_data_system.core.db_manager import DatabaseManager


class StorageError(RuntimeError):
    """Raised when file operations cannot be completed."""


@dataclass
class StoredFile:
    """Represents a file stored on the shared drive."""

    absolute_path: Path
    relative_path: Path
    test_type: str
    size_bytes: int

    def as_uri(self) -> str:
        return self.absolute_path.as_uri()


class LocalStorageManager:
    """Manage interactions with the shared drive file system."""

    def __init__(
        self,
        *,
        config: Optional[AppConfig] = None,
        database: Optional[DatabaseManager] = None,
    ) -> None:
        self.config = config or get_config()
        self.database = database or DatabaseManager()
        self.base_path = self.config.files_base_path
        self.config.ensure_directories()
        self._last_drive_state: bool = self.base_path.exists()

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _resolve(self, path: Path | str) -> Path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.base_path / candidate
        return candidate

    def ensure_folder_exists(self, test_type: str) -> Path:
        if not self.ensure_drive_available():
            raise StorageError("Shared drive is not accessible.")
        folder = self.base_path / "tests" / test_type
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"Unable to create folder for '{test_type}': {exc}") from exc
        return folder

    def _unique_destination(self, destination: Path) -> Path:
        if not destination.exists():
            return destination
        stem = destination.stem
        suffix = destination.suffix
        counter = 1
        while True:
            candidate = destination.with_name(f"{stem}_{int(time.time())}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _validate_extension(self, filename: str) -> None:
        allowed = {".csv", ".xlsx", ".xlsm", ".xltx", ".xltm"}
        if Path(filename).suffix.lower() not in allowed:
            raise StorageError(
                f"Unsupported file extension for '{filename}'. Allowed types: {', '.join(sorted(allowed))}."
            )

    def check_storage_limit(self, additional_bytes: int = 0) -> None:
        limit_bytes = self.config.storage_limit_mb * 1024 * 1024
        current_usage = self.database.get_storage_usage()
        if current_usage + additional_bytes > limit_bytes:
            raise StorageError(
                "Storage limit reached on the shared drive. Please archive older files before uploading new ones."
            )

    def is_drive_available(self) -> bool:
        available = self.base_path.exists()
        self._last_drive_state = available
        return available

    def ensure_drive_available(self, retries: int = 3, delay: float = 1.0) -> bool:
        if self.is_drive_available():
            return True
        for attempt in range(retries):
            time.sleep(delay * (attempt + 1))
            if self.is_drive_available():
                return True
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upload_file(self, source_path: Path | str, test_type: str, filename: Optional[str] = None) -> StoredFile:
        source = Path(source_path)
        if not source.is_file():
            raise StorageError(f"Source file '{source}' does not exist.")

        if not self.ensure_drive_available():
            raise StorageError("Shared drive is not accessible. Please reconnect and try again.")

        self._validate_extension(source.name if filename is None else filename)
        destination_folder = self.ensure_folder_exists(test_type)
        destination_name = filename or source.name
        destination = destination_folder / destination_name
        destination = self._unique_destination(destination)

        file_size = source.stat().st_size
        self.check_storage_limit(file_size)

        try:
            shutil.copy2(source, destination)
        except OSError as exc:
            raise StorageError(f"Failed to copy file to shared drive: {exc}") from exc

        relative_path = destination.relative_to(self.base_path)
        return StoredFile(
            absolute_path=destination,
            relative_path=relative_path,
            test_type=test_type,
            size_bytes=file_size,
        )

    def delete_file(self, file_path: Path | str) -> None:
        target = self._resolve(file_path)
        if not target.exists():
            return
        try:
            target.unlink()
        except OSError as exc:
            raise StorageError(f"Unable to delete file '{target}': {exc}") from exc

    def get_file_path(self, test_type: str, filename: str) -> Path:
        folder = self.ensure_folder_exists(test_type)
        return folder / filename

    def list_files(self, test_type: Optional[str] = None) -> List[StoredFile]:
        if not self.ensure_drive_available():
            return []
        base = self.base_path / "tests"
        if test_type:
            base = base / test_type
            if not base.exists():
                return []
        stored: List[StoredFile] = []
        for path in base.rglob("*"):
            if path.is_file():
                relative = path.relative_to(self.base_path)
                stored.append(
                    StoredFile(
                        absolute_path=path,
                        relative_path=relative,
                        test_type=relative.parts[1] if len(relative.parts) > 1 else test_type or "",
                        size_bytes=path.stat().st_size,
                    )
                )
        return stored

    def get_file_url(self, file_path: Path | str) -> str:
        return self._resolve(file_path).as_uri()


__all__ = ["LocalStorageManager", "StorageError", "StoredFile"]
