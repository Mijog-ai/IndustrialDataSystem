"""Convenience accessors for AI tooling used across applications."""

from industrial_data_system.ai.analysis.data_study import run as run_ai_data_study
from industrial_data_system.ai.anomaly_detection.anomaly_detector import run as run_anomaly_detector
from industrial_data_system.ai.anomaly_detection.anomaly_detector import run_standalone as run_anomaly_detector_standalone
from industrial_data_system.ai.training.simulator import run as run_training_simulation
from industrial_data_system.ai.visualization.plotter import run as run_plotter

__all__ = ["run_ai_data_study", "run_plotter", "run_training_simulation", "run_anomaly_detector", "run_anomaly_detector_standalone"]
