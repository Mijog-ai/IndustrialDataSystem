"""Upload CSV files to OneDrive using Microsoft Graph."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Union

import requests

from onedrive_auth import get_access_token


def upload_to_onedrive(file_path: Union[str, Path], username: str, access_token: str) -> None:
    """Upload ``file_path`` to the admin's OneDrive under the user folder."""

    user_email = os.getenv("ONEDRIVE_USER_EMAIL")
    upload_root = os.getenv("ONEDRIVE_UPLOAD_ROOT", "Uploads")

    if not user_email:
        raise ValueError("Missing ONEDRIVE_USER_EMAIL in .env")

    path = Path(file_path)
    file_name = path.name
    safe_username = username.replace("/", "_")
    upload_path = f"{upload_root}/{safe_username}/{file_name}"

    upload_url = (
        "https://graph.microsoft.com/v1.0/users/"
        f"{user_email}/drive/root:/{upload_path}:/content"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }

    with path.open("rb") as handle:
        response = requests.put(upload_url, headers=headers, data=handle)

    if response.status_code in (200, 201):
        print(f"✅ Uploaded '{file_name}' for user '{username}'")
        return

    print(f"❌ Upload failed: {response.status_code} {response.text}")
    raise RuntimeError(f"Upload failed: {response.status_code} {response.text}")


def upload_file_to_onedrive(local_path: Union[str, Path], username: str) -> None:
    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(path)

    token = get_access_token()
    upload_to_onedrive(path, username, token)
