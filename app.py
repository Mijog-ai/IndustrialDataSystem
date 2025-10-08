"""PyQt5 desktop application for the Industrial Data System."""
from __future__ import annotations

import csv
import os
import re
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
import cloudinary
import cloudinary.uploader
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY must be configured in environment variables."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


class SessionState:
    """Manage Supabase authentication state for the desktop application."""

    def __init__(self, client: Client) -> None:
        self._client = client
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None

    def set_tokens(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.refresh_user()

    def refresh_user(self) -> Optional[Dict[str, Any]]:
        if not self.access_token or not self.refresh_token:
            self.user = None
            return None

        try:
            session_response = self._client.auth.set_session(
                self.access_token, self.refresh_token
            )
            response = self._client.auth.get_user(self.access_token)
        except Exception:
            self.clear()
            return None

        user = response.user if response else None
        if not user:
            self.clear()
            return None

        current_session = None
        if session_response and getattr(session_response, "session", None):
            current_session = session_response.session
        else:
            current_session = getattr(self._client.auth, "session", None)

        if current_session is not None:
            self.access_token = getattr(
                current_session, "access_token", self.access_token
            )
            self.refresh_token = getattr(
                current_session, "refresh_token", self.refresh_token
            )

        self.user = {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", ""),
            "metadata": getattr(user, "user_metadata", {}) or {},
        }
        return self.user

    def clear(self) -> None:
        self.access_token = None
        self.refresh_token = None
        self.user = None


class LoginPage(QWidget):
    """Authentication interface allowing login and signup flows."""

    login_requested = pyqtSignal(str, str)
    signup_requested = pyqtSignal(str, str, str)
    forgot_password_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Industrial Data System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(12)
        toggle_row.setContentsMargins(0, 24, 0, 12)

        self.login_toggle = QPushButton("Login")
        self.signup_toggle = QPushButton("Signup")
        for button in (self.login_toggle, self.signup_toggle):
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFlat(True)
            button.setStyleSheet("padding: 6px 12px; font-size: 16px;")

        self.login_toggle.clicked.connect(lambda: self._switch_mode("login"))
        self.signup_toggle.clicked.connect(lambda: self._switch_mode("signup"))

        toggle_row.addStretch()
        toggle_row.addWidget(self.login_toggle)
        toggle_row.addWidget(self.signup_toggle)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        self.form_stack = QStackedWidget()
        layout.addWidget(self.form_stack)

        self.login_form = QWidget()
        login_layout = QVBoxLayout(self.login_form)
        login_layout.setSpacing(12)

        login_username_label = QLabel("Username")
        self.login_username_input = QLineEdit()
        self.login_username_input.setPlaceholderText("Enter username")
        self.login_username_input.setMaxLength(6)
        login_layout.addWidget(login_username_label)
        login_layout.addWidget(self.login_username_input)

        login_password_label = QLabel("Password")
        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("Enter password")
        self.login_password_input.setEchoMode(QLineEdit.Password)
        self.login_password_input.setMaxLength(6)
        login_layout.addWidget(login_password_label)
        login_layout.addWidget(self.login_password_input)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self._emit_login_request)
        login_layout.addWidget(login_button)

        forgot_button = QPushButton("Forgot Password?")
        forgot_button.setFlat(True)
        forgot_button.setCursor(Qt.PointingHandCursor)
        forgot_button.clicked.connect(self.forgot_password_requested)
        login_layout.addWidget(forgot_button)

        login_layout.addStretch()

        self.form_stack.addWidget(self.login_form)

        self.signup_form = QWidget()
        signup_layout = QVBoxLayout(self.signup_form)
        signup_layout.setSpacing(12)

        signup_email_label = QLabel("Email")
        self.signup_email_input = QLineEdit()
        self.signup_email_input.setPlaceholderText("Enter email for password recovery")
        signup_layout.addWidget(signup_email_label)
        signup_layout.addWidget(self.signup_email_input)

        signup_username_label = QLabel("Username")
        self.signup_username_input = QLineEdit()
        self.signup_username_input.setPlaceholderText("Choose a username (max 6 characters)")
        self.signup_username_input.setMaxLength(6)
        signup_layout.addWidget(signup_username_label)
        signup_layout.addWidget(self.signup_username_input)

        signup_password_label = QLabel("Password")
        self.signup_password_input = QLineEdit()
        self.signup_password_input.setPlaceholderText("Create a password (max 6 characters)")
        self.signup_password_input.setEchoMode(QLineEdit.Password)
        self.signup_password_input.setMaxLength(6)
        signup_layout.addWidget(signup_password_label)
        signup_layout.addWidget(self.signup_password_input)

        signup_confirm_label = QLabel("Confirm Password")
        self.signup_confirm_input = QLineEdit()
        self.signup_confirm_input.setPlaceholderText("Re-enter password")
        self.signup_confirm_input.setEchoMode(QLineEdit.Password)
        self.signup_confirm_input.setMaxLength(6)
        signup_layout.addWidget(signup_confirm_label)
        signup_layout.addWidget(self.signup_confirm_input)

        signup_button = QPushButton("Create Account")
        signup_button.clicked.connect(self._emit_signup_request)
        signup_layout.addWidget(signup_button)

        signup_layout.addStretch()

        self.form_stack.addWidget(self.signup_form)

        self._switch_mode("login")

    def show_login(self, username: str = "") -> None:
        """Display the login form and optionally prefill the username."""

        self.login_username_input.setText(username)
        self.login_password_input.clear()
        self.signup_email_input.clear()
        self.signup_username_input.clear()
        self.signup_password_input.clear()
        self.signup_confirm_input.clear()
        self._switch_mode("login")
        if username:
            self.login_password_input.setFocus()
        else:
            self.login_username_input.setFocus()

    def show_signup(self) -> None:
        """Display the signup form."""

        self.login_username_input.clear()
        self.login_password_input.clear()
        self._switch_mode("signup")
        self.signup_email_input.setFocus()

    def _switch_mode(self, mode: str) -> None:
        if mode == "signup":
            self.form_stack.setCurrentWidget(self.signup_form)
            self.signup_toggle.setChecked(True)
            self.login_toggle.setChecked(False)
        else:
            self.form_stack.setCurrentWidget(self.login_form)
            self.login_toggle.setChecked(True)
            self.signup_toggle.setChecked(False)

        active_style = (
            "QPushButton { border: none; border-bottom: 2px solid #0d6efd;"
            " color: #0d6efd; font-weight: 600; padding: 6px 12px; }"
        )
        inactive_style = (
            "QPushButton { border: none; border-bottom: 2px solid transparent;"
            " color: #6c757d; padding: 6px 12px; }"
            "QPushButton:hover { color: #0d6efd; }"
        )

        self.login_toggle.setStyleSheet(active_style if self.login_toggle.isChecked() else inactive_style)
        self.signup_toggle.setStyleSheet(
            active_style if self.signup_toggle.isChecked() else inactive_style
        )

    def _emit_login_request(self) -> None:
        username = self.login_username_input.text().strip()
        password = self.login_password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Industrial Data System", "Username and password are required.")
            return
        self.login_requested.emit(username, password)

    def _emit_signup_request(self) -> None:
        email = self.signup_email_input.text().strip()
        username = self.signup_username_input.text().strip()
        password = self.signup_password_input.text()
        confirm = self.signup_confirm_input.text()

        if not email or not username or not password or not confirm:
            QMessageBox.warning(self, "Industrial Data System", "All signup fields are required.")
            return

        if password != confirm:
            QMessageBox.warning(self, "Industrial Data System", "Passwords do not match.")
            return

        self.signup_requested.emit(email, username, password)


class ForgotPasswordPage(QWidget):
    """Interface allowing the user to initiate a password reset."""

    reset_requested = pyqtSignal(str)
    back_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Reset Password")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        layout.addWidget(self.email_input)

        reset_button = QPushButton("Send Reset Instructions")
        reset_button.clicked.connect(self._emit_reset_request)
        layout.addWidget(reset_button)

        back_button = QPushButton("Back to Sign In")
        back_button.clicked.connect(self.back_requested)
        layout.addWidget(back_button)

    def _emit_reset_request(self) -> None:
        email = self.email_input.text().strip().lower()
        self.reset_requested.emit(email)


class DashboardPage(QWidget):
    """Dashboard interface displaying uploaded files."""

    logout_requested = pyqtSignal()
    upload_requested = pyqtSignal(str)
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        self.welcome_label = QLabel("Welcome")
        self.welcome_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.welcome_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Filename", "URL", "Uploaded"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        self.csv_preview_label = QLabel("CSV Preview")
        self.csv_preview_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.csv_preview_label.hide()
        layout.addWidget(self.csv_preview_label)

        self.csv_table = QTableWidget(0, 0)
        self.csv_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.csv_table.hide()
        layout.addWidget(self.csv_table)

        upload_button = QPushButton("Upload File")
        upload_button.clicked.connect(self._select_file)
        layout.addWidget(upload_button)

        refresh_button = QPushButton("Refresh Files")
        refresh_button.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(refresh_button)

        logout_button = QPushButton("Sign Out")
        logout_button.clicked.connect(self.logout_requested)
        layout.addWidget(logout_button)

    def set_user_identity(self, username: str, email: str) -> None:
        username = username.strip()
        email = email.strip()
        parts = [part for part in (username, email) if part]
        if parts:
            self.welcome_label.setText(f"Welcome, {' · '.join(parts)}")
        else:
            self.welcome_label.setText("Welcome")

    def update_files(self, files: List[Dict[str, Any]]) -> None:
        self.table.setRowCount(len(files))
        for row, file_record in enumerate(files):
            filename_item = QTableWidgetItem(file_record.get("filename", ""))
            url_item = QTableWidgetItem(file_record.get("url", ""))
            created_item = QTableWidgetItem(file_record.get("created_at", ""))

            for item in (filename_item, url_item, created_item):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row, 0, filename_item)
            self.table.setItem(row, 1, url_item)
            self.table.setItem(row, 2, created_item)

    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if file_path:
            self.upload_requested.emit(file_path)

    def display_csv_preview(self, headers: List[str], rows: List[List[str]]) -> None:
        if not headers:
            self.clear_csv_preview()
            return

        column_count = len(headers)
        self.csv_table.setColumnCount(column_count)
        self.csv_table.setHorizontalHeaderLabels(headers)

        self.csv_table.setRowCount(len(rows))
        for row_index, row_values in enumerate(rows):
            for column_index in range(column_count):
                value = row_values[column_index] if column_index < len(row_values) else ""
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.csv_table.setItem(row_index, column_index, item)

        self.csv_preview_label.show()
        self.csv_table.show()

    def clear_csv_preview(self) -> None:
        self.csv_table.clear()
        self.csv_table.setRowCount(0)
        self.csv_table.setColumnCount(0)
        self.csv_table.hide()
        self.csv_preview_label.hide()

class IndustrialDataApp(QMainWindow):
    """Main window hosting the Industrial Data System interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial Data System")
        self.resize(900, 600)

        self.session_state = SessionState(supabase)
        self.current_username: str = ""

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.forgot_page = ForgotPasswordPage()
        self.dashboard_page = DashboardPage()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.forgot_page)
        self.stack.addWidget(self.dashboard_page)

        self.login_page.login_requested.connect(self.handle_login)
        self.login_page.signup_requested.connect(self.handle_signup)
        self.login_page.forgot_password_requested.connect(self.show_forgot_password)

        self.forgot_page.reset_requested.connect(self.handle_password_reset)
        self.forgot_page.back_requested.connect(self.show_login)

        self.dashboard_page.logout_requested.connect(self.handle_logout)
        self.dashboard_page.upload_requested.connect(self.handle_upload)
        self.dashboard_page.refresh_requested.connect(self.refresh_files)

        self.show_login()

    def show_login(self, username: str = "") -> None:
        self.stack.setCurrentWidget(self.login_page)
        self.login_page.show_login(username)

    def show_forgot_password(self) -> None:
        self.stack.setCurrentWidget(self.forgot_page)

    def show_dashboard(self) -> None:
        self.stack.setCurrentWidget(self.dashboard_page)

    def handle_login(self, username: str, password: str) -> None:
        username = username.strip()
        if not username or not password:
            self._alert("Username and password are required.", QMessageBox.Warning)
            return

        try:
            email = self._resolve_email_for_username(username)
        except RuntimeError as exc:
            self._alert(str(exc), QMessageBox.Critical)
            return

        if not email:
            self._alert("No account found for the provided username.", QMessageBox.Warning)
            return

        try:
            auth_response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            self._alert(f"Unable to sign in: {exc}", QMessageBox.Critical)
            return

        if not getattr(auth_response, "session", None):
            self._alert("No active Supabase session returned.", QMessageBox.Critical)
            return

        self.session_state.set_tokens(
            auth_response.session.access_token,
            auth_response.session.refresh_token,
        )

        user = self.session_state.user
        if not user:
            self._alert("Unable to determine the current user.", QMessageBox.Critical)
            return

        metadata = (user.get("metadata") or {})
        stored_username = str(
            metadata.get("username") or metadata.get("username_normalized") or username
        ).strip()
        self.current_username = stored_username or username

        self.dashboard_page.set_user_identity(self.current_username, user.get("email", ""))
        self.show_dashboard()
        self.refresh_files()

    def handle_signup(self, email: str, username: str, password: str) -> None:
        email = email.strip().lower()
        username = username.strip()
        if not email or not username or not password:
            self._alert("All signup fields are required.", QMessageBox.Warning)
            return

        if len(username) > 6 or len(password) > 6:
            self._alert(
                "Username and password must be 6 characters or fewer.",
                QMessageBox.Warning,
            )
            return

        if not self._is_valid_email(email):
            self._alert("Enter a valid email address.", QMessageBox.Warning)
            return

        normalized_username = username.lower()

        try:
            existing_email = self._resolve_email_for_username(normalized_username)
        except RuntimeError as exc:
            self._alert(str(exc), QMessageBox.Critical)
            return

        if existing_email:
            self._alert("That username is already in use.", QMessageBox.Warning)
            return

        metadata = {
            "username": username,
            "username_normalized": normalized_username,
        }

        try:
            response = supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {"data": metadata},
                }
            )
        except Exception as exc:
            self._alert(f"Unable to create the account: {exc}", QMessageBox.Critical)
            return

        if not getattr(response, "user", None):
            self._alert("Signup did not complete successfully.", QMessageBox.Critical)
            return

        self._alert(
            "Signup successful! Check your email to verify the account and then log in using your username.",
            QMessageBox.Information,
        )
        self.show_login(username)

    def handle_password_reset(self, email: str) -> None:
        if not email:
            self._alert("Email is required to reset the password.", QMessageBox.Warning)
            return

        try:
            supabase.auth.reset_password_email(email)
        except Exception as exc:
            self._alert(f"Failed to initiate password reset: {exc}", QMessageBox.Critical)
            return

        self._alert(
            "Password reset instructions have been sent if the email exists.",
            QMessageBox.Information,
        )
        self.show_login()

    def handle_logout(self) -> None:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        self.session_state.clear()
        self.current_username = ""
        self._alert("You have been signed out.", QMessageBox.Information)
        self.show_login()

    def refresh_files(self) -> None:
        user = self.session_state.refresh_user()
        if not user:
            self._alert("Session expired. Please sign in again.", QMessageBox.Warning)
            self.show_login()
            return

        metadata = (user.get("metadata") or {})
        metadata_username = str(
            metadata.get("username")
            or metadata.get("username_normalized")
            or self.current_username
        ).strip()
        if metadata_username:
            self.current_username = metadata_username

        self.dashboard_page.set_user_identity(
            self.current_username,
            user.get("email", ""),
        )

        try:
            response = (
                supabase.table("files")
                .select("id, filename, url, created_at")
                .eq("user_id", user["id"])
                .order("created_at", desc=True)
                .execute()
            )
            files = response.data or []
        except Exception as exc:
            self._alert(f"Failed to load files from Supabase: {exc}", QMessageBox.Critical)
            files = []

        self.dashboard_page.update_files(files)

    def handle_upload(self, file_path: str) -> None:
        user = self.session_state.user
        if not user:
            self._alert("Session expired. Please sign in again.", QMessageBox.Warning)
            self.show_login()
            return

        if not file_path.lower().endswith(".csv"):
            self._alert("Only CSV files can be uploaded.", QMessageBox.Warning)
            self.dashboard_page.clear_csv_preview()
            return

        preview_result = self._prepare_csv_preview(file_path)
        if preview_result is None:
            return

        headers, rows = preview_result
        self.dashboard_page.display_csv_preview(headers, rows)

        try:
            upload_result = cloudinary.uploader.upload(file_path)
        except Exception as exc:
            self._alert(f"Cloudinary upload failed: {exc}", QMessageBox.Critical)
            return

        file_url = upload_result.get("secure_url")
        if not file_url:
            self._alert("Cloudinary did not return a file URL.", QMessageBox.Critical)
            return

        metadata = {
            "user_id": user.get("id"),
            "filename": os.path.basename(file_path),
            "url": file_url,
        }

        try:
            supabase.table("files").insert(metadata).execute()
        except Exception as exc:
            self._alert(
                f"Failed to store file metadata in Supabase: {exc}", QMessageBox.Critical
            )
            return

        self._alert("File uploaded successfully.", QMessageBox.Information)
        self.refresh_files()

    def _resolve_email_for_username(self, username: str) -> Optional[str]:
        normalized = username.strip().lower()
        if not normalized:
            return None

        admin_api = getattr(getattr(supabase, "auth", None), "admin", None)
        if admin_api is None:
            raise RuntimeError("Supabase admin client is not available for username lookup.")

        page = 1
        try:
            while True:
                response = admin_api.list_users(page=page, per_page=100)
                users = getattr(response, "users", []) or []
                for user in users:
                    metadata = getattr(user, "user_metadata", {}) or {}
                    metadata_username = str(
                        metadata.get("username_normalized")
                        or metadata.get("username")
                        or ""
                    ).strip().lower()
                    if metadata_username == normalized:
                        return getattr(user, "email", None)

                next_page = getattr(response, "next_page", None)
                if not next_page or next_page == page:
                    break
                page = next_page
        except Exception as exc:
            raise RuntimeError(f"Unable to query Supabase users: {exc}") from exc

        return None

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))

    def _prepare_csv_preview(
        self, file_path: str
    ) -> Optional[tuple[List[str], List[List[str]]]]:
        try:
            with open(file_path, newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                rows = list(reader)
        except Exception as exc:
            self._alert(f"Unable to read CSV file: {exc}", QMessageBox.Critical)
            self.dashboard_page.clear_csv_preview()
            return None

        if not rows:
            self._alert("The selected CSV file is empty.", QMessageBox.Warning)
            self.dashboard_page.clear_csv_preview()
            return None

        headers = rows[0]
        data_rows = rows[1:101]
        return headers, data_rows

    def _alert(self, message: str, icon: QMessageBox.Icon) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setText(message)
        dialog.setWindowTitle("Industrial Data System")
        dialog.exec_()


def main() -> None:
    app = QApplication(sys.argv)
    window = IndustrialDataApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
