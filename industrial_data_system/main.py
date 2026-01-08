"""Desktop application with menu bar and tabbed interface."""

from __future__ import annotations

import sys
from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCloseEvent, QFont, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMainWindow,
    QMenuBar,
    QTabWidget,
    QWidget,
    QVBoxLayout,
)

from industrial_data_system.apps import IndustrialDataApp, IndustrialTheme, ReaderApp

# Enable High DPI scaling for different screen resolutions
if hasattr(Qt, "AA_EnableHighDpiScaling"):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)


class TabbedDesktopApp(QMainWindow):
    """Main desktop application with menu bar and tabbed interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Inline Data System")
        self.setMinimumSize(1024, 768)

        # Tab counter for naming
        self._upload_tab_counter = 0
        self._reader_tab_counter = 0

        # Track tab widgets and their associated apps
        self._tab_reader_apps: Dict[int, ReaderApp] = {}
        self._tab_upload_apps: Dict[int, IndustrialDataApp] = {}  # ADD THIS LINE

        # Create central tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # Create menu bar
        self._create_menu_bar()

        # Show welcome message when no tabs are open
        self._show_welcome_tab()

    def _create_menu_bar(self) -> None:
        """Create the application menu bar with File, Edit, View, and Help menus."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        new_upload_action = QAction("New &Upload Tab", self)
        new_upload_action.setShortcut(QKeySequence.New)
        new_upload_action.setStatusTip("Open a new upload tab")
        new_upload_action.triggered.connect(self.new_upload_tab)
        file_menu.addAction(new_upload_action)

        new_reader_action = QAction("New &Reader Tab", self)
        new_reader_action.setShortcut(QKeySequence("Ctrl+R"))
        new_reader_action.setStatusTip("Open a new reader tab")
        new_reader_action.triggered.connect(self.new_reader_tab)
        file_menu.addAction(new_reader_action)

        file_menu.addSeparator()

        close_tab_action = QAction("&Close Tab", self)
        close_tab_action.setShortcut(QKeySequence.Close)
        close_tab_action.setStatusTip("Close the current tab")
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")

        preferences_action = QAction("&Preferences", self)
        preferences_action.setShortcut(QKeySequence.Preferences)
        preferences_action.setStatusTip("Open preferences")
        preferences_action.triggered.connect(self.open_preferences)
        edit_menu.addAction(preferences_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _show_welcome_tab(self) -> None:
        """Show a welcome tab when the application starts."""
        from PyQt5.QtWidgets import QLabel, QVBoxLayout

        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Welcome to Inline Data System")
        title.setProperty("heading", True)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "Use File → New Upload Tab (Ctrl+N) or File → New Reader Tab (Ctrl+R) to get started."
        )
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setProperty("caption", True)
        layout.addWidget(subtitle)

        self.tab_widget.addTab(welcome_widget, "Welcome")

    def create_tool_tab(self, tool_name: str, widget: QWidget) -> None:
        """Create a new tab for a tool widget.

        Args:
            tool_name: Name of the tool for the tab title
            widget: The widget to display in the tab
        """
        try:
            # Remove welcome tab if it exists
            if self.tab_widget.count() == 1 and self.tab_widget.tabText(0) == "Welcome":
                self.tab_widget.removeTab(0)

            tab_index = self.tab_widget.addTab(widget, tool_name)
            self.tab_widget.setCurrentIndex(tab_index)
        except Exception as e:
            print(f"Error creating tool tab: {e}")
            import traceback
            traceback.print_exc()

    def new_upload_tab(self) -> None:
        """Create a new upload tab."""
        try:
            # Remove welcome tab if it exists
            if self.tab_widget.count() == 1 and self.tab_widget.tabText(0) == "Welcome":
                self.tab_widget.removeTab(0)

            self._upload_tab_counter += 1

            # Create upload app - don't hide it, just don't show it
            upload_app = IndustrialDataApp()

            # Get central widget directly
            central_widget = upload_app.centralWidget()

            # Add to tab widget
            tab_index = self.tab_widget.addTab(
                central_widget,
                f"Upload {self._upload_tab_counter}"
            )

            # Store reference to upload app to prevent garbage collection
            if not hasattr(self, '_tab_upload_apps'):
                self._tab_upload_apps: Dict[int, IndustrialDataApp] = {}
            self._tab_upload_apps[tab_index] = upload_app

            self.tab_widget.setCurrentIndex(tab_index)

            # IMPORTANT: Trigger refresh after tab is shown
            # Use QTimer to ensure the widget is fully initialized
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, upload_app.refresh_files)

        except Exception as e:
            print(f"Error creating upload tab: {e}")
            import traceback
            traceback.print_exc()

    def new_reader_tab(self) -> None:
        """Create a new reader tab."""
        try:
            # Remove welcome tab if it exists
            if self.tab_widget.count() == 1 and self.tab_widget.tabText(0) == "Welcome":
                self.tab_widget.removeTab(0)

            self._reader_tab_counter += 1

            # Create reader app
            reader_app = ReaderApp()

            # Get the stack widget directly
            stack_widget = reader_app.stack

            # Add to tab widget
            tab_index = self.tab_widget.addTab(
                stack_widget,
                f"Reader {self._reader_tab_counter}"
            )

            # Store reference to reader app
            self._tab_reader_apps[tab_index] = reader_app

            # Connect signal AFTER tab is added
            try:
                reader_app.dashboard.open_tool_in_tab.connect(self.create_tool_tab)
            except Exception as e:
                print(f"Warning: Could not connect signal: {e}")

            self.tab_widget.setCurrentIndex(tab_index)

        except Exception as e:
            print(f"Error creating reader tab: {e}")
            import traceback
            traceback.print_exc()

    def close_tab(self, index: int) -> None:
        """Close a tab at the specified index."""
        try:
            if index >= 0:
                # Clean up reader app if this was a reader tab
                if index in self._tab_reader_apps:
                    reader_app = self._tab_reader_apps.pop(index)
                    try:
                        reader_app.dashboard.open_tool_in_tab.disconnect(self.create_tool_tab)
                    except:
                        pass

                # Clean up upload app if this was an upload tab
                if hasattr(self, '_tab_upload_apps') and index in self._tab_upload_apps:
                    self._tab_upload_apps.pop(index)

                self.tab_widget.removeTab(index)

                # Update remaining tab indices in the dictionaries
                updated_reader_apps = {}
                for tab_idx, app in self._tab_reader_apps.items():
                    if tab_idx > index:
                        updated_reader_apps[tab_idx - 1] = app
                    else:
                        updated_reader_apps[tab_idx] = app
                self._tab_reader_apps = updated_reader_apps

                if hasattr(self, '_tab_upload_apps'):
                    updated_upload_apps = {}
                    for tab_idx, app in self._tab_upload_apps.items():
                        if tab_idx > index:
                            updated_upload_apps[tab_idx - 1] = app
                        else:
                            updated_upload_apps[tab_idx] = app
                    self._tab_upload_apps = updated_upload_apps

                # Show welcome tab if all tabs are closed
                if self.tab_widget.count() == 0:
                    self._show_welcome_tab()
        except Exception as e:
            print(f"Error closing tab: {e}")
            import traceback
            traceback.print_exc()

    def close_current_tab(self) -> None:
        """Close the currently active tab."""
        current_index = self.tab_widget.currentIndex()
        # Don't allow closing the welcome tab if it's the only tab
        if current_index >= 0:
            if self.tab_widget.count() == 1 and self.tab_widget.tabText(current_index) == "Welcome":
                return  # Don't close the last welcome tab
            if self.tab_widget.tabText(current_index) != "Welcome":
                self.close_tab(current_index)

    def next_tab(self) -> None:
        """Switch to the next tab."""
        current = self.tab_widget.currentIndex()
        next_index = (current + 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(next_index)

    def previous_tab(self) -> None:
        """Switch to the previous tab."""
        current = self.tab_widget.currentIndex()
        prev_index = (current - 1) % self.tab_widget.count()
        self.tab_widget.setCurrentIndex(prev_index)

    def open_preferences(self) -> None:
        """Open preferences dialog (placeholder)."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Preferences",
            "Preferences dialog would open here.",
        )

    def show_about(self) -> None:
        """Show about dialog."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About Inline Data System",
            "Inline Data System\n\n"
            "A desktop application for managing industrial data uploads and reading.\n\n"
            "Version 1.0",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up all tabs when the main window is closed."""
        try:
            # Disconnect all reader signals
            for reader_app in list(self._tab_reader_apps.values()):
                try:
                    reader_app.dashboard.open_tool_in_tab.disconnect(self.create_tool_tab)
                except:
                    pass
            self._tab_reader_apps.clear()

            # Clear upload apps
            if hasattr(self, '_tab_upload_apps'):
                self._tab_upload_apps.clear()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(IndustrialTheme.get_stylesheet())
    app.setFont(QFont("Segoe UI", 10))

    desktop_app = TabbedDesktopApp()
    desktop_app.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()