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
    QWidget, QTableWidget, QHeaderView, QTableWidgetItem,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
# Add this import at the top with other matplotlib imports
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run"]

class StatisticsArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Column", "Max", "Mean", "Min", "Std"])
        self.layout.addWidget(self.stats_table)

    def update_stats(self, df):
        if df is not None and not df.empty:
            stats = df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{row['max']:.4g}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{row['mean']:.4g}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{row['min']:.4g}"))
                self.stats_table.setItem(i, 4, QTableWidgetItem(f"{row['std']:.4g}"))
            self.stats_table.resizeColumnsToContents()
        else:
            self.clear_stats()

    def clear_stats(self):
        self.stats_table.setRowCount(0)



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

        # NEW: Add metadata table
        self.metadata_table = QTableWidget()
        self.metadata_table.setRowCount(1)
        self.metadata_table.setColumnCount(4)
        self.metadata_table.setHorizontalHeaderLabels([
            "File Name",
            "Upload Time",
            "File Size",
            "Rows × Columns"
        ])
        self.metadata_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.metadata_table.verticalHeader().setVisible(False)
        self.metadata_table.setMaximumHeight(80)
        self.metadata_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metadata_table.setSelectionMode(QTableWidget.NoSelection)
        self.metadata_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.metadata_table)

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
        self.y_selector.setSelectionMode(QAbstractItemView.MultiSelection)
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

        # --- Plot and Statistics Area side by side ---
        plot_stats_container = QWidget()
        plot_stats_layout = QHBoxLayout(plot_stats_container)
        plot_stats_layout.setContentsMargins(0, 0, 0, 0)
        plot_stats_layout.setSpacing(12)

        # Left: Plot area (narrower width)
        plot_area = QVBoxLayout()
        plot_area.addWidget(self.toolbar)
        plot_area.addWidget(self.canvas, stretch=1)
        plot_stats_layout.addLayout(plot_area, 2)  # give plot less width (2 parts)

        # Right: Statistics area
        self.stats_area = StatisticsArea(self)
        plot_stats_layout.addWidget(self.stats_area, 1)  # smaller width (1 part)

        layout.addWidget(plot_stats_container, stretch=1)

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
        self._populate_metadata_table()
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



    # Replace the _plot_data method with this version:
    # In the _plot_data method, replace the legend section with this:

    def _plot_data(self, x_column: str, y_columns: List[str]) -> None:
        if self._dataframe is None:
            raise ValueError("No data is loaded for plotting.")

        df = self._dataframe.copy()

        try:
            x_data = pd.to_numeric(df[x_column], errors="coerce")
        except Exception as exc:
            raise ValueError(f"Unable to interpret '{x_column}' as numeric: {exc}")

        if x_data.isna().all():
            raise ValueError(f"Column '{x_column}' does not contain numeric data.")

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#FFFFFF")

        # Generate a color map with distinct colors
        n_colors = len(y_columns)
        color_map = plt.cm.get_cmap('jet')(np.linspace(0, 1, n_colors))

        axes = [ax]
        plotted_any = False
        all_lines = []  # Collect all lines for legend

        for i, (column, base_color) in enumerate(zip(y_columns, color_map)):
            series = pd.to_numeric(df[column], errors="coerce")
            if series.isna().all():
                continue
            valid = series.notna() & x_data.notna()
            if not valid.any():
                continue

            # Create new axis for each y-column after the first
            if i > 0:
                new_ax = ax.twinx()
                new_ax.spines['right'].set_visible(True)
                if i % 2 == 0:  # Even indices go to the left side
                    new_ax.spines['right'].set_visible(False)
                    new_ax.spines['left'].set_position(('axes', -0.1 * (i // 2)))
                    new_ax.yaxis.set_label_position('left')
                    new_ax.yaxis.set_ticks_position('left')
                else:  # Odd indices go to the right side
                    new_ax.spines['left'].set_visible(False)
                    new_ax.spines['right'].set_position(('axes', 1 + 0.1 * ((i - 1) // 2)))
                    new_ax.yaxis.set_label_position('right')
                    new_ax.yaxis.set_ticks_position('right')
                axes.append(new_ax)
            else:
                new_ax = ax

            # Plot with colored line
            line, = new_ax.plot(x_data[valid], series[valid], color=base_color, label=column)
            all_lines.append(line)

            # Style the y-axis with matching color
            new_ax.set_ylabel(column, color=base_color)
            new_ax.tick_params(axis='y', colors=base_color)

            plotted_any = True

        if not plotted_any:
            raise ValueError("None of the selected y-axis columns contain numeric data.")

        ax.set_xlabel(x_column)
        # ax.set_title(self._file_path.name)
        ax.grid(color="#E2E8F0", alpha=0.5)

        # Create a single legend below the plot
        labels = [line.get_label() for line in all_lines]
        ax.legend(all_lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15),
                  ncol=min(len(labels), 3), frameon=True)

        self.figure.tight_layout()
        self.canvas.draw_idle()
        try:
            stats_df = df[y_columns].select_dtypes(include=[np.number])
            self.stats_area.update_stats(stats_df)
        except Exception:
            self.stats_area.clear_stats()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)

    def _populate_metadata_table(self) -> None:
        """Populate the metadata table with file information."""
        if self._dataframe is None:
            return

        # Get file stats
        file_stats = self._file_path.stat()
        file_size_mb = file_stats.st_size / (1024 * 1024)

        # Format file size
        if file_size_mb < 1:
            size_str = f"{file_stats.st_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size_mb:.2f} MB"

        # Format timestamp
        import datetime
        timestamp = datetime.datetime.fromtimestamp(file_stats.st_mtime)
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # DataFrame shape
        shape_str = f"{self._dataframe.shape[0]} × {self._dataframe.shape[1]}"

        # Populate table
        self.metadata_table.setItem(0, 0, QTableWidgetItem(self._file_path.stem))
        self.metadata_table.setItem(0, 1, QTableWidgetItem(time_str))
        self.metadata_table.setItem(0, 2, QTableWidgetItem(size_str))
        self.metadata_table.setItem(0, 3, QTableWidgetItem(shape_str))

        # Style the table
        for col in range(4):
            item = self.metadata_table.item(0, col)
            if item:
                item.setTextAlignment(Qt.AlignCenter)


_open_windows: List[QuickPlotterWindow] = []

from typing import List, Optional

def run(file_path: Path | str, parent: Optional[QWidget] = None) -> None:
    """Launch the quick plotter window for the provided file path.

    Args:
        file_path: Path to the file to plot
        parent: Optional parent widget (used to manage window lifecycle)
    """

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