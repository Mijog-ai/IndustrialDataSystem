"""Styling helpers for the standalone plotter window."""

from __future__ import annotations

from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import QWidget


class PlotterTheme:
    """Centralised colour palette and widget styling for the plotter UI."""

    WINDOW = "#0B1120"
    SURFACE = "#111827"
    PANEL = "#1E293B"
    BORDER = "#1F2937"
    BORDER_LIGHT = "#27303F"
    TEXT = "#E2E8F0"
    TEXT_MUTED = "#94A3B8"
    ACCENT = "#38BDF8"
    CHART_BG = "#101828"

    @classmethod
    def apply(cls, widget: QWidget) -> None:
        """Apply palette and stylesheet to the provided widget tree."""

        palette = widget.palette() if widget.palette() is not None else QPalette()
        palette.setColor(QPalette.Window, QColor(cls.WINDOW))
        palette.setColor(QPalette.WindowText, QColor(cls.TEXT))
        palette.setColor(QPalette.Base, QColor(cls.PANEL))
        palette.setColor(QPalette.AlternateBase, QColor(cls.SURFACE))
        palette.setColor(QPalette.Text, QColor(cls.TEXT))
        palette.setColor(QPalette.Button, QColor(cls.PANEL))
        palette.setColor(QPalette.ButtonText, QColor(cls.TEXT))
        palette.setColor(QPalette.Highlight, QColor(cls.ACCENT))
        palette.setColor(QPalette.HighlightedText, QColor(cls.WINDOW))
        widget.setPalette(palette)
        widget.setFont(QFont("Segoe UI", 10))
        widget.setStyleSheet(cls.stylesheet())

    @classmethod
    def stylesheet(cls) -> str:
        return f"""
            QMainWindow#plotter-window {{
                background-color: {cls.WINDOW};
            }}

            QWidget#plotter-surface {{
                background-color: {cls.SURFACE};
                border-radius: 12px;
            }}

            QWidget#plotter-panel {{
                background-color: {cls.PANEL};
                border-radius: 10px;
            }}

            QGroupBox {{
                background-color: {cls.PANEL};
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                margin-top: 16px;
                padding: 12px 16px 16px 16px;
                color: {cls.TEXT};
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                top: 10px;
                padding: 0px 4px;
            }}

            QLabel {{
                color: {cls.TEXT};
            }}

            QLabel[secondary="true"] {{
                color: {cls.TEXT_MUTED};
            }}

            QComboBox, QLineEdit {{
                background-color: {cls.SURFACE};
                border: 1px solid {cls.BORDER_LIGHT};
                border-radius: 6px;
                padding: 6px 8px;
                color: {cls.TEXT};
            }}

            QComboBox::drop-down {{
                border: 0px;
            }}

            QPushButton {{
                background-color: {cls.ACCENT};
                border-radius: 6px;
                padding: 6px 14px;
                color: {cls.WINDOW};
                font-weight: 600;
            }}

            QPushButton:disabled {{
                background-color: {cls.BORDER};
                color: {cls.TEXT_MUTED};
            }}

            QPushButton[secondary="true"] {{
                background-color: transparent;
                border: 1px solid {cls.BORDER_LIGHT};
                color: {cls.TEXT};
            }}

            QListWidget, QTableWidget {{
                background-color: {cls.SURFACE};
                alternate-background-color: {cls.PANEL};
                border: 1px solid {cls.BORDER_LIGHT};
                border-radius: 6px;
                color: {cls.TEXT};
                gridline-color: {cls.BORDER_LIGHT};
            }}

            QHeaderView::section {{
                background-color: {cls.PANEL};
                border: none;
                border-bottom: 1px solid {cls.BORDER_LIGHT};
                color: {cls.TEXT_MUTED};
                padding: 6px;
                font-weight: 600;
            }}

            QSplitter::handle {{
                background-color: {cls.BORDER_LIGHT};
                width: 1px;
            }}

            QTabBar::tab {{
                background: transparent;
                padding: 8px 18px;
                color: {cls.TEXT_MUTED};
            }}

            QTabBar::tab:selected {{
                color: {cls.TEXT};
                border-bottom: 2px solid {cls.ACCENT};
            }}

            QTabWidget::pane {{
                border: none;
            }}

            QToolBar {{
                background-color: transparent;
                border: none;
                spacing: 8px;
            }}

            QLabel#toolbar-file-label {{
                color: {cls.TEXT_MUTED};
                padding-left: 12px;
            }}
        """

