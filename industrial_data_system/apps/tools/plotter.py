"""Interactive plotter window launched from the reader application."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from plotter_gui_component.main_window import MainWindow as PlotterMainWindow

__all__ = ["run"]


class PlotterWindow(PlotterMainWindow):
    """Standalone window that hosts the advanced plotting interface."""

    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._initialise_with_file()

    def _initialise_with_file(self) -> None:
        self.load_file(
            str(self._file_path),
            show_message=False,
            raise_on_error=True,
        )

        if self.df is None or self.df.empty:
            raise ValueError("The selected file did not contain any data to display.")

        self.setWindowTitle(f"Inline Analytical tool - {self._file_path.name}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)


_open_windows: List[PlotterWindow] = []


def run(file_path: Path | str) -> None:
    """Launch the plotter window for the provided file path."""

    path = Path(file_path)
    if not path.exists():
        QMessageBox.warning(None, "Plotter", f"The file '{path}' could not be found.")
        return

    try:
        window = PlotterWindow(path)
    except ValueError as exc:
        QMessageBox.warning(None, "Plotter", str(exc))
        return
    except Exception as exc:
        QMessageBox.critical(None, "Plotter", f"Unable to open plotter: {exc}")
        return

    window.show()
    window.raise_()
    window.activateWindow()
    _open_windows.append(window)

