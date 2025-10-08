"""PyQt5 application providing authentication, CSV preview, and OneDrive uploads."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

from auth import (
    LoginError,
    RegistrationError,
    approve_user,
    authenticate_user,
    list_pending_users,
    register_user,
    reject_user,
    User,
)
from onedrive_upload import upload_file_to_onedrive


class DropArea(QtWidgets.QLabel):
    """Widget that accepts dragged CSV files."""

    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("Drop CSV Here")
        self.setStyleSheet(
            """
            QLabel {
                border: 2px dashed #2980b9;
                border-radius: 6px;
                padding: 16px;
                background-color: #ecf6fd;
                color: #2980b9;
                font-weight: bold;
            }
            """
        )
        self.setMinimumSize(200, 120)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls() and any(url.toLocalFile().lower().endswith(".csv") for url in event.mimeData().urls()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".csv"):
                self.fileDropped.emit(path)
                break
        event.acceptProposedAction()


class CsvViewer(QtWidgets.QTableWidget):
    """Simple table widget to display pandas DataFrames."""

    def load_dataframe(self, frame: pd.DataFrame) -> None:
        self.clear()
        self.setRowCount(len(frame.index))
        self.setColumnCount(len(frame.columns))
        self.setHorizontalHeaderLabels([str(column) for column in frame.columns])
        for row_index, (_, row) in enumerate(frame.iterrows()):
            for column_index, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value))
                self.setItem(row_index, column_index, item)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()


class MainWindow(QtWidgets.QMainWindow):
    """Main application window for approved end users."""

    def __init__(self, user: User) -> None:
        super().__init__()
        self.user = user
        self.setWindowTitle(f"Industrial Data System - {user.username}")
        self.resize(900, 600)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.upload_button = QtWidgets.QPushButton("Upload CSV")
        self.upload_button.clicked.connect(self.open_file_dialog)

        self.viewer = CsvViewer()

        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.process_file)

        layout.addWidget(self.upload_button, 0, 0, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        layout.addWidget(self.viewer, 1, 0, 1, 2)
        layout.addWidget(self.drop_area, 2, 1, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.setCentralWidget(central)

    def open_file_dialog(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV", str(Path.home()), "CSV Files (*.csv)"
        )
        if file_path:
            self.process_file(file_path)

    def process_file(self, path: str) -> None:
        try:
            dataframe = pd.read_csv(path)
        except Exception as exc:  # pragma: no cover - GUI feedback path
            QtWidgets.QMessageBox.critical(self, "CSV Error", f"Failed to read CSV file:\n{exc}")
            return

        self.viewer.load_dataframe(dataframe)

        try:
            upload_file_to_onedrive(path, self.user.username)
        except Exception as exc:  # pragma: no cover - GUI feedback path
            QtWidgets.QMessageBox.critical(self, "Upload Failed", str(exc))
            return

        QtWidgets.QMessageBox.information(
            self,
            "Upload Complete",
            f"{Path(path).name} uploaded to OneDrive successfully.",
        )


class LoginWidget(QtWidgets.QWidget):
    loginRequested = QtCore.pyqtSignal(str, str)
    showRegister = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Login")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        login_button = QtWidgets.QPushButton("Login")
        login_button.clicked.connect(self._emit_login)

        register_link = QtWidgets.QPushButton("Register")
        register_link.setFlat(True)
        register_link.clicked.connect(self.showRegister.emit)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(login_button)
        layout.addSpacing(6)
        layout.addWidget(register_link)
        layout.addStretch(1)

    def _emit_login(self) -> None:
        self.loginRequested.emit(self.username_input.text(), self.password_input.text())


class RegisterWidget(QtWidgets.QWidget):
    registerRequested = QtCore.pyqtSignal(str, str, str)
    showLogin = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Register")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("Email")

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        register_button = QtWidgets.QPushButton("Submit Registration")
        register_button.clicked.connect(self._emit_register)

        login_link = QtWidgets.QPushButton("Back to Login")
        login_link.setFlat(True)
        login_link.clicked.connect(self.showLogin.emit)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(register_button)
        layout.addSpacing(6)
        layout.addWidget(login_link)
        layout.addStretch(1)

    def _emit_register(self) -> None:
        self.registerRequested.emit(
            self.username_input.text(), self.email_input.text(), self.password_input.text()
        )


class AdminPanel(QtWidgets.QMainWindow):
    def __init__(self, admin: User) -> None:
        super().__init__()
        self.admin = admin
        self.setWindowTitle("Admin Panel - Pending Users")
        self.resize(500, 400)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        self.pending_list = QtWidgets.QListWidget()

        button_layout = QtWidgets.QHBoxLayout()
        self.approve_button = QtWidgets.QPushButton("Approve")
        self.reject_button = QtWidgets.QPushButton("Reject")
        self.refresh_button = QtWidgets.QPushButton("Refresh")

        self.approve_button.clicked.connect(self.approve_selected)
        self.reject_button.clicked.connect(self.reject_selected)
        self.refresh_button.clicked.connect(self.refresh_pending)

        button_layout.addWidget(self.approve_button)
        button_layout.addWidget(self.reject_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.refresh_button)

        layout.addWidget(QtWidgets.QLabel(f"Logged in as admin: {admin.username}"))
        layout.addWidget(self.pending_list)
        layout.addLayout(button_layout)

        self.setCentralWidget(central)

        self.refresh_pending()

    def refresh_pending(self) -> None:
        self.pending_list.clear()
        for user in list_pending_users():
            item = QtWidgets.QListWidgetItem(f"{user.username} ({user.email}) - {user.status}")
            item.setData(QtCore.Qt.UserRole, user.username)
            self.pending_list.addItem(item)

    def _selected_username(self) -> str | None:
        item = self.pending_list.currentItem()
        if item:
            return item.data(QtCore.Qt.UserRole)
        QtWidgets.QMessageBox.warning(self, "Selection Required", "Select a user first.")
        return None

    def approve_selected(self) -> None:
        username = self._selected_username()
        if not username:
            return
        approve_user(username)
        QtWidgets.QMessageBox.information(self, "User Approved", f"{username} is now approved.")
        self.refresh_pending()

    def reject_selected(self) -> None:
        username = self._selected_username()
        if not username:
            return
        reject_user(username)
        QtWidgets.QMessageBox.information(self, "User Rejected", f"{username} has been rejected.")
        self.refresh_pending()


class AuthWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Industrial Data System - Login")
        self.resize(360, 320)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        self.stack = QtWidgets.QStackedWidget()
        self.login_widget = LoginWidget()
        self.register_widget = RegisterWidget()

        self.login_widget.loginRequested.connect(self.handle_login)
        self.login_widget.showRegister.connect(self.show_register)

        self.register_widget.registerRequested.connect(self.handle_registration)
        self.register_widget.showLogin.connect(self.show_login)

        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.register_widget)

        layout.addWidget(self.stack)
        self.setCentralWidget(central)

        self.main_window: MainWindow | None = None
        self.admin_panel: AdminPanel | None = None

    def show_register(self) -> None:
        self.stack.setCurrentWidget(self.register_widget)

    def show_login(self) -> None:
        self.stack.setCurrentWidget(self.login_widget)

    def handle_login(self, username: str, password: str) -> None:
        try:
            user = authenticate_user(username, password)
        except LoginError as exc:
            QtWidgets.QMessageBox.warning(self, "Login Failed", str(exc))
            return

        if user.role == "admin":
            self.admin_panel = AdminPanel(user)
            self.admin_panel.show()
            QtWidgets.QMessageBox.information(
                self, "Admin Login", "Admin panel opened in a new window."
            )
            self.close()
            return

        if user.status != "approved":
            QtWidgets.QMessageBox.information(
                self,
                "Awaiting Approval",
                "Your registration is pending admin approval.",
            )
            return

        self.main_window = MainWindow(user)
        self.main_window.show()
        self.close()

    def handle_registration(self, username: str, email: str, password: str) -> None:
        try:
            register_user(username, email, password)
        except RegistrationError as exc:
            QtWidgets.QMessageBox.warning(self, "Registration Failed", str(exc))
            return

        QtWidgets.QMessageBox.information(
            self,
            "Registration Submitted",
            "Registration received. Please wait for admin approval before logging in.",
        )
        self.show_login()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
