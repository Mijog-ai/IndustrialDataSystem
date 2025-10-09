"""Standalone reader application for browsing Cloudinary assets."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import cloudinary.api

from app import IndustrialTheme, SessionState, supabase


@dataclass
class CloudinaryResource:
    """Small helper wrapper around Cloudinary resource metadata."""

    name: str
    resource: Dict[str, Any]
    path_parts: List[str]

    @property
    def secure_url(self) -> str:
        return self.resource.get("secure_url", "")

    @property
    def format(self) -> str:
        return (self.resource.get("format") or "").lower()

    @property
    def resource_type(self) -> str:
        return (self.resource.get("resource_type") or "").lower()

    @property
    def display_name(self) -> str:
        if self.format and not self.name.lower().endswith(f".{self.format}"):
            return f"{self.name}.{self.format}"
        return self.name

    @property
    def folder(self) -> str:
        folder = self.resource.get("folder")
        return folder or "/".join(self.path_parts[:-1])

    @property
    def bytes(self) -> Optional[int]:
        value = self.resource.get("bytes")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def public_id(self) -> str:
        return self.resource.get("public_id", "")


class ReaderLoginPage(QWidget):
    """Minimal login screen dedicated to reader accounts."""

    login_requested = pyqtSignal(str, str)

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 120, 80, 120)
        layout.setSpacing(24)

        title = QLabel("Reader Portal")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sign in with your reader credentials to browse files.")
        subtitle.setProperty("caption", True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #EF4444; font-weight: 500;")
        self.error_label.hide()
        layout.addWidget(self.error_label, alignment=Qt.AlignCenter)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(24, 24, 24, 24)

        email_label = QLabel("Email")
        email_label.setStyleSheet(
            f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;"
        )
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("reader@example.com")
        form_layout.addWidget(self.email_input)

        password_label = QLabel("Password")
        password_label.setStyleSheet(
            f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;"
        )
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_input)

        self.login_button = QPushButton("Sign In")
        self.login_button.setProperty("primary", True)
        self.login_button.clicked.connect(self._emit_login)
        form_layout.addWidget(self.login_button)

        layout.addWidget(form_container, alignment=Qt.AlignCenter)
        layout.addStretch()

    def _emit_login(self) -> None:
        self.error_label.hide()
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()
        self.login_requested.emit(email, password)

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()


class ReaderDashboard(QWidget):
    """Dashboard that renders Cloudinary folders and file previews."""

    logout_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        self.user_label = QLabel()
        self.user_label.setProperty("heading", True)
        header_layout.addWidget(self.user_label)
        header_layout.addStretch()

        refresh_button = QPushButton("Refresh")
        refresh_button.setProperty("secondary", True)
        refresh_button.clicked.connect(self.refresh_requested.emit)
        header_layout.addWidget(refresh_button)

        logout_button = QPushButton("Sign Out")
        logout_button.setProperty("danger", True)
        logout_button.clicked.connect(self.logout_requested.emit)
        header_layout.addWidget(logout_button)

        main_layout.addLayout(header_layout)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Folder"])
        self.tree.setColumnWidth(0, 280)
        splitter.addWidget(self.tree)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(12)

        self.preview_title = QLabel("Select a file to preview")
        self.preview_title.setProperty("subheading", True)
        preview_layout.addWidget(self.preview_title)

        self.preview_message = QLabel()
        self.preview_message.setWordWrap(True)
        preview_layout.addWidget(self.preview_message)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide()
        preview_layout.addWidget(self.image_preview)

        self.text_preview = QPlainTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.hide()
        preview_layout.addWidget(self.text_preview, stretch=1)

        self.download_button = QPushButton("Download")
        self.download_button.setProperty("primary", True)
        self.download_button.setEnabled(False)
        preview_layout.addWidget(self.download_button)

        splitter.addWidget(preview_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, stretch=1)

        self.tree.currentItemChanged.connect(self._handle_selection)

        self._current_resource: Optional[CloudinaryResource] = None

    def set_user_identity(self, display_name: str, email: str) -> None:
        if display_name:
            text = display_name
        else:
            text = email
        self.user_label.setText(text or "Reader Dashboard")

    def clear(self) -> None:
        self.tree.clear()
        self._show_message("Select a file to preview")
        self.image_preview.hide()
        self.text_preview.hide()
        self.download_button.setEnabled(False)
        self._current_resource = None

    def populate(self, resources: Iterable[CloudinaryResource]) -> None:
        self.clear()
        folders: Dict[str, QTreeWidgetItem] = {}
        root = self.tree.invisibleRootItem()

        for resource in resources:
            parent = root
            path_so_far: List[str] = []
            for folder_name in resource.path_parts[:-1]:
                path_so_far.append(folder_name)
                path_key = "/".join(path_so_far)
                if path_key not in folders:
                    folder_item = QTreeWidgetItem(
                        [folder_name, "Folder", "/".join(path_so_far[:-1])]
                    )
                    folder_item.setData(0, Qt.UserRole, {"type": "folder"})
                    parent.addChild(folder_item)
                    folders[path_key] = folder_item
                parent = folders[path_key]

            file_item = QTreeWidgetItem(
                [resource.display_name, resource.format.upper() or "File", resource.folder]
            )
            file_item.setData(0, Qt.UserRole, {"type": "file", "resource": resource})
            parent.addChild(file_item)

        self.tree.expandAll()
        if self.tree.topLevelItemCount() == 0:
            self._show_message("No files were found in Cloudinary.")

    def _handle_selection(self, current: Optional[QTreeWidgetItem], _: Optional[QTreeWidgetItem]) -> None:
        if not current:
            self._current_resource = None
            self.download_button.setEnabled(False)
            self._show_message("Select a file to preview")
            return

        data = current.data(0, Qt.UserRole) or {}
        if data.get("type") != "file":
            self._current_resource = None
            self.download_button.setEnabled(False)
            self._show_message("Select a file to preview")
            return

        resource: CloudinaryResource = data["resource"]
        self._current_resource = resource
        self.download_button.setEnabled(True)
        self._preview_resource(resource)

    def _preview_resource(self, resource: CloudinaryResource) -> None:
        self.image_preview.hide()
        self.text_preview.hide()

        secure_url = resource.secure_url
        if not secure_url:
            self._show_message("No secure URL is available for this file.")
            return

        preview_type = resource.resource_type
        fmt = resource.format

        try:
            if preview_type == "image":
                response = requests.get(secure_url, timeout=30)
                response.raise_for_status()
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                self.image_preview.setPixmap(
                    pixmap.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                self.image_preview.show()
                self._show_message("Image preview")
                return

            if fmt in {"txt", "csv", "json", "log", "md"} or preview_type == "text":
                response = requests.get(secure_url, timeout=30)
                response.raise_for_status()
                text = response.text
                if len(text) > 12000:
                    text = text[:12000] + "\n\n… Preview truncated."
                self.text_preview.setPlainText(text)
                self.text_preview.show()
                self._show_message("Text preview")
                return

            self._show_message("Preview is not available. Use Download to open the file.")
        except Exception as exc:
            self._show_message(f"Unable to preview this file: {exc}")

    def _show_message(self, message: str) -> None:
        self.preview_message.setText(message)
        if not self.preview_message.isVisible():
            self.preview_message.show()

    def download_current(self) -> None:
        if not self._current_resource:
            return

        default_name = self._current_resource.display_name or "download"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", default_name)
        if not file_path:
            return

        secure_url = self._current_resource.secure_url
        if not secure_url:
            QMessageBox.critical(self, "Download Failed", "This file does not have a secure URL.")
            return

        try:
            response = requests.get(secure_url, stream=True, timeout=60)
            response.raise_for_status()
            with open(file_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        handle.write(chunk)
        except Exception as exc:
            QMessageBox.critical(self, "Download Failed", f"Unable to download file: {exc}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


def _collect_resources(prefix: str) -> List[CloudinaryResource]:
    normalized_prefix = prefix.strip("/")
    api_prefix = f"{normalized_prefix}/" if normalized_prefix else ""

    resources: List[Dict[str, Any]] = []
    next_cursor: Optional[str] = None

    while True:
        params = {
            "type": "upload",
            "prefix": api_prefix,
            "max_results": 500,
        }
        if next_cursor:
            params["next_cursor"] = next_cursor
        response = cloudinary.api.resources(**params)
        resources.extend(response.get("resources", []))
        next_cursor = response.get("next_cursor")
        if not next_cursor:
            break

    structured: List[CloudinaryResource] = []
    for raw in resources:
        public_id = raw.get("public_id", "")
        if api_prefix and public_id.startswith(api_prefix):
            relative = public_id[len(api_prefix):]
        else:
            relative = public_id
        parts = [segment for segment in relative.split("/") if segment]
        if not parts:
            continue
        name = parts[-1]
        structured.append(
            CloudinaryResource(name=name, resource=raw, path_parts=parts)
        )

    structured.sort(key=lambda res: res.path_parts)
    return structured


class ReaderApp(QMainWindow):
    """Main window that orchestrates authentication and browsing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cloudinary Reader App")
        self.setMinimumSize(1100, 700)

        self.session_state = SessionState(supabase)
        self.allowed_roles = {
            role.strip().lower()
            for role in os.getenv("READER_ALLOWED_ROLES", "reader").split(",")
            if role.strip()
        }
        self.cloudinary_root = os.getenv("CLOUDINARY_READER_ROOT", "tests")

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = ReaderLoginPage()
        self.dashboard = ReaderDashboard()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard)

        self.login_page.login_requested.connect(self.handle_login)
        self.dashboard.logout_requested.connect(self.handle_logout)
        self.dashboard.refresh_requested.connect(self.refresh_resources)
        self.dashboard.download_button.clicked.connect(self.dashboard.download_current)

        self.show_login()

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    def show_login(self) -> None:
        self.stack.setCurrentWidget(self.login_page)
        self.dashboard.clear()

    def show_dashboard(self) -> None:
        self.stack.setCurrentWidget(self.dashboard)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def handle_login(self, email: str, password: str) -> None:
        if not email or not password:
            self.login_page.show_error("Email and password are required.")
            return

        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password,
            })
        except Exception as exc:
            self.login_page.show_error(f"Unable to sign in: {exc}")
            return

        session = getattr(response, "session", None)
        if not session:
            self.login_page.show_error("Supabase did not return a session.")
            return

        access_token = getattr(session, "access_token", None)
        refresh_token = getattr(session, "refresh_token", None)
        if not access_token or not refresh_token:
            self.login_page.show_error("Authentication response was incomplete.")
            return

        self.session_state.set_tokens(access_token, refresh_token)
        user = self.session_state.user
        if not user:
            self.login_page.show_error("Unable to retrieve user information.")
            return

        metadata = user.get("metadata") or {}
        if not self._is_reader(metadata):
            self.session_state.clear()
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            self.login_page.show_error("This account does not have reader access.")
            return

        display_name = (
            metadata.get("display_name")
            or metadata.get("username")
            or metadata.get("full_name")
            or ""
        )
        self.dashboard.set_user_identity(display_name, user.get("email", ""))
        self.show_dashboard()
        self.refresh_resources()

    def _is_reader(self, metadata: Dict[str, Any]) -> bool:
        if not self.allowed_roles:
            return True
        role = metadata.get("role") or metadata.get("user_role")
        if role is None:
            return False
        return str(role).strip().lower() in self.allowed_roles

    def handle_logout(self) -> None:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        self.session_state.clear()
        self.show_login()

    # ------------------------------------------------------------------
    # Cloudinary integration
    # ------------------------------------------------------------------

    def refresh_resources(self) -> None:
        try:
            resources = _collect_resources(self.cloudinary_root)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Cloudinary Error",
                f"Unable to load Cloudinary resources: {exc}",
            )
            return

        self.dashboard.populate(resources)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(IndustrialTheme.get_stylesheet())
    app.setFont(QFont("Segoe UI", 10))

    window = ReaderApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
