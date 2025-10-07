"""Application configuration management for Industrial Data Upload System."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"


@dataclass(frozen=True)
class AppConfig:
    """Dataclass holding core configuration values for the application."""

    admin_client_id: str
    admin_tenant_id: str
    admin_redirect_uri: str
    onedrive_root_folder: str
    metadata_file_name: str
    user_activity_file_name: str
    default_user_quota_mb: int
    enable_quota_check: bool
    session_timeout_hours: int
    encryption_key: str
    log_level: str
    auto_create_user_folders: bool


def _env_flag(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_app_config() -> AppConfig:
    """Load application configuration from environment variables with defaults."""

    try:
        admin_auth_defaults = load_json_config("admin_auth_config.json")
    except FileNotFoundError:
        admin_auth_defaults = {}

    return AppConfig(
        admin_client_id=os.getenv(
            "ADMIN_CLIENT_ID", admin_auth_defaults.get("client_id", "")
        ),
        admin_tenant_id=os.getenv(
            "ADMIN_TENANT_ID", admin_auth_defaults.get("tenant_id", "")
        ),
        admin_redirect_uri=os.getenv(
            "ADMIN_REDIRECT_URI",
            admin_auth_defaults.get("redirect_uri", "http://localhost:8080"),
        ),
        onedrive_root_folder=os.getenv("ONEDRIVE_ROOT_FOLDER", "IndustrialDataSystem"),
        metadata_file_name=os.getenv("METADATA_FILE_NAME", "upload_metadata.xlsx"),
        user_activity_file_name=os.getenv("USER_ACTIVITY_FILE_NAME", "user_activity_log.xlsx"),
        default_user_quota_mb=int(os.getenv("DEFAULT_USER_QUOTA_MB", "5000")),
        enable_quota_check=_env_flag(os.getenv("ENABLE_QUOTA_CHECK"), True),
        session_timeout_hours=int(os.getenv("SESSION_TIMEOUT_HOURS", "8")),
        encryption_key=os.getenv("ENCRYPTION_KEY", "auto_generated_key"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        auto_create_user_folders=_env_flag(os.getenv("AUTO_CREATE_USER_FOLDERS"), True),
    )


def load_json_config(filename: str) -> Dict[str, Any]:
    """Load a JSON configuration file from the config directory."""

    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Configuration file {filename} not found in {CONFIG_DIR}.")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
