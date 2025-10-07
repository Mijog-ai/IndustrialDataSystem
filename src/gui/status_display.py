"""Status display widget for user feedback."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatusDisplay(ttk.Frame):
    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master)
        self.var = tk.StringVar(value="Ready")
        label = ttk.Label(self, textvariable=self.var, relief=tk.SUNKEN, anchor=tk.W)
        label.pack(fill=tk.X, expand=True)

    def update_status(self, message: str) -> None:
        self.var.set(message)
