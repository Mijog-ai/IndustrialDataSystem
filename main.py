"""Application gateway that routes to the upload or reader tools."""

from __future__ import annotations

import sys
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCloseEvent, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.apps import DesktopTheme, IndustrialDataApp, ReaderApp

# Enable High DPI scaling for different screen resolutions
if hasattr(Qt, "AA_EnableHighDpiScaling"):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class GatewayWindow(QMainWindow):
    """Simple landing window that lets the operator choose an app."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Inline Data System")
        self.setMinimumSize(480, 300)

        # Create menu bar
        self._create_menu_bar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Inline Data System")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Application selection group box
        app_group = QGroupBox("Select Application")
        app_layout = QVBoxLayout(app_group)
        app_layout.setSpacing(12)

        subtitle = QLabel(
            "Choose between uploading new data or browsing existing files."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        app_layout.addWidget(subtitle)

        self.upload_button = QPushButton("Upload App")
        self.upload_button.setProperty("primary", True)
        self.upload_button.setMinimumHeight(32)
        self.upload_button.clicked.connect(self.launch_upload_app)
        app_layout.addWidget(self.upload_button)

        self.reader_button = QPushButton("Read && Process App")
        self.reader_button.setProperty("secondary", True)
        self.reader_button.setMinimumHeight(32)
        self.reader_button.clicked.connect(self.launch_reader_app)
        app_layout.addWidget(self.reader_button)

        main_layout.addWidget(app_group)
        main_layout.addStretch()

        self.setCentralWidget(container)

        self._open_windows: List[QMainWindow] = []

    def _create_menu_bar(self) -> None:
        """Create traditional desktop menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        upload_action = QAction("Launch &Upload App", self)
        upload_action.setShortcut(QKeySequence("Ctrl+U"))
        upload_action.triggered.connect(self.launch_upload_app)
        file_menu.addAction(upload_action)

        reader_action = QAction("Launch &Reader App", self)
        reader_action.setShortcut(QKeySequence("Ctrl+R"))
        reader_action.triggered.connect(self.launch_reader_app)
        file_menu.addAction(reader_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Alt+F4"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _show_about_dialog(self) -> None:
        """Show about dialog."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About Inline Data System",
            "<h3>Inline Data System</h3>"
            "<p>Version 1.0</p>"
            "<p>Gateway for industrial data management applications.</p>"
        )

    # ------------------------------------------------------------------
    # Launch helpers
    # ------------------------------------------------------------------
    def _track_window(self, window: QMainWindow) -> None:
        self._open_windows.append(window)
        window.destroyed.connect(lambda: self._on_child_closed(window))

    def _on_child_closed(self, window: QMainWindow) -> None:
        try:
            self._open_windows.remove(window)
        except ValueError:
            pass
        if not self._open_windows:
            self.show()

    def launch_upload_app(self) -> None:
        window = IndustrialDataApp()
        self._track_window(window)
        window.show()
        self.hide()

    def launch_reader_app(self) -> None:
        window = ReaderApp()
        self._track_window(window)
        window.show()
        self.hide()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Quit the application when the gateway window is closed."""
        for window in self._open_windows:
            window.close()
        QApplication.quit()
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(DesktopTheme.get_stylesheet())
    app.setFont(QFont("Segoe UI", 9))
    app.setQuitOnLastWindowClosed(False)

    gateway = GatewayWindow()
    gateway.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
