"""Anomaly prediction plotter for visualizing model predictions vs actual data."""

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
            self, "Export Statistics", "prediction_statistics.csv", "CSV Files (*.csv)"
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


class AnomalyPredictionPlotterWindow(QMainWindow):
    """Window for plotting predictions vs actual data from anomaly detection."""

    BUTTON_STYLES = """
        QPushButton {
            background-color: #DC2626;
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
            background-color: #B91C1C;
        }
        QPushButton:pressed:!disabled {
            background-color: #991B1B;
        }
        QPushButton[secondary="true"] {
            background-color: #6B7280;
        }
        QPushButton[secondary="true"]:hover:!disabled {
            background-color: #4B5563;
        }
        QPushButton[primary="true"] {
            background-color: #1D4ED8;
        }
        QPushButton[primary="true"]:hover:!disabled {
            background-color: #1E40AF;
        }
    """

    def __init__(
        self,
        actual_data: pd.DataFrame,
        predictions: pd.DataFrame,
        file_name: str = "Anomaly Predictions"
    ) -> None:
        super().__init__()
        self._actual_data = actual_data
        self._predictions = predictions

        self.setObjectName("anomaly-prediction-plotter")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(f"Prediction Plotter - {file_name}")
        self.resize(1600, 900)

        self._build_ui()
        self._populate_selectors()

    def _build_ui(self) -> None:
        """Build the main user interface."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main horizontal layout
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
                background: #DC2626;
            }
            """
        )

        # ========== LEFT PANEL: Controls ==========
        left_panel = QWidget()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(600)
        left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(0)

        # Header
        header = QLabel("Prediction Plotter")
        header.setStyleSheet("font-size: 20px; font-weight: 600; color: #DC2626; margin-bottom: 12px;")
        left_layout.addWidget(header)

        # Create vertical splitter for resizable group boxes
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setHandleWidth(6)
        left_splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: #E5E7EB;
                margin: 2px 0px;
            }
            QSplitter::handle:hover {
                background: #DC2626;
            }
            """
        )
        left_layout.addWidget(left_splitter)

        # Data info group
        info_group = QGroupBox("Data Information")
        info_layout = QVBoxLayout(info_group)

        self.info_table = QTableWidget()
        self.info_table.setRowCount(3)
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.info_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.info_table.verticalHeader().setVisible(False)
        self.info_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.info_table.setSelectionMode(QTableWidget.NoSelection)
        self.info_table.setMaximumHeight(120)

        # Populate info table
        properties = [
            ("Actual Data Points", str(len(self._actual_data))),
            ("Actual Columns", str(len(self._actual_data.columns))),
            ("Prediction Columns", str(len(self._predictions.columns))),
        ]
        for row, (prop, value) in enumerate(properties):
            self.info_table.setItem(row, 0, QTableWidgetItem(prop))
            self.info_table.setItem(row, 1, QTableWidgetItem(value))
            prop_item = self.info_table.item(row, 0)
            if prop_item:
                prop_item.setForeground(Qt.darkGray)
                font = prop_item.font()
                font.setBold(True)
                prop_item.setFont(font)

        self.info_table.resizeColumnsToContents()
        info_layout.addWidget(self.info_table)

        left_splitter.addWidget(info_group)

        # Axis selectors group
        selectors_group = QGroupBox("Axis Selection")
        selectors_layout = QVBoxLayout(selectors_group)

        # X Axis
        x_label = QLabel("X Axis (Index)")
        x_label.setStyleSheet("font-weight: 600; color: #1F2937;")
        selectors_layout.addWidget(x_label)

        self.x_info = QLabel("Using row index as X-axis")
        self.x_info.setStyleSheet("color: #6B7280; font-size: 12px; padding: 4px;")
        selectors_layout.addWidget(self.x_info)

        # Prediction Y Axes
        pred_label = QLabel("Y Axes - Predictions (Multi-select)")
        pred_label.setStyleSheet("font-weight: 600; color: #DC2626; margin-top: 8px;")
        selectors_layout.addWidget(pred_label)

        self.y_pred_selector = QListWidget()
        self.y_pred_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        self.y_pred_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.y_pred_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        selectors_layout.addWidget(self.y_pred_selector)

        # Actual Y Axes
        actual_label = QLabel("Y Axes - Actual Data (Multi-select)")
        actual_label.setStyleSheet("font-weight: 600; color: #1D4ED8; margin-top: 8px;")
        selectors_layout.addWidget(actual_label)

        self.y_actual_selector = QListWidget()
        self.y_actual_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        self.y_actual_selector.itemSelectionChanged.connect(self._handle_selection_change)
        self.y_actual_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        selectors_layout.addWidget(self.y_actual_selector)

        left_splitter.addWidget(selectors_group)

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

        self.show_difference = QCheckBox("Show Difference Plot")
        self.show_difference.stateChanged.connect(self._plot_current_selection)
        options_layout.addWidget(self.show_difference)

        left_splitter.addWidget(options_group)

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

        left_splitter.addWidget(range_group)

        # Export buttons container
        export_container = QWidget()
        export_layout = QVBoxLayout(export_container)
        export_layout.setContentsMargins(0, 0, 0, 0)
        export_layout.setSpacing(8)

        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.setProperty("secondary", True)
        export_plot_btn.clicked.connect(self._export_plot)
        export_layout.addWidget(export_plot_btn)

        export_data_btn = QPushButton("Export Data")
        export_data_btn.setProperty("secondary", True)
        export_data_btn.clicked.connect(self._export_data)
        export_layout.addWidget(export_data_btn)

        close_btn = QPushButton("Close")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(self.close)
        export_layout.addWidget(close_btn)

        export_layout.addStretch()

        left_splitter.addWidget(export_container)

        # Configure splitter stretch factors
        left_splitter.setStretchFactor(0, 0)  # Data Information
        left_splitter.setStretchFactor(1, 3)  # Axis Selection
        left_splitter.setStretchFactor(2, 0)  # Plot Options
        left_splitter.setStretchFactor(3, 0)  # X-Axis Range
        left_splitter.setStretchFactor(4, 0)  # Export buttons

        # Set collapsible behavior
        for i in range(left_splitter.count()):
            left_splitter.setCollapsible(i, False)

        # ========== RIGHT PANEL: Plots and Statistics ==========
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Status label
        self.status_label = QLabel("Select axes to plot")
        self.status_label.setStyleSheet(
            "color: #0F172A; font-weight: 500; padding: 8px; "
            "background: #FEF3C7; border-radius: 6px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)

        # Create vertical splitter for plot and statistics
        plot_stats_splitter = QSplitter(Qt.Vertical)
        plot_stats_splitter.setHandleWidth(8)
        plot_stats_splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: #E5E7EB;
            }
            QSplitter::handle:hover {
                background: #DC2626;
            }
            """
        )

        # Plot container
        plot_container = QWidget()
        plot_layout = QVBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(4)

        # Matplotlib figure
        self.figure = Figure(figsize=(12, 10), dpi=100)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setMinimumHeight(400)

        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setMouseTracking(True)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")

        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)

        # Statistics container
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
        plot_stats_splitter.setSizes([700, 300])
        plot_stats_splitter.setStretchFactor(0, 3)
        plot_stats_splitter.setStretchFactor(1, 1)

        right_layout.addWidget(plot_stats_splitter)

        # Add panels to main splitter
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
            QMainWindow#anomaly-prediction-plotter {
                background: #FFFFFF;
            }
            QWidget {
                background: #FFFFFF;
                color: #0F172A;
            }
            QGroupBox {
                font-weight: 600;
                border: 2px solid #FCA5A5;
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
                background: #FEE2E2;
                color: #991B1B;
            }
            QListWidget::item:hover {
                background: #FEF2F2;
            }
            QLineEdit {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 6px;
                background: #F9FAFB;
            }
            QLineEdit:focus {
                border: 2px solid #DC2626;
                background: #FFFFFF;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #D1D5DB;
                border-radius: 4px;
                background: #FFFFFF;
            }
            QCheckBox::indicator:checked {
                background: #DC2626;
                border-color: #DC2626;
            }
            QCheckBox::indicator:hover {
                border-color: #DC2626;
            }
            QTableWidget {
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
            """
            + self.BUTTON_STYLES
        )

    def _populate_selectors(self) -> None:
        """Populate axis selectors with column names."""
        self.y_pred_selector.clear()
        self.y_actual_selector.clear()

        # Populate prediction columns
        pred_numeric_columns = [
            col for col in self._predictions.columns
            if pd.api.types.is_numeric_dtype(self._predictions[col])
        ]
        for column in pred_numeric_columns:
            item = QListWidgetItem(f"Pred: {column}")
            item.setData(Qt.UserRole, column)  # Store original column name
            self.y_pred_selector.addItem(item)

        # Populate actual data columns
        actual_numeric_columns = [
            col for col in self._actual_data.columns
            if pd.api.types.is_numeric_dtype(self._actual_data[col])
        ]
        for column in actual_numeric_columns:
            item = QListWidgetItem(f"Actual: {column}")
            item.setData(Qt.UserRole, column)  # Store original column name
            self.y_actual_selector.addItem(item)

        # Select first column from each by default
        if self.y_pred_selector.count() > 0:
            self.y_pred_selector.item(0).setSelected(True)
        if self.y_actual_selector.count() > 0:
            self.y_actual_selector.item(0).setSelected(True)

        self._update_status()
        self._plot_current_selection()

    def _handle_selection_change(self) -> None:
        """Handle selection changes in axis selectors."""
        self._update_status()
        self._plot_current_selection()

    def _update_status(self) -> None:
        """Update status label based on current selections."""
        pred_cols = self._current_prediction_columns()
        actual_cols = self._current_actual_columns()

        if not pred_cols and not actual_cols:
            self.status_label.setText("⚠ Select at least one column from predictions or actual data")
        else:
            parts = []
            if pred_cols:
                parts.append(f"Predictions: {', '.join(pred_cols)}")
            if actual_cols:
                parts.append(f"Actual: {', '.join(actual_cols)}")
            self.status_label.setText(f"📊 Plotting: {' | '.join(parts)}")
            self.status_label.setStyleSheet(
                "color: #0F172A; font-weight: 500; padding: 8px; "
                "background: #D1FAE5; border-radius: 6px;"
            )

    def _current_prediction_columns(self) -> List[str]:
        """Get currently selected prediction columns."""
        return [item.data(Qt.UserRole) for item in self.y_pred_selector.selectedItems()]

    def _current_actual_columns(self) -> List[str]:
        """Get currently selected actual data columns."""
        return [item.data(Qt.UserRole) for item in self.y_actual_selector.selectedItems()]

    def _plot_current_selection(self) -> None:
        """Plot the currently selected axes."""
        pred_columns = self._current_prediction_columns()
        actual_columns = self._current_actual_columns()

        if not pred_columns and not actual_columns:
            return

        try:
            self._plot_data(pred_columns, actual_columns)
        except ValueError as exc:
            QMessageBox.warning(self, "Plotter", str(exc))

    def _plot_data(self, pred_columns: List[str], actual_columns: List[str]) -> None:
        """Plot predictions and actual data."""
        if not pred_columns and not actual_columns:
            raise ValueError("No columns selected for plotting.")

        self.figure.clear()

        # Create subplot(s) based on whether difference plot is enabled
        show_diff = self.show_difference.isChecked() and pred_columns and actual_columns

        if show_diff:
            ax = self.figure.add_subplot(211)
            ax_diff = self.figure.add_subplot(212)
        else:
            ax = self.figure.add_subplot(111)
            ax_diff = None

        ax.set_facecolor("#FFFFFF")

        # Professional color palette
        pred_colors = ["#DC2626", "#B91C1C", "#991B1B", "#7F1D1D"]  # Red shades for predictions
        actual_colors = ["#1D4ED8", "#1E40AF", "#1E3A8A", "#1E3A8A"]  # Blue shades for actual

        # Determine if we should show markers
        show_markers = self.show_markers.isChecked()
        marker = "o" if show_markers else None
        markersize = 3 if show_markers else None

        all_lines = []
        all_labels = []

        # X-axis: use row index
        x_data = np.arange(len(self._actual_data))

        # Plot predictions
        for i, column in enumerate(pred_columns):
            color = pred_colors[i % len(pred_colors)]
            y_data = self._predictions[column].values

            (line,) = ax.plot(
                x_data,
                y_data,
                color=color,
                label=f"Pred: {column}",
                marker=marker,
                markersize=markersize,
                linewidth=2.5,
                alpha=0.8,
                linestyle="--",
            )
            all_lines.append(line)
            all_labels.append(f"Pred: {column}")

        # Plot actual data
        for i, column in enumerate(actual_columns):
            color = actual_colors[i % len(actual_colors)]
            y_data = self._actual_data[column].values

            (line,) = ax.plot(
                x_data,
                y_data,
                color=color,
                label=f"Actual: {column}",
                marker=marker,
                markersize=markersize,
                linewidth=2.5,
                alpha=0.8,
                linestyle="-",
            )
            all_lines.append(line)
            all_labels.append(f"Actual: {column}")

        # Style main plot
        ax.set_xlabel("Data Point Index", fontsize=12, fontweight="bold", labelpad=15)
        ax.set_ylabel("Value", fontsize=12, fontweight="bold", labelpad=15)
        ax.set_title("Predictions vs Actual Data", fontweight="bold", fontsize=14, pad=15)
        ax.tick_params(axis="both", labelsize=10, width=1.5, length=6)

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

        # Legend
        legend_ncol = min(len(all_labels), 4)
        ax.legend(
            all_lines,
            all_labels,
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

        # Plot difference if enabled
        if ax_diff is not None:
            ax_diff.set_facecolor("#FFFFFF")

            # Calculate and plot differences for matching columns
            for pred_col in pred_columns:
                if pred_col in actual_columns:
                    diff = self._actual_data[pred_col].values - self._predictions[pred_col].values
                    ax_diff.plot(
                        x_data,
                        diff,
                        label=f"Error: {pred_col}",
                        marker=marker,
                        markersize=markersize,
                        linewidth=2,
                        alpha=0.7,
                    )

            # Add zero line
            ax_diff.axhline(y=0, color="black", linestyle="-", linewidth=1, alpha=0.5)

            ax_diff.set_xlabel("Data Point Index", fontsize=12, fontweight="bold", labelpad=15)
            ax_diff.set_ylabel("Error (Actual - Predicted)", fontsize=12, fontweight="bold", labelpad=15)
            ax_diff.set_title("Prediction Error", fontweight="bold", fontsize=14, pad=15)
            ax_diff.tick_params(axis="both", labelsize=10, width=1.5, length=6)

            if self.grid_toggle.isChecked():
                ax_diff.grid(
                    True,
                    color="#E2E8F0",
                    alpha=0.4,
                    linestyle="--",
                    linewidth=0.8,
                    zorder=0
                )
                ax_diff.set_axisbelow(True)

            ax_diff.legend(
                loc="upper right",
                frameon=True,
                fancybox=True,
                shadow=True,
                fontsize=9,
                edgecolor="#E5E7EB",
                framealpha=0.95,
            )

        self.figure.tight_layout()
        self.canvas.draw_idle()

        # Update statistics
        try:
            all_selected_cols = []
            stats_df_parts = []

            if pred_columns:
                pred_stats = self._predictions[pred_columns].copy()
                pred_stats.columns = [f"Pred: {col}" for col in pred_columns]
                stats_df_parts.append(pred_stats)

            if actual_columns:
                actual_stats = self._actual_data[actual_columns].copy()
                actual_stats.columns = [f"Actual: {col}" for col in actual_columns]
                stats_df_parts.append(actual_stats)

            if stats_df_parts:
                stats_df = pd.concat(stats_df_parts, axis=1)
                self.stats_area.update_stats(stats_df.select_dtypes(include=[np.number]))
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
                    for ax in axes:
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
            for ax in axes:
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

        self.canvas.draw_idle()

    def _export_plot(self) -> None:
        """Export current plot to image file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            "prediction_plot.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches="tight")
                QMessageBox.information(self, "Export Success", f"Plot saved to:\n{file_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export plot:\n{exc}")

    def _export_data(self) -> None:
        """Export predictions and actual data to CSV file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "prediction_data.csv",
            "CSV Files (*.csv)",
        )

        if file_path:
            try:
                # Combine predictions and actual data
                combined_df = pd.DataFrame()

                # Add predictions with prefix
                for col in self._predictions.columns:
                    combined_df[f"Pred_{col}"] = self._predictions[col]

                # Add actual data with prefix
                for col in self._actual_data.columns:
                    combined_df[f"Actual_{col}"] = self._actual_data[col]

                combined_df.to_csv(file_path, index=True, index_label="Index")
                QMessageBox.information(
                    self, "Export Success", f"Data exported to:\n{file_path}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export data:\n{exc}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Handle window close event."""
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)


# Global list to track open plotter windows
_open_windows: List[AnomalyPredictionPlotterWindow] = []


def run(
    actual_data: pd.DataFrame,
    predictions: pd.DataFrame,
    file_name: str = "Anomaly Predictions",
    parent: Optional[QWidget] = None
) -> None:
    """Launch the prediction plotter window.

    Args:
        actual_data: DataFrame containing actual data
        predictions: DataFrame containing model predictions
        file_name: Name to display in window title
        parent: Optional parent widget
    """
    try:
        window = AnomalyPredictionPlotterWindow(actual_data, predictions, file_name)
    except Exception as exc:
        QMessageBox.critical(None, "Prediction Plotter", f"Unable to open plotter: {exc}")
        return

    window.show()
    window.raise_()
    window.activateWindow()
    _open_windows.append(window)
