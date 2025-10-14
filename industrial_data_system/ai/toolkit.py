"""Convenience accessors for AI tooling used across applications."""

from industrial_data_system.ai.analysis.data_study import run as run_ai_data_study
from industrial_data_system.ai.training.simulator import run as run_training_simulation
from industrial_data_system.ai.visualization.plotter import run as run_plotter

__all__ = ["run_ai_data_study", "run_plotter", "run_training_simulation"]
