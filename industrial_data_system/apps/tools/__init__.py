"""Utility entry points for reader tool buttons."""

__all__ = [
    "run_plotter_tool",
    "run_analyzer_tool",
    "run_ai_data_study_tool",
    "run_train_tool",
]


def __getattr__(name: str):
    if name == "run_plotter_tool":
        from .plotter import run as run_plotter_tool

        return run_plotter_tool
    if name == "run_analyzer_tool":
        from .analyzer import run as run_analyzer_tool

        return run_analyzer_tool
    if name == "run_ai_data_study_tool":
        from .ai_data_study import run as run_ai_data_study_tool

        return run_ai_data_study_tool
    if name == "run_train_tool":
        from .train import run as run_train_tool

        return run_train_tool
    raise AttributeError(f"module 'industrial_data_system.apps.tools' has no attribute '{name}'")
