"""PyQt5 application providing authentication, CSV preview, and cloud uploads."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from pandas.errors import ParserError
from PyQt5 import QtCore, QtGui, QtWidgets
from dotenv import load_dotenv

from auth import (
    LoginError,
    RegistrationError,
    PasswordResetError,
    SessionError,
    approve_user,
    authenticate_user,
    create_session_token,
    list_pending_users,
    request_password_reset,
    reset_password,
    validate_session_token,
    register_user,
    reject_user,
    User,
)
from cloudinary_upload import upload_to_cloudinary

load_dotenv()


class DropArea(QtWidgets.QLabel):
    """Widget that accepts dragged CSV files."""

    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setText("Drop CSV Here to Preview & Upload")
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

    logoutRequested = QtCore.pyqtSignal()

    def __init__(self, user: User, session_token: str) -> None:
        super().__init__()
        self.user = user
        self.session_token = session_token
        self._logout_in_progress = False
        self.setWindowTitle(f"Industrial Data System - {user.username}")
        self.resize(900, 600)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.upload_button = QtWidgets.QPushButton("Upload CSV")
        self.upload_button.clicked.connect(self.open_file_dialog)

        self.logout_button = QtWidgets.QPushButton("Logout")
        self.logout_button.clicked.connect(self._trigger_logout)

        self.viewer = CsvViewer()

        self.drop_area = DropArea()
        self.drop_area.fileDropped.connect(self.process_file)

        layout.addWidget(self.upload_button, 0, 0, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        layout.addWidget(self.logout_button, 0, 1, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        layout.addWidget(self.viewer, 1, 0, 1, 2)
        layout.addWidget(self.drop_area, 2, 1, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)

        layout.setRowStretch(1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.setCentralWidget(central)

    def open_file_dialog(self) -> None:
        if not self._ensure_session_active():
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select CSV", str(Path.home()), "CSV Files (*.csv)"
        )
        if file_path:
            self.process_file(file_path)

    def process_file(self, path: str) -> None:
        if not self._ensure_session_active():
            return
        try:
            dataframe = self._read_csv_with_fallback(path)
        except Exception as exc:  # pragma: no cover - GUI feedback path
            QtWidgets.QMessageBox.critical(self, "CSV Error", f"Failed to read CSV file:\n{exc}")
            return

        self.viewer.load_dataframe(dataframe)

        reply = QtWidgets.QMessageBox.question(
            self,
            "Upload to Cloudinary?",
            (
                f"Preview loaded for {Path(path).name}.\n\n"
                "Would you like to upload this file to Cloudinary now?"
            ),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        try:
            url = upload_to_cloudinary(path, self.user.username)
        except Exception as exc:  # pragma: no cover - GUI feedback path
            QtWidgets.QMessageBox.critical(self, "Upload Failed", str(exc))
            return

        QtWidgets.QMessageBox.information(
            self,
            "Upload Complete",
            f"{Path(path).name} uploaded to Cloudinary successfully.\nURL: {url}",
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if not self._logout_in_progress:
            self.logoutRequested.emit()
        super().closeEvent(event)

    def _trigger_logout(self) -> None:
        if self._logout_in_progress:
            return
        self._logout_in_progress = True
        self.logoutRequested.emit()
        self.close()

    def _ensure_session_active(self) -> bool:
        try:
            validate_session_token(self.session_token)
        except SessionError as exc:
            QtWidgets.QMessageBox.warning(self, "Session Expired", str(exc))
            self._trigger_logout()
            return False
        return True

    def _read_csv_with_fallback(self, path: str) -> pd.DataFrame:
        """Load CSV allowing delimiter detection when default parsing fails."""

        try:
            return pd.read_csv(path)
        except ParserError:
            # Some files use semicolons or other delimiters which raise a
            # ``ParserError`` when read with the default C engine. Re-try with
            # the Python engine so pandas can sniff the delimiter.
            return pd.read_csv(path, sep=None, engine="python")


class LoginWidget(QtWidgets.QWidget):
    loginRequested = QtCore.pyqtSignal(str, str)
    showRegister = QtCore.pyqtSignal()
    showForgot = QtCore.pyqtSignal()

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

        forgot_link = QtWidgets.QPushButton("Forgot Password?")
        forgot_link.setFlat(True)
        forgot_link.clicked.connect(self.showForgot.emit)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(login_button)
        layout.addSpacing(6)
        layout.addWidget(register_link)
        layout.addWidget(forgot_link)
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


class ForgotPasswordWidget(QtWidgets.QWidget):
    resetRequested = QtCore.pyqtSignal(str)
    showLogin = QtCore.pyqtSignal()
    showReset = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Forgot Password")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        description = QtWidgets.QLabel(
            "Enter the email address associated with your account to receive a reset token."
        )
        description.setWordWrap(True)

        self.email_input = QtWidgets.QLineEdit()
        self.email_input.setPlaceholderText("Email")

        send_button = QtWidgets.QPushButton("Send Reset Link")
        send_button.clicked.connect(self._emit_reset_request)

        login_link = QtWidgets.QPushButton("Back to Login")
        login_link.setFlat(True)
        login_link.clicked.connect(self.showLogin.emit)

        have_token_link = QtWidgets.QPushButton("Already have a token? Reset Password")
        have_token_link.setFlat(True)
        have_token_link.clicked.connect(self.showReset.emit)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(description)
        layout.addWidget(self.email_input)
        layout.addWidget(send_button)
        layout.addSpacing(6)
        layout.addWidget(have_token_link)
        layout.addWidget(login_link)
        layout.addStretch(1)

    def _emit_reset_request(self) -> None:
        email = self.email_input.text().strip()
        if not email:
            QtWidgets.QMessageBox.warning(self, "Email Required", "Enter your email first.")
            return
        self.resetRequested.emit(email)


class ResetPasswordWidget(QtWidgets.QWidget):
    resetSubmitted = QtCore.pyqtSignal(str, str)
    showLogin = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

        title = QtWidgets.QLabel("Reset Password")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        description = QtWidgets.QLabel(
            "Paste the reset token from your email and set a new password."
        )
        description.setWordWrap(True)

        self.token_input = QtWidgets.QLineEdit()
        self.token_input.setPlaceholderText("Reset Token")

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("New Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)

        self.confirm_input = QtWidgets.QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm Password")
        self.confirm_input.setEchoMode(QtWidgets.QLineEdit.Password)

        reset_button = QtWidgets.QPushButton("Update Password")
        reset_button.clicked.connect(self._emit_reset)

        login_link = QtWidgets.QPushButton("Back to Login")
        login_link.setFlat(True)
        login_link.clicked.connect(self.showLogin.emit)

        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(description)
        layout.addWidget(self.token_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(reset_button)
        layout.addSpacing(6)
        layout.addWidget(login_link)
        layout.addStretch(1)

    def _emit_reset(self) -> None:
        token = self.token_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        if not token or not password:
            QtWidgets.QMessageBox.warning(
                self, "Details Required", "Provide both the reset token and new password."
            )
            return
        if password != confirm:
            QtWidgets.QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return
        self.resetSubmitted.emit(token, password)

class AdminPanel(QtWidgets.QMainWindow):
    logoutRequested = QtCore.pyqtSignal()

    def __init__(self, admin: User) -> None:
        super().__init__()
        self.admin = admin
        self._logout_in_progress = False
        self.setWindowTitle("Admin Panel - Pending Users")
        self.resize(500, 400)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)

        self.pending_list = QtWidgets.QListWidget()

        button_layout = QtWidgets.QHBoxLayout()
        self.approve_button = QtWidgets.QPushButton("Approve")
        self.reject_button = QtWidgets.QPushButton("Reject")
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.logout_button = QtWidgets.QPushButton("Logout")

        self.approve_button.clicked.connect(self.approve_selected)
        self.reject_button.clicked.connect(self.reject_selected)
        self.refresh_button.clicked.connect(self.refresh_pending)
        self.logout_button.clicked.connect(self._trigger_logout)

        button_layout.addWidget(self.approve_button)
        button_layout.addWidget(self.reject_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.logout_button)

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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if not self._logout_in_progress:
            self.logoutRequested.emit()
        super().closeEvent(event)

    def _trigger_logout(self) -> None:
        if self._logout_in_progress:
            return
        self._logout_in_progress = True
        self.logoutRequested.emit()
        self.close()


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
        self.forgot_widget = ForgotPasswordWidget()
        self.reset_widget = ResetPasswordWidget()

        self.login_widget.loginRequested.connect(self.handle_login)
        self.login_widget.showRegister.connect(self.show_register)
        self.login_widget.showForgot.connect(self.show_forgot)

        self.register_widget.registerRequested.connect(self.handle_registration)
        self.register_widget.showLogin.connect(self.show_login)

        self.forgot_widget.resetRequested.connect(self.handle_password_reset_request)
        self.forgot_widget.showLogin.connect(self.show_login)
        self.forgot_widget.showReset.connect(self.show_reset)

        self.reset_widget.resetSubmitted.connect(self.handle_password_reset_submission)
        self.reset_widget.showLogin.connect(self.show_login)

        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.register_widget)
        self.stack.addWidget(self.forgot_widget)
        self.stack.addWidget(self.reset_widget)

        layout.addWidget(self.stack)
        self.setCentralWidget(central)

        self.main_window: MainWindow | None = None
        self.admin_panel: AdminPanel | None = None
        self.current_session_token: str | None = None

    def show_register(self) -> None:
        self.stack.setCurrentWidget(self.register_widget)

    def show_login(self) -> None:
        self.stack.setCurrentWidget(self.login_widget)

    def show_forgot(self) -> None:
        self.stack.setCurrentWidget(self.forgot_widget)

    def show_reset(self) -> None:
        self.stack.setCurrentWidget(self.reset_widget)

    def handle_login(self, username: str, password: str) -> None:
        username = username.strip()
        if not username or not password:
            QtWidgets.QMessageBox.warning(
                self,
                "Login Details Required",
                "Enter both a username and password before continuing.",
            )
            return

        try:
            user = authenticate_user(username, password)
        except LoginError as exc:
            QtWidgets.QMessageBox.warning(self, "Login Failed", str(exc))
            return

        if user.role == "admin":
            self.admin_panel = AdminPanel(user)
            self.admin_panel.logoutRequested.connect(self.handle_admin_logout)
            self.admin_panel.show()
            QtWidgets.QMessageBox.information(
                self, "Admin Login", "Admin panel opened in a new window."
            )
            self.hide()
            return

        if user.status != "approved":
            QtWidgets.QMessageBox.information(
                self,
                "Awaiting Approval",
                "Your registration is pending admin approval.",
            )
            return

        try:
            session_token = create_session_token(user)
        except SessionError as exc:
            QtWidgets.QMessageBox.critical(self, "Session Error", str(exc))
            return

        self.current_session_token = session_token
        self.main_window = MainWindow(user, session_token)
        self.main_window.logoutRequested.connect(self.handle_logout)
        self.main_window.show()
        self.hide()

    def handle_registration(self, username: str, email: str, password: str) -> None:
        username = username.strip()
        email = email.strip()
        if not username or not email or not password:
            QtWidgets.QMessageBox.warning(
                self,
                "Registration Incomplete",
                "All registration fields are required before submitting.",
            )
            return

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

    def handle_logout(self) -> None:
        self.current_session_token = None
        if self.main_window:
            try:
                self.main_window.logoutRequested.disconnect(self.handle_logout)
            except TypeError:
                pass
            self.main_window = None
        self.show()
        self.show_login()

    def handle_admin_logout(self) -> None:
        if self.admin_panel:
            try:
                self.admin_panel.logoutRequested.disconnect(self.handle_admin_logout)
            except TypeError:
                pass
            self.admin_panel = None
        self.show()
        self.show_login()

    def handle_password_reset_request(self, email: str) -> None:
        try:
            dev_token = request_password_reset(email)
        except PasswordResetError as exc:
            QtWidgets.QMessageBox.warning(self, "Password Reset Failed", str(exc))
            return

        if dev_token:
            QtWidgets.QMessageBox.information(
                self,
                "Reset Token Created",
                (
                    "Email delivery is not configured. Use this token to reset your password:\n"
                    f"{dev_token}"
                ),
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Reset Email Sent",
                "If the email is registered, a password reset message has been sent.",
            )

        self.show_reset()

    def handle_password_reset_submission(self, token: str, password: str) -> None:
        try:
            reset_password(token, password)
        except PasswordResetError as exc:
            QtWidgets.QMessageBox.warning(self, "Reset Failed", str(exc))
            return

        QtWidgets.QMessageBox.information(
            self,
            "Password Updated",
            "Password reset successful. You can now log in with your new password.",
        )
        self.reset_widget.token_input.clear()
        self.reset_widget.password_input.clear()
        self.reset_widget.confirm_input.clear()
        self.show_login()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = AuthWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
