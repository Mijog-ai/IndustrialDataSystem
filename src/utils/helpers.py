"""Generic helper functions."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


def timestamp_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
