"""Standalone reader application for browsing shared-drive assets."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.ai.toolkit import (  # run_ai_data_study,; run_training_simulation,
    run_anomaly_detector_standalone,
    run_plotter,
)
from industrial_data_system.apps.desktop.uploader import IndustrialTheme
from industrial_data_system.core.auth import LocalAuthStore, LocalUser, SessionManager
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
    pump_series: str
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
    back_to_gateway_requested = pyqtSignal()

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
        email_label.setStyleSheet(f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;")
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("reader@example.com")
        form_layout.addWidget(self.email_input)

        password_label = QLabel("Password")
        password_label.setStyleSheet(f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;")
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(self.password_input)

        code_label = QLabel("Security Code")
        code_label.setStyleSheet(f"color: {IndustrialTheme.TEXT_SECONDARY}; font-weight: 500;")
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

        back_button = QPushButton("← Back to App Selection")
        back_button.setProperty("flat", True)
        back_button.clicked.connect(self.back_to_gateway_requested.emit)
        form_layout.addWidget(back_button)

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
        self.display_name_input.setPlaceholderText("Reader Name (optional)")
        form_layout.addRow("Display Name", self.display_name_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Password")
        form_layout.addRow("Password", self.password_input)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        form_layout.addRow("Confirm", self.confirm_password_input)

        layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #EF4444; font-weight: 500;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self.error_label.hide()
        email = self.email_input.text().strip().lower()
        display_name = self.display_name_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not email or not password:
            self.error_label.setText("Email and password are required.")
            self.error_label.show()
            return

        if password != confirm_password:
            self.error_label.setText("Passwords do not match.")
            self.error_label.show()
            return

        super().accept()

    def get_result(self) -> Optional[Dict[str, str]]:
        if self.result() != QDialog.Accepted:
            return None
        return {
            "email": self.email_input.text().strip().lower(),
            "password": self.password_input.text(),
            "display_name": self.display_name_input.text().strip(),
        }


class ReaderDashboard(QWidget):
    """Main dashboard for browsing local resources."""

    logout_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    open_tool_in_tab = pyqtSignal(str, QWidget)  # Signal to open tool in new tab

    def __init__(self) -> None:
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet(f"background-color: {IndustrialTheme.SURFACE}; border-bottom: 1px solid #E5E7EB;")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(16, 0, 16, 0)

        self.user_label = QLabel("Reader Dashboard")
        self.user_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {IndustrialTheme.TEXT_PRIMARY};")
        top_bar_layout.addWidget(self.user_label)
        top_bar_layout.addStretch()

        refresh_button = QPushButton("Refresh")
        refresh_button.setProperty("secondary", True)
        refresh_button.clicked.connect(self.refresh_requested.emit)
        top_bar_layout.addWidget(refresh_button)

        logout_button = QPushButton("Logout")
        logout_button.setProperty("secondary", True)
        logout_button.clicked.connect(self.logout_requested.emit)
        top_bar_layout.addWidget(logout_button)

        main_layout.addWidget(top_bar)

        # File browser
        splitter = QSplitter(Qt.Horizontal)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(16, 16, 8, 16)

        tree_header = QLabel("Files & Folders")
        tree_header.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {IndustrialTheme.TEXT_PRIMARY};")
        tree_layout.addWidget(tree_header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Series", "Path"])
        self.tree.setAlternatingRowColors(True)
        self.tree.header().setSectionResizeMode(0, self.tree.header().Stretch)
        tree_layout.addWidget(self.tree)

        splitter.addWidget(tree_container)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(8, 16, 16, 16)

        preview_header = QLabel("Preview & Tools")
        preview_header.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {IndustrialTheme.TEXT_PRIMARY};")
        preview_layout.addWidget(preview_header)

        content_layout = QHBoxLayout()

        # Preview area
        preview_content = QWidget()
        preview_content_layout = QVBoxLayout(preview_content)
        preview_content_layout.setContentsMargins(0, 0, 0, 0)

        self.message_label = QLabel("Select a file to preview")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(f"color: {IndustrialTheme.TEXT_SECONDARY}; font-size: 14px;")
        preview_content_layout.addWidget(self.message_label)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.hide()
        preview_content_layout.addWidget(self.image_preview)

        self.text_preview = QPlainTextEdit()
        self.text_preview.setReadOnly(True)
        self.text_preview.hide()
        preview_content_layout.addWidget(self.text_preview)

        # Table preview for parquet files
        self.table_preview = QTableWidget()
        self.table_preview.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.hide()
        preview_content_layout.addWidget(self.table_preview)

        # Tools panel
        tools_container = QWidget()
        tools_container.setMaximumWidth(200)
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(8, 0, 0, 0)
        tools_layout.setSpacing(8)

        tools_label = QLabel("AI Tools")
        tools_label.setStyleSheet(f"font-weight: 600; color: {IndustrialTheme.TEXT_PRIMARY};")
        tools_layout.addWidget(tools_label)

        self.plotter_button = QPushButton("Plotter")
        self.plotter_button.setProperty("secondary", True)
        self.plotter_button.clicked.connect(lambda: self._launch_tool("Plotter", run_plotter, True))
        tools_layout.addWidget(self.plotter_button)

        self.anomaly_button = QPushButton("Anomaly Detector")
        self.anomaly_button.setProperty("secondary", True)
        self.anomaly_button.clicked.connect(lambda: self._launch_tool("Anomaly Detector", run_anomaly_detector_standalone, False))
        tools_layout.addWidget(self.anomaly_button)

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

        # Include index as first column
        df_with_index = df.reset_index()

        self.table_preview.setRowCount(df_with_index.shape[0])
        self.table_preview.setColumnCount(df_with_index.shape[1])

        # Set headers
        headers = df_with_index.columns.astype(str).tolist()
        self.table_preview.setHorizontalHeaderLabels(headers)

        # Fill table cells
        for row in range(df_with_index.shape[0]):
            for col in range(df_with_index.shape[1]):
                item = QTableWidgetItem(str(df_with_index.iat[row, col]))
                self.table_preview.setItem(row, col, item)

        # Auto-resize columns
        self.table_preview.resizeColumnsToContents()
        self.table_preview.setColumnWidth(0, 60)  # Index column

        # IMPORTANT: Resize rows to content
        self.table_preview.resizeRowsToContents()

        # Show table and hide others
        self.table_preview.show()
        self.text_preview.hide()
        self.image_preview.hide()

        # Force minimum size
        self.table_preview.setMinimumHeight(400)

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
                        [folder_name, "Folder", "", "/".join(path_so_far[:-1])]
                    )
                    folder_item.setData(0, Qt.UserRole, {"type": "folder"})
                    parent.addChild(folder_item)
                    folders[path_key] = folder_item
                parent = folders[path_key]

            file_item = QTreeWidgetItem(
                [
                    resource.display_name,
                    resource.absolute_path.suffix.replace(".", "").upper() or "File",
                    resource.pump_series,
                    resource.folder,
                ]
            )
            file_item.setData(0, Qt.UserRole, {"type": "file", "resource": resource})
            parent.addChild(file_item)

        self.tree.expandAll()
        if self.tree.topLevelItemCount() == 0:
            self._show_message("No files were found on the shared drive.")

    def _handle_selection(
        self, current: Optional[QTreeWidgetItem], _: Optional[QTreeWidgetItem]
    ) -> None:
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

        # Handle Plotter - create widget
        if title == "Plotter" and path:
            try:
                from industrial_data_system.ai.visualization.plotter import create_plotter_widget
                plotter_widget = create_plotter_widget(path)
                if plotter_widget:
                    self.open_tool_in_tab.emit(f"Plotter - {path.name}", plotter_widget)
                return
            except Exception as exc:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Plotter Error", f"Failed to create plotter: {exc}")
                return

        # Handle Anomaly Detector - create widget
        if title == "Anomaly Detector":
            try:
                from industrial_data_system.ai.anomaly_detection.anomaly_detector import create_anomaly_widget
                anomaly_widget = create_anomaly_widget(path)  # path can be None for standalone
                if anomaly_widget:
                    tab_title = f"Anomaly Detector - {path.name}" if path else "Anomaly Detector"
                    self.open_tool_in_tab.emit(tab_title, anomaly_widget)
                return
            except Exception as exc:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Anomaly Detector Error", f"Failed to create anomaly detector: {exc}")
                return

        # For any other tools that return text output
        try:
            if requires_resource:
                assert path is not None
                output = runner(path)
            else:
                output = runner()
        except Exception as exc:
            output = f"An error occurred while running {title}: {exc}"

        if output is None:
            return

        # Create a widget for text output
        tool_widget = QWidget()
        layout = QVBoxLayout(tool_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(output)
        layout.addWidget(text_edit)

        self.open_tool_in_tab.emit(title, tool_widget)

    def _preview_resource(self, resource: LocalResource) -> None:
        self.image_preview.hide()
        self.text_preview.hide()
        self.table_preview.hide()

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

        # Add parquet preview
        if suffix == ".parquet":
            try:
                import pandas as pd

                df = pd.read_parquet(path, engine="pyarrow")
            except Exception as exc:
                self._show_message(f"Unable to read parquet file: {exc}")
                return

            # Check if DataFrame is empty
            if len(df) == 0:
                self._show_message("Parquet file is empty.")
                return

            # Limit preview to first 1000 rows
            df_preview = df.head(1000)
            self._show_table(df_preview)
            self._show_message(f"Parquet preview (showing {len(df_preview)} of {len(df)} rows)")
            return

        self._show_message("No preview available for this file type.")

    def _show_message(self, text: str) -> None:
        self.message_label.setText(text)
        self.message_label.show()

    def download_current(self) -> None:
        if not self._current_resource:
            QMessageBox.information(self, "Download", "No file is selected.")
            return

        src_path = self._current_resource.absolute_path
        if not src_path.exists():
            QMessageBox.warning(
                self,
                "Download",
                "The selected file could not be found on the shared drive.",
            )
            return

        dest_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            src_path.name,
            f"All Files (*{src_path.suffix})",
        )

        if not dest_path:
            return

        try:
            shutil.copy2(src_path, dest_path)
            QMessageBox.information(
                self,
                "Download",
                f"File saved successfully to:\n{dest_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to copy file:\n{exc}",
            )


def _collect_resources(
    db_manager: DatabaseManager,
    storage_manager: LocalStorageManager,
) -> List[LocalResource]:
    """Collect all uploaded resources from the shared drive."""
    resources: List[LocalResource] = []
    upload_records = db_manager.list_uploads()

    for record in upload_records:
        absolute_path = storage_manager.base_path / record.pump_series / record.test_type / record.filename
        relative_path = Path(record.pump_series) / record.test_type / record.filename

        if not absolute_path.exists():
            continue

        file_size = absolute_path.stat().st_size if absolute_path.exists() else None
        resources.append(
            LocalResource(
                name=record.filename,
                absolute_path=absolute_path,
                relative_path=relative_path,
                test_type=record.test_type,
                pump_series=record.pump_series,
                file_size=file_size,
                created_at=record.created_at,
            )
        )

    return resources


class ReaderApp(QMainWindow):
    """Main application window for the reader portal."""

    def __init__(self) -> None:
        super().__init__()
        try:
            self.setWindowTitle("Reader Portal")
            self.setMinimumSize(1100, 700)

            self.config = get_config()
            self.db_manager = DatabaseManager()
            self.storage_manager = LocalStorageManager(config=self.config, database=self.db_manager)
            self.auth_store = LocalAuthStore(self.db_manager)
            self.current_user: Optional[LocalUser] = None

            self.session_manager = SessionManager(timeout_minutes=30)

            # Add session timeout checker
            self.session_timer = QTimer(self)
            self.session_timer.timeout.connect(self._check_session_timeout)
            self.session_timer.start(60000)  # Check every minute

            self.stack = QStackedWidget()
            self.setCentralWidget(self.stack)

            self.login_page = ReaderLoginPage()
            self.dashboard = ReaderDashboard()

            self.stack.addWidget(self.login_page)
            self.stack.addWidget(self.dashboard)

            self.login_page.login_requested.connect(self.handle_login)
            self.login_page.signup_requested.connect(self.open_signup_dialog)
            self.login_page.back_to_gateway_requested.connect(self.close)
            self.dashboard.logout_requested.connect(self.handle_logout)
            self.dashboard.refresh_requested.connect(self.refresh_resources)
            self.dashboard.download_button.clicked.connect(self.dashboard.download_current)
            # Don't connect open_tool_in_tab here - it will be connected by parent TabbedDesktopApp
        except Exception as e:
            print(f"Error initializing ReaderApp: {e}")
            import traceback
            traceback.print_exc()
            raise

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

        # CHECK FOR ACCOUNT LOCKOUT FIRST
        failed_count = self.db_manager.get_failed_login_count(email, minutes=15)
        if failed_count >= 5:
            self.login_page.show_error(
                "Account temporarily locked due to multiple failed login attempts. "
                "Please try again in 15 minutes."
            )
            return

        user = self.auth_store.authenticate(email, password)
        if not user:
            # Log failed login
            self.db_manager.log_security_event(
                user_id=None,
                event_type="LOGIN_FAILED",
                description=f"Failed login attempt for email: {email}",
                success=False,
            )
            remaining_attempts = 5 - failed_count - 1
            if remaining_attempts > 0:
                self.login_page.show_error(
                    f"Invalid email or password. {remaining_attempts} attempts remaining."
                )
            else:
                self.login_page.show_error(
                    "Invalid email or password. Account will be locked after next failed attempt."
                )
            return

        # Log successful login
        self.db_manager.log_security_event(
            user_id=user.id,
            event_type="LOGIN_SUCCESS",
            description=f"Successful login for user: {email}",
            success=True,
        )

        self.session_manager.create_session(user.id)
        self.current_user = user

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
        if self.current_user:
            self.session_manager.invalidate_session(self.current_user.id)
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
            self.current_user.metadata.get("display_name") or self.current_user.display_name()
        )
        self.dashboard.set_user_identity(display_name, self.current_user.email)
        self.dashboard.populate(resources)

    def _check_session_timeout(self) -> None:
        """Check if current session has timed out."""
        if not self.current_user:
            return

        user_id = self.current_user.id
        if not self.session_manager.is_session_valid(user_id):
            self._handle_session_timeout()
        else:
            # Update activity on any interaction
            self.session_manager.update_activity(user_id)

    def _handle_session_timeout(self) -> None:
        """Handle session timeout - force logout."""
        if self.current_user:
            self.session_manager.invalidate_session(self.current_user.id)

        QMessageBox.information(
            self,
            "Session Expired",
            "Your session has expired due to inactivity. Please sign in again.",
        )
        self.handle_logout()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(IndustrialTheme.get_stylesheet())
    app.setFont(QFont("Segoe UI", 10))

    window = ReaderApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()