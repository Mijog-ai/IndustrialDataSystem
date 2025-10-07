"""High level Excel editing helpers using pandas."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class ExcelEditor:
    def load(self, path: Path) -> pd.DataFrame:
        if path.exists():
            return pd.read_excel(path, engine="openpyxl")
        return pd.DataFrame()

    def save(self, path: Path, dataframe: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_excel(path, index=False, engine="openpyxl")

    def add_row(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        return pd.concat([dataframe, pd.DataFrame([{}])], ignore_index=True)

    def delete_row(self, dataframe: pd.DataFrame, index: int) -> pd.DataFrame:
        if 0 <= index < len(dataframe):
            dataframe = dataframe.drop(index).reset_index(drop=True)
        return dataframe
