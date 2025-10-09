"""Configuration helpers for the Industrial Data System applications."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


_ENV_LOCK = threading.Lock()
_ENV_INITIALISED = False


class ConfigError(RuntimeError):
    """Raised when configuration values cannot be resolved."""


def _load_environment() -> None:
    """Load environment variables from common locations once per process."""

    global _ENV_INITIALISED
    if _ENV_INITIALISED:
        return

    with _ENV_LOCK:
        if _ENV_INITIALISED:
            return

        candidate_paths = []
        script_directory = Path(__file__).resolve().parent
        candidate_paths.append(script_directory / ".env")
        candidate_paths.append(script_directory.parent / ".env")
        candidate_paths.append(script_directory.parent.parent / ".env")

        meipass_dir = getattr(os, "_MEIPASS", None)
        if meipass_dir:
            candidate_paths.append(Path(meipass_dir) / ".env")

        candidate_paths.append(Path.cwd() / ".env")

        for env_path in candidate_paths:
            if env_path.is_file():
                load_dotenv(env_path)
                break
        else:
            load_dotenv()

        _ENV_INITIALISED = True


def _normalise_path(value: Optional[str]) -> Optional[Path]:
    """Normalise environment path values across operating systems."""

    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    expanded = os.path.expandvars(value)
    if os.name != "nt":
        expanded = expanded.replace("\\\\", "/")
    path = Path(expanded).expanduser()
    return Path(os.path.normpath(str(path)))


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration loaded from the environment and filesystem."""

    shared_drive_path: Path
    database_path: Path
    files_base_path: Path
    storage_limit_mb: int

    def ensure_directories(self) -> None:
        """Create the folder structure required by the applications."""

        database_dir = self.database_path.parent
        files_dir = self.files_base_path
        tests_dir = files_dir / "tests"

        for directory in (database_dir, files_dir, tests_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigError(
                    f"Unable to create required directory '{directory}': {exc}"
                ) from exc

    def validate_paths(self) -> None:
        """Ensure the shared drive paths exist or are creatable."""

        for path in (self.shared_drive_path, self.files_base_path, self.database_path.parent):
            if not path.exists():
                try:
                    if path.suffix:
                        path.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        path.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    raise ConfigError(
                        f"Required path '{path}' is unavailable: {exc}"
                    ) from exc

    def resolve_file_path(self, *relative_parts: str) -> Path:
        """Resolve a relative path inside the shared files directory."""

        return (self.files_base_path.joinpath(*relative_parts)).resolve()

    def resolve_database_path(self) -> Path:
        """Return the absolute database path."""

        return self.database_path.resolve()


_CONFIG_SINGLETON: Optional[AppConfig] = None
_CONFIG_LOCK = threading.Lock()


def get_config() -> AppConfig:
    """Return an :class:`AppConfig` instance shared across the process."""

    global _CONFIG_SINGLETON
    if _CONFIG_SINGLETON is not None:
        return _CONFIG_SINGLETON

    with _CONFIG_LOCK:
        if _CONFIG_SINGLETON is not None:
            return _CONFIG_SINGLETON

        _load_environment()

        default_root = Path(__file__).resolve().parent / "data"
        default_root.mkdir(parents=True, exist_ok=True)

        shared_drive = _normalise_path(os.getenv("SHARED_DRIVE_PATH")) or default_root
        database_path = _normalise_path(os.getenv("DATABASE_PATH"))
        if database_path is None:
            database_path = shared_drive / "database" / "industrial_data.db"
        files_path = _normalise_path(os.getenv("FILES_BASE_PATH"))
        if files_path is None:
            files_path = shared_drive / "files"
        storage_limit_mb = int(os.getenv("STORAGE_LIMIT_MB", "10240"))

        config = AppConfig(
            shared_drive_path=shared_drive,
            database_path=Path(database_path),
            files_base_path=Path(files_path),
            storage_limit_mb=storage_limit_mb,
        )
        config.ensure_directories()
        config.validate_paths()
        _CONFIG_SINGLETON = config
        return config


__all__ = ["AppConfig", "ConfigError", "get_config"]
