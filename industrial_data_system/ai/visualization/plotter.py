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
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
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
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run", "create_plotter_widget"]


class PlotCard(QWidget):
    """Individual plot card that can be edited and customized."""

    def __init__(self, df: pd.DataFrame, plot_id: int, parent=None):
        super().__init__(parent)
        self.df = df
        self.plot_id = plot_id
        self.x_column = None
        self.y_columns = []
        self.plot_title = f"Plot {plot_id + 1}"
        self.show_grid = True
        self.line_colors = {}
        self.line_styles = {}
        self.line_widths = {}

        self.setup_ui()

    def setup_ui(self):
        """Initialize the plot card UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header with title and remove button
        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.plot_title)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #1F2937;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        remove_btn.clicked.connect(lambda: self.parent().remove_plot_card(self))
        header_layout.addWidget(remove_btn)

        layout.addLayout(header_layout)

        # Matplotlib figure
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFixedHeight(350)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 2px;")

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Set background
        self.setStyleSheet("""
            PlotCard {
                background: white;
                border: 2px solid #E5E7EB;
                border-radius: 8px;
            }
        """)

    def update_plot(self, x_column=None, y_columns=None, title=None, show_grid=None):
        """Update the plot with new data."""
        if x_column is not None:
            self.x_column = x_column
        if y_columns is not None:
            self.y_columns = y_columns
        if title is not None:
            self.plot_title = title
            self.title_label.setText(title)
        if show_grid is not None:
            self.show_grid = show_grid

        if not self.x_column or not self.y_columns:
            return

        self.render_plot()

    def render_plot(self):
        """Render the plot on the canvas."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#FFFFFF")

        try:
            x_data = pd.to_numeric(self.df[self.x_column], errors="coerce")

            # Professional color palette
            professional_colors = [
                "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
            ]

            for i, column in enumerate(self.y_columns):
                series = pd.to_numeric(self.df[column], errors="coerce")
                valid = series.notna() & x_data.notna()

                if not valid.any():
                    continue

                # Get custom styling or use defaults
                color = self.line_colors.get(column, professional_colors[i % len(professional_colors)])
                style = self.line_styles.get(column, '-')
                width = self.line_widths.get(column, 2.0)

                ax.plot(
                    x_data[valid],
                    series[valid],
                    color=color,
                    linestyle=style,
                    linewidth=width,
                    label=column,
                    alpha=0.9,
                )

            ax.set_xlabel(self.x_column, fontsize=10, fontweight="bold")
            ax.set_ylabel("Value", fontsize=10, fontweight="bold")
            ax.set_title(self.plot_title, fontsize=11, fontweight="bold", pad=10)

            if self.show_grid:
                ax.grid(True, color="#E2E8F0", alpha=0.4, linestyle="--", linewidth=0.8)
                ax.set_axisbelow(True)

            if self.y_columns:
                ax.legend(loc="best", fontsize=9, framealpha=0.95, edgecolor="#E5E7EB")

            self.figure.tight_layout()
            self.canvas.draw_idle()

        except Exception as e:
            print(f"Error rendering plot: {e}")


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
        self._plot_cards = []
        self._plot_counter = 0

        self.setObjectName("quick-plotter-window")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(f"Plot Editor - {self._file_path.name}")
        self.resize(1400, 900)

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        """Build the main user interface with LEFT=plots, RIGHT=toolbar."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main horizontal layout
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
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

        # ========== LEFT PANEL: Scrollable Plot Area (like PDF) ==========
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(8)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📊 Plot Report")
        header.setStyleSheet("font-size: 18px; font-weight: 600; color: #0F172A;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        # Save Report button
        save_report_btn = QPushButton("💾 Save as PDF Report")
        save_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        save_report_btn.clicked.connect(self._save_as_report)
        header_layout.addWidget(save_report_btn)

        left_layout.addLayout(header_layout)

        # Scrollable area for plots
        self.plots_scroll_area = QScrollArea()
        self.plots_scroll_area.setWidgetResizable(True)
        self.plots_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.plots_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.plots_scroll_area.setFrameShape(QScrollArea.StyledPanel)
        self.plots_scroll_area.setStyleSheet("""
            QScrollArea {
                background: #F9FAFB;
                border: 2px solid #E5E7EB;
                border-radius: 8px;
            }
        """)

        # Container for plot cards
        self.plots_container = QWidget()
        self.plots_layout = QVBoxLayout(self.plots_container)
        self.plots_layout.setContentsMargins(12, 12, 12, 12)
        self.plots_layout.setSpacing(16)
        self.plots_layout.addStretch()

        self.plots_scroll_area.setWidget(self.plots_container)
        left_layout.addWidget(self.plots_scroll_area)

        # ========== RIGHT PANEL: Toolbar and Controls ==========
        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(400)
        right_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(12)

        # Toolbar header
        toolbar_header = QLabel("🛠 Plot Toolbar")
        toolbar_header.setStyleSheet("font-size: 16px; font-weight: 600; color: #0F172A;")
        right_layout.addWidget(toolbar_header)

        # File information
        file_info_group = QGroupBox("File Information")
        file_info_layout = QVBoxLayout(file_info_group)

        self.file_info_label = QLabel()
        self.file_info_label.setWordWrap(True)
        self.file_info_label.setStyleSheet("color: #4B5563; font-size: 11px;")
        file_info_layout.addWidget(self.file_info_label)

        right_layout.addWidget(file_info_group)

        # Add Plot Section
        add_plot_group = QGroupBox("Add New Plot")
        add_plot_layout = QVBoxLayout(add_plot_group)

        add_plot_btn = QPushButton("➕ Add Plot")
        add_plot_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #1E40AF;
            }
        """)
        add_plot_btn.clicked.connect(self._add_new_plot)
        add_plot_layout.addWidget(add_plot_btn)

        right_layout.addWidget(add_plot_group)

        # Plot Configuration Section
        config_group = QGroupBox("Plot Configuration")
        config_layout = QVBoxLayout(config_group)

        # Plot title
        title_label = QLabel("Plot Title:")
        title_label.setStyleSheet("font-weight: 600; color: #1F2937; font-size: 11px;")
        config_layout.addWidget(title_label)

        self.plot_title_input = QLineEdit()
        self.plot_title_input.setPlaceholderText("Enter plot title...")
        self.plot_title_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background: white;
            }
        """)
        config_layout.addWidget(self.plot_title_input)

        # X Axis selection
        x_label = QLabel("X Axis:")
        x_label.setStyleSheet("font-weight: 600; color: #1F2937; margin-top: 8px; font-size: 11px;")
        config_layout.addWidget(x_label)

        self.x_selector = QComboBox()
        self.x_selector.setStyleSheet("""
            QComboBox {
                padding: 6px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background: white;
            }
        """)
        config_layout.addWidget(self.x_selector)

        # Y Axes selection
        y_label = QLabel("Y Axes (Multi-select):")
        y_label.setStyleSheet("font-weight: 600; color: #1F2937; margin-top: 8px; font-size: 11px;")
        config_layout.addWidget(y_label)

        self.y_selector = QListWidget()
        self.y_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        self.y_selector.setStyleSheet("""
            QListWidget {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px;
                background: white;
            }
            QListWidget::item:selected {
                background: #DBEAFE;
                color: #1E3A8A;
            }
        """)
        config_layout.addWidget(self.y_selector)

        # Grid toggle
        self.grid_toggle = QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)
        self.grid_toggle.setStyleSheet("margin-top: 8px;")
        config_layout.addWidget(self.grid_toggle)

        # Apply button
        apply_btn = QPushButton("Apply to Selected Plot")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #7C3AED;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 8px;
            }
            QPushButton:hover {
                background-color: #6D28D9;
            }
        """)
        apply_btn.clicked.connect(self._apply_plot_config)
        config_layout.addWidget(apply_btn)

        right_layout.addWidget(config_group)

        # Statistics area
        self.stats_area = StatisticsArea(self)
        right_layout.addWidget(self.stats_area)

        right_layout.addStretch()

        # Add panels to splitter
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(right_panel)

        # Set initial splitter sizes (70% left, 30% right)
        self.main_splitter.setStretchFactor(0, 7)
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
        self._populate_file_info()
        self._populate_selectors(df)

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

    def _populate_file_info(self) -> None:
        """Populate file information label."""
        if self._dataframe is None:
            return

        shape_str = f"{self._dataframe.shape[0]} rows × {self._dataframe.shape[1]} columns"
        info_text = f"<b>File:</b> {self._file_path.name}<br><b>Size:</b> {shape_str}"
        self.file_info_label.setText(info_text)

    def _populate_selectors(self, df: pd.DataFrame) -> None:
        """Populate axis selectors with column names."""
        self.x_selector.clear()
        self.y_selector.clear()

        numeric_columns = [
            column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])
        ]

        # Populate X axis combo box
        for column in df.columns:
            self.x_selector.addItem(column)

        # Populate Y axis list widget with numeric columns
        for column in numeric_columns:
            item = QListWidgetItem(column)
            self.y_selector.addItem(item)

    def _add_new_plot(self) -> None:
        """Add a new plot card to the scrollable area."""
        if self._dataframe is None:
            QMessageBox.warning(self, "Plotter", "No data loaded.")
            return

        # Create new plot card
        plot_card = PlotCard(self._dataframe, self._plot_counter, self.plots_container)
        self._plot_cards.append(plot_card)
        self._plot_counter += 1

        # Insert before the stretch
        self.plots_layout.insertWidget(self.plots_layout.count() - 1, plot_card)

        # Scroll to the new plot
        QApplication.processEvents()
        self.plots_scroll_area.ensureWidgetVisible(plot_card)

    def remove_plot_card(self, plot_card: PlotCard) -> None:
        """Remove a plot card from the scrollable area."""
        if plot_card in self._plot_cards:
            self._plot_cards.remove(plot_card)
            self.plots_layout.removeWidget(plot_card)
            plot_card.deleteLater()

    def _apply_plot_config(self) -> None:
        """Apply configuration to the most recently added plot."""
        if not self._plot_cards:
            QMessageBox.information(self, "Plot Configuration", "Please add a plot first using the '➕ Add Plot' button.")
            return

        # Get the last plot card
        plot_card = self._plot_cards[-1]

        # Get configuration values
        x_column = self.x_selector.currentText()
        selected_y_items = self.y_selector.selectedItems()
        y_columns = [item.text() for item in selected_y_items]
        title = self.plot_title_input.text() or f"Plot {plot_card.plot_id + 1}"
        show_grid = self.grid_toggle.isChecked()

        if not x_column:
            QMessageBox.warning(self, "Configuration", "Please select an X axis column.")
            return

        if not y_columns:
            QMessageBox.warning(self, "Configuration", "Please select at least one Y axis column.")
            return

        # Apply configuration to the plot
        plot_card.update_plot(
            x_column=x_column,
            y_columns=y_columns,
            title=title,
            show_grid=show_grid
        )

        # Update statistics
        try:
            stats_df = self._dataframe[y_columns].select_dtypes(include=[np.number])
            self.stats_area.update_stats(stats_df)
        except Exception:
            self.stats_area.clear_stats()

    def _save_as_report(self) -> None:
        """Save all plots as a PDF report."""
        if not self._plot_cards:
            QMessageBox.information(self, "Save Report", "No plots to save. Please add plots first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report as PDF",
            f"{self._file_path.stem}_report.pdf",
            "PDF (*.pdf)",
        )

        if not file_path:
            return

        try:
            from matplotlib.backends.backend_pdf import PdfPages

            with PdfPages(file_path) as pdf:
                for plot_card in self._plot_cards:
                    if plot_card.x_column and plot_card.y_columns:
                        # Save each plot's figure to PDF
                        pdf.savefig(plot_card.figure, bbox_inches="tight")

            QMessageBox.information(
                self,
                "Save Success",
                f"Report saved successfully to:\n{file_path}\n\nTotal plots: {len(self._plot_cards)}"
            )

        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", f"Failed to save report:\n{exc}")

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