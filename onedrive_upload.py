"""Placeholder module retaining disabled OneDrive upload hooks."""
from __future__ import annotations

from pathlib import Path
from typing import Union


def upload_file_to_onedrive(local_path: Union[str, Path], username: str) -> None:
    """Raise an informative error while OneDrive uploads are disabled."""

    path = Path(local_path)
    if not path.exists():
        raise FileNotFoundError(path)

    raise RuntimeError(
        "OneDrive upload has been disabled. Please select the Cloudinary option instead."
    )
