"""Convenience accessors for AI tooling used across applications."""

from industrial_data_system.Integrations.analysis.data_study import run as run_ai_data_study
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import run as run_anomaly_detector
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import run_standalone as run_anomaly_detector_standalone
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import create_anomaly_widget
from industrial_data_system.Integrations.training.simulator import run as run_training_simulation
from industrial_data_system.Integrations.visualization.plotter import run as run_plotter
from industrial_data_system.Integrations.visualization.plotter import create_plotter_widget
from industrial_data_system.Integrations.Test_APP.TestApp import run_test_app

__all__ = [
    "run_ai_data_study",
    "run_plotter",
    "run_training_simulation",
    "run_anomaly_detector",
    "run_anomaly_detector_standalone",
    "create_plotter_widget",
    "create_anomaly_widget",
    "run_test_app"
]