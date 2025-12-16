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
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
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

__all__ = ["run"]


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

        # Export button
        self.export_btn = QPushButton("Export Statistics")
        self.export_btn.clicked.connect(self.export_statistics)
        self.layout.addWidget(self.export_btn)

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

    def export_statistics(self):
        """Export statistics table to CSV file."""
        if self._current_df is None or self._current_df.empty:
            QMessageBox.warning(self, "Export Statistics", "No statistics available to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Statistics", "statistics.csv", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                stats_df = self._current_df.describe()
                stats_df.to_csv(file_path)
                QMessageBox.information(
                    self, "Export Success", f"Statistics exported to:\n{file_path}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export statistics:\n{exc}")


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
        QPushButton[secondary="true"] {
            background-color: #6B7280;
        }
        QPushButton[secondary="true"]:hover:!disabled {
            background-color: #4B5563;
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
        left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(12)

        # Header
        header = QLabel("Quick Plotter")
        header.setStyleSheet("font-size: 20px; font-weight: 600; color: #0F172A;")
        left_layout.addWidget(header)

        # Metadata table
        metadata_group = QGroupBox("File Information")
        metadata_layout = QVBoxLayout(metadata_group)

        self.metadata_table = QTableWidget()
        self.metadata_table.setRowCount(4)
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

        self.show_markers = QCheckBox("Show Markers")
        self.show_markers.stateChanged.connect(self._plot_current_selection)
        options_layout.addWidget(self.show_markers)

        self.grid_toggle = QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)
        self.grid_toggle.stateChanged.connect(self._plot_current_selection)
        options_layout.addWidget(self.grid_toggle)

        left_layout.addWidget(options_group)

        # Range filter group
        range_group = QGroupBox("X-Axis Range")
        range_layout = QGridLayout(range_group)

        range_layout.addWidget(QLabel("Min:"), 0, 0)
        self.x_min_input = QLineEdit()
        self.x_min_input.setPlaceholderText("Auto")
        range_layout.addWidget(self.x_min_input, 0, 1)

        range_layout.addWidget(QLabel("Max:"), 1, 0)
        self.x_max_input = QLineEdit()
        self.x_max_input.setPlaceholderText("Auto")
        range_layout.addWidget(self.x_max_input, 1, 1)

        apply_range_btn = QPushButton("Apply")
        apply_range_btn.setProperty("secondary", True)
        apply_range_btn.clicked.connect(self._zoom_to_selection)
        range_layout.addWidget(apply_range_btn, 2, 0)

        reset_range_btn = QPushButton("Reset")
        reset_range_btn.setProperty("secondary", True)
        reset_range_btn.clicked.connect(self._reset_zoom)
        range_layout.addWidget(reset_range_btn, 2, 1)

        left_layout.addWidget(range_group)

        # Action buttons
        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.clicked.connect(self._export_plot)
        left_layout.addWidget(export_plot_btn)

        refresh_btn = QPushButton("Refresh Plot")
        refresh_btn.clicked.connect(self._plot_current_selection)
        left_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        left_layout.addWidget(close_btn)

        left_layout.addStretch()

        # ========== RIGHT PANEL: Plot and Statistics ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Status label
        self.status_label = QLabel("Select axes to plot")
        self.status_label.setStyleSheet(
            "color: #0F172A; font-weight: 500; padding: 8px; "
            "background: #F3F4F6; border-radius: 6px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)

        # Plot area with statistics (vertical splitter for flexibility)
        plot_stats_splitter = QSplitter(Qt.Vertical)
        plot_stats_splitter.setHandleWidth(8)
        plot_stats_splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: #E5E7EB;
            }
            QSplitter::handle:hover {
                background: #3B82F6;
            }
            """
        )

        # Top section: Plot area
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(4)

        # Matplotlib figure (taller aspect ratio)
        self.figure = Figure(figsize=(10, 8), dpi=100)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(400)

        # Enable mouse interaction and focus for pan/zoom controls
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setMouseTracking(True)

        # Connect scroll event for Ctrl+scroll zooming
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        # Bottom section: Statistics area
        stats_container = QWidget()
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(0)

        self.stats_area = StatisticsArea(self)
        self.stats_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stats_area.setMinimumHeight(150)
        stats_layout.addWidget(self.stats_area)

        # Add to splitter
        plot_stats_splitter.addWidget(plot_container)
        plot_stats_splitter.addWidget(stats_container)

        # Set initial sizes (70% plot, 30% statistics)
        plot_stats_splitter.setSizes([600, 300])
        plot_stats_splitter.setStretchFactor(0, 3)
        plot_stats_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(plot_stats_splitter)

        # Add panels to splitter
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)

        # Set initial splitter sizes (25% left, 75% right)
        self.main_splitter.setSizes([350, 1050])

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
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 6px;
                background: #F9FAFB;
            }
            QLineEdit:focus {
                border: 2px solid #3B82F6;
                background: #FFFFFF;
            }
            QCheckBox {
                spacing: 8px;
            }
            QTableWidget {
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
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

        # Populate table with property-value pairs
        properties = [
            ("File Name", self._file_path.name),
            ("Modified", time_str),
            ("Size", size_str),
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

        # Calculate how many axes on each side (first axis is left, then alternate right/left)
        # Index 0: left (primary)
        # Index 1: right
        # Index 2: left
        # Index 3: right, etc.
        n_left_axes = (n_axes + 1) // 2  # Axes at indices 0, 2, 4, ...
        n_right_axes = n_axes // 2  # Axes at indices 1, 3, 5, ...

        # Calculate dynamic margins (each additional axis needs ~0.1 width)
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

        # Professional color palette (more distinct and pleasant than jet)
        professional_colors = [
            "#1f77b4",  # Blue
            "#ff7f0e",  # Orange
            "#2ca02c",  # Green
            "#d62728",  # Red
            "#9467bd",  # Purple
            "#8c564b",  # Brown
            "#e377c2",  # Pink
            "#7f7f7f",  # Gray
            "#bcbd22",  # Olive
            "#17becf",  # Cyan
        ]

        # If we have more columns than colors, cycle through
        color_map = []
        for i in range(n_axes):
            color_map.append(professional_colors[i % len(professional_colors)])

        axes = [ax]
        plotted_any = False
        all_lines = []
        left_spine_offset = 0
        right_spine_offset = 0

        # Determine if we should show markers
        show_markers = self.show_markers.isChecked()
        marker = "o" if show_markers else None
        markersize = 3 if show_markers else None

        for i, (column, color) in enumerate(zip(y_columns, color_map)):
            series = pd.to_numeric(df[column], errors="coerce")
            if series.isna().all():
                continue
            valid = series.notna() & x_data.notna()
            if not valid.any():
                continue

            # Create new axis for each y-column after the first
            if i == 0:
                # First axis is the primary left axis
                new_ax = ax
                new_ax.spines["left"].set_color(color)
                new_ax.spines["left"].set_linewidth(2)
            elif i % 2 == 1:
                # Odd indices (1, 3, 5, ...) go to the right side
                new_ax = ax.twinx()
                # Hide left spine, show right spine
                new_ax.spines["left"].set_visible(False)
                new_ax.spines["right"].set_visible(True)
                new_ax.spines["right"].set_color(color)
                new_ax.spines["right"].set_linewidth(2)

                # Position the spine
                new_ax.spines["right"].set_position(("axes", 1.0 + right_spine_offset))
                new_ax.yaxis.set_label_position("right")
                new_ax.yaxis.set_ticks_position("right")

                right_spine_offset += 0.15
                axes.append(new_ax)
            else:
                # Even indices (2, 4, 6, ...) go to the left side
                new_ax = ax.twinx()
                # Hide right spine, show left spine
                new_ax.spines["right"].set_visible(False)
                new_ax.spines["left"].set_visible(True)
                new_ax.spines["left"].set_color(color)
                new_ax.spines["left"].set_linewidth(2)

                # Position the spine
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
                marker=marker,
                markersize=markersize,
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

        # Create legend with better positioning
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

    def _zoom_to_selection(self) -> None:
        """Zoom plot to selected X range from inputs."""
        try:
            x_min = float(self.x_min_input.text()) if self.x_min_input.text() else None
            x_max = float(self.x_max_input.text()) if self.x_max_input.text() else None

            if x_min is not None or x_max is not None:
                axes = self.figure.get_axes()
                if axes:
                    ax = axes[0]
                    current_xlim = ax.get_xlim()
                    new_xlim = (
                        x_min if x_min is not None else current_xlim[0],
                        x_max if x_max is not None else current_xlim[1],
                    )
                    ax.set_xlim(new_xlim)
                    self.canvas.draw_idle()
        except ValueError:
            QMessageBox.warning(self, "Invalid Range", "Please enter valid numeric values.")

    def _reset_zoom(self) -> None:
        """Reset zoom to show all data."""
        self.x_min_input.clear()
        self.x_max_input.clear()
        axes = self.figure.get_axes()
        if axes:
            ax = axes[0]
            ax.autoscale()
            self.canvas.draw_idle()

    def _on_scroll(self, event) -> None:
        """Handle scroll events for zooming with Ctrl+scroll."""
        if event.key != "control":
            return

        if event.inaxes is None:
            return

        # Get the current axis limits
        ax = event.inaxes
        xdata = event.xdata
        ydata = event.ydata

        if xdata is None or ydata is None:
            return

        # Zoom factor: scroll up (event.step > 0) zooms in, scroll down zooms out
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
