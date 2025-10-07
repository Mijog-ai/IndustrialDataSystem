"""Abstraction layer for OneDrive operations."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path, PurePath, PurePosixPath
from typing import Optional

import requests

from config.settings import DATA_DIR, load_app_config
from src.auth.admin_onedrive_auth import AdminOneDriveAuth
from src.utils.helpers import ensure_directory

logger = logging.getLogger(__name__)


class AdminOneDriveConnector:
    """Connector that supports both local mock and real OneDrive storage."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    GRAPH_TIMEOUT = 30

    def __init__(self) -> None:
        self.config = load_app_config()
        self.auth = AdminOneDriveAuth()
        self.mode = (self.config.onedrive_storage_mode or "local").strip().lower()
        if self.mode not in {"local", "cloud"}:
            logger.warning(
                "Unknown ONEDRIVE_STORAGE_MODE '%s'; falling back to local mode.",
                self.mode,
            )
            self.mode = "local"

        self.cache_root = DATA_DIR / "mock_onedrive" / self.config.onedrive_root_folder
        ensure_directory(self.cache_root)

        if self.is_cloud_mode:
            root_folder = (self.config.onedrive_root_folder or "IndustrialDataSystem").strip("/")
            self.drive_root: PurePath = PurePosixPath(root_folder) if root_folder else PurePosixPath("")
        else:
            self.drive_root = self.cache_root

        self.session = requests.Session()
        self._token: Optional[str] = None

    @property
    def is_cloud_mode(self) -> bool:
        return self.mode == "cloud"

    def ensure_authenticated(self) -> Optional[str]:
        if self._token:
            return self._token
        token = self.auth.acquire_token()
        if token:
            logger.info("Admin authenticated successfully.")
            self._token = token
        elif self.is_cloud_mode:
            logger.error("Cloud mode requested but authentication failed.")
        else:
            logger.warning("Running in offline mode without OneDrive token.")
        return self._token

    def base_path(self) -> Path:
        """Return the local cache base path used for metadata and offline storage."""

        ensure_directory(self.cache_root)
        return self.cache_root

    def drive_base_path(self) -> PurePath:
        """Return the logical root of the OneDrive structure."""

        return self.drive_root

    # ------------------------------------------------------------------
    # Folder helpers
    # ------------------------------------------------------------------
    def ensure_user_structure(self, user_id: str) -> dict[str, PurePath]:
        base = self.drive_base_path()
        user_root = base / "Users" / user_id
        folders: dict[str, PurePath] = {
            "root": user_root,
            "csv": user_root / "CSV",
            "images": user_root / "Images",
            "excel": user_root / "Excel",
            "logs": user_root / "Logs",
        }

        if self.is_cloud_mode:
            for folder in folders.values():
                self._ensure_remote_folder(folder)
        else:
            for folder in folders.values():
                ensure_directory(Path(folder))

        return folders

    def metadata_path(self) -> Path:
        return self.base_path() / "Metadata"

    def templates_path(self) -> Path:
        return self.base_path() / "Templates"

    # ------------------------------------------------------------------
    # Upload/download helpers for cloud mode
    # ------------------------------------------------------------------
    def upload_to_drive(
        self,
        target_path: PurePath,
        *,
        local_path: Path | None = None,
        data: bytes | None = None,
    ) -> dict:
        """Upload file bytes to the configured storage location."""

        if not self.is_cloud_mode:
            destination = Path(target_path)
            ensure_directory(destination.parent)
            if data is not None:
                destination.write_bytes(data)
            elif local_path is not None:
                shutil.copy2(local_path, destination)
            else:
                raise ValueError("Either local_path or data must be provided for upload.")
            return {"size": destination.stat().st_size, "local_path": str(destination)}

        if data is None:
            if local_path is None:
                raise ValueError("Either local_path or data must be provided for upload.")
            data = local_path.read_bytes()

        self._ensure_remote_folder(target_path.parent)
        response = self.session.put(
            self._drive_content_url(target_path),
            headers=self._graph_headers(content_type="application/octet-stream"),
            data=data,
            timeout=self.GRAPH_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        cache_path = self._write_cache(target_path, data)
        result["local_cache_path"] = str(cache_path)
        return result

    def download_to_cache(self, target_path: PurePath) -> Optional[Path]:
        if not self.is_cloud_mode:
            local_path = Path(target_path)
            return local_path if local_path.exists() else None

        cache_path = self._cache_path_for(target_path)
        if cache_path.exists():
            return cache_path

        response = self.session.get(
            self._drive_content_url(target_path),
            headers=self._graph_headers(),
            timeout=self.GRAPH_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        ensure_directory(cache_path.parent)
        cache_path.write_bytes(response.content)
        return cache_path

    def drive_relative_string(self, path: PurePath) -> str:
        return self.relative_to_drive_root(path).as_posix()

    def relative_to_drive_root(self, path: PurePath) -> PurePosixPath:
        base = self.drive_base_path()
        try:
            relative = path.relative_to(base)
        except ValueError:
            relative = path
        return PurePosixPath(relative.as_posix())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _drive_path_str(self, path: PurePath) -> str:
        return path.as_posix().lstrip("/")

    def _drive_item_url(self, path: PurePath) -> str:
        relative = self._drive_path_str(path)
        if relative:
            return f"{self.GRAPH_BASE_URL}/me/drive/root:/{relative}:"
        return f"{self.GRAPH_BASE_URL}/me/drive/root"

    def _drive_content_url(self, path: PurePath) -> str:
        relative = self._drive_path_str(path)
        if relative:
            return f"{self.GRAPH_BASE_URL}/me/drive/root:/{relative}:/content"
        return f"{self.GRAPH_BASE_URL}/me/drive/root/content"

    def _graph_headers(self, content_type: str | None = None) -> dict[str, str]:
        token = self.ensure_authenticated()
        if not token:
            raise RuntimeError("OneDrive authentication failed; cannot perform cloud operation.")
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _ensure_remote_folder(self, folder: PurePath) -> None:
        if not self.is_cloud_mode:
            return
        if str(folder) in {".", ""}:
            return
        # Ensure parent first
        parent = folder.parent
        if parent != folder:
            self._ensure_remote_folder(parent)

        response = self.session.get(
            self._drive_item_url(folder),
            headers=self._graph_headers(),
            timeout=self.GRAPH_TIMEOUT,
        )
        if response.status_code == 200:
            return
        if response.status_code != 404:
            response.raise_for_status()

        parent_url = (
            f"{self.GRAPH_BASE_URL}/me/drive/root/children"
            if folder.parent == folder or str(folder.parent) in {".", ""}
            else f"{self.GRAPH_BASE_URL}/me/drive/root:/{self._drive_path_str(folder.parent)}:/children"
        )
        create_response = self.session.post(
            parent_url,
            headers=self._graph_headers(content_type="application/json"),
            json={
                "name": folder.name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace",
            },
            timeout=self.GRAPH_TIMEOUT,
        )
        if create_response.status_code not in {200, 201}:
            create_response.raise_for_status()

    def _cache_path_for(self, path: PurePath) -> Path:
        relative = self.relative_to_drive_root(path)
        return self.base_path() / Path(relative.as_posix())

    def _write_cache(self, path: PurePath, data: bytes) -> Path:
        cache_path = self._cache_path_for(path)
        ensure_directory(cache_path.parent)
        cache_path.write_bytes(data)
        return cache_path
