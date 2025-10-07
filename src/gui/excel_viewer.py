"""Dialog to preview Excel files in read-only mode."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pandas as pd

from src.gui.data_grid import DataGrid


class ExcelViewer(tk.Toplevel):
    def __init__(self, master: tk.Widget, dataframe: pd.DataFrame, title: str = "Excel Preview") -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("600x400")
        grid = DataGrid(self, dataframe=dataframe)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.tree.configure(selectmode="none")
        for col in grid.tree["columns"]:
            grid.tree.heading(col, text=col)
        grid.tree.bind("<Double-1>", lambda e: None)
