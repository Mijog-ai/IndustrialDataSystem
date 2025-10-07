"""Basic Excel validation helpers."""
from __future__ import annotations

import pandas as pd


class ExcelValidator:
    def validate(self, df: pd.DataFrame) -> list[str]:
        errors: list[str] = []
        if df.empty:
            errors.append("Excel sheet is empty. Populate with at least one row before upload.")
        return errors
