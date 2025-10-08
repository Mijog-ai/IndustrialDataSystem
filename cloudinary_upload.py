"""Cloudinary upload helpers for Industrial Data System."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Union

import cloudinary
import cloudinary.api  # noqa: F401  # Imported to ensure API availability
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

_CONFIGURED = False


def configure_cloudinary() -> None:
    """Configure the Cloudinary SDK using environment variables."""

    global _CONFIGURED
    if _CONFIGURED:
        return

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    missing = [
        name
        for name, value in {
            "CLOUDINARY_CLOUD_NAME": cloud_name,
            "CLOUDINARY_API_KEY": api_key,
            "CLOUDINARY_API_SECRET": api_secret,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing Cloudinary configuration for: " + ", ".join(missing)
        )

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    _CONFIGURED = True


def upload_to_cloudinary(file_path: Union[str, Path], username: str) -> str:
    """Upload a file to Cloudinary and return the secure URL."""

    configure_cloudinary()

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(path)

    safe_username = username.replace("/", "_")
    result = cloudinary.uploader.upload(
        str(path),
        folder=f"IndustrialDataSystem/{safe_username}/",
        resource_type="auto",
    )

    url = result.get("secure_url")
    if not url:
        raise RuntimeError("Cloudinary response did not include a secure URL.")

    with open("upload_log.csv", "a", encoding="utf-8") as log:
        log.write(
            f"{datetime.utcnow().isoformat()},{safe_username},{path.name},{url}\n"
        )

    print(f"✅ Uploaded to Cloudinary: {url}")
    return url
