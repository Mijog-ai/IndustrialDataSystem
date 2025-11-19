"""Standalone reader application for browsing shared-drive assets."""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

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
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QFormLayout, QTableWidgetItem, QTableWidget, QFrame, QScrollArea,
)

from industrial_data_system.ai.toolkit import (
    run_ai_data_study,
    run_plotter,
    run_training_simulation,
)
from industrial_data_system.apps.desktop.uploader import IndustrialTheme
from industrial_data_system.core.auth import LocalAuthStore, LocalUser
from industrial_data_system.core.config import get_config
from industrial_data_system.core.db_manager import DatabaseManager
from industrial_data_system.core.storage import LocalStorageManager


def get_reader_security_code() -> str:
    """Get the reader security code from environment variable.

    Returns:
        str: The security code from IDS_READER_SECURITY_CODE environment variable.

    Raises:
        RuntimeError: If the environment variable is not set.
    """
    code = os.getenv("IDS_READER_SECURITY_CODE")
    if not code:
        raise RuntimeError(
            "IDS_READER_SECURITY_CODE environment variable is not set. "
            "Please set it in your .env file or system environment."
        )
    return code.strip()


@dataclass
class LocalResource:
    """Representation of a file stored on the shared drive."""

    name: str
    absolute_path: Path
    relative_path: Path
    test_type: str
    file_size: Optional[int]
    created_at: Optional[str]

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def folder(self) -> str:
        parts = list(self.relative_path.parts)
        if len(parts) > 1:
            return "/".join(parts[:-1])
        return ""


class ReaderLoginPage(QWidget):
    """Minimal login screen dedicated to reader accounts."""

    login_requested = pyqtSignal(str, str, str)
    signup_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        # Use scroll area for better responsiveness
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)  # Reduced from 80, 120, 80, 120
        layout.setSpacing(16)  # Reduced from 24
        layout.setAlignment(Qt.AlignCenter)

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

        code_label = QLabel("Security Code")
        code_label.setStyleSheet(
            f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;"
        )
        form_layout.addWidget(code_label)

        self.security_input = QLineEdit()
        self.security_input.setPlaceholderText("Enter security code")
        self.security_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.security_input)

        self.login_button = QPushButton("Sign In")
        self.login_button.setProperty("primary", True)
        self.login_button.clicked.connect(self._emit_login)
        form_layout.addWidget(self.login_button)

        self.signup_button = QPushButton("Create Account")
        self.signup_button.setProperty("secondary", True)
        self.signup_button.clicked.connect(self.signup_requested.emit)
        form_layout.addWidget(self.signup_button)

        layout.addWidget(form_container, alignment=Qt.AlignCenter)
        layout.addStretch()

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _emit_login(self) -> None:
        self.error_label.hide()
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()
        security_code = self.security_input.text().strip()
        self.login_requested.emit(email, password, security_code)

    def show_error(self, message: str) -> None:
        if message:
            self.error_label.setText(message)
            self.error_label.show()
        else:
            self.error_label.hide()

    def reset_fields(self) -> None:
        self.email_input.clear()
        self.password_input.clear()
        self.security_input.clear()
        self.error_label.hide()


class ReaderSignupDialog(QDialog):
    """Dialog for creating reader accounts."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Reader Account")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("reader@example.com")
        form_layout.addRow("Email", self.email_input)

        self.display_name_input = QLineEdit()
        self.display_name_input.setPlaceholderText("Display name (optional)")
        form_layout.addRow("Display Name", self.display_name_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password", self.password_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Confirm Password", self.confirm_input)

        self.code_input = QLineEdit()
        self.code_input.setEchoMode(QLineEdit.Password)
        self.code_input.setPlaceholderText("Security code")
        form_layout.addRow("Security Code", self.code_input)

        layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #EF4444; font-weight: 500;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._result: Optional[Dict[str, str]] = None

    def accept(self) -> None:
        email = self.email_input.text().strip().lower()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        security_code = self.code_input.text().strip()
        display_name = self.display_name_input.text().strip()

        if not email or not password or not security_code:
            self._show_error("Email, password, and security code are required.")
            return

        if password != confirm:
            self._show_error("Passwords do not match.")
            return

        try:
            expected_code = get_reader_security_code()
            if security_code != expected_code:
                self._show_error("Invalid security code.")
                return
        except RuntimeError as exc:
            self._show_error(f"Configuration error: {exc}")
            return

        self._result = {
            "email": email,
            "password": password,
            "display_name": display_name,
        }
        self._show_error("")
        super().accept()

    def _show_error(self, message: str) -> None:
        if message:
            self.error_label.setText(message)
            self.error_label.show()
        else:
            self.error_label.hide()

    def get_result(self) -> Optional[Dict[str, str]]:
        return self._result

class ReaderDashboard(QWidget):
    """Dashboard that renders shared-drive folders and file previews."""

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

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)

        preview_content = QWidget()
        preview_content_layout = QVBoxLayout(preview_content)
        preview_content_layout.setContentsMargins(0, 0, 0, 0)
        preview_content_layout.setSpacing(12)

        self.preview_title = QLabel("Select a file to preview")
        self.preview_title.setProperty("subheading", True)
        preview_content_layout.addWidget(self.preview_title)

        self.preview_message = QLabel()
        self.preview_message.setWordWrap(True)
        preview_content_layout.addWidget(self.preview_message)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide()
        preview_content_layout.addWidget(self.image_preview)

        self.text_preview = QPlainTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.hide()
        preview_content_layout.addWidget(self.text_preview, stretch=1)

        self.table_preview = QTableWidget()
        self.table_preview.hide()
        preview_content_layout.addWidget(self.table_preview)

        tools_container = QWidget()
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(8)

        tool_buttons: List[tuple[str, Callable[..., Optional[str]], bool]] = [

            ("Plotter", run_plotter, True),
            ("AI Data Lab", run_ai_data_study, False),
            ("Train", run_training_simulation, False),
        ]

        for label, callback, requires_resource in tool_buttons:
            button = QPushButton(label)
            button.setProperty("secondary", True)
            button.clicked.connect(
                lambda _, name=label, runner=callback, needs_resource=requires_resource: self._launch_tool(
                    name, runner, needs_resource
                )
            )
            tools_layout.addWidget(button)

        tools_layout.addStretch()

        content_layout.addWidget(preview_content, stretch=4)
        content_layout.addWidget(tools_container, stretch=1)

        preview_layout.addLayout(content_layout, stretch=1)

        self.tool_tabs = QTabWidget()
        self.tool_tabs.hide()
        preview_layout.addWidget(self.tool_tabs, stretch=1)

        self.download_button = QPushButton("Download")
        self.download_button.setProperty("primary", True)
        self.download_button.setEnabled(False)
        preview_layout.addWidget(self.download_button)

        splitter.addWidget(preview_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)
        main_layout.addWidget(splitter, stretch=1)

        self.tree.currentItemChanged.connect(self._handle_selection)

        self._current_resource: Optional[LocalResource] = None
        self._tool_outputs: Dict[str, QPlainTextEdit] = {}

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

    def _show_table(self, df):
        self.table_preview.clear()
        self.table_preview.setRowCount(df.shape[0])
        self.table_preview.setColumnCount(df.shape[1])
        self.table_preview.setHorizontalHeaderLabels(df.columns.astype(str).tolist())

        # Fill table cells
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iat[row, col]))
                self.table_preview.setItem(row, col, item)

        self.table_preview.resizeColumnsToContents()
        self.table_preview.show()
        self.text_preview.hide()
        self.image_preview.hide()


    def populate(self, resources: Iterable[LocalResource]) -> None:
        self.clear()
        folders: Dict[str, QTreeWidgetItem] = {}
        root = self.tree.invisibleRootItem()

        for resource in resources:
            parent = root
            path_so_far: List[str] = []
            parts = list(resource.relative_path.parts)
            for folder_name in parts[:-1]:
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
                [
                    resource.display_name,
                    resource.absolute_path.suffix.replace(".", "").upper() or "File",
                    resource.folder,
                ]
            )
            file_item.setData(0, Qt.UserRole, {"type": "file", "resource": resource})
            parent.addChild(file_item)

        self.tree.expandAll()
        if self.tree.topLevelItemCount() == 0:
            self._show_message("No files were found on the shared drive.")

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

        resource: LocalResource = data["resource"]
        self._current_resource = resource
        self.download_button.setEnabled(True)
        self._preview_resource(resource)

    def _launch_tool(
            self,
            title: str,
            runner: Callable[..., Optional[str]],
            requires_resource: bool = False,
    ) -> None:
        path: Optional[Path] = None
        if requires_resource:
            if not self._current_resource:
                QMessageBox.information(
                    self,
                    f"{title} Tool",
                    "Please select a file before launching this tool.",
                )
                return
            path = self._current_resource.absolute_path
        try:
            if requires_resource:
                assert path is not None
                # Pass self as parent for plotter to close with main window
                if title == "Plotter":
                    output = runner(path, self)
                else:
                    output = runner(path)
            else:
                output = runner()
        except Exception as exc:
            output = f"An error occurred while running {title}: {exc}"

        if output is None:
            return

        if title in self._tool_outputs:
            text_edit = self._tool_outputs[title]
            text_edit.setPlainText(output)
            container = text_edit.parentWidget()
            index = self.tool_tabs.indexOf(container)
            if index != -1:
                self.tool_tabs.setCurrentIndex(index)
            self.tool_tabs.show()
            return

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(output)
        layout.addWidget(text_edit)

        self.tool_tabs.addTab(container, title)
        self.tool_tabs.show()
        self.tool_tabs.setCurrentWidget(container)
        self._tool_outputs[title] = text_edit

    def _preview_resource(self, resource: LocalResource) -> None:
        self.image_preview.hide()
        self.text_preview.hide()

        path = resource.absolute_path
        if not path.exists():
            self._show_message("File is not accessible on the shared drive.")
            return

        suffix = path.suffix.lower()
        image_ext = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
        text_ext = {".txt", ".csv", ".json", ".log", ".md"}

        if suffix in image_ext:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self._show_message("Unable to load image preview.")
                return
            self.image_preview.setPixmap(
                pixmap.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            self.image_preview.show()
            self._show_message("Image preview")
            return

        if suffix in text_ext:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read(12000)
                    if handle.read(1):
                        text += "\n\n… Preview truncated."
            except Exception as exc:
                self._show_message(f"Unable to read file: {exc}")
                return
            self.text_preview.setPlainText(text)
            self.text_preview.show()
            self._show_message("Text preview")
            return

        # Add parquet preview (replaces ASC preview)
        if suffix == ".parquet":
            try:
                import pandas as pd
                df = pd.read_parquet(path, engine='pyarrow')
            except Exception as exc:
                self._show_message(f"Unable to read parquet file: {exc}")
                return

            # Show first 300 rows as a table
            self._show_table(df.head(300))
            self._show_message("Parquet Table Preview")
            return

        # CSV or ASC → show as table
        if suffix in {".csv", ".asc"}:
            try:
                import pandas as pd
                df = pd.read_csv(path)
            except Exception as exc:
                self._show_message(f"Unable to read table file: {exc}")
                return

            self._show_table(df.head(300))
            self._show_message("Table Preview")
            return

        self._show_message("Preview is not available. Use Download to open the file.")

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

        source = self._current_resource.absolute_path
        if not source.exists():
            QMessageBox.critical(
                self,
                "Download Failed",
                "The source file is not accessible on the shared drive.",
            )
            return

        try:
            shutil.copy2(source, file_path)
        except Exception as exc:
            QMessageBox.critical(self, "Download Failed", f"Unable to copy file: {exc}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


def _collect_resources(
        manager: DatabaseManager, storage: LocalStorageManager
) -> List[LocalResource]:
    resources: List[LocalResource] = []
    for record in manager.list_uploads():
        file_path = record.file_path
        if not file_path:
            continue
        relative_path = Path(file_path)
        absolute_path = storage.base_path / relative_path

        # Check if a parquet version exists
        if absolute_path.suffix.lower() == '.asc':
            parquet_path = absolute_path.with_suffix('.parquet')
            if parquet_path.exists():
                # Use parquet instead of ASC
                absolute_path = parquet_path
                relative_path = parquet_path.relative_to(storage.base_path)

        # Skip ASC files if they don't have parquet equivalents
        if absolute_path.suffix.lower() == '.asc':
            continue

        resources.append(
            LocalResource(
                name=absolute_path.name,
                absolute_path=absolute_path,
                relative_path=relative_path,
                test_type=record.test_type,
                file_size=record.file_size,
                created_at=record.created_at,
            )
        )
    resources.sort(key=lambda res: (res.test_type.lower(), res.relative_path.parts))
    return resources

class ReaderApp(QMainWindow):
    """Main window that orchestrates authentication and browsing."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial Data Reader")
        self.setMinimumSize(1100, 700)

        self.config = get_config()
        self.db_manager = DatabaseManager()
        self.storage_manager = LocalStorageManager(config=self.config, database=self.db_manager)
        self.auth_store = LocalAuthStore(self.db_manager)
        self.current_user: Optional[LocalUser] = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.login_page = ReaderLoginPage()
        self.dashboard = ReaderDashboard()

        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard)

        self.login_page.login_requested.connect(self.handle_login)
        self.login_page.signup_requested.connect(self.open_signup_dialog)
        self.dashboard.logout_requested.connect(self.handle_logout)
        self.dashboard.refresh_requested.connect(self.refresh_resources)
        self.dashboard.download_button.clicked.connect(self.dashboard.download_current)

    def show_login(self) -> None:
        self.login_page.reset_fields()
        self.stack.setCurrentWidget(self.login_page)
        self.dashboard.clear()

    def show_dashboard(self) -> None:
        self.stack.setCurrentWidget(self.dashboard)

    def handle_login(self, email: str, password: str, security_code: str) -> None:
        if not email or not password or not security_code:
            self.login_page.show_error("Email, password, and security code are required.")
            return

        try:
            expected_code = get_reader_security_code()
            if security_code != expected_code:
                self.login_page.show_error("Invalid security code.")
                return
        except RuntimeError as exc:
            self.login_page.show_error(f"Configuration error: {exc}")
            return

        user = self.auth_store.authenticate(email, password)
        if not user:
            self.login_page.show_error("Invalid email or password.")
            return
        role = user.metadata.get("role")
        if role and role != "reader":
            self.login_page.show_error("This account does not have reader access.")
            return

        self.login_page.show_error("")
        self.current_user = user
        display_name = user.metadata.get("display_name") or user.display_name()
        self.dashboard.set_user_identity(display_name, user.email)
        self.show_dashboard()
        self.refresh_resources()

    def open_signup_dialog(self) -> None:
        dialog = ReaderSignupDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        metadata: Dict[str, str] = {"role": "reader"}
        if result.get("display_name"):
            metadata["display_name"] = result["display_name"]

        try:
            self.auth_store.create_user(
                email=result["email"],
                password=result["password"],
                metadata=metadata,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Reader Signup", str(exc))
            return

        QMessageBox.information(
            self,
            "Reader Signup",
            "Account created successfully. You can now sign in.",
        )
        self.show_login()
        self.login_page.email_input.setText(result["email"])

    def handle_logout(self) -> None:
        self.current_user = None
        self.show_login()

    def refresh_resources(self) -> None:
        if not self.current_user:
            self.login_page.show_error("Please sign in to view files.")
            self.show_login()
            return

        base_path = self.storage_manager.base_path
        if not base_path.exists():
            QMessageBox.critical(
                self,
                "Shared Drive Error",
                "The shared drive is not accessible. Please check your connection.",
            )
            return

        self.db_manager.prune_missing_uploads(base_path)

        try:
            resources = _collect_resources(self.db_manager, self.storage_manager)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Shared Drive Error",
                f"Unable to load local resources: {exc}",
            )
            return

        display_name = (
            self.current_user.metadata.get("display_name")
            or self.current_user.display_name()
        )
        self.dashboard.set_user_identity(display_name, self.current_user.email)
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