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
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.core.db_manager import DatabaseManager, ModelRegistryRecord
from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run"]


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

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self._file_path = file_path
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
        self.setWindowTitle(f"Anomaly Detection - {self._file_path.name}")
        self.resize(1600, 900)

        self._build_ui()
        self._load_data()
        self._extract_path_info()
        self._load_available_versions()
        self._load_model()

    def _build_ui(self) -> None:
        """Build the main user interface."""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ========== LEFT PANEL: Controls ==========
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Header
        header = QLabel("Anomaly Detector")
        header.setStyleSheet("font-size: 20px; font-weight: 600; color: #DC2626;")
        left_layout.addWidget(header)

        # Model info group
        model_group = QGroupBox("Model Information")
        model_layout = QVBoxLayout(model_group)

        # Version selection
        version_layout = QHBoxLayout()
        version_layout.addWidget(QLabel("Model Version:"))
        self.version_combo = QComboBox()
        self.version_combo.setMinimumWidth(150)
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        version_layout.addWidget(self.version_combo)
        version_layout.addStretch()
        model_layout.addLayout(version_layout)

        left_layout.addWidget(model_group)

        # Comparison mode group
        compare_group = QGroupBox("Model Comparison")
        compare_layout = QVBoxLayout(compare_group)

        self.compare_checkbox = QCheckBox("Enable Comparison Mode")
        self.compare_checkbox.stateChanged.connect(self._on_comparison_toggled)
        compare_layout.addWidget(self.compare_checkbox)

        compare_version_layout = QHBoxLayout()
        compare_version_layout.addWidget(QLabel("Compare with:"))
        self.compare_version_combo = QComboBox()
        self.compare_version_combo.setMinimumWidth(150)
        self.compare_version_combo.setEnabled(False)
        self.compare_version_combo.currentIndexChanged.connect(self._on_compare_version_changed)
        compare_version_layout.addWidget(self.compare_version_combo)
        compare_version_layout.addStretch()
        compare_layout.addLayout(compare_version_layout)

        left_layout.addWidget(compare_group)

        # Detection settings group
        settings_group = QGroupBox("Detection Settings")
        settings_layout = QGridLayout(settings_group)

        settings_layout.addWidget(QLabel("Threshold Method:"), 0, 0)
        self.threshold_method = QListWidget()
        self.threshold_method.addItems(
            ["Mean + 2×Std", "Mean + 3×Std", "95th Percentile", "99th Percentile", "Custom Value"]
        )
        self.threshold_method.setCurrentRow(1)  # Default: Mean + 3×Std
        self.threshold_method.setMaximumHeight(120)
        self.threshold_method.currentRowChanged.connect(self._on_threshold_method_changed)
        settings_layout.addWidget(self.threshold_method, 1, 0, 1, 2)

        settings_layout.addWidget(QLabel("Custom Threshold:"), 2, 0)
        self.custom_threshold = QDoubleSpinBox()
        self.custom_threshold.setDecimals(6)
        self.custom_threshold.setRange(0.0, 1000.0)
        self.custom_threshold.setValue(0.1)
        self.custom_threshold.setEnabled(False)
        settings_layout.addWidget(self.custom_threshold, 2, 1)

        detect_btn = QPushButton("Detect Anomalies")
        detect_btn.setProperty("primary", True)
        detect_btn.clicked.connect(self._detect_anomalies)
        settings_layout.addWidget(detect_btn, 3, 0, 1, 2)

        left_layout.addWidget(settings_group)

        # Statistics group
        stats_group = QGroupBox("Detection Results")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(6)
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setMaximumHeight(220)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        stats_layout.addWidget(self.stats_table)

        left_layout.addWidget(stats_group)

        # Export buttons
        export_anomalies_btn = QPushButton("Export Anomalies")
        export_anomalies_btn.setProperty("secondary", True)
        export_anomalies_btn.clicked.connect(self._export_anomalies)
        left_layout.addWidget(export_anomalies_btn)

        export_plot_btn = QPushButton("Export Plot")
        export_plot_btn.setProperty("secondary", True)
        export_plot_btn.clicked.connect(self._export_plot)
        left_layout.addWidget(export_plot_btn)

        close_btn = QPushButton("Close")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(self.close)
        left_layout.addWidget(close_btn)

        left_layout.addStretch()

        # ========== RIGHT PANEL: Plots ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Status label
        self.status_label = QLabel("Loading model...")
        self.status_label.setStyleSheet(
            "color: #0F172A; font-weight: 500; padding: 8px; "
            "background: #FEF3C7; border-radius: 6px;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.status_label)

        # Matplotlib figure
        self.figure = Figure(figsize=(12, 10), dpi=100)
        self.figure.patch.set_facecolor("#FFFFFF")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setStyleSheet("background: #F9FAFB; border: none; padding: 4px;")

        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas)

        # Add panels to main layout
        main_layout.addWidget(left_panel, stretch=1)
        main_layout.addWidget(right_panel, stretch=3)

        # Apply styles
        self.setStyleSheet(
            """
            QMainWindow#anomaly-detector-window {
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
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #DC2626;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
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
            """
            + self.BUTTON_STYLES
        )

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
        if ext == ".asc":
            return load_and_process_asc_file(str(path))
        if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
            return pd.read_excel(path)

        raise ValueError(f"Unsupported file type: {ext}")

    def _extract_path_info(self) -> None:
        """Extract pump series, test type, and file type from file path."""
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
        test_folder = self._file_path.parent

        # Find the record for this version
        record = next(
            (r for r in self._available_versions if r.version == version), None
        )

        if record:
            # Use paths from database record
            model_path = Path(record.model_path)
            scaler_path = Path(record.scaler_path) if record.scaler_path else None
            metadata_path = Path(record.metadata_path) if record.metadata_path else None
        else:
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

    def _load_model(self, version: Optional[int] = None) -> None:
        """Load the trained model for this file's test type.

        Args:
            version: Specific version to load. If None, loads the latest version.
        """
        try:
            test_folder = self._file_path.parent

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

            # Fallback to non-versioned paths if versioned don't exist
            if not model_path.exists():
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
            # 2x2 grid for comparison mode
            ax1 = self.figure.add_subplot(221)
            ax2 = self.figure.add_subplot(222)
            ax3 = self.figure.add_subplot(223)
            ax4 = self.figure.add_subplot(224)

            # ====== Primary Model (Left Column) ======
            # Top-left: Reconstruction error over data points
            ax1.plot(
                indices,
                self._reconstruction_errors,
                "b-",
                linewidth=1,
                label="Reconstruction Error",
                alpha=0.7,
            )
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                ax1.scatter(
                    self._anomaly_indices,
                    self._reconstruction_errors[self._anomaly_indices],
                    c="red",
                    s=30,
                    marker="o",
                    label=f"Anomalies ({len(self._anomaly_indices)})",
                    zorder=5,
                )
            ax1.axhline(
                y=self._threshold,
                color="r",
                linestyle="--",
                linewidth=2,
                label=f"Threshold = {self._threshold:.4f}",
            )
            ax1.set_xlabel("Data Point Index", fontweight="bold")
            ax1.set_ylabel("Reconstruction Error", fontweight="bold")
            ax1.set_title(f"Model v{self._current_version} - Error vs Data Points", fontweight="bold", fontsize=10)
            ax1.legend(loc="upper right", fontsize=8)
            ax1.grid(True, alpha=0.3)

            # Bottom-left: Histogram
            ax3.hist(
                self._reconstruction_errors,
                bins=50,
                color="skyblue",
                edgecolor="black",
                alpha=0.7,
                label="Normal",
            )
            if self._anomaly_indices is not None and len(self._anomaly_indices) > 0:
                ax3.hist(
                    self._reconstruction_errors[self._anomaly_indices],
                    bins=50,
                    color="red",
                    edgecolor="darkred",
                    alpha=0.7,
                    label="Anomalies",
                )
            ax3.axvline(x=self._threshold, color="r", linestyle="--", linewidth=2)
            ax3.set_xlabel("Reconstruction Error", fontweight="bold")
            ax3.set_ylabel("Frequency", fontweight="bold")
            ax3.set_title(f"Model v{self._current_version} - Distribution", fontweight="bold", fontsize=10)
            ax3.legend(loc="upper right", fontsize=8)
            ax3.grid(True, alpha=0.3, axis="y")

            # ====== Comparison Model (Right Column) ======
            # Top-right: Reconstruction error over data points
            ax2.plot(
                indices,
                self._compare_reconstruction_errors,
                "g-",
                linewidth=1,
                label="Reconstruction Error",
                alpha=0.7,
            )
            if self._compare_anomaly_indices is not None and len(self._compare_anomaly_indices) > 0:
                ax2.scatter(
                    self._compare_anomaly_indices,
                    self._compare_reconstruction_errors[self._compare_anomaly_indices],
                    c="orange",
                    s=30,
                    marker="o",
                    label=f"Anomalies ({len(self._compare_anomaly_indices)})",
                    zorder=5,
                )
            ax2.axhline(
                y=self._compare_threshold,
                color="orange",
                linestyle="--",
                linewidth=2,
                label=f"Threshold = {self._compare_threshold:.4f}",
            )
            ax2.set_xlabel("Data Point Index", fontweight="bold")
            ax2.set_ylabel("Reconstruction Error", fontweight="bold")
            ax2.set_title(f"Model v{self._compare_version} - Error vs Data Points", fontweight="bold", fontsize=10)
            ax2.legend(loc="upper right", fontsize=8)
            ax2.grid(True, alpha=0.3)

            # Bottom-right: Histogram
            ax4.hist(
                self._compare_reconstruction_errors,
                bins=50,
                color="lightgreen",
                edgecolor="black",
                alpha=0.7,
                label="Normal",
            )
            if self._compare_anomaly_indices is not None and len(self._compare_anomaly_indices) > 0:
                ax4.hist(
                    self._compare_reconstruction_errors[self._compare_anomaly_indices],
                    bins=50,
                    color="orange",
                    edgecolor="darkorange",
                    alpha=0.7,
                    label="Anomalies",
                )
            ax4.axvline(x=self._compare_threshold, color="orange", linestyle="--", linewidth=2)
            ax4.set_xlabel("Reconstruction Error", fontweight="bold")
            ax4.set_ylabel("Frequency", fontweight="bold")
            ax4.set_title(f"Model v{self._compare_version} - Distribution", fontweight="bold", fontsize=10)
            ax4.legend(loc="upper right", fontsize=8)
            ax4.grid(True, alpha=0.3, axis="y")

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
