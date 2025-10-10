"""Interactive plotter window launched from the reader application."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

__all__ = ["run"]


class PlotterWindow(QMainWindow):
    """Standalone window that enables quick plotting of CSV data."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self._file_path = file_path
        self._data_rows, self._numeric_columns = self._load_data()

        if len(self._numeric_columns) < 2:
            raise ValueError(
                "The selected file must contain at least two numeric columns to plot."
            )

        self._initializing = True
        self._setup_ui()
        self._initializing = False
        self.plot_data()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"Plotter - {self._file_path.name}")
        self.resize(960, 640)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel(f"Plotting data from: {self._file_path}")
        header.setWordWrap(True)
        header.setStyleSheet("font-weight: 600;")
        layout.addWidget(header)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        x_label = QLabel("X axis:")
        controls.addWidget(x_label)

        self.x_combo = QComboBox()
        for column in self._numeric_columns:
            self.x_combo.addItem(column.strip() or column, column)
        self.x_combo.currentIndexChanged.connect(self._auto_plot)
        controls.addWidget(self.x_combo)

        y_label = QLabel("Y axis:")
        controls.addWidget(y_label)

        self.y_combo = QComboBox()
        for column in self._numeric_columns:
            self.y_combo.addItem(column.strip() or column, column)
        if len(self._numeric_columns) > 1:
            self.y_combo.setCurrentIndex(1)
        self.y_combo.currentIndexChanged.connect(self._auto_plot)
        controls.addWidget(self.y_combo)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot_data)
        controls.addWidget(self.plot_button)
        controls.addStretch(1)

        layout.addLayout(controls)

        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas, stretch=1)

        self.status_label = QLabel(
            "Select the desired columns and click Plot to generate the chart."
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.setCentralWidget(central)

    def _load_data(self) -> tuple[List[Dict[str, Optional[float]]], List[str]]:
        if not self._file_path.exists():
            raise FileNotFoundError("The selected file could not be located.")

        try:
            with self._file_path.open("r", encoding="utf-8", newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                reader = csv.DictReader(handle, dialect=dialect)
                headers = [header for header in reader.fieldnames or [] if header]
                if not headers:
                    raise ValueError("The selected file does not include column headers.")

                data_rows: List[Dict[str, Optional[float]]] = []
                numeric_presence: Dict[str, bool] = {header: False for header in headers}

                for raw_row in reader:
                    row: Dict[str, Optional[float]] = {}
                    for header in headers:
                        raw_value = (raw_row.get(header, "") or "").strip()
                        if raw_value == "":
                            row[header] = None
                            continue
                        try:
                            number = float(raw_value)
                        except ValueError:
                            row[header] = None
                        else:
                            row[header] = number
                            numeric_presence[header] = True
                    data_rows.append(row)
        except UnicodeDecodeError:
            raise ValueError("The plotter currently supports UTF-8 encoded CSV files only.")

        if not data_rows:
            raise ValueError("The selected file does not contain any rows to plot.")

        numeric_columns = [
            header
            for header, has_numeric in numeric_presence.items()
            if has_numeric
        ]

        return data_rows, numeric_columns

    def _auto_plot(self) -> None:
        if self._initializing:
            return
        self.plot_data()

    def plot_data(self) -> None:
        x_column = self.x_combo.currentData(Qt.UserRole)
        y_column = self.y_combo.currentData(Qt.UserRole)

        if not isinstance(x_column, str) or not isinstance(y_column, str):
            self.status_label.setText("Select columns for both the X and Y axes.")
            return

        if not x_column or not y_column:
            self.status_label.setText("Select columns for both the X and Y axes.")
            return

        x_label = self.x_combo.currentText()
        y_label = self.y_combo.currentText()

        paired_points = [
            (row.get(x_column), row.get(y_column))
            for row in self._data_rows
            if row.get(x_column) is not None and row.get(y_column) is not None
        ]

        if len(paired_points) < 2:
            self.figure.clear()
            self.canvas.draw_idle()
            self.status_label.setText(
                "Not enough numeric data pairs were found to create a plot."
            )
            return

        x_values, y_values = zip(*paired_points)

        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.plot(x_values, y_values, marker="o", linestyle="-", linewidth=1.5)
        axis.set_xlabel(x_label)
        axis.set_ylabel(y_label)
        axis.set_title(f"{y_label} vs {x_label}")
        axis.grid(True, linestyle="--", alpha=0.5)
        self.canvas.draw_idle()

        points_word = "points" if len(paired_points) != 1 else "point"
        self.status_label.setText(
            f"Plot generated with {len(paired_points)} {points_word} using "
            f"{x_label} (X) and {y_label} (Y)."
        )

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

    return None

