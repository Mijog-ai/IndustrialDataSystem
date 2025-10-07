"""Login window for the Industrial Data Upload System."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.auth.session_manager import SessionManager
from src.auth.user_manager import UserManager
from src.cloud.user_folder_creator import UserFolderCreator


class LoginWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Industrial Data Upload System - Login")
        self.geometry("320x200")
        self.resizable(False, False)
        self.user_manager = UserManager()
        self.session_manager = SessionManager()
        self.folder_creator = UserFolderCreator()

        ttk.Label(self, text="User ID").pack(pady=(30, 5))
        self.user_id_entry = ttk.Entry(self)
        self.user_id_entry.pack(fill=tk.X, padx=40)

        ttk.Label(self, text="Password (optional)").pack(pady=(10, 5))
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.pack(fill=tk.X, padx=40)

        login_button = ttk.Button(self, text="Login", command=self._login)
        login_button.pack(pady=20)

        self.bind("<Return>", lambda event: self._login())

    def _login(self) -> None:
        user_id = self.user_id_entry.get().strip()
        password = self.password_entry.get().strip() or None
        if not user_id:
            messagebox.showwarning("Login", "Enter your user ID.")
            return
        user = self.user_manager.authenticate(user_id, password)
        if not user:
            messagebox.showerror("Login", "Invalid credentials.")
            return
        self.session_manager.create_session(user.user_id)
        self.folder_creator.ensure(user.user_id)
        self.destroy()
        from src.gui.main_window import MainWindow

        app = MainWindow({"user_id": user.user_id, "name": user.name, "quota_mb": user.quota_mb})
        app.mainloop()
