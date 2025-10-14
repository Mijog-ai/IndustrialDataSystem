"""High-level application entry points for Industrial Data System user interfaces."""

from industrial_data_system.apps.desktop.reader import ReaderApp
from industrial_data_system.apps.desktop.uploader import IndustrialDataApp, IndustrialTheme

__all__ = ["ReaderApp", "IndustrialDataApp", "IndustrialTheme"]
