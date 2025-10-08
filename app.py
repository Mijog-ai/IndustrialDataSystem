"""PyQt5 desktop application for the Industrial Data System."""
from __future__ import annotations

import csv
import os
import sys
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QButtonGroup,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
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


def normalize_role(role: Optional[str]) -> str:
    """Normalize a role label to a comparable identifier."""

    if not role:
        return ""
    normalized = str(role).strip().lower()
    return normalized.replace("-", "_").replace(" ", "_")


def format_role_label(role: Optional[str]) -> str:
    """Create a human-friendly label for a role value."""

    normalized = normalize_role(role)
    if not normalized:
        return ""
    return normalized.replace("_", " ").title()


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
    """Login interface for the application."""

    login_requested = pyqtSignal(str, str, str)
    forgot_password_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Industrial Data System")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        layout.addWidget(self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        role_box = QGroupBox("Sign in as")
        role_layout = QHBoxLayout()
        role_layout.setContentsMargins(12, 8, 12, 8)
        role_layout.setSpacing(16)

        self.role_group = QButtonGroup(self)

        admin_radio = QRadioButton("Administrator")
        admin_radio.setProperty("role", "admin")
        self.role_group.addButton(admin_radio)
        role_layout.addWidget(admin_radio)

        joiner_radio = QRadioButton("New Joiner")
        joiner_radio.setProperty("role", "new_joiner")
        joiner_radio.setChecked(True)
        self.role_group.addButton(joiner_radio)
        role_layout.addWidget(joiner_radio)

        role_layout.addStretch()
        role_box.setLayout(role_layout)
        layout.addWidget(role_box)

        login_button = QPushButton("Sign In")
        login_button.clicked.connect(self._emit_login_request)
        layout.addWidget(login_button)

        forgot_button = QPushButton("Forgot Password?")
        forgot_button.clicked.connect(self.forgot_password_requested)
        layout.addWidget(forgot_button)

    def _emit_login_request(self) -> None:
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()
        checked = self.role_group.checkedButton()
        role = checked.property("role") if checked else "new_joiner"
        self.login_requested.emit(email, password, role)


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

    def set_user_email(self, email: str, role: Optional[str] = None) -> None:
        role_suffix = f" · {role}" if role else ""
        self.welcome_label.setText(f"Welcome, {email}{role_suffix}")

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
        self.active_role_display: Optional[str] = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = LoginPage()
        self.forgot_page = ForgotPasswordPage()
        self.dashboard_page = DashboardPage()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.forgot_page)
        self.stack.addWidget(self.dashboard_page)

        self.login_page.login_requested.connect(self.handle_login)
        self.login_page.forgot_password_requested.connect(self.show_forgot_password)

        self.forgot_page.reset_requested.connect(self.handle_password_reset)
        self.forgot_page.back_requested.connect(self.show_login)

        self.dashboard_page.logout_requested.connect(self.handle_logout)
        self.dashboard_page.upload_requested.connect(self.handle_upload)
        self.dashboard_page.refresh_requested.connect(self.refresh_files)

        self.show_login()

    def show_login(self) -> None:
        self.active_role_display = None
        self.stack.setCurrentWidget(self.login_page)

    def show_forgot_password(self) -> None:
        self.stack.setCurrentWidget(self.forgot_page)

    def show_dashboard(self) -> None:
        self.stack.setCurrentWidget(self.dashboard_page)

    def handle_login(self, email: str, password: str, role: str) -> None:
        if not email or not password:
            self._alert("Email and password are required.", QMessageBox.Warning)
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

        selected_role = normalize_role(role) or "new_joiner"
        metadata_role = normalize_role((user.get("metadata") or {}).get("role"))

        if metadata_role and metadata_role != selected_role:
            attempted_label = format_role_label(selected_role)
            actual_label = format_role_label(metadata_role)
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            self.session_state.clear()
            self._alert(
                (
                    "You attempted to sign in as "
                    f"{attempted_label or 'the selected role'}, "
                    "but this account is registered as "
                    f"{actual_label or 'a different role'}."
                ),
                QMessageBox.Critical,
            )
            return

        display_role = metadata_role or selected_role
        self.active_role_display = format_role_label(display_role)

        self.dashboard_page.set_user_email(
            user.get("email", ""), self.active_role_display
        )
        self.show_dashboard()
        self.refresh_files()

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
        self.active_role_display = None
        self._alert("You have been signed out.", QMessageBox.Information)
        self.show_login()

    def refresh_files(self) -> None:
        user = self.session_state.refresh_user()
        if not user:
            self._alert("Session expired. Please sign in again.", QMessageBox.Warning)
            self.show_login()
            return

        if not self.active_role_display:
            metadata_label = format_role_label((user.get("metadata") or {}).get("role"))
            if metadata_label:
                self.active_role_display = metadata_label

        self.dashboard_page.set_user_email(
            user.get("email", ""), self.active_role_display
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
