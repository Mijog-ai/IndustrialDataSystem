"""Create Excel files from templates or blank sheets."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from src.excel.excel_templates import ExcelTemplateManager


class ExcelCreator:
    def __init__(self, template_manager: ExcelTemplateManager | None = None) -> None:
        self.template_manager = template_manager or ExcelTemplateManager()

    def create_from_template(self, template_filename: str, destination: Path) -> Path:
        template_path = self.template_manager.template_path(template_filename)
        if template_path.exists():
            df = pd.read_excel(template_path, engine="openpyxl")
        else:
            df = pd.DataFrame()
        df.to_excel(destination, index=False, engine="openpyxl")
        return destination

    def create_blank(self, destination: Path) -> Path:
        df = pd.DataFrame()
        df.to_excel(destination, index=False, engine="openpyxl")
        return destination
