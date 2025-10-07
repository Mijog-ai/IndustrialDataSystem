"""Handles read/write of the metadata Excel workbook."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict

import pandas as pd

from config.settings import load_app_config
from src.cloud.folder_manager import FolderManager
from src.metadata.metadata_schema import COLUMNS
from src.utils.helpers import timestamp_now


class MetadataExcelHandler:
    def __init__(self, manager: FolderManager | None = None) -> None:
        self.manager = manager or FolderManager()
        self.config = load_app_config()

    def _metadata_path(self) -> Path:
        folder = self.manager.metadata_folder()
        folder.mkdir(parents=True, exist_ok=True)
        return folder / self.config.metadata_file_name

    def _read_existing(self) -> pd.DataFrame:
        path = self._metadata_path()
        if path.exists():
            return pd.read_excel(path, engine="openpyxl")
        return pd.DataFrame(columns=COLUMNS)

    def append_entry(self, data: Dict[str, str]) -> None:
        df = self._read_existing()
        entry = {column: data.get(column, "") for column in COLUMNS}
        if not entry.get("Upload_ID"):
            entry["Upload_ID"] = str(uuid.uuid4())
        if not entry.get("Upload_Timestamp"):
            entry["Upload_Timestamp"] = timestamp_now()
        df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        df.to_excel(self._metadata_path(), index=False, engine="openpyxl")
