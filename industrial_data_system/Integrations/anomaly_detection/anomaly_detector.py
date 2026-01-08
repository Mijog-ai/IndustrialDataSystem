"""Anomaly detection visualization using trained autoencoder models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# from industrial_data_system.Integrations.anomaly_detection import anomaly_prediction_plotter
from industrial_data_system.core.config import get_config
from industrial_data_system.core.db_manager import DatabaseManager, ModelRegistryRecord
from industrial_data_system.utils.asc_utils import (
    convert_asc_to_parquet,
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run", "run_standalone"]


class AnomalyDetectorWindow(QMainWindow):
    """Window for detecting and visualizing anomalies using trained models."""

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

    def __init__(self, file_path: Optional[Path] = None) -> None:
        super().__init__()
        self._file_path: Optional[Path] = file_path
        self._dataframe: Optional[pd.DataFrame] = None
        self._model = None
        self._scaler = None
        self._reconstruction_errors: Optional[np.ndarray] = None
        self._anomaly_indices: Optional[np.ndarray] = None
        self._threshold: float = 0.0

        # Model version management
        self._database = DatabaseManager()
        self._pump_series: str = ""
        self._test_type: str = ""
        self._file_type: str = ""
        self._available_versions: List[ModelRegistryRecord] = []
        self._current_version: Optional[int] = None
        self._metadata: Dict[str, Any] = {}

        # Comparison mode
        self._comparison_mode: bool = False
        self._compare_model = None
        self._compare_scaler = None
        self._compare_reconstruction_errors: Optional[np.ndarray] = None
        self._compare_anomaly_indices: Optional[np.ndarray] = None
        self._compare_threshold: float = 0.0
        self._compare_version: Optional[int] = None
        self._compare_metadata: Dict[str, Any] = {}

        self.setObjectName("anomaly-detector-window")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        window_title = f"Anomaly Detection - {file_path.name}" if file_path else "Anomaly Detection"
        self.setWindowTitle(window_title)
        self.resize(1600, 900)

        self._build_ui()

        # Only load data if file_path is provided
        if file_path:
            self._load_data()
            self._extract_path_info()
            self._load_available_versions()
            self._load_model()
        else:
            # Standalone mode: populate pump series and test types
            self._populate_pump_series()
            self._disable_controls()

    def _build_ui(self) -> None:
        """Build the main user interface."""
        # ========== MENU BAR ==========
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        load_action = QAction("Load Data File...", self)
        load_action.triggered.connect(self._load_file_dialog)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main horizontal layout to hold the splitter
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

        # # ========== LEFT PANEL: Controls ==========
        # left_panel = QWidget()
        # left_panel.setMinimumWidth(300)
        # left_panel.setMaximumWidth(600)  # Increased max width, but still constrained
        # left_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # left_layout = QVBoxLayout(left_panel)
        # left_layout.setContentsMargins(0, 0, 8, 0)
        # left_layout.setSpacing(0)
        #
        # # Header
        # header = QLabel("Anomaly Detector")
        # header.setStyleSheet("font-size: 20px; font-weight: 600; color: #DC2626; margin-bottom: 12px;")
        # left_layout.addWidget(header)
        #
        # # Create vertical splitter for resizable group boxes
        # left_splitter = QSplitter(Qt.Vertical)
        # left_splitter.setHandleWidth(6)
        # left_splitter.setStyleSheet(
        #     """
        #     QSplitter::handle {
        #         background: #E5E7EB;
        #         margin: 2px 0px;
        #     }
        #     QSplitter::handle:hover {
        #         background: #DC2626;
        #     }
        #     """
        # )
        # left_layout.addWidget(left_splitter)
        #
        # # Data selection group (for standalone mode)
        # self.data_selection_group = QGroupBox("Data Selection")
        # data_selection_layout = QVBoxLayout(self.data_selection_group)
        #
        # # Pump series selection
        # pump_layout = QHBoxLayout()
        # pump_layout.addWidget(QLabel("Pump Series:"))
        # self.pump_series_combo = QComboBox()
        # self.pump_series_combo.setMinimumWidth(150)
        # self.pump_series_combo.currentIndexChanged.connect(self._on_pump_series_changed)
        # pump_layout.addWidget(self.pump_series_combo)
        # pump_layout.addStretch()
        # data_selection_layout.addLayout(pump_layout)
        #
        # # Test type selection
        # test_layout = QHBoxLayout()
        # test_layout.addWidget(QLabel("Test Type:"))
        # self.test_type_combo = QComboBox()
        # self.test_type_combo.setMinimumWidth(150)
        # self.test_type_combo.currentIndexChanged.connect(self._on_test_type_changed)
        # test_layout.addWidget(self.test_type_combo)
        # test_layout.addStretch()
        # data_selection_layout.addLayout(test_layout)
        #
        # left_splitter.addWidget(self.data_selection_group)
        #
        # # Model info group
        # model_group = QGroupBox("Model Information")
        # model_layout = QVBoxLayout(model_group)
        #
        # # Version selection
        # version_layout = QHBoxLayout()
        # version_layout.addWidget(QLabel("Model Version:"))
        # self.version_combo = QComboBox()
        # self.version_combo.setMinimumWidth(150)
        # self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        # version_layout.addWidget(self.version_combo)
        # version_layout.addStretch()
        # model_layout.addLayout(version_layout)
        #
        # left_splitter.addWidget(model_group)
        #
        # # Comparison mode group
        # compare_group = QGroupBox("Model Comparison")
        # compare_layout = QVBoxLayout(compare_group)
        #
        # self.compare_checkbox = QCheckBox("Enable Comparison Mode")
        # self.compare_checkbox.stateChanged.connect(self._on_comparison_toggled)
        # compare_layout.addWidget(self.compare_checkbox)
        #
        # compare_version_layout = QHBoxLayout()
        # compare_version_layout.addWidget(QLabel("Compare with:"))
        # self.compare_version_combo = QComboBox()
        # self.compare_version_combo.setMinimumWidth(150)
        # self.compare_version_combo.setEnabled(False)
        # self.compare_version_combo.currentIndexChanged.connect(self._on_compare_version_changed)
        # compare_version_layout.addWidget(self.compare_version_combo)
        # compare_version_layout.addStretch()
        # compare_layout.addLayout(compare_version_layout)
        #
        # left_splitter.addWidget(compare_group)
        #
        # # Detection settings group
        # settings_group = QGroupBox("Detection Settings")
        # settings_layout = QGridLayout(settings_group)
        #
        # settings_layout.addWidget(QLabel("Threshold Method:"), 0, 0)
        # self.threshold_method = QListWidget()
        # self.threshold_method.addItems(
        #     ["Mean + 2×Std", "Mean + 3×Std", "95th Percentile", "99th Percentile", "Custom Value"]
        # )
        # self.threshold_method.setCurrentRow(1)  # Default: Mean + 3×Std
        # self.threshold_method.setMaximumHeight(120)
        # self.threshold_method.currentRowChanged.connect(self._on_threshold_method_changed)
        # settings_layout.addWidget(self.threshold_method, 1, 0, 1, 2)
        #
        # settings_layout.addWidget(QLabel("Custom Threshold:"), 2, 0)
        # self.custom_threshold = QDoubleSpinBox()
        # self.custom_threshold.setDecimals(6)
        # self.custom_threshold.setRange(0.0, 1000.0)
        # self.custom_threshold.setValue(0.1)
        # self.custom_threshold.setEnabled(False)
        # settings_layout.addWidget(self.custom_threshold, 2, 1)
        #
        # detect_btn = QPushButton("Detect Anomalies")
        # detect_btn.setProperty("primary", True)
        # detect_btn.clicked.connect(self._detect_anomalies)
        # settings_layout.addWidget(detect_btn, 3, 0, 1, 2)
        #
        # left_splitter.addWidget(settings_group)
        #
        # # Statistics group
        # stats_group = QGroupBox("Detection Results")
        # stats_layout = QVBoxLayout(stats_group)
        #
        # self.stats_table = QTableWidget()
        # self.stats_table.setRowCount(6)
        # self.stats_table.setColumnCount(2)
        # self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        # self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # self.stats_table.verticalHeader().setVisible(False)
        # self.stats_table.setMaximumHeight(220)
        # self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        # stats_layout.addWidget(self.stats_table)
        #
        # left_splitter.addWidget(stats_group)
        #
        # # Export buttons container
        # export_container = QWidget()
        # export_layout = QVBoxLayout(export_container)
        # export_layout.setContentsMargins(0, 0, 0, 0)
        # export_layout.setSpacing(8)
        #
        # export_anomalies_btn = QPushButton("Export Anomalies")
        # export_anomalies_btn.setProperty("secondary", True)
        # export_anomalies_btn.clicked.connect(self._export_anomalies)
        # export_layout.addWidget(export_anomalies_btn)
        #
        # export_plot_btn = QPushButton("Export Plot")
        # export_plot_btn.setProperty("secondary", True)
        # export_plot_btn.clicked.connect(self._export_plot)
        # export_layout.addWidget(export_plot_btn)
        #
        # decode_predict_btn = QPushButton("Decode & Predict")
        # decode_predict_btn.setProperty("primary", True)
        # decode_predict_btn.clicked.connect(self._decode_and_predict)
        # export_layout.addWidget(decode_predict_btn)
        #
        # close_btn = QPushButton("Close")
        # close_btn.setProperty("secondary", True)
        # close_btn.clicked.connect(self.close)
        # export_layout.addWidget(close_btn)
        #
        # export_layout.addStretch()
        #
        # left_splitter.addWidget(export_container)
        #
        # # Configure splitter stretch factors
        # # Make stats and export container take minimal space by default
        # left_splitter.setStretchFactor(0, 1)  # Data Selection
        # left_splitter.setStretchFactor(1, 0)  # Model Information
        # left_splitter.setStretchFactor(2, 0)  # Model Comparison
        # left_splitter.setStretchFactor(3, 1)  # Detection Settings
        # left_splitter.setStretchFactor(4, 2)  # Detection Results
        # left_splitter.setStretchFactor(5, 0)  # Export buttons
        #
        # # Set collapsible behavior for all sections
        # for i in range(left_splitter.count()):
        #     left_splitter.setCollapsible(i, False)
        #
        # # ========== RIGHT PANEL: Plots ==========
        # right_panel = QWidget()
        # right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # right_layout = QVBoxLayout(right_panel)
        # right_layout.setContentsMargins(0, 0, 0, 0)
        # right_layout.setSpacing(12)
        #
        # # Status label
        # self.status_label = QLabel("Loading model...")
        # self.status_label.setStyleSheet(
        #     "color: #0F172A; font-weight: 500; padding: 8px; "
        #     "background: #FEF3C7; border-radius: 6px;"
        # )
        # self.status_label.setAlignment(Qt.AlignCenter)
        # right_layout.addWidget(self.status_label)
        #
        # # Matplotlib figure with dynamic DPI based on device pixel ratio
        # # Get device pixel ratio for proper scaling across different screen sizes
        # pixel_ratio = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
        # dpi = int(100 * pixel_ratio)
        # self.figure = Figure(figsize=(12, 10), dpi=dpi)
        # self.figure.patch.set_facecolor("#FFFFFF")
        # self.canvas = FigureCanvas(self.figure)
        # self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #
        # self.toolbar = NavigationToolbar(self.canvas, self)
        # self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")
        #
        # right_layout.addWidget(self.toolbar)
        # right_layout.addWidget(self.canvas)
        #
        # # Add panels to splitter
        # self.main_splitter.addWidget(left_panel)
        # self.main_splitter.addWidget(right_panel)
        #
        # # Set initial splitter sizes (25% left, 75% right)
        # # Using proportional sizes that adapt to window size
        # self.main_splitter.setStretchFactor(0, 1)  # Left panel
        # self.main_splitter.setStretchFactor(1, 3)  # Right panel gets more space
        #
        # # Set collapsible behavior
        # self.main_splitter.setCollapsible(0, False)
        # self.main_splitter.setCollapsible(1, False)
        #
        # # Add splitter to main layout
        # main_layout.addWidget(self.main_splitter)
        #
        # # Apply styles
        # self.setStyleSheet(
        #     """
        #     QMainWindow#anomaly-detector-window {
        #         background: #FFFFFF;
        #     }
        #     QWidget {
        #         background: #FFFFFF;
        #         color: #0F172A;
        #     }
        #     QGroupBox {
        #         font-weight: 600;
        #         border: 2px solid #FCA5A5;
        #         border-radius: 8px;
        #         margin-top: 12px;
        #         padding-top: 8px;
        #     }
        #     QGroupBox::title {
        #         subcontrol-origin: margin;
        #         left: 10px;
        #         padding: 0 5px;
        #     }
        #     QListWidget {
        #         border: 1px solid #D1D5DB;
        #         border-radius: 6px;
        #         padding: 4px;
        #         background: #F9FAFB;
        #     }
        #     QListWidget::item:selected {
        #         background: #FEE2E2;
        #         color: #991B1B;
        #     }
        #     QListWidget::item:hover {
        #         background: #FEF2F2;
        #     }
        #     QTableWidget {
        #         background: #F9FAFB;
        #         border: 1px solid #E5E7EB;
        #         border-radius: 4px;
        #     }
        #     QComboBox {
        #         border: 1px solid #D1D5DB;
        #         border-radius: 4px;
        #         padding: 4px 8px;
        #         background: #F9FAFB;
        #         min-height: 24px;
        #     }
        #     QComboBox:hover {
        #         border-color: #DC2626;
        #     }
        #     QComboBox::drop-down {
        #         border: none;
        #         padding-right: 8px;
        #     }
        #     QCheckBox {
        #         spacing: 8px;
        #     }
        #     QCheckBox::indicator {
        #         width: 18px;
        #         height: 18px;
        #         border: 2px solid #D1D5DB;
        #         border-radius: 4px;
        #         background: #FFFFFF;
        #     }
        #     QCheckBox::indicator:checked {
        #         background: #DC2626;
        #         border-color: #DC2626;
        #     }
        #     QCheckBox::indicator:hover {
        #         border-color: #DC2626;
        #     }
        #     """
        #     + self.BUTTON_STYLES
        # )

    def _load_data(self) -> None:
        """Load data from the file."""
        df = self._read_file(self._file_path)

        if df.empty:
            raise ValueError("The selected file did not contain any data.")

        self._dataframe = df
        self.status_label.setText(f"✓ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")

    @staticmethod
    def _read_file(path: Path) -> pd.DataFrame:
        """Read file and return DataFrame."""
        ext = path.suffix.lower()

        if ext == ".parquet":
            return pd.read_parquet(path, engine="pyarrow")
        if ext == ".csv":
            return load_and_process_csv_file(str(path))
        if ext == ".tdms":
            return load_and_process_tdms_file(str(path))
        if ext in {".asc", ".sc"}:  # .sc files treated same as .asc
            return load_and_process_asc_file(str(path))
        if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
            return pd.read_excel(path)

        raise ValueError(f"Unsupported file type: {ext}")

    def _extract_path_info(self) -> None:
        """Extract pump series, test type, and file type from file path."""
        if not self._file_path:
            # In standalone mode, use selected values from dropdowns
            self._pump_series = self.pump_series_combo.currentText()
            self._test_type = self.test_type_combo.currentText()
            self._file_type = "parquet"  # Default to parquet for loaded files
            return

        # Check if we're in standalone mode with a loaded file
        # (i.e., pump series and test type are already selected from dropdowns)
        pump_series_selected = self.pump_series_combo.currentText() and \
                              self.pump_series_combo.currentText() != "Select Pump Series"
        test_type_selected = self.test_type_combo.currentText() and \
                            self.test_type_combo.currentText() != "Select Test Type"

        if pump_series_selected and test_type_selected:
            # Standalone mode with loaded file - use dropdown selections
            self._pump_series = self.pump_series_combo.currentText()
            self._test_type = self.test_type_combo.currentText()
            ext = self._file_path.suffix.lower()
            self._file_type = "parquet" if ext == ".parquet" else "csv"
            return

        # Regular mode - extract from file path
        file_parts = self._file_path.parts

        if "tests" not in file_parts:
            raise ValueError("Could not determine test type from file path")

        tests_index = file_parts.index("tests")
        if tests_index + 1 >= len(file_parts):
            raise ValueError("Invalid file path structure")

        self._test_type = file_parts[tests_index + 1]
        self._pump_series = file_parts[tests_index - 1] if tests_index > 0 else "General"

        ext = self._file_path.suffix.lower()
        self._file_type = "parquet" if ext == ".parquet" else "csv"

    def _load_file_dialog(self) -> None:
        """Open file dialog to load a new data file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Data File",
            "",
            "All Supported Files (*.sc *.asc *.parquet *.csv *.tdms);;SC Files (*.sc);;ASC Files (*.asc);;Parquet Files (*.parquet);;CSV Files (*.csv);;TDMS Files (*.tdms);;All Files (*.*)"
        )

        if not file_path:
            return  # User cancelled

        file_path = Path(file_path)

        # Check if pump series and test type are selected
        if not self.pump_series_combo.currentText() or not self.test_type_combo.currentText():
            QMessageBox.warning(
                self,
                "Selection Required",
                "Please select Pump Series and Test Type before loading a file."
            )
            return

        try:
            # Convert .sc or .asc files to parquet first
            if file_path.suffix.lower() in {'.sc', '.asc'}:
                self.status_label.setText("Converting file to Parquet format...")

                # Get pump series and test type from selections
                pump_series = self.pump_series_combo.currentText()
                test_type = self.test_type_combo.currentText()

                # Construct path: files_base_path / pump_series / tests / test_type / newdatasets
                config = get_config()
                newdatasets_dir = config.files_base_path / pump_series / "tests" / "newdatasets"

                # Create the directory if it doesn't exist
                newdatasets_dir.mkdir(parents=True, exist_ok=True)

                # Construct the target parquet file path
                parquet_filename = file_path.stem + ".parquet"
                target_parquet_path = newdatasets_dir / parquet_filename

                # Convert to parquet at the new location
                parquet_path = convert_asc_to_parquet(file_path, parquet_path=target_parquet_path, preserve_asc=True)
                if parquet_path is None:
                    QMessageBox.critical(
                        self,
                        "Conversion Failed",
                        "The file could not be converted to Parquet format. It may be empty or invalid."
                    )
                    return
                file_path = parquet_path

            # Load the data
            self._file_path = file_path
            self._load_data()
            self._extract_path_info()
            self._load_available_versions()

            if self._available_versions:
                self._load_model()
                self._enable_controls()
                self.setWindowTitle(f"Anomaly Detection - {file_path.name}")
            else:
                QMessageBox.warning(
                    self,
                    "No Models Available",
                    f"No trained models found for {self._pump_series}/{self._test_type}. Please train a model first."
                )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Failed to load file:\n{exc}"
            )

    def _populate_pump_series(self) -> None:
        """Populate pump series dropdown from database."""
        try:
            pump_series_records = self._database.list_pump_series()
            self.pump_series_combo.clear()
            self.pump_series_combo.addItem("Select Pump Series", None)

            for record in pump_series_records:
                self.pump_series_combo.addItem(record.name, record.name)

        except Exception as exc:
            self.status_label.setText(f"⚠ Failed to load pump series: {exc}")

    def _on_pump_series_changed(self, index: int) -> None:
        """Handle pump series selection change."""
        pump_series = self.pump_series_combo.currentData()

        if pump_series:
            # Load test types for this pump series
            try:
                test_type_records = self._database.list_test_types(pump_series=pump_series)
                self.test_type_combo.clear()
                self.test_type_combo.addItem("Select Test Type", None)

                for record in test_type_records:
                    self.test_type_combo.addItem(record.name, record.name)

            except Exception as exc:
                self.status_label.setText(f"⚠ Failed to load test types: {exc}")
        else:
            self.test_type_combo.clear()
            self.test_type_combo.addItem("Select Test Type", None)

    def _on_test_type_changed(self, index: int) -> None:
        """Handle test type selection change."""
        test_type = self.test_type_combo.currentData()
        pump_series = self.pump_series_combo.currentData()

        if test_type and pump_series:
            # Update model versions for this combination
            self._pump_series = pump_series
            self._test_type = test_type
            self._file_type = "parquet"  # Default to parquet
            self._load_available_versions()

            # Enable controls and load model if versions are available
            if self._available_versions:
                self._enable_controls()
                # Load the latest model version if data is available
                if self._dataframe is not None:
                    self._load_model()
            else:
                # Show a message if no models are available
                self.status_label.setText(
                    f"⚠ No trained models found for {self._pump_series}/{self._test_type}. "
                    "Please train a model first or load a data file."
                )
                self.status_label.setStyleSheet(
                    "color: #0F172A; font-weight: 500; padding: 8px; "
                    "background: #FEF3C7; border-radius: 6px;"
                )

    def _disable_controls(self) -> None:
        """Disable controls when no data is loaded."""
        self.version_combo.setEnabled(False)
        self.compare_checkbox.setEnabled(False)
        self.compare_version_combo.setEnabled(False)
        self.threshold_method.setEnabled(False)
        self.custom_threshold.setEnabled(False)
        self.status_label.setText("Load a data file from File menu to begin")

    def _enable_controls(self) -> None:
        """Enable controls when data is loaded."""
        self.version_combo.setEnabled(True)
        self.compare_checkbox.setEnabled(True)
        self.threshold_method.setEnabled(True)

    def _load_available_versions(self) -> None:
        """Load all available model versions from database."""
        try:
            self._available_versions = self._database.get_all_model_versions(
                self._pump_series, self._test_type, self._file_type
            )

            # Populate version combo boxes
            self.version_combo.blockSignals(True)
            self.compare_version_combo.blockSignals(True)

            self.version_combo.clear()
            self.compare_version_combo.clear()

            if self._available_versions:
                for record in self._available_versions:
                    version_text = f"v{record.version} ({record.trained_at[:10]}, {record.file_count} files)"
                    self.version_combo.addItem(version_text, record.version)
                    self.compare_version_combo.addItem(version_text, record.version)

                # Select latest version by default
                self.version_combo.setCurrentIndex(0)
                # Select second version for comparison if available
                if len(self._available_versions) > 1:
                    self.compare_version_combo.setCurrentIndex(1)
            else:
                self.version_combo.addItem("No models available", None)
                self.compare_version_combo.addItem("No models available", None)

            self.version_combo.blockSignals(False)
            self.compare_version_combo.blockSignals(False)

        except Exception as exc:
            self.status_label.setText(f"⚠ Failed to load model versions: {exc}")

    def _get_version_paths(self, version: int) -> Tuple[Path, Path, Path]:
        """Get model, scaler, and metadata paths for a specific version."""
        # Find the record for this version
        record = next(
            (r for r in self._available_versions if r.version == version), None
        )

        if record:
            # Use paths from database record
            model_path = Path(record.model_path)
            scaler_path = Path(record.scaler_path) if record.scaler_path else None
            metadata_path = Path(record.metadata_path) if record.metadata_path else None
            return model_path, scaler_path, metadata_path

        # Fallback: try to construct paths from file path if available
        if self._file_path:
            test_folder = self._file_path.parent

            # Fallback to versioned file naming convention
            if version == self._available_versions[0].version if self._available_versions else 0:
                # Latest version uses non-versioned filename
                model_path = test_folder / f"model_{self._file_type}.pkl"
                scaler_path = test_folder / f"scaler_{self._file_type}.pkl"
                metadata_path = test_folder / f"metadata_{self._file_type}.json"
            else:
                # Older versions use versioned filename
                model_path = test_folder / f"model_{self._file_type}_v{version:03d}.pkl"
                scaler_path = test_folder / f"scaler_{self._file_type}_v{version:03d}.pkl"
                metadata_path = test_folder / f"metadata_{self._file_type}_v{version:03d}.json"

            return model_path, scaler_path, metadata_path

        # No paths available
        raise ValueError("Cannot determine model paths: no database record or file path available")

    def _load_model(self, version: Optional[int] = None) -> None:
        """Load the trained model for this file's test type.

        Args:
            version: Specific version to load. If None, loads the latest version.
        """
        try:
            # Determine which version to load
            if version is None:
                if self._available_versions:
                    version = self._available_versions[0].version
                else:
                    # Fallback: try to load default model file
                    version = 1

            self._current_version = version

            # Get paths for this version
            model_path, scaler_path, metadata_path = self._get_version_paths(version)

            # Fallback to non-versioned paths if versioned don't exist (only if we have a file path)
            if not model_path.exists() and self._file_path:
                test_folder = self._file_path.parent
                model_path = test_folder / f"model_{self._file_type}.pkl"
                scaler_path = test_folder / f"scaler_{self._file_type}.pkl"
                metadata_path = test_folder / f"metadata_{self._file_type}.json"

            if not model_path.exists():
                raise FileNotFoundError(
                    f"No trained model found for {self._pump_series}/{self._test_type}. "
                    f"Upload training data first to create a model."
                )

            # Load model state
            model_state = joblib.load(model_path)
            self._model = self._create_model_from_state(model_state)

            # Load scaler
            if scaler_path and scaler_path.exists():
                self._scaler = joblib.load(scaler_path)
            else:
                raise FileNotFoundError("Scaler file not found")

            # Load metadata
            self._metadata = {}
            if metadata_path and metadata_path.exists():
                self._metadata = json.loads(metadata_path.read_text())

            self.status_label.setText(
                f"✓ Model loaded: {self._pump_series} / {self._test_type} (v{version})"
            )
            self.status_label.setStyleSheet(
                "color: #0F172A; font-weight: 500; padding: 8px; "
                "background: #D1FAE5; border-radius: 6px;"
            )

        except Exception as exc:
            self.status_label.setText(f"⚠ Model loading failed: {exc}")
            self.status_label.setStyleSheet(
                "color: #0F172A; font-weight: 500; padding: 8px; "
                "background: #FEE2E2; border-radius: 6px;"
            )
            QMessageBox.warning(
                self,
                "Model Loading Failed",
                f"Could not load trained model:\n\n{exc}\n\n"
                "Please ensure training data has been uploaded for this test type.",
            )


    def _load_compare_model(self, version: int) -> None:

        """Load a model for comparison."""
        try:
            model_path, scaler_path, metadata_path = self._get_version_paths(version)

            # Fallback to non-versioned paths if versioned don't exist
            test_folder = self._file_path.parent
            if not model_path.exists():
                model_path = test_folder / f"model_{self._file_type}.pkl"
                scaler_path = test_folder / f"scaler_{self._file_type}.pkl"
                metadata_path = test_folder / f"metadata_{self._file_type}.json"

            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found for version {version}")

            # Load model state
            model_state = joblib.load(model_path)
            self._compare_model = self._create_model_from_state(model_state)

            # Load scaler
            if scaler_path and scaler_path.exists():
                self._compare_scaler = joblib.load(scaler_path)
            else:
                raise FileNotFoundError("Scaler file not found")

            # Load metadata
            self._compare_metadata = {}
            if metadata_path and metadata_path.exists():
                self._compare_metadata = json.loads(metadata_path.read_text())

            self._compare_version = version

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Comparison Model Loading Failed",
                f"Could not load comparison model (v{version}):\n\n{exc}",
            )

    def _create_model_from_state(self, state: dict):
        """Recreate model from saved state."""

        class SimpleAutoencoder:
            def __init__(self, state_dict):
                self.W1 = np.array(state_dict["W1"], dtype=np.float32)
                self.b1 = np.array(state_dict["b1"], dtype=np.float32)
                self.W2 = np.array(state_dict["W2"], dtype=np.float32)
                self.b2 = np.array(state_dict["b2"], dtype=np.float32)
                self.input_dim = int(state_dict.get("input_dim", self.W1.shape[0]))
                self.hidden_dim = int(state_dict.get("hidden_dim", self.W1.shape[1]))

            def forward(self, features):
                hidden = features @ self.W1 + self.b1
                hidden = np.maximum(0.0, hidden)  # ReLU
                reconstructed = hidden @ self.W2 + self.b2
                return reconstructed, hidden

            def reconstruction_error(self, data):
                reconstructed, _ = self.forward(data)
                return np.mean((reconstructed - data) ** 2, axis=1)

        return SimpleAutoencoder(state)

    def _on_version_changed(self, index: int) -> None:
        """Handle version selection change."""
        if index < 0:
            return

        version = self.version_combo.currentData()
        if version is not None and version != self._current_version:
            self._load_model(version)
            # Clear previous detection results
            self._reconstruction_errors = None
            self._anomaly_indices = None
            self.figure.clear()
            self.canvas.draw_idle()

    def _on_comparison_toggled(self, state: int) -> None:
        """Handle comparison mode toggle."""
        self._comparison_mode = state == Qt.Checked
        self.compare_version_combo.setEnabled(self._comparison_mode)

        if self._comparison_mode:
            # Load comparison model
            compare_version = self.compare_version_combo.currentData()
            if compare_version is not None:
                self._load_compare_model(compare_version)
        else:
            # Clear comparison data
            self._compare_model = None
            self._compare_scaler = None
            self._compare_reconstruction_errors = None
            self._compare_anomaly_indices = None

    def _on_compare_version_changed(self, index: int) -> None:
        """Handle comparison version selection change."""
        if index < 0 or not self._comparison_mode:
            return

        version = self.compare_version_combo.currentData()
        if version is not None and version != self._compare_version:
            self._load_compare_model(version)
            # Clear previous comparison results
            self._compare_reconstruction_errors = None
            self._compare_anomaly_indices = None

    def _on_threshold_method_changed(self) -> None:
        """Handle threshold method selection change."""
        current_method = self.threshold_method.currentItem()
        if current_method and current_method.text() == "Custom Value":
            self.custom_threshold.setEnabled(True)
        else:
            self.custom_threshold.setEnabled(False)

    def _detect_anomalies(self) -> None:
        """Run anomaly detection using the loaded model."""
        if self._model is None or self._scaler is None:
            QMessageBox.warning(
                self, "Anomaly Detection", "No model is loaded. Cannot detect anomalies."
            )
            return

        if self._dataframe is None:
            QMessageBox.warning(self, "Anomaly Detection", "No data is loaded.")
            return

        try:
            # Prepare data
            df = self._dataframe.copy()
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                raise ValueError("No numeric columns found in data")

            # CRITICAL: Remove empty columns (all NaN) to match training behavior
            # This prevents dimension mismatches when files have empty columns
            numeric_df = numeric_df.dropna(axis=1, how="all")

            # Handle missing values
            numeric_df = numeric_df.fillna(0.0)
            numeric_df = numeric_df.replace([np.inf, -np.inf], 0.0)

            # Check if columns match model input
            if numeric_df.shape[1] != self._model.input_dim:
                raise ValueError(
                    f"Data has {numeric_df.shape[1]} columns but model expects "
                    f"{self._model.input_dim} columns"
                )

            # Scale data for primary model
            scaled_data = self._scaler.transform(numeric_df.values)

            # Calculate reconstruction errors for primary model
            self._reconstruction_errors = self._model.reconstruction_error(scaled_data)

            # Determine threshold
            self._threshold = self._calculate_threshold(self._reconstruction_errors)

            # Find anomalies
            self._anomaly_indices = np.where(self._reconstruction_errors > self._threshold)[0]

            # If comparison mode is enabled, run detection on comparison model
            if self._comparison_mode and self._compare_model is not None and self._compare_scaler is not None:
                try:
                    # Check dimension compatibility
                    if numeric_df.shape[1] != self._compare_model.input_dim:
                        QMessageBox.warning(
                            self,
                            "Comparison Warning",
                            f"Comparison model expects {self._compare_model.input_dim} columns "
                            f"but data has {numeric_df.shape[1]} columns. Skipping comparison.",
                        )
                    else:
                        # Scale data for comparison model
                        compare_scaled_data = self._compare_scaler.transform(numeric_df.values)

                        # Calculate reconstruction errors for comparison model
                        self._compare_reconstruction_errors = self._compare_model.reconstruction_error(
                            compare_scaled_data
                        )

                        # Determine threshold for comparison
                        self._compare_threshold = self._calculate_threshold(
                            self._compare_reconstruction_errors
                        )

                        # Find anomalies for comparison
                        self._compare_anomaly_indices = np.where(
                            self._compare_reconstruction_errors > self._compare_threshold
                        )[0]
                except Exception as compare_exc:
                    QMessageBox.warning(
                        self,
                        "Comparison Warning",
                        f"Comparison model detection failed:\n{compare_exc}",
                    )

            # Update statistics
            self._update_statistics()

            # Plot results
            self._plot_results()

            status_msg = f"✓ Detection complete: {len(self._anomaly_indices)} anomalies found"
            if self._comparison_mode and self._compare_anomaly_indices is not None:
                status_msg += f" (comparison: {len(self._compare_anomaly_indices)})"

            self.status_label.setText(status_msg)
            self.status_label.setStyleSheet(
                "color: #0F172A; font-weight: 500; padding: 8px; "
                "background: #D1FAE5; border-radius: 6px;"
            )

        except Exception as exc:
            QMessageBox.critical(self, "Detection Failed", f"Anomaly detection failed:\n\n{exc}")

    def _calculate_threshold(self, reconstruction_errors: Optional[np.ndarray] = None) -> float:
        """Calculate anomaly threshold based on selected method.

        Args:
            reconstruction_errors: Array of reconstruction errors. If None, uses self._reconstruction_errors.
        """
        errors = reconstruction_errors if reconstruction_errors is not None else self._reconstruction_errors
        if errors is None:
            return 0.0

        method = self.threshold_method.currentItem().text()

        mean_error = np.mean(errors)
        std_error = np.std(errors)

        if method == "Mean + 2×Std":
            return mean_error + 2 * std_error
        elif method == "Mean + 3×Std":
            return mean_error + 3 * std_error
        elif method == "95th Percentile":
            return np.percentile(errors, 95)
        elif method == "99th Percentile":
            return np.percentile(errors, 99)
        elif method == "Custom Value":
            return self.custom_threshold.value()

        return mean_error + 3 * std_error  # Default

    def _update_statistics(self) -> None:
        """Update detection statistics table."""
        if self._reconstruction_errors is None:
            return

        total_points = len(self._reconstruction_errors)
        num_anomalies = len(self._anomaly_indices) if self._anomaly_indices is not None else 0
        anomaly_percent = (num_anomalies / total_points * 100) if total_points > 0 else 0

        mean_error = np.mean(self._reconstruction_errors)
        max_error = np.max(self._reconstruction_errors)
        min_error = np.min(self._reconstruction_errors)

        stats = [
            ("Total Points", str(total_points)),
            ("Anomalies Found", str(num_anomalies)),
            ("Anomaly Rate", f"{anomaly_percent:.2f}%"),
            ("Threshold", f"{self._threshold:.6f}"),
            ("Mean Error", f"{mean_error:.6f}"),
            ("Max Error", f"{max_error:.6f}"),
        ]

        for row, (metric, value) in enumerate(stats):
            self.stats_table.setItem(row, 0, QTableWidgetItem(metric))
            self.stats_table.setItem(row, 1, QTableWidgetItem(value))

            metric_item = self.stats_table.item(row, 0)
            if metric_item:
                metric_item.setForeground(Qt.darkGray)
                font = metric_item.font()
                font.setBold(True)
                metric_item.setFont(font)

        self.stats_table.resizeColumnsToContents()

    def _plot_results(self) -> None:
        """Plot reconstruction errors and anomalies."""
        if self._reconstruction_errors is None:
            return

        self.figure.clear()

        indices = np.arange(len(self._reconstruction_errors))

        # Check if comparison mode with valid comparison data
        show_comparison = (
            self._comparison_mode
            and self._compare_reconstruction_errors is not None
            and len(self._compare_reconstruction_errors) == len(self._reconstruction_errors)
        )

        if show_comparison:
            # Single plot comparison mode - both models on same plots
            ax1 = self.figure.add_subplot(211)
            ax2 = self.figure.add_subplot(212)

            # ====== Top Plot: Reconstruction Error Comparison ======
            # Primary model (blue)
            ax1.plot(
                indices,
                self._reconstruction_errors,
                "b-",
                linewidth=1,
                label=f"v{self._current_version} Error",
                alpha=0.7,
            )
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                ax1.scatter(
                    self._anomaly_indices,
                    self._reconstruction_errors[self._anomaly_indices],
                    c="red",
                    s=30,
                    marker="o",
                    label=f"v{self._current_version} Anomalies ({len(self._anomaly_indices)})",
                    zorder=5,
                )
            ax1.axhline(
                y=self._threshold,
                color="r",
                linestyle="--",
                linewidth=2,
                label=f"v{self._current_version} Threshold = {self._threshold:.4f}",
            )

            # Comparison model (green)
            ax1.plot(
                indices,
                self._compare_reconstruction_errors,
                "g-",
                linewidth=1,
                label=f"v{self._compare_version} Error",
                alpha=0.7,
            )
            if self._compare_anomaly_indices is not None and len(self._compare_anomaly_indices) > 0:
                ax1.scatter(
                    self._compare_anomaly_indices,
                    self._compare_reconstruction_errors[self._compare_anomaly_indices],
                    c="orange",
                    s=30,
                    marker="s",
                    label=f"v{self._compare_version} Anomalies ({len(self._compare_anomaly_indices)})",
                    zorder=5,
                )
            ax1.axhline(
                y=self._compare_threshold,
                color="orange",
                linestyle="--",
                linewidth=2,
                label=f"v{self._compare_version} Threshold = {self._compare_threshold:.4f}",
            )

            ax1.set_xlabel("Data Point Index", fontweight="bold")
            ax1.set_ylabel("Reconstruction Error", fontweight="bold")
            ax1.set_title(f"Model Comparison: v{self._current_version} vs v{self._compare_version} - Reconstruction Error", fontweight="bold", fontsize=11)
            ax1.legend(loc="upper right", fontsize=7, ncol=2)
            ax1.grid(True, alpha=0.3)

            # ====== Bottom Plot: Histogram Comparison ======
            # Primary model histogram (blue/red)
            ax2.hist(
                self._reconstruction_errors,
                bins=50,
                color="skyblue",
                edgecolor="blue",
                alpha=0.5,
                label=f"v{self._current_version} Normal",
            )
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                ax2.hist(
                    self._reconstruction_errors[self._anomaly_indices],
                    bins=50,
                    color="red",
                    edgecolor="darkred",
                    alpha=0.5,
                    label=f"v{self._current_version} Anomalies",
                )
            ax2.axvline(x=self._threshold, color="r", linestyle="--", linewidth=2, label=f"v{self._current_version} Threshold")

            # Comparison model histogram (green/orange)
            ax2.hist(
                self._compare_reconstruction_errors,
                bins=50,
                color="lightgreen",
                edgecolor="green",
                alpha=0.5,
                label=f"v{self._compare_version} Normal",
            )
            if self._compare_anomaly_indices is not None and len(self._compare_anomaly_indices) > 0:
                ax2.hist(
                    self._compare_reconstruction_errors[self._compare_anomaly_indices],
                    bins=50,
                    color="orange",
                    edgecolor="darkorange",
                    alpha=0.5,
                    label=f"v{self._compare_version} Anomalies",
                )
            ax2.axvline(x=self._compare_threshold, color="orange", linestyle="--", linewidth=2, label=f"v{self._compare_version} Threshold")

            ax2.set_xlabel("Reconstruction Error", fontweight="bold")
            ax2.set_ylabel("Frequency", fontweight="bold")
            ax2.set_title(f"Model Comparison: v{self._current_version} vs v{self._compare_version} - Error Distribution", fontweight="bold", fontsize=11)
            ax2.legend(loc="upper right", fontsize=7, ncol=2)
            ax2.grid(True, alpha=0.3, axis="y")

        else:
            # Standard 2-row layout (no comparison)
            ax1 = self.figure.add_subplot(211)
            ax2 = self.figure.add_subplot(212)

            # Plot 1: Reconstruction error over data points
            ax1.plot(
                indices,
                self._reconstruction_errors,
                "b-",
                linewidth=1,
                label="Reconstruction Error",
                alpha=0.7,
            )

            # Highlight anomalies
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                ax1.scatter(
                    self._anomaly_indices,
                    self._reconstruction_errors[self._anomaly_indices],
                    c="red",
                    s=50,
                    marker="o",
                    label="Anomalies",
                    zorder=5,
                )

            # Threshold line
            ax1.axhline(
                y=self._threshold,
                color="r",
                linestyle="--",
                linewidth=2,
                label=f"Threshold = {self._threshold:.4f}",
            )

            ax1.set_xlabel("Data Point Index", fontweight="bold")
            ax1.set_ylabel("Reconstruction Error", fontweight="bold")
            ax1.set_title("Reconstruction Error vs Data Points", fontweight="bold", fontsize=12)
            ax1.legend(loc="upper right")
            ax1.grid(True, alpha=0.3)

            # Plot 2: Histogram of reconstruction errors
            ax2.hist(
                self._reconstruction_errors,
                bins=50,
                color="skyblue",
                edgecolor="black",
                alpha=0.7,
                label="Normal",
            )

            # Highlight anomaly region
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                anomaly_errors = self._reconstruction_errors[self._anomaly_indices]
                ax2.hist(
                    anomaly_errors,
                    bins=50,
                    color="red",
                    edgecolor="darkred",
                    alpha=0.7,
                    label="Anomalies",
                )

            # Threshold line
            ax2.axvline(
                x=self._threshold,
                color="r",
                linestyle="--",
                linewidth=2,
                label=f"Threshold = {self._threshold:.4f}",
            )

            ax2.set_xlabel("Reconstruction Error", fontweight="bold")
            ax2.set_ylabel("Frequency", fontweight="bold")
            ax2.set_title("Distribution of Reconstruction Errors", fontweight="bold", fontsize=12)
            ax2.legend(loc="upper right")
            ax2.grid(True, alpha=0.3, axis="y")

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def _export_anomalies(self) -> None:
        """Export detected anomalies to CSV file."""
        if self._anomaly_indices is None or len(self._anomaly_indices) == 0:
            QMessageBox.warning(self, "Export Anomalies", "No anomalies detected to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Anomalies", f"{self._file_path.stem}_anomalies.csv", "CSV Files (*.csv)"
        )

        if file_path:
            try:
                # Create DataFrame with anomalies
                anomaly_df = self._dataframe.iloc[self._anomaly_indices].copy()
                anomaly_df["reconstruction_error"] = self._reconstruction_errors[
                    self._anomaly_indices
                ]
                anomaly_df["data_point_index"] = self._anomaly_indices

                # Reorder columns to put index and error first
                cols = ["data_point_index", "reconstruction_error"] + [
                    col
                    for col in anomaly_df.columns
                    if col not in ["data_point_index", "reconstruction_error"]
                ]
                anomaly_df = anomaly_df[cols]

                anomaly_df.to_csv(file_path, index=False)
                QMessageBox.information(
                    self,
                    "Export Success",
                    f"Anomalies exported to:\n{file_path}\n\n"
                    f"Total anomalies: {len(self._anomaly_indices)}",
                )
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export anomalies:\n{exc}")

    def _export_plot(self) -> None:
        """Export current plot to image file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Plot",
            f"{self._file_path.stem}_anomaly_plot.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)",
        )

        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches="tight")
                QMessageBox.information(self, "Export Success", f"Plot saved to:\n{file_path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export Failed", f"Failed to export plot:\n{exc}")

    def _decode_and_predict(self) -> None:
        """Decode the data using the model and open prediction plotter."""
        if self._model is None or self._scaler is None:
            QMessageBox.warning(
                self,
                "Decode & Predict",
                "No model is loaded. Cannot decode predictions."
            )
            return

        if self._dataframe is None:
            QMessageBox.warning(
                self,
                "Decode & Predict",
                "No data is loaded."
            )
            return

        try:
            # Prepare data (same as in _detect_anomalies)
            df = self._dataframe.copy()
            numeric_df = df.select_dtypes(include=[np.number])

            if numeric_df.empty:
                raise ValueError("No numeric columns found in data")

            # Remove empty columns (all NaN) to match training behavior
            numeric_df = numeric_df.dropna(axis=1, how="all")

            # Handle missing values
            numeric_df = numeric_df.fillna(0.0)
            numeric_df = numeric_df.replace([np.inf, -np.inf], 0.0)

            # Check if columns match model input
            if numeric_df.shape[1] != self._model.input_dim:
                raise ValueError(
                    f"Data has {numeric_df.shape[1]} columns but model expects "
                    f"{self._model.input_dim} columns"
                )

            # # Scale data
            # scaled_data = self._scaler.transform(numeric_df.values)

            # # Get predictions (reconstructions) from the model
            # reconstructed_data, _ = self._model.forward(scaled_data)

            # # Inverse transform to get predictions in original scale
            # predictions = self._scaler.inverse_transform(reconstructed_data)

            # # Create DataFrames for predictions and actual data
            # predictions_df = pd.DataFrame(
            #     predictions,
            #     columns=numeric_df.columns,
            #     index=numeric_df.index
            # )

            # # Determine file name
            # file_name = self._file_path.name if self._file_path else "New Dataset"

            # # Open the prediction plotter window
            # anomaly_prediction_plotter.run(
            #     actual_data=numeric_df,
            #     predictions=predictions_df,
            #     file_name=file_name
            # )

            # # Update status
            # self.status_label.setText("✓ Prediction plotter opened")
            # self.status_label.setStyleSheet(
            #     "color: #0F172A; font-weight: 500; padding: 8px; "
            #     "background: #D1FAE5; border-radius: 6px;"
            # )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Decode Failed",
                f"Failed to decode predictions:\n\n{exc}"
            )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Handle window close event."""
        try:
            _open_windows.remove(self)
        except ValueError:
            pass
        super().closeEvent(event)


# Global list to track open detector windows
_open_windows: List[AnomalyDetectorWindow] = []




def run(file_path: Path | str, parent: Optional[QWidget] = None) -> None:
    """Launch the anomaly detector window for the provided file path.

    Args:
        file_path: Path to the file to analyze
        parent: Optional parent widget
    """
    path = Path(file_path)
    if not path.exists():
        QMessageBox.warning(None, "Anomaly Detector", f"The file '{path}' could not be found.")
        return

    try:
        window = AnomalyDetectorWindow(path)
    except ValueError as exc:
        QMessageBox.warning(None, "Anomaly Detector", str(exc))
        return
    except Exception as exc:
        QMessageBox.critical(None, "Anomaly Detector", f"Unable to open detector: {exc}")
        return

    window.show()
    window.raise_()
    window.activateWindow()
    _open_windows.append(window)


def run_standalone(parent: Optional[QWidget] = None) -> None:
    """Launch the anomaly detector window in standalone mode without a file.

    This allows users to:
    1. Select pump series and test type from dropdowns
    2. Load a data file (.sc, .asc, or parquet) via File menu
    3. Automatically convert .sc/.asc files to parquet
    4. Analyze the data with trained models for the selected pump/test type

    Args:
        parent: Optional parent widget
    """
    try:
        window = AnomalyDetectorWindow(file_path=None)
    except Exception as exc:
        QMessageBox.critical(None, "Anomaly Detector", f"Unable to open detector: {exc}")
        return

    window.show()
    window.raise_()
    window.activateWindow()
    _open_windows.append(window)


# Enhanced Anomaly Detector Widget Implementation
# Add this to the end of your anomaly_detector.py file, replacing the existing create_anomaly_widget

# Enhanced Anomaly Detector Widget Implementation
# Add this to the end of your anomaly_detector.py file, replacing the existing create_anomaly_widget

def create_anomaly_widget(file_path: Optional[Path] = None) -> Optional[QWidget]:
    """Create an embeddable anomaly detector widget with full functionality.

    This creates a two-panel layout similar to the enhanced plotter:
    - Left panel: Controls and settings
    - Right panel: Plots and visualizations

    Args:
        file_path: Optional path to the data file

    Returns:
        QWidget containing the anomaly detector interface
    """
    try:
        # Create main widget
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #E5E7EB;
            }
            QSplitter::handle:hover {
                background: #DC2626;
            }
        """)

        # ========== LEFT PANEL: Controls ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        # Title
        title = QLabel("Anomaly Detector")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #DC2626;")
        left_layout.addWidget(title)

        # File info
        if file_path:
            file_label = QLabel(f"File: {file_path.name}")
        else:
            file_label = QLabel("No file loaded")
        file_label.setStyleSheet("font-size: 11px; color: #6B7280; padding: 4px;")
        left_layout.addWidget(file_label)

        # Load file button
        load_file_btn = QPushButton("📁 Load Data File")
        load_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #047857;
            }
        """)
        left_layout.addWidget(load_file_btn)

        # Data/Model selection group
        selection_group = QGroupBox("Configuration")
        selection_layout = QVBoxLayout(selection_group)

        # Pump series
        pump_layout = QHBoxLayout()
        pump_layout.addWidget(QLabel("Pump Series:"))
        pump_combo = QComboBox()
        pump_combo.setMinimumWidth(150)
        pump_layout.addWidget(pump_combo)
        selection_layout.addLayout(pump_layout)

        # Test type
        test_layout = QHBoxLayout()
        test_layout.addWidget(QLabel("Test Type:"))
        test_combo = QComboBox()
        test_combo.setMinimumWidth(150)
        test_layout.addWidget(test_combo)
        selection_layout.addLayout(test_layout)

        # Model version
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Model Version:"))
        version_combo = QComboBox()
        version_combo.setMinimumWidth(150)
        version_layout.addWidget(version_combo)
        selection_layout.addLayout(version_layout)

        left_layout.addWidget(selection_group)

        # Detection settings
        settings_group = QGroupBox("Detection Settings")
        settings_layout = QVBoxLayout(settings_group)

        # Threshold method
        settings_layout.addWidget(QLabel("Threshold Method:"))
        threshold_list = QListWidget()
        threshold_list.addItems([
            "Mean + 2×Std",
            "Mean + 3×Std",
            "95th Percentile",
            "99th Percentile"
        ])
        threshold_list.setCurrentRow(1)
        threshold_list.setMaximumHeight(100)
        settings_layout.addWidget(threshold_list)

        # Detect button
        detect_btn = QPushButton("Detect Anomalies")
        detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
        """)
        settings_layout.addWidget(detect_btn)

        left_layout.addWidget(settings_group)

        # Results group
        results_group = QGroupBox("Detection Results")
        results_layout = QVBoxLayout(results_group)

        results_table = QTableWidget()
        results_table.setRowCount(4)
        results_table.setColumnCount(2)
        results_table.setHorizontalHeaderLabels(["Metric", "Value"])
        results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        results_table.verticalHeader().setVisible(False)
        results_table.setMaximumHeight(150)
        results_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Initialize with placeholder data
        metrics = [
            ("Total Points", "-"),
            ("Anomalies Found", "-"),
            ("Anomaly Rate", "-"),
            ("Threshold", "-")
        ]
        for row, (metric, value) in enumerate(metrics):
            results_table.setItem(row, 0, QTableWidgetItem(metric))
            results_table.setItem(row, 1, QTableWidgetItem(value))

        results_layout.addWidget(results_table)
        left_layout.addWidget(results_group)

        # Action buttons
        action_layout = QVBoxLayout()

        export_anomalies_btn = QPushButton("Export Anomalies")
        export_anomalies_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        action_layout.addWidget(export_anomalies_btn)

        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        action_layout.addWidget(export_plot_btn)

        open_full_btn = QPushButton("Open Full Detector")
        open_full_btn.setStyleSheet("""
            QPushButton {
                background-color: #1D4ED8;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E40AF;
            }
        """)
        action_layout.addWidget(open_full_btn)

        left_layout.addLayout(action_layout)
        left_layout.addStretch()

        # ========== RIGHT PANEL: Plot Area ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        # Status label
        status_label = QLabel("Load data and detect anomalies to view results")
        status_label.setStyleSheet("""
            QLabel {
                color: #0F172A;
                font-weight: 500;
                padding: 8px;
                background: #FEF3C7;
                border-radius: 6px;
            }
        """)
        status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(status_label)

        # Matplotlib figure
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

        figure = Figure(figsize=(10, 8), dpi=100)
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, widget)
        toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")

        right_layout.addWidget(toolbar)
        right_layout.addWidget(canvas)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)

        # Set stretch factors (30-70 split)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 7)

        main_layout.addWidget(splitter)

        # Store references to prevent garbage collection
        widget._file_path = file_path
        widget._dataframe = None
        widget._model = None
        widget._scaler = None
        widget._reconstruction_errors = None
        widget._anomaly_indices = None
        widget._threshold = 0.0
        widget._figure = figure
        widget._canvas = canvas
        widget._status_label = status_label
        widget._results_table = results_table
        widget._pump_combo = pump_combo
        widget._test_combo = test_combo
        widget._version_combo = version_combo
        widget._threshold_list = threshold_list
        widget._detect_btn = detect_btn
        widget._export_anomalies_btn = export_anomalies_btn
        widget._export_plot_btn = export_plot_btn
        widget._file_label = file_label

        # Helper functions
        def load_data_file():
            """Open file dialog and load data."""
            from PyQt5.QtWidgets import QFileDialog, QMessageBox

            file_path, _ = QFileDialog.getOpenFileName(
                widget,
                "Load Data File",
                "",
                "All Supported Files (*.sc *.asc *.parquet *.csv *.tdms);;SC Files (*.sc);;ASC Files (*.asc);;Parquet Files (*.parquet);;CSV Files (*.csv);;TDMS Files (*.tdms);;All Files (*.*)"
            )

            if not file_path:
                return

            file_path = Path(file_path)

            # Check if pump series and test type are selected
            if not pump_combo.currentText() or pump_combo.currentText() == "Select":
                QMessageBox.warning(
                    widget,
                    "Selection Required",
                    "Please select Pump Series and Test Type before loading a file."
                )
                return

            try:
                # Convert .sc or .asc files to parquet if needed
                if file_path.suffix.lower() in {'.sc', '.asc'}:
                    status_label.setText("Converting file to Parquet format...")

                    # Get pump series and test type
                    pump_series = pump_combo.currentText()
                    test_type = test_combo.currentText()

                    # Create target directory
                    from industrial_data_system.core.config import get_config
                    config = get_config()
                    newdatasets_dir = config.files_base_path / pump_series / "tests" / "newdatasets"
                    newdatasets_dir.mkdir(parents=True, exist_ok=True)

                    # Convert to parquet
                    parquet_filename = file_path.stem + ".parquet"
                    target_parquet_path = newdatasets_dir / parquet_filename

                    from industrial_data_system.utils.asc_utils import convert_asc_to_parquet
                    parquet_path = convert_asc_to_parquet(file_path, parquet_path=target_parquet_path,
                                                          preserve_asc=True)

                    if parquet_path is None:
                        QMessageBox.critical(
                            widget,
                            "Conversion Failed",
                            "The file could not be converted to Parquet format."
                        )
                        return
                    file_path = parquet_path

                # Load the data
                df = AnomalyDetectorWindow._read_file(file_path)
                widget._dataframe = df
                widget._file_path = file_path

                # Update file label
                file_label.setText(f"File: {file_path.name}")

                # Update status
                status_label.setText(f"✓ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
                status_label.setStyleSheet("""
                    QLabel {
                        color: #0F172A;
                        font-weight: 500;
                        padding: 8px;
                        background: #D1FAE5;
                        border-radius: 6px;
                    }
                """)

                # Try to load model if pump/test selected
                if pump_combo.currentText() and test_combo.currentText():
                    load_model()

            except Exception as e:
                QMessageBox.critical(
                    widget,
                    "Load Failed",
                    f"Failed to load file:\n{e}"
                )
                status_label.setText(f"⚠ Error: {e}")

        def load_model():
            """Load the model for current selection."""
            try:
                pump_series = pump_combo.currentText()
                test_type = test_combo.currentText()
                version = version_combo.currentData()

                if not pump_series or not test_type or version is None:
                    return

                # Load model using database
                database = DatabaseManager()
                file_type = "parquet" if widget._file_path and widget._file_path.suffix == ".parquet" else "csv"

                versions = database.get_all_model_versions(pump_series, test_type, file_type)
                if not versions:
                    status_label.setText("⚠ No models available for this selection")
                    return

                # Get model paths
                record = next((r for r in versions if r.version == version), None)
                if not record:
                    return

                import joblib

                # Load model
                model_state = joblib.load(record.model_path)
                widget._model = create_model_from_state(model_state)

                # Load scaler
                if record.scaler_path:
                    widget._scaler = joblib.load(record.scaler_path)

                status_label.setText(f"✓ Model loaded: v{version}")
                status_label.setStyleSheet("""
                    QLabel {
                        color: #0F172A;
                        font-weight: 500;
                        padding: 8px;
                        background: #D1FAE5;
                        border-radius: 6px;
                    }
                """)

            except Exception as e:
                status_label.setText(f"⚠ Model load failed: {e}")

        def create_model_from_state(state: dict):
            """Recreate model from saved state."""

            class SimpleAutoencoder:
                def __init__(self, state_dict):
                    import numpy as np
                    self.W1 = np.array(state_dict["W1"], dtype=np.float32)
                    self.b1 = np.array(state_dict["b1"], dtype=np.float32)
                    self.W2 = np.array(state_dict["W2"], dtype=np.float32)
                    self.b2 = np.array(state_dict["b2"], dtype=np.float32)
                    self.input_dim = int(state_dict.get("input_dim", self.W1.shape[0]))
                    self.hidden_dim = int(state_dict.get("hidden_dim", self.W1.shape[1]))

                def forward(self, features):
                    import numpy as np
                    hidden = features @ self.W1 + self.b1
                    hidden = np.maximum(0.0, hidden)
                    reconstructed = hidden @ self.W2 + self.b2
                    return reconstructed, hidden

                def reconstruction_error(self, data):
                    import numpy as np
                    reconstructed, _ = self.forward(data)
                    return np.mean((reconstructed - data) ** 2, axis=1)

            return SimpleAutoencoder(state)

        def detect_anomalies():
            """Run anomaly detection."""
            if widget._model is None or widget._scaler is None:
                QMessageBox.warning(widget, "Detection", "No model loaded")
                return

            if widget._dataframe is None:
                QMessageBox.warning(widget, "Detection", "No data loaded")
                return

            try:
                import numpy as np

                # Prepare data
                df = widget._dataframe.copy()
                numeric_df = df.select_dtypes(include=[np.number])
                numeric_df = numeric_df.dropna(axis=1, how="all")
                numeric_df = numeric_df.fillna(0.0)
                numeric_df = numeric_df.replace([np.inf, -np.inf], 0.0)

                # Scale and detect
                scaled_data = widget._scaler.transform(numeric_df.values)
                widget._reconstruction_errors = widget._model.reconstruction_error(scaled_data)

                # Calculate threshold
                method = threshold_list.currentItem().text()
                mean_error = np.mean(widget._reconstruction_errors)
                std_error = np.std(widget._reconstruction_errors)

                if method == "Mean + 2×Std":
                    widget._threshold = mean_error + 2 * std_error
                elif method == "Mean + 3×Std":
                    widget._threshold = mean_error + 3 * std_error
                elif method == "95th Percentile":
                    widget._threshold = np.percentile(widget._reconstruction_errors, 95)
                else:
                    widget._threshold = np.percentile(widget._reconstruction_errors, 99)

                # Find anomalies
                widget._anomaly_indices = np.where(widget._reconstruction_errors > widget._threshold)[0]

                # Update results table
                total = len(widget._reconstruction_errors)
                anomalies = len(widget._anomaly_indices)
                rate = (anomalies / total * 100) if total > 0 else 0

                results_table.setItem(0, 1, QTableWidgetItem(f"{total:,}"))
                results_table.setItem(1, 1, QTableWidgetItem(f"{anomalies:,}"))
                results_table.setItem(2, 1, QTableWidgetItem(f"{rate:.2f}%"))
                results_table.setItem(3, 1, QTableWidgetItem(f"{widget._threshold:.6f}"))

                # Plot results
                plot_results()

                status_label.setText(f"✓ Detection complete: {anomalies} anomalies found")
                status_label.setStyleSheet("""
                    QLabel {
                        color: #0F172A;
                        font-weight: 500;
                        padding: 8px;
                        background: #D1FAE5;
                        border-radius: 6px;
                    }
                """)

            except Exception as e:
                QMessageBox.critical(widget, "Detection Failed", f"Error: {e}")
                import traceback
                traceback.print_exc()

        def plot_results():
            """Plot anomaly detection results."""
            if widget._reconstruction_errors is None:
                return

            import numpy as np

            figure.clear()

            indices = np.arange(len(widget._reconstruction_errors))

            # Top plot: Reconstruction error
            ax1 = figure.add_subplot(211)
            ax1.plot(indices, widget._reconstruction_errors, 'b-', linewidth=1, alpha=0.7, label='Error')

            if widget._anomaly_indices is not None and len(widget._anomaly_indices) > 0:
                ax1.scatter(
                    widget._anomaly_indices,
                    widget._reconstruction_errors[widget._anomaly_indices],
                    c='red', s=50, marker='o', label='Anomalies', zorder=5
                )

            ax1.axhline(y=widget._threshold, color='r', linestyle='--', linewidth=2,
                        label=f'Threshold = {widget._threshold:.4f}')
            ax1.set_xlabel('Data Point Index', fontweight='bold')
            ax1.set_ylabel('Reconstruction Error', fontweight='bold')
            ax1.set_title('Anomaly Detection Results', fontweight='bold')
            ax1.legend(loc='upper right')
            ax1.grid(True, alpha=0.3)

            # Bottom plot: Histogram
            ax2 = figure.add_subplot(212)
            ax2.hist(widget._reconstruction_errors, bins=50, color='skyblue',
                     edgecolor='black', alpha=0.7, label='Normal')

            if widget._anomaly_indices is not None and len(widget._anomaly_indices) > 0:
                ax2.hist(widget._reconstruction_errors[widget._anomaly_indices], bins=50,
                         color='red', edgecolor='darkred', alpha=0.7, label='Anomalies')

            ax2.axvline(x=widget._threshold, color='r', linestyle='--', linewidth=2,
                        label=f'Threshold = {widget._threshold:.4f}')
            ax2.set_xlabel('Reconstruction Error', fontweight='bold')
            ax2.set_ylabel('Frequency', fontweight='bold')
            ax2.set_title('Error Distribution', fontweight='bold')
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3, axis='y')

            figure.tight_layout()
            canvas.draw()

        def export_anomalies():
            """Export anomalies to CSV."""
            if widget._anomaly_indices is None or len(widget._anomaly_indices) == 0:
                QMessageBox.warning(widget, "Export", "No anomalies to export")
                return

            from PyQt5.QtWidgets import QFileDialog
            import pandas as pd

            file_path, _ = QFileDialog.getSaveFileName(
                widget, "Export Anomalies", "anomalies.csv", "CSV Files (*.csv)"
            )

            if file_path:
                try:
                    anomaly_df = widget._dataframe.iloc[widget._anomaly_indices].copy()
                    anomaly_df['reconstruction_error'] = widget._reconstruction_errors[widget._anomaly_indices]
                    anomaly_df.to_csv(file_path, index=False)
                    QMessageBox.information(widget, "Success", f"Exported {len(widget._anomaly_indices)} anomalies")
                except Exception as e:
                    QMessageBox.critical(widget, "Export Failed", str(e))

        def export_plot():
            """Export plot to file."""
            from PyQt5.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                widget, "Export Plot", "anomaly_plot.png", "PNG (*.png);;PDF (*.pdf)"
            )

            if file_path:
                try:
                    figure.savefig(file_path, dpi=300, bbox_inches='tight')
                    QMessageBox.information(widget, "Success", f"Plot saved to:\n{file_path}")
                except Exception as e:
                    QMessageBox.critical(widget, "Export Failed", str(e))

        # Populate pump series on initialization
        def populate_pump_series():
            """Load pump series from database."""
            try:
                database = DatabaseManager()
                records = database.list_pump_series()
                pump_combo.clear()
                pump_combo.addItem("Select Pump Series", None)
                for record in records:
                    pump_combo.addItem(record.name, record.name)
            except:
                pass

        def on_pump_changed():
            """Handle pump series selection."""
            pump = pump_combo.currentData()
            if pump:
                try:
                    database = DatabaseManager()
                    records = database.list_test_types(pump_series=pump)
                    test_combo.clear()
                    test_combo.addItem("Select Test Type", None)
                    for record in records:
                        test_combo.addItem(record.name, record.name)
                except:
                    pass

        def on_test_changed():
            """Handle test type selection."""
            pump = pump_combo.currentData()
            test = test_combo.currentData()
            if pump and test:
                try:
                    database = DatabaseManager()
                    file_type = "parquet"
                    versions = database.get_all_model_versions(pump, test, file_type)
                    version_combo.clear()
                    for record in versions:
                        text = f"v{record.version} ({record.trained_at[:10]})"
                        version_combo.addItem(text, record.version)
                except:
                    pass

        # Connect signals
        load_file_btn.clicked.connect(load_data_file)
        detect_btn.clicked.connect(detect_anomalies)
        export_anomalies_btn.clicked.connect(export_anomalies)
        export_plot_btn.clicked.connect(export_plot)
        pump_combo.currentIndexChanged.connect(on_pump_changed)
        test_combo.currentIndexChanged.connect(on_test_changed)
        version_combo.currentIndexChanged.connect(load_model)

        # Populate pump series
        populate_pump_series()

        # Load data if file path provided
        if file_path and file_path.exists():
            try:
                # Load data
                df = AnomalyDetectorWindow._read_file(file_path)
                widget._dataframe = df

                # Try to extract pump/test info from path
                try:
                    file_parts = file_path.parts
                    if "tests" in file_parts:
                        tests_index = file_parts.index("tests")
                        test_type = file_parts[tests_index + 1]
                        pump_series = file_parts[tests_index - 1] if tests_index > 0 else "General"

                        # Set selections
                        pump_idx = pump_combo.findData(pump_series)
                        if pump_idx >= 0:
                            pump_combo.setCurrentIndex(pump_idx)
                            on_pump_changed()

                            test_idx = test_combo.findData(test_type)
                            if test_idx >= 0:
                                test_combo.setCurrentIndex(test_idx)
                                on_test_changed()

                        status_label.setText(f"✓ Data loaded: {df.shape[0]} rows, {df.shape[1]} columns")
                        status_label.setStyleSheet("""
                            QLabel {
                                color: #0F172A;
                                font-weight: 500;
                                padding: 8px;
                                background: #D1FAE5;
                                border-radius: 6px;
                            }
                        """)

                        # Try to load model
                        if version_combo.count() > 0:
                            load_model()

                except:
                    pass

            except Exception as e:
                status_label.setText(f"⚠ Error loading data: {e}")

        # Connect button to open full detector
        def open_full_detector():
            if widget._file_path:
                run(widget._file_path)
            else:
                run_standalone()

        open_full_btn.clicked.connect(open_full_detector)

        # Apply global styling
        widget.setStyleSheet("""
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
            QTableWidget {
                background: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
            QComboBox {
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 4px 8px;
                background: #F9FAFB;
            }
        """)

        return widget

    except Exception as e:
        print(f"Error creating anomaly detector widget: {e}")
        import traceback
        traceback.print_exc()

        # Return error widget
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_label = QLabel(f"Error loading anomaly detector:\n{str(e)}")
        error_label.setWordWrap(True)
        error_label.setStyleSheet("color: red; padding: 20px;")
        error_layout.addWidget(error_label)
        return error_widget
