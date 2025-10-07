"""Main application window with tabbed interface."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.cloud.folder_manager import FolderManager
from src.gui.excel_editor_panel import ExcelEditorPanel
from src.gui.status_display import StatusDisplay
from src.gui.upload_panel import UploadPanel


class MyFilesPanel(ttk.Frame):
    def __init__(self, master: tk.Widget, user_context: dict, folder_manager: FolderManager) -> None:
        super().__init__(master)
        self.user_context = user_context
        self.folder_manager = folder_manager
        self.tree = ttk.Treeview(self)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def refresh(self) -> None:
        folders = self.folder_manager.ensure_user_folders(self.user_context["user_id"])
        root_path = folders["root"]
        self.tree.delete(*self.tree.get_children())
        root_node = self.tree.insert("", tk.END, text=root_path.name, open=True)
        self._populate(root_node, root_path)

    def _populate(self, parent: str, path: Path) -> None:
        for item in sorted(path.iterdir()):
            node = self.tree.insert(parent, tk.END, text=item.name, open=False)
            if item.is_dir():
                self._populate(node, item)


class MainWindow(tk.Tk):
    def __init__(self, user_context: dict) -> None:
        super().__init__()
        self.user_context = user_context
        self.title("Industrial Data Upload System")
        self.geometry("900x600")
        self.folder_manager = FolderManager()
        self.status_bar = StatusDisplay(self)
        self._build_ui()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)

        upload_tab = UploadPanel(notebook, self.user_context, self.update_status)
        notebook.add(upload_tab, text="Direct Upload")

        excel_tab = ExcelEditorPanel(notebook, self.user_context, self.update_status)
        notebook.add(excel_tab, text="Excel Editor")

        files_tab = MyFilesPanel(notebook, self.user_context, self.folder_manager)
        notebook.add(files_tab, text="My Files")

        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def update_status(self, message: str) -> None:
        self.status_bar.update_status(message)
