"""Handles Excel template discovery and loading."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from config.settings import CONFIG_DIR, TEMPLATES_DIR


class ExcelTemplateManager:
    def __init__(self) -> None:
        self.templates_config = self._load_config()

    def _load_config(self) -> Dict:
        path = CONFIG_DIR / "excel_templates.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_templates(self) -> List[dict]:
        return list(self.templates_config.get("templates", []))

    def default_template(self) -> str:
        return self.templates_config.get("default_template", "blank_template.xlsx")

    def template_path(self, filename: str) -> Path:
        local_path = TEMPLATES_DIR / filename
        if local_path.exists():
            return local_path
        # fallback to base config folder for shipped templates
        return CONFIG_DIR / filename
