"""Panel handling direct file uploads."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from src.cloud.onedrive_uploader import OneDriveUploader
from src.metadata.excel_handler import MetadataExcelHandler
from src.utils.file_validator import validate_file_type


class UploadPanel(ttk.Frame):
    def __init__(self, master: tk.Widget, user_context: dict, status_callback) -> None:
        super().__init__(master)
        self.user_context = user_context
        self.status_callback = status_callback
        self.uploader = OneDriveUploader()
        self.metadata_handler = MetadataExcelHandler()
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self, text="Direct Upload", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=5)
        ttk.Button(self, text="Select File", command=self.select_file).pack(anchor=tk.CENTER, pady=10)

    def select_file(self) -> None:
        file_path = filedialog.askopenfilename(title="Select file", filetypes=[
            ("Supported", "*.csv *.xlsx *.xlsm *.png *.jpg *.jpeg *.bmp *.tiff"),
            ("CSV", "*.csv"),
            ("Excel", "*.xlsx *.xlsm"),
            ("Images", "*.png *.jpg *.jpeg *.bmp *.tiff"),
        ])
        if not file_path:
            return
        try:
            file_type = validate_file_type(Path(file_path))
            record = self.uploader.upload_file(self.user_context["user_id"], Path(file_path))
            metadata = {
                "User_ID": self.user_context["user_id"],
                "User_Name": self.user_context.get("name", self.user_context["user_id"]),
                "File_Name": record["file_name"],
                "File_Type": record["file_type"],
                "File_Size_KB": record["size_kb"],
                "Creation_Method": "Direct_Upload",
                "OneDrive_Path": record["onedrive_path"],
                "OneDrive_URL": record.get("onedrive_url", ""),
                "Status": "Success",
            }
            self.metadata_handler.append_entry(metadata)
            messagebox.showinfo("Upload", f"{file_type} uploaded successfully.")
            self.status_callback(f"Uploaded {record['file_name']} to OneDrive.")
        except Exception as exc:
            messagebox.showerror("Upload failed", str(exc))
            self.status_callback(f"Upload failed: {exc}")
