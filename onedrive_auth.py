"""Helpers for acquiring an access token for Microsoft Graph."""
from __future__ import annotations

import os

import msal
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}" if TENANT_ID else None
SCOPE = ["https://graph.microsoft.com/.default"]


def _validate_settings() -> None:
    missing = [
        name
        for name, value in {
            "CLIENT_ID": CLIENT_ID,
            "TENANT_ID": TENANT_ID,
            "CLIENT_SECRET": CLIENT_SECRET,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing OneDrive configuration for: {', '.join(missing)}")


def get_access_token() -> str:
    _validate_settings()
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )
    result = app.acquire_token_silent(SCOPE, account=None)
    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" in result:
        return result["access_token"]
    raise RuntimeError(result.get("error_description"))
