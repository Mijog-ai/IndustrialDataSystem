"""Generic helper functions."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict


def timestamp_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_user_structure(base: Path, user_id: str) -> Dict[str, Path]:
    user_root = base / "Users" / user_id
    folders = {
        "root": user_root,
        "csv": user_root / "CSV",
        "images": user_root / "Images",
        "excel": user_root / "Excel",
        "logs": user_root / "Logs",
    }
    for folder in folders.values():
        ensure_directory(folder)
    return folders
