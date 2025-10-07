"""File validation utilities."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

ALLOWED_IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}
ALLOWED_CSV_EXTENSIONS: set[str] = {".csv"}
ALLOWED_EXCEL_EXTENSIONS: set[str] = {".xlsx", ".xlsm"}


def is_allowed_file(path: Path, extensions: Iterable[str]) -> bool:
    return path.suffix.lower() in {ext.lower() for ext in extensions}


def validate_file_type(path: Path) -> str:
    """Validate the file type and return a category string."""

    suffix = path.suffix.lower()
    if suffix in ALLOWED_CSV_EXTENSIONS:
        return "CSV"
    if suffix in ALLOWED_IMAGE_EXTENSIONS:
        return "Image"
    if suffix in ALLOWED_EXCEL_EXTENSIONS:
        return "Excel"
    raise ValueError(f"Unsupported file type: {suffix}")


def human_readable_size(path: Path) -> float:
    return round(path.stat().st_size / 1024.0, 2)
