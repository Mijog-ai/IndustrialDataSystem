"""Application gateway that routes to the upload or reader tools."""
from __future__ import annotations

import sys
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import IndustrialDataApp, IndustrialTheme
from reader_app import ReaderApp


class GatewayWindow(QMainWindow):
    """Simple landing window that lets the operator choose an app."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial Data System")
        self.setMinimumSize(520, 360)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        title = QLabel("Select an application to launch")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Choose between uploading new data or browsing existing Cloudinary files."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setProperty("caption", True)
        layout.addWidget(subtitle)

        self.upload_button = QPushButton("Upload App")
        self.upload_button.setProperty("primary", True)
        self.upload_button.setMinimumHeight(48)
        self.upload_button.clicked.connect(self.launch_upload_app)
        layout.addWidget(self.upload_button)

        self.reader_button = QPushButton("Read & Process App")
        self.reader_button.setProperty("secondary", True)
        self.reader_button.setMinimumHeight(48)
        self.reader_button.clicked.connect(self.launch_reader_app)
        layout.addWidget(self.reader_button)

        self.setCentralWidget(container)

        self._open_windows: List[QMainWindow] = []

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


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(IndustrialTheme.get_stylesheet())
    app.setFont(QFont("Segoe UI", 10))

    gateway = GatewayWindow()
    gateway.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
