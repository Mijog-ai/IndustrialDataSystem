"""Utility for applying simple formatting to Excel DataFrames."""
from __future__ import annotations

import pandas as pd


class ExcelFormatter:
    def auto_fill_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            df = pd.DataFrame({"Column1": [""], "Column2": [""]})
        return df
