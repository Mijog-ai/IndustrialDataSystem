"""Simple Tkinter-based data grid for editing pandas DataFrames."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, List

import pandas as pd


class DataGrid(ttk.Frame):
    def __init__(self, master: tk.Widget, dataframe: pd.DataFrame | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._df = dataframe if dataframe is not None else pd.DataFrame()
        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_double_click)
        self._edit_window: tk.Entry | None = None
        self.refresh()

    @property
    def dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self._df = df.copy()
        self.refresh()

    def refresh(self) -> None:
        for column in self.tree["columns"]:
            self.tree.heading(column, text="")
        self.tree.delete(*self.tree.get_children())
        if self._df.empty:
            self.tree["columns"] = []
            return
        columns = list(self._df.columns)
        self.tree["columns"] = columns
        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=120)
        for index, row in self._df.iterrows():
            self.tree.insert("", tk.END, iid=str(index), values=list(row.values))

    def _on_double_click(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or not column:
            return
        column_index = int(column.replace("#", "")) - 1
        x, y, width, height = self.tree.bbox(item, column)
        value = self.tree.set(item, self.tree["columns"][column_index])

        if self._edit_window:
            self._edit_window.destroy()

        self._edit_window = tk.Entry(self.tree)
        self._edit_window.insert(0, value)
        self._edit_window.place(x=x, y=y, width=width, height=height)
        self._edit_window.focus_set()
        self._edit_window.bind("<Return>", lambda e: self._save_edit(item, column_index))
        self._edit_window.bind("<FocusOut>", lambda e: self._save_edit(item, column_index))

    def _save_edit(self, item: str, column_index: int) -> None:
        if not self._edit_window:
            return
        new_value = self._edit_window.get()
        row_index = int(item)
        column_name = self._df.columns[column_index]
        self._df.at[row_index, column_name] = new_value
        self.tree.set(item, column_name, new_value)
        self._edit_window.destroy()
        self._edit_window = None
