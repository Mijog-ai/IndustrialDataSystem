"""Upload CSV files to OneDrive using Microsoft Graph."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

import requests

from onedrive_auth import get_access_token

APP_FOLDER = os.getenv("ONEDRIVE_APP_FOLDER", "IndustrialDataSystem")


def _build_upload_url(filename: str, username: str) -> str:
    safe_username = username.replace("/", "_")
    return (
        "https://graph.microsoft.com/v1.0/me/drive/root:/"
        f"Apps/{APP_FOLDER}/Users/{safe_username}/{filename}:/content"
    )


def upload_file_to_onedrive(local_path: Union[str, Path], username: str) -> None:
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(path)
    token = get_access_token()
    upload_url = _build_upload_url(path.name, username)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "text/csv"}
    with path.open("rb") as handle:
        response = requests.put(upload_url, headers=headers, data=handle)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed: {response.status_code} {response.text}")
