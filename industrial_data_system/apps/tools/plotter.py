"""Lightweight plotter window launched from the reader application."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run"]


class QuickPlotterWindow(QMainWindow):
    """Streamlined window that renders a simple plot for the selected file."""

    BUTTON_STYLES = """
        QPushButton {
            background-color: #1D4ED8;
            color: #FFFFFF;
            padding: 8px 18px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }
        QPushButton:disabled {
            background-color: #94A3B8;
            color: #FFFFFF;
        }
        QPushButton:hover:!disabled {
            background-color: #1E40AF;
        }
        QPushButton:pressed:!disabled {
            background-color: #1E3A8A;
        }
    """

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self._file_path = file_path
        self._dataframe: pd.DataFrame | None = None

        self.setObjectName("quick-plotter-window")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(f"Plot Preview - {self._file_path.name}")
        self.resize(960, 720)

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Quick Plotter")
        header.setStyleSheet("font-size: 22px; font-weight: 600; color: #0F172A;")
        layout.addWidget(header)

        subtitle = QLabel("Select the axes you would like to visualise.")
        subtitle.setStyleSheet("color: #475569;")
        layout.addWidget(subtitle)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #0F172A; font-weight: 500;")
        layout.addWidget(self.status_label)

        selectors_container = QWidget()
        selectors_layout = QHBoxLayout(selectors_container)
        selectors_layout.setContentsMargins(0, 0, 0, 0)
        selectors_layout.setSpacing(12)

        x_axis_layout = QVBoxLayout()
        x_axis_label = QLabel("X Axis")
        x_axis_label.setStyleSheet("font-weight: 600; color: #1F2937;")
        self.x_selector = QListWidget()
        self.x_selector.setSelectionMode(QAbstractItemView.SingleSelection)
        self.x_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.x_selector.setMinimumWidth(200)
        x_axis_layout.addWidget(x_axis_label)
        x_axis_layout.addWidget(self.x_selector)

        y_axis_layout = QVBoxLayout()
        y_axis_label = QLabel("Y Axes")
        y_axis_label.setStyleSheet("font-weight: 600; color: #1F2937;")
        self.y_selector = QListWidget()
        self.y_selector.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.y_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.y_selector.setMinimumWidth(240)
        y_axis_layout.addWidget(y_axis_label)
        y_axis_layout.addWidget(self.y_selector)

        selectors_layout.addLayout(x_axis_layout)
        selectors_layout.addLayout(y_axis_layout)
        selectors_layout.addStretch(1)

        layout.addWidget(selectors_container)

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #FFFFFF; border: none;")

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)

        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)

        buttons_layout.addStretch(1)

        self.refresh_button = QPushButton("Refresh Plot")
        self.refresh_button.clicked.connect(self._plot_current_selection)
        buttons_layout.addWidget(self.refresh_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        layout.addWidget(buttons_container)

        self.setStyleSheet(
            """
            QMainWindow#quick-plotter-window {
                background: #FFFFFF;
            }
            QWidget {
                background: #FFFFFF;
                color: #0F172A;
            }
            QListWidget {
                border: 1px solid #CBD5F5;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item:selected {
                background: #DBEAFE;
                color: #1E3A8A;
            }
            QListWidget::item:hover {
                background: #EFF6FF;
            }
            """
            + self.BUTTON_STYLES
        )

    def _load_data(self) -> None:
        df = self._read_file(self._file_path)

        if df.empty:
            raise ValueError("The selected file did not contain any data to display.")

        self._dataframe = df
        self._populate_selectors(df)
        self._plot_current_selection()

    @staticmethod
    def _read_file(path: Path) -> pd.DataFrame:
        ext = path.suffix.lower()

        # Handle Parquet files (highest priority - processed data)
        if ext == ".parquet":
            return pd.read_parquet(path, engine='pyarrow')

        if ext == ".csv":
            return load_and_process_csv_file(str(path))
        if ext == ".tdms":
            return load_and_process_tdms_file(str(path))
        if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
            return pd.read_excel(path)
        if not ext:
            raise ValueError("Files without an extension are not supported by the quick plotter.")
        raise ValueError(f"Unsupported file type: {ext}")

    def _populate_selectors(self, df: pd.DataFrame) -> None:
        self.x_selector.clear()
        self.y_selector.clear()

        numeric_columns = [
            column
            for column in df.columns
            if pd.api.types.is_numeric_dtype(df[column])
        ]

        for column in df.columns:
            item = QListWidgetItem(column)
            self.x_selector.addItem(item)
            if column in numeric_columns:
                y_item = QListWidgetItem(column)
                y_item.setSelected(False)
                self.y_selector.addItem(y_item)

        if self.x_selector.count() > 0:
            self.x_selector.setCurrentRow(0)

        # Select up to two numeric columns by default
        for index in range(min(2, len(numeric_columns))):
            items = self.y_selector.findItems(numeric_columns[index], Qt.MatchExactly)
            if items:
                items[0].setSelected(True)

        self._update_status()

    def _handle_selection_change(self) -> None:
        self._update_status()
        self._plot_current_selection()

    def _update_status(self) -> None:
        if self._dataframe is None:
            self.status_label.setText("")
            return

        selected_x = self._current_x_axis()
        selected_y = self._current_y_axes()
        if not selected_x:
            self.status_label.setText("Select a column for the x axis.")
        elif not selected_y:
            self.status_label.setText("Select one or more numeric columns for the y axis.")
        else:
            self.status_label.setText(
                f"Plotting '{selected_x}' against {', '.join(selected_y)}"
            )

    def _current_x_axis(self) -> str | None:
        selected_items = self.x_selector.selectedItems()
        return selected_items[0].text() if selected_items else None

    def _current_y_axes(self) -> List[str]:
        return [item.text() for item in self.y_selector.selectedItems()]

    def _plot_current_selection(self) -> None:
        if self._dataframe is None:
            return

        x_column = self._current_x_axis()
        y_columns = self._current_y_axes()

        if not x_column or not y_columns:
            return

        try:
            self._plot_data(x_column, y_columns)
        except ValueError as exc:
            QMessageBox.warning(self, "Plotter", str(exc))

    def _plot_data(self, x_column: str, y_columns: List[str]) -> None:
        if self._dataframe is None:
            raise ValueError("No data is loaded for plotting.")

        df = self._dataframe.copy()

        try:
            x_data = pd.to_numeric(df[x_column], errors="coerce")
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unable to interpret '{x_column}' as numeric: {exc}")

        if x_data.isna().all():
            raise ValueError(f"Column '{x_column}' does not contain numeric data.")

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#FFFFFF")

        plotted_any = False

        for column in y_columns:
            series = pd.to_numeric(df[column], errors="coerce")
            if series.isna().all():
                continue
            valid = series.notna() & x_data.notna()
            if not valid.any():
                continue
            ax.plot(x_data[valid], series[valid], label=column)
            plotted_any = True

        if not plotted_any:
            raise ValueError("None of the selected y-axis columns contain numeric data.")

        ax.set_xlabel(x_column)
        ax.set_ylabel("Value")
        ax.grid(color="#E2E8F0", alpha=0.5)
        ax.legend(loc="best")
        ax.set_title(self._file_path.name)

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)


_open_windows: List[QuickPlotterWindow] = []


def run(file_path: Path | str) -> None:
    """Launch the quick plotter window for the provided file path."""

    path = Path(file_path)
    if not path.exists():
        QMessageBox.warning(None, "Plotter", f"The file '{path}' could not be found.")
        return

    try:
        window = QuickPlotterWindow(path)
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