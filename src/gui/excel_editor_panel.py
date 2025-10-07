"""Panel providing Excel editing capabilities."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path

import pandas as pd

from src.cloud.onedrive_downloader import OneDriveDownloader
from src.cloud.onedrive_uploader import OneDriveUploader
from src.excel.excel_creator import ExcelCreator
from src.excel.excel_editor import ExcelEditor
from src.excel.excel_templates import ExcelTemplateManager
from src.excel.excel_validator import ExcelValidator
from src.gui.data_grid import DataGrid
from src.metadata.excel_handler import MetadataExcelHandler
from src.utils.helpers import timestamp_now


class ExcelEditorPanel(ttk.Frame):
    def __init__(self, master: tk.Widget, user_context: dict, status_callback) -> None:
        super().__init__(master)
        self.user_context = user_context
        self.status_callback = status_callback
        self.template_manager = ExcelTemplateManager()
        self.creator = ExcelCreator(self.template_manager)
        self.editor = ExcelEditor()
        self.validator = ExcelValidator()
        self.downloader = OneDriveDownloader()
        self.uploader = OneDriveUploader()
        self.metadata_handler = MetadataExcelHandler()
        self.current_path: Path | None = None
        self.df = pd.DataFrame()
        self._build_ui()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, pady=5)

        ttk.Button(controls, text="Load Template", command=self.load_template).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Open Existing", command=self.open_existing).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Add Row", command=self.add_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Delete Row", command=self.delete_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Save Local", command=self.save_local).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Upload to OneDrive", command=self.upload_onedrive).pack(side=tk.LEFT, padx=5)

        self.grid = DataGrid(self, dataframe=self.df)
        self.grid.pack(fill=tk.BOTH, expand=True)

    def load_template(self) -> None:
        options = self.template_manager.list_templates()
        if not options:
            messagebox.showwarning("Templates", "No templates configured.")
            return
        template_names = [template["name"] for template in options]
        selection = simpledialog.askstring("Template", f"Enter template name:\n{', '.join(template_names)}")
        if not selection:
            return
        match = next((tpl for tpl in options if tpl["name"].lower() == selection.lower()), None)
        if not match:
            messagebox.showerror("Template", "Template not found.")
            return
        temp_path = Path("data/temp_excel") / f"{match['filename']}"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        self.creator.create_from_template(match["filename"], temp_path)
        self.current_path = temp_path
        self.df = self.editor.load(temp_path)
        self.grid.set_dataframe(self.df)
        self.status_callback(f"Loaded template {match['name']}")

    def open_existing(self) -> None:
        filename = filedialog.askopenfilename(title="Open Excel", filetypes=[("Excel", "*.xlsx *.xlsm")])
        if filename:
            self.current_path = Path(filename)
            self.df = self.editor.load(self.current_path)
            self.grid.set_dataframe(self.df)
            self.status_callback(f"Opened {self.current_path.name}")

    def add_row(self) -> None:
        self.df = self.editor.add_row(self.grid.dataframe)
        self.grid.set_dataframe(self.df)

    def delete_row(self) -> None:
        selection = self.grid.tree.selection()
        if not selection:
            messagebox.showinfo("Delete Row", "Select a row to delete.")
            return
        index = int(selection[0])
        self.df = self.editor.delete_row(self.grid.dataframe, index)
        self.grid.set_dataframe(self.df)

    def save_local(self) -> None:
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not filename:
            return
        self.editor.save(Path(filename), self.grid.dataframe)
        self.status_callback(f"Saved Excel locally to {filename}")

    def upload_onedrive(self) -> None:
        df = self.grid.dataframe
        errors = self.validator.validate(df)
        if errors:
            messagebox.showerror("Validation", "\n".join(errors))
            return
        temp_path = Path("data/temp_excel") / f"{self.user_context['user_id']}_edit.xlsx"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        self.editor.save(temp_path, df)
        record = self.uploader.upload_file(self.user_context["user_id"], temp_path)
        metadata = {
            "User_ID": self.user_context["user_id"],
            "User_Name": self.user_context.get("name", self.user_context["user_id"]),
            "File_Name": record["file_name"],
            "File_Type": record["file_type"],
            "File_Size_KB": record["size_kb"],
            "Creation_Method": "Excel_Editor",
            "Excel_Template_Used": self.current_path.name if self.current_path else "Custom",
            "Edit_Count": len(df),
            "Last_Edit_Date": timestamp_now(),
            "OneDrive_Path": record["onedrive_path"],
            "Status": "Success",
        }
        self.metadata_handler.append_entry(metadata)
        self.status_callback(f"Uploaded edited Excel {record['file_name']}")
        messagebox.showinfo("Upload", "Excel uploaded successfully.")
