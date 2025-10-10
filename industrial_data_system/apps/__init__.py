"""GUI applications for the Industrial Data System."""

__all__ = ["IndustrialDataApp", "IndustrialTheme", "ReaderApp"]


def __getattr__(name: str):
    if name == "ReaderApp":
        from .reader import ReaderApp  # noqa: F401

        return ReaderApp
    if name in {"IndustrialDataApp", "IndustrialTheme"}:
        from .upload import IndustrialDataApp, IndustrialTheme  # noqa: F401

        return {"IndustrialDataApp": IndustrialDataApp, "IndustrialTheme": IndustrialTheme}[name]
    raise AttributeError(f"module 'industrial_data_system.apps' has no attribute '{name}'")
