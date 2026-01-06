"""Lightweight plotter window launched from the reader application."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run", "create_plotter_widget"]


class StatisticsArea(QWidget):
    """Widget displaying statistical summary of selected data columns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setup_ui()

    def setup_ui(self):
        """Initialize the statistics table UI."""
        header = QLabel("Statistics")
        header.setStyleSheet("font-weight: 600; color: #1F2937; font-size: 14px;")
        self.layout.addWidget(header)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Column", "Max", "Mean", "Min", "Std"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        self.layout.addWidget(self.stats_table)

        self._current_df = None

    def update_stats(self, df):
        """Update statistics table with data from DataFrame."""
        if df is not None and not df.empty:
            self._current_df = df
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
        """Clear all statistics from the table."""
        self.stats_table.setRowCount(0)
        self._current_df = None


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
            min-height: 32px;
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
        self.resize(1400, 900)

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        """Build the main user interface."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main horizontal splitter: Left controls + Right plot area
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)

        # Create horizontal splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: #E5E7EB;
            }
            QSplitter::handle:hover {
                background: #3B82F6;
            }
            """
        )

        # ========== LEFT PANEL: Controls ==========
        left_panel = QWidget()
        left_panel.setMinimumWidth(250)
        left_panel.setMaximumWidth(500)
        left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Header
        header = QLabel("Quick Plotter")
        header.setStyleSheet("font-size: 20px; font-weight: 600; color: #0F172A;")
        left_layout.addWidget(header)

        # Metadata table (simplified - only filename and dimensions)
        metadata_group = QGroupBox("File Information")
        metadata_layout = QVBoxLayout(metadata_group)

        self.metadata_table = QTableWidget()
        self.metadata_table.setRowCount(2)
        self.metadata_table.setColumnCount(2)
        self.metadata_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.metadata_table.verticalHeader().setVisible(False)
        self.metadata_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.metadata_table.setSelectionMode(QTableWidget.NoSelection)
        self.metadata_table.setFocusPolicy(Qt.NoFocus)
        self.metadata_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        metadata_layout.addWidget(self.metadata_table)

        left_layout.addWidget(metadata_group)

        # Axis selectors group
        selectors_group = QGroupBox("Axis Selection")
        selectors_layout = QVBoxLayout(selectors_group)

        # X Axis
        x_label = QLabel("X Axis")
        x_label.setStyleSheet("font-weight: 600; color: #1F2937;")
        selectors_layout.addWidget(x_label)

        self.x_selector = QListWidget()
        self.x_selector.setSelectionMode(QAbstractItemView.SingleSelection)
        self.x_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.x_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        selectors_layout.addWidget(self.x_selector)

        # Y Axes
        y_label = QLabel("Y Axes (Multi-select)")
        y_label.setStyleSheet("font-weight: 600; color: #1F2937; margin-top: 8px;")
        selectors_layout.addWidget(y_label)

        self.y_selector = QListWidget()
        self.y_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        self.y_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.y_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        selectors_layout.addWidget(self.y_selector)

        left_layout.addWidget(selectors_group)

        # Plot options group
        options_group = QGroupBox("Plot Options")
        options_layout = QVBoxLayout(options_group)

        self.grid_toggle = QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)
        self.grid_toggle.stateChanged.connect(self._plot_current_selection)
        options_layout.addWidget(self.grid_toggle)

        left_layout.addWidget(options_group)

        # Action buttons
        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.clicked.connect(self._export_plot)
        left_layout.addWidget(export_plot_btn)

        left_layout.addStretch()

        # ========== RIGHT PANEL: Scrollable Plot and Statistics ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        scroll_layout.setSpacing(12)

        # Status label
        self.status_label = QLabel("Select axes to plot")
        self.status_label.setStyleSheet(
            "color: #0F172A; font-weight: 500; padding: 8px; "
            "background: #F3F4F6; border-radius: 6px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(self.status_label)

        # Plot area with FIXED height
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(4)

        # Matplotlib figure with fixed size
        pixel_ratio = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
        dpi = int(100 * pixel_ratio)
        self.figure = Figure(figsize=(10, 6), dpi=dpi)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)

        # Set FIXED height for the plot canvas
        self.canvas.setFixedHeight(500)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Enable mouse interaction and focus for pan/zoom controls
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setMouseTracking(True)

        # Connect scroll event for Ctrl+scroll zooming
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        scroll_layout.addWidget(plot_container)

        # Divider between plot and statistics
        divider = QLabel()
        divider.setStyleSheet("background-color: #E5E7EB; min-height: 2px; max-height: 2px;")
        scroll_layout.addWidget(divider)

        # Statistics area
        self.stats_area = StatisticsArea(self)
        self.stats_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll_layout.addWidget(self.stats_area)

        # Add stretch at the bottom
        scroll_layout.addStretch()

        # Set the scroll content and add to right panel
        scroll_area.setWidget(scroll_content)
        right_layout.addWidget(scroll_area)

        # Add panels to splitter
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)

        # Set initial splitter sizes (25% left, 75% right)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 3)

        # Set collapsible behavior
        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

        # Add splitter to main layout
        main_layout.addWidget(self.main_splitter)

        # Apply styles
        self.setStyleSheet(
            """
            QMainWindow#quick-plotter-window {
                background: #FFFFFF;
            }
            QWidget {
                background: #FFFFFF;
                color: #0F172A;
            }
            QGroupBox {
                font-weight: 600;
                border: 2px solid #E5E7EB;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px;
                background: #F9FAFB;
            }
            QListWidget::item:selected {
                background: #DBEAFE;
                color: #1E3A8A;
            }
            QListWidget::item:hover {
                background: #EFF6FF;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTableWidget {
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background: #F3F4F6;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            """
            + self.BUTTON_STYLES
        )

    def _load_data(self) -> None:
        """Load data from the file."""
        df = self._read_file(self._file_path)

        if df.empty:
            raise ValueError("The selected file did not contain any data to display.")

        self._dataframe = df
        self._populate_metadata_table()
        self._populate_selectors(df)
        self._plot_current_selection()

    @staticmethod
    def _read_file(path: Path) -> pd.DataFrame:
        """Read file and return DataFrame."""
        ext = path.suffix.lower()

        # Handle Parquet files (highest priority - processed data)
        if ext == ".parquet":
            return pd.read_parquet(path, engine="pyarrow")

        if ext == ".csv":
            return load_and_process_csv_file(str(path))
        if ext == ".tdms":
            return load_and_process_tdms_file(str(path))
        if ext == ".asc":
            return load_and_process_asc_file(str(path))
        if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
            return pd.read_excel(path)
        if not ext:
            raise ValueError("Files without an extension are not supported by the quick plotter.")
        raise ValueError(f"Unsupported file type: {ext}")

    def _populate_metadata_table(self) -> None:
        """Populate the metadata table with file information."""
        if self._dataframe is None:
            return

        # DataFrame shape
        shape_str = f"{self._dataframe.shape[0]} × {self._dataframe.shape[1]}"

        # Populate table with property-value pairs (simplified)
        properties = [
            ("File Name", self._file_path.name),
            ("Dimensions", shape_str),
        ]

        for row, (prop, value) in enumerate(properties):
            self.metadata_table.setItem(row, 0, QTableWidgetItem(prop))
            self.metadata_table.setItem(row, 1, QTableWidgetItem(value))

            # Style property column
            prop_item = self.metadata_table.item(row, 0)
            if prop_item:
                prop_item.setForeground(Qt.darkGray)
                font = prop_item.font()
                font.setBold(True)
                prop_item.setFont(font)

        self.metadata_table.resizeColumnsToContents()

    def _populate_selectors(self, df: pd.DataFrame) -> None:
        """Populate axis selectors with column names."""
        self.x_selector.clear()
        self.y_selector.clear()

        numeric_columns = [
            column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])
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
        """Handle selection changes in axis selectors."""
        self._update_status()
        self._plot_current_selection()

    def _update_status(self) -> None:
        """Update status label based on current selections."""
        if self._dataframe is None:
            self.status_label.setText("No data loaded")
            return

        selected_x = self._current_x_axis()
        selected_y = self._current_y_axes()
        if not selected_x:
            self.status_label.setText("⚠ Select a column for the X axis")
        elif not selected_y:
            self.status_label.setText("⚠ Select one or more numeric columns for the Y axis")
        else:
            self.status_label.setText(f"📊 Plotting: {selected_x} vs [{', '.join(selected_y)}]")

    def _current_x_axis(self) -> str | None:
        """Get currently selected X axis column."""
        selected_items = self.x_selector.selectedItems()
        return selected_items[0].text() if selected_items else None

    def _current_y_axes(self) -> List[str]:
        """Get currently selected Y axis columns."""
        return [item.text() for item in self.y_selector.selectedItems()]

    def _plot_current_selection(self) -> None:
        """Plot the currently selected axes."""
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
        """Plot data on the figure with dynamic margins for multiple y-axes."""
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

        # Calculate number of axes needed
        n_axes = len(y_columns)

        # Calculate how many axes on each side
        n_left_axes = (n_axes + 1) // 2
        n_right_axes = n_axes // 2

        # Calculate dynamic margins
        left_margin = 0.08 + (n_left_axes - 1) * 0.12
        right_margin = 0.92 - (n_right_axes) * 0.12

        # Ensure margins don't overlap
        if left_margin >= right_margin:
            raise ValueError(
                f"Too many y-axes ({n_axes}) to display properly. "
                "Consider plotting fewer columns at once."
            )

        # Create subplot
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#FFFFFF")

        # Professional color palette
        professional_colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        ]

        color_map = [professional_colors[i % len(professional_colors)] for i in range(n_axes)]

        axes = [ax]
        plotted_any = False
        all_lines = []
        left_spine_offset = 0
        right_spine_offset = 0

        for i, (column, color) in enumerate(zip(y_columns, color_map)):
            series = pd.to_numeric(df[column], errors="coerce")
            if series.isna().all():
                continue
            valid = series.notna() & x_data.notna()
            if not valid.any():
                continue

            # Create new axis for each y-column after the first
            if i == 0:
                new_ax = ax
                new_ax.spines["left"].set_color(color)
                new_ax.spines["left"].set_linewidth(2)
            elif i % 2 == 1:
                # Odd indices go to the right side
                new_ax = ax.twinx()
                new_ax.spines["left"].set_visible(False)
                new_ax.spines["right"].set_visible(True)
                new_ax.spines["right"].set_color(color)
                new_ax.spines["right"].set_linewidth(2)
                new_ax.spines["right"].set_position(("axes", 1.0 + right_spine_offset))
                new_ax.yaxis.set_label_position("right")
                new_ax.yaxis.set_ticks_position("right")
                right_spine_offset += 0.15
                axes.append(new_ax)
            else:
                # Even indices go to the left side
                new_ax = ax.twinx()
                new_ax.spines["right"].set_visible(False)
                new_ax.spines["left"].set_visible(True)
                new_ax.spines["left"].set_color(color)
                new_ax.spines["left"].set_linewidth(2)
                left_spine_offset += 0.15
                new_ax.spines["left"].set_position(("axes", -left_spine_offset))
                new_ax.yaxis.set_label_position("left")
                new_ax.yaxis.set_ticks_position("left")
                axes.append(new_ax)

            # Plot with colored line
            (line,) = new_ax.plot(
                x_data[valid],
                series[valid],
                color=color,
                label=column,
                linewidth=2.5,
                alpha=0.9,
            )
            all_lines.append(line)

            # Style the y-axis with matching color
            new_ax.set_ylabel(
                column,
                color=color,
                fontsize=11,
                fontweight="bold",
                labelpad=10
            )
            new_ax.tick_params(
                axis="y",
                colors=color,
                labelsize=9,
                width=2,
                length=6
            )

            plotted_any = True

        if not plotted_any:
            raise ValueError("None of the selected y-axis columns contain numeric data.")

        # Style X-axis
        ax.set_xlabel(x_column, fontsize=12, fontweight="bold", labelpad=15)
        ax.tick_params(axis="x", labelsize=10, width=1.5, length=6)
        ax.spines["bottom"].set_linewidth(1.5)
        ax.spines["top"].set_visible(False)

        # Grid toggle
        if self.grid_toggle.isChecked():
            ax.grid(
                True,
                color="#E2E8F0",
                alpha=0.4,
                linestyle="--",
                linewidth=0.8,
                zorder=0
            )
            ax.set_axisbelow(True)

        # Create legend
        labels = [line.get_label() for line in all_lines]
        legend_ncol = min(len(labels), 4)
        ax.legend(
            all_lines,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            ncol=legend_ncol,
            frameon=True,
            fancybox=True,
            shadow=True,
            fontsize=9,
            edgecolor="#E5E7EB",
            framealpha=0.95,
        )

        # Adjust layout with dynamic margins
        self.figure.subplots_adjust(
            left=left_margin,
            right=right_margin,
            top=0.96,
            bottom=0.18
        )

        self.canvas.draw_idle()

        # Update statistics
        try:
            stats_df = df[y_columns].select_dtypes(include=[np.number])
            self.stats_area.update_stats(stats_df)
        except Exception:
            self.stats_area.clear_stats()

    def _on_scroll(self, event) -> None:
        """Handle scroll events for zooming with Ctrl+scroll."""
        if event.key != "control":
            return

        if event.inaxes is None:
            return

        ax = event.inaxes
        xdata = event.xdata
        ydata = event.ydata

        if xdata is None or ydata is None:
            return

        # Zoom factor
        zoom_factor = 1.2 if event.button == "up" else 0.8

        # Get current limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        # Calculate new limits centered on cursor position
        new_width = (xlim[1] - xlim[0]) * zoom_factor
        new_height = (ylim[1] - ylim[0]) * zoom_factor

        relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
        rely = (ylim[1] - ydata) / (ylim[1] - ylim[0])

        ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])

        # Update all twin axes to maintain synchronization
        for other_ax in self.figure.get_axes():
            if other_ax != ax and hasattr(other_ax, "get_shared_x_axes"):
                shared_x = other_ax.get_shared_x_axes()
                if shared_x.joined(ax, other_ax):
                    other_ax.set_xlim(ax.get_xlim())

        self.canvas.draw_idle()

    def _export_plot(self) -> None:
        """Export current plot to image file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            f"{self._file_path.stem}_plot.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches="tight")
                QMessageBox.information(self, "Export Success", f"Plot saved to:\n{file_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export plot:\n{exc}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Handle window close event."""
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)


# Global list to track open plotter windows
_open_windows: List[QuickPlotterWindow] = []


def run(file_path: Path | str) -> None:
    """Launch the quick plotter window for the provided file path.

    Args:
        file_path: Path to the file to plot
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


def create_plotter_widget(file_path: Path) -> Optional[QWidget]:
    """Create a scrollable plotter widget with statistics for embedding in other interfaces.

    This is a simplified embeddable version used by other parts of the application.

    Args:
        file_path: Path to the file to plot

    Returns:
        QWidget containing the plotter interface, or None if creation fails
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None

        # Load the data
        suffix = path.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(path, engine="pyarrow")
        elif suffix == ".asc":
            df = load_and_process_asc_file(str(path))
        elif suffix == ".csv":
            df = load_and_process_csv_file(str(path))
        elif suffix == ".tdms":
            df = load_and_process_tdms_file(str(path))
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        if df is None or df.empty:
            raise ValueError("No data loaded from file")

        # Create main widget
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # LEFT: Controls (Fixed)
        left_panel = QWidget()
        left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel(f"Plotter: {path.name}")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(title)

        # Column selector
        columns_group = QGroupBox("Select Columns")
        columns_layout = QVBoxLayout(columns_group)

        column_list = QListWidget()
        column_list.setSelectionMode(QAbstractItemView.MultiSelection)

        numeric_cols = df.select_dtypes(include=['float64', 'int64', 'float32', 'int32']).columns
        for col in numeric_cols:
            item = QListWidgetItem(str(col))
            column_list.addItem(item)
            if len(numeric_cols) <= 5:  # Auto-select if 5 or fewer
                item.setSelected(True)

        columns_layout.addWidget(column_list)
        left_layout.addWidget(columns_group)

        # Update button
        update_btn = QPushButton("Update Plot")
        update_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1E40AF;
            }
        """)
        left_layout.addWidget(update_btn)

        # Download button
        download_btn = QPushButton("Download Plot")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        left_layout.addWidget(download_btn)

        left_layout.addStretch()

        main_layout.addWidget(left_panel)

        # RIGHT: Scrollable Plot and Statistics Area
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll_layout.setSpacing(12)

        # Plot area (Fixed height)
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib figure and canvas
        figure = Figure(figsize=(10, 6), dpi=100)
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, widget)

        plot_layout.addWidget(toolbar)
        plot_layout.addWidget(canvas)

        scroll_layout.addWidget(plot_container)

        # Statistics area
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        stats_table = QTableWidget()
        stats_table.setColumnCount(5)
        stats_table.setHorizontalHeaderLabels(["Column", "Max", "Mean", "Min", "Std"])
        stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stats_table.verticalHeader().setVisible(False)
        stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        stats_table.setSelectionMode(QTableWidget.NoSelection)

        stats_layout.addWidget(stats_table)
        scroll_layout.addWidget(stats_group)

        # Set scroll content and add to right panel
        scroll_area.setWidget(scroll_content)
        right_layout.addWidget(scroll_area)

        main_layout.addWidget(right_panel)

        # Store references in widget to prevent garbage collection
        widget._df = df
        widget._figure = figure
        widget._canvas = canvas
        widget._column_list = column_list
        widget._stats_table = stats_table

        # Plot update function
        def update_plot():
            try:
                selected_items = column_list.selectedItems()
                if not selected_items:
                    return

                selected_cols = [item.text() for item in selected_items]

                # Main plot
                figure.clear()
                ax = figure.add_subplot(111)

                for col in selected_cols:
                    if col in df.columns:
                        ax.plot(df.index, df[col], label=col, linewidth=1.5, alpha=0.8)

                ax.set_xlabel("Index", fontsize=10)
                ax.set_ylabel("Value", fontsize=10)
                ax.set_title(f"Data Plot: {path.name}", fontsize=12, fontweight='bold')
                ax.legend(loc='best', fontsize=9)
                ax.grid(True, alpha=0.3, linestyle='--')

                figure.tight_layout()
                canvas.draw()

                # Update statistics
                stats_df = df[selected_cols].describe().T
                stats_table.setRowCount(len(stats_df))
                for i, (index, row) in enumerate(stats_df.iterrows()):
                    stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                    stats_table.setItem(i, 1, QTableWidgetItem(f"{row['max']:.4g}"))
                    stats_table.setItem(i, 2, QTableWidgetItem(f"{row['mean']:.4g}"))
                    stats_table.setItem(i, 3, QTableWidgetItem(f"{row['min']:.4g}"))
                    stats_table.setItem(i, 4, QTableWidgetItem(f"{row['std']:.4g}"))

            except Exception as e:
                print(f"Error updating plot: {e}")

        def download_plot():
            """Download the current plot as an image."""
            try:
                file_path, _ = QFileDialog.getSaveFileName(
                    widget, "Save Plot", f"{path.stem}_plot.png", "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
                )
                if file_path:
                    figure.savefig(file_path, dpi=300, bbox_inches="tight")
            except Exception as e:
                print(f"Error downloading plot: {e}")

        update_btn.clicked.connect(update_plot)
        download_btn.clicked.connect(download_plot)

        # Initial plot
        update_plot()

        return widget

    except Exception as e:
        print(f"Error creating plotter widget: {e}")
        import traceback
        traceback.print_exc()

        # Return error widget
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_label = QLabel(f"Error loading plotter:\n{str(e)}")
        error_label.setWordWrap(True)
        error_label.setStyleSheet("color: red; padding: 20px;")
        error_layout.addWidget(error_label)
        return error_widget