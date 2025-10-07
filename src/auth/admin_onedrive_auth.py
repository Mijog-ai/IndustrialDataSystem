"""Handles admin authentication with Microsoft Graph via MSAL."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import msal

from config.settings import CONFIG_DIR, load_app_config
from src.utils.encryption import read_encrypted_payload, store_encrypted_payload

logger = logging.getLogger(__name__)

TOKEN_NAME = "admin_token"


class AdminOneDriveAuth:
    def __init__(self) -> None:
        self.config = load_app_config()
        self.msal_config = self._load_msal_config()

    def _load_msal_config(self) -> dict:
        path = CONFIG_DIR / "admin_auth_config.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_app(self) -> msal.PublicClientApplication:
        return msal.PublicClientApplication(
            client_id=self.config.admin_client_id,
            authority=self.msal_config.get("authority"),
        )

    def acquire_token(self, force_refresh: bool = False) -> Optional[str]:
        cached = None if force_refresh else read_encrypted_payload(TOKEN_NAME)
        if cached:
            logger.debug("Using cached admin token.")
            return cached

        if not self.config.admin_client_id:
            logger.warning("Admin client ID not configured; returning None token.")
            return None

        app = self._build_app()
        flow = app.initiate_device_flow(scopes=self.msal_config.get("scopes", []))
        if "user_code" not in flow:
            logger.error("Failed to create device flow: %s", flow)
            return None

        logger.info("Visit %s and enter the code %s to authenticate.", flow["verification_uri"], flow["user_code"])

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" in result:
            token = result["access_token"]
            store_encrypted_payload(TOKEN_NAME, token)
            return token
        logger.error("Failed to acquire token: %s", result)
        return None
