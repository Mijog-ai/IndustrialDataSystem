"""Enhanced plotter with scrollable report generation and interactive toolbar."""

from __future__ import annotations

import datetime
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QTextCursor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from industrial_data_system.utils.asc_utils import (
    load_and_process_asc_file,
    load_and_process_csv_file,
    load_and_process_tdms_file,
)

__all__ = ["run", "create_plotter_widget"]


# ============================================================================
# REPORT SECTION CLASSES
# ============================================================================

class ReportSection(QWidget):
    """Base class for all report sections with collapsible header."""

    section_removed = pyqtSignal(object)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_collapsed = False
        self._build_ui()

    def _build_ui(self):
        """Build the section UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        # Header
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)

        # Collapse button
        self.collapse_btn = QPushButton("▼")
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(self.collapse_btn)

        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #1F2937;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Remove button
        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(24, 24)
        remove_btn.clicked.connect(lambda: self.section_removed.emit(self))
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #DC2626;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FEE2E2;
                border-radius: 4px;
            }
        """)
        header_layout.addWidget(remove_btn)

        layout.addWidget(header_widget)

        # Content container
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.content_widget)

    def _toggle_collapse(self):
        """Toggle section collapse state."""
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        self.collapse_btn.setText("▶" if self.is_collapsed else "▼")

    def get_content_layout(self):
        """Get the layout where content should be added."""
        return self.content_layout


class ReportHeader(ReportSection):
    """Report header with title and metadata."""

    def __init__(self, file_name: str, parent=None):
        super().__init__("Report Header", parent)
        self.file_name = file_name
        self._build_content()

    def _build_content(self):
        """Build header content."""
        layout = self.get_content_layout()

        # Title
        self.title_edit = QLineEdit("Data Analysis Report")
        self.title_edit.setStyleSheet("""
            QLineEdit {
                font-size: 20px;
                font-weight: bold;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                padding: 8px;
                background: white;
            }
        """)
        layout.addWidget(self.title_edit)

        # Metadata
        meta_widget = QWidget()
        meta_layout = QFormLayout(meta_widget)

        self.file_label = QLabel(self.file_name)
        self.date_label = QLabel(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.author_edit = QLineEdit("Analyst")

        meta_layout.addRow("File:", self.file_label)
        meta_layout.addRow("Generated:", self.date_label)
        meta_layout.addRow("Author:", self.author_edit)

        layout.addWidget(meta_widget)

    def get_data(self) -> Dict[str, str]:
        """Get header data."""
        return {
            "title": self.title_edit.text(),
            "file": self.file_label.text(),
            "date": self.date_label.text(),
            "author": self.author_edit.text()
        }


class ReportText(ReportSection):
    """Free-form text section."""

    def __init__(self, title: str, initial_text: str = "", parent=None):
        super().__init__(title, parent)
        self._build_content(initial_text)

    def _build_content(self, initial_text: str):
        """Build text editor."""
        layout = self.get_content_layout()

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setMinimumHeight(150)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                padding: 8px;
                background: white;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.text_edit)

    def get_text(self) -> str:
        """Get the text content."""
        return self.text_edit.toPlainText()


class ReportPlot(ReportSection):
    """Plot section with matplotlib figure."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._build_content()

    def _build_content(self):
        """Build plot area."""
        layout = self.get_content_layout()

        # Plot figure
        self.figure = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(400)
        layout.addWidget(self.canvas)

        # Caption
        caption_label = QLabel("Caption:")
        caption_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        layout.addWidget(caption_label)

        self.caption_edit = QTextEdit()
        self.caption_edit.setPlainText("Add plot description here...")
        self.caption_edit.setMaximumHeight(80)
        self.caption_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                padding: 6px;
                background: white;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.caption_edit)

    def get_caption(self) -> str:
        """Get the caption text."""
        return self.caption_edit.toPlainText()

    def get_figure(self) -> Figure:
        """Get the matplotlib figure."""
        return self.figure


class ReportStatistics(ReportSection):
    """Statistics table section."""

    def __init__(self, parent=None):
        super().__init__("Statistical Analysis", parent)
        self._build_content()

    def _build_content(self):
        """Build statistics table."""
        layout = self.get_content_layout()

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Column", "Max", "Mean", "Min", "Std"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.stats_table)

    def update_stats(self, df: pd.DataFrame):
        """Update statistics table with data."""
        if df is not None and not df.empty:
            stats = df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{row['max']:.4g}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{row['mean']:.4g}"))
                self.stats_table.setItem(i, 3, QTableWidgetItem(f"{row['min']:.4g}"))
                self.stats_table.setItem(i, 4, QTableWidgetItem(f"{row['std']:.4g}"))


class ReportDataOverview(ReportSection):
    """Data overview section with metadata."""

    def __init__(self, df: pd.DataFrame, file_path: Path, parent=None):
        super().__init__("Data Overview", parent)
        self._build_content(df, file_path)

    def _build_content(self, df: pd.DataFrame, file_path: Path):
        """Build overview table."""
        layout = self.get_content_layout()

        overview_table = QTableWidget()
        overview_table.setColumnCount(2)
        overview_table.setHorizontalHeaderLabels(["Property", "Value"])
        overview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        overview_table.verticalHeader().setVisible(False)
        overview_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Calculate properties
        props = [
            ("File Name", file_path.name),
            ("Dimensions", f"{df.shape[0]:,} × {df.shape[1]}"),
            ("Columns", ", ".join(df.columns[:5].tolist()) + ("..." if len(df.columns) > 5 else "")),
            ("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024**2:.2f} MB"),
        ]

        overview_table.setRowCount(len(props))
        for i, (prop, value) in enumerate(props):
            prop_item = QTableWidgetItem(prop)
            prop_item.setFont(QFont("", -1, QFont.Bold))
            prop_item.setForeground(QColor("#6B7280"))
            overview_table.setItem(i, 0, prop_item)
            overview_table.setItem(i, 1, QTableWidgetItem(str(value)))

        overview_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
            }
        """)

        layout.addWidget(overview_table)


# ============================================================================
# SCROLLABLE REPORT CONTAINER
# ============================================================================

class ScrollableReport(QScrollArea):
    """Scrollable container for all report sections."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sections: List[ReportSection] = []
        self._build_ui()

    def _build_ui(self):
        """Build scrollable area."""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFrameShape(QScrollArea.NoFrame)

        # Container widget
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(16, 16, 16, 16)
        self.container_layout.setSpacing(16)

        # Add section button at bottom
        self.add_section_btn = QPushButton("➕ Add Section")
        self.add_section_btn.setStyleSheet("""
            QPushButton {
                background: #DBEAFE;
                color: #1E40AF;
                padding: 12px;
                border: 2px dashed #3B82F6;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #BFDBFE;
            }
        """)
        self.add_section_btn.clicked.connect(self._show_add_section_menu)

        self.container_layout.addStretch()
        self.container_layout.addWidget(self.add_section_btn)

        self.setWidget(self.container)

        # Styling
        self.setStyleSheet("""
            QScrollArea {
                background: white;
                border: none;
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
        """)

    def add_section(self, section: ReportSection):
        """Add a new section to the report."""
        section.section_removed.connect(self.remove_section)
        self.sections.append(section)
        # Insert before stretch and add button
        self.container_layout.insertWidget(len(self.sections) - 1, section)

    def remove_section(self, section: ReportSection):
        """Remove a section from the report."""
        if section in self.sections:
            self.sections.remove(section)
            self.container_layout.removeWidget(section)
            section.deleteLater()

    def _show_add_section_menu(self):
        """Show menu to add different section types."""
        # For now, just add a text section
        text_section = ReportText("Notes", "Add your notes here...")
        self.add_section(text_section)

    def export_to_pdf(self, filepath: str):
        """Export report as PDF."""
        temp_files = []  # Track temp files to clean up later

        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors

            # Create document
            doc = SimpleDocTemplate(
                filepath,
                pagesize=landscape(A4),
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.5*inch,
                bottomMargin=0.5*inch
            )

            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1F2937'),
                spaceAfter=12
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#374151'),
                spaceAfter=6
            )

            # Process each section
            for section in self.sections:
                if isinstance(section, ReportHeader):
                    data = section.get_data()
                    story.append(Paragraph(data['title'], title_style))
                    story.append(Spacer(1, 0.2*inch))

                    meta_text = f"<b>File:</b> {data['file']}<br/>" \
                                f"<b>Generated:</b> {data['date']}<br/>" \
                                f"<b>Author:</b> {data['author']}"
                    story.append(Paragraph(meta_text, styles['Normal']))
                    story.append(Spacer(1, 0.3*inch))

                elif isinstance(section, ReportText):
                    story.append(Paragraph(section.title, heading_style))
                    text = section.get_text().replace('\n', '<br/>')
                    story.append(Paragraph(text, styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))

                elif isinstance(section, ReportPlot):
                    story.append(Paragraph(section.title, heading_style))

                    # Save figure to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                        temp_path = tmp.name

                    # Save the figure
                    section.get_figure().savefig(temp_path, format='png', dpi=150, bbox_inches='tight')

                    # Track for cleanup
                    temp_files.append(temp_path)

                    # Add image to PDF (file must exist until doc.build() completes)
                    img = Image(temp_path, width=9*inch, height=5*inch)
                    story.append(img)

                    # Add caption
                    caption = section.get_caption()
                    if caption:
                        story.append(Spacer(1, 0.1*inch))
                        caption_style = ParagraphStyle(
                            'Caption',
                            parent=styles['Normal'],
                            fontSize=9,
                            textColor=colors.HexColor('#6B7280'),
                            italic=True
                        )
                        story.append(Paragraph(f"<i>{caption}</i>", caption_style))

                    story.append(Spacer(1, 0.2*inch))

                elif isinstance(section, ReportStatistics):
                    story.append(Paragraph(section.title, heading_style))

                    # Convert QTableWidget to reportlab Table
                    table = section.stats_table
                    data = []

                    # Headers
                    headers = []
                    for col in range(table.columnCount()):
                        headers.append(table.horizontalHeaderItem(col).text())
                    data.append(headers)

                    # Rows
                    for row in range(table.rowCount()):
                        row_data = []
                        for col in range(table.columnCount()):
                            item = table.item(row, col)
                            row_data.append(item.text() if item else "")
                        data.append(row_data)

                    # Create table
                    t = Table(data)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
                    ]))

                    story.append(t)
                    story.append(Spacer(1, 0.2*inch))

            # Build PDF (this is when ReportLab actually reads the image files)
            doc.build(story)

            return True

        except Exception as e:
            print(f"Error exporting to PDF: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Clean up all temporary files AFTER PDF is built
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except Exception as e:
                    print(f"Warning: Could not delete temp file {temp_file}: {e}")


# Continue in next part...


# ============================================================================
# TOOLBAR TOOLS
# ============================================================================

class BaseTool:
    """Base class for all interactive tools."""

    def __init__(self, canvas: FigureCanvas):
        self.canvas = canvas
        self.figure = canvas.figure
        self.active = False
        self.connection_ids = []

    def activate(self):
        """Activate the tool and connect events."""
        self.active = True
        self.connect_events()

    def deactivate(self):
        """Deactivate the tool and disconnect events."""
        self.active = False
        self.disconnect_events()

    def connect_events(self):
        """Connect matplotlib events."""
        pass

    def disconnect_events(self):
        """Disconnect matplotlib events."""
        for cid in self.connection_ids:
            self.canvas.mpl_disconnect(cid)
        self.connection_ids = []

    def on_press(self, event):
        """Handle mouse press."""
        pass

    def on_motion(self, event):
        """Handle mouse motion."""
        pass

    def on_release(self, event):
        """Handle mouse release."""
        pass


class SelectionTool(BaseTool):
    """Tool for selecting regions of data."""

    def __init__(self, canvas: FigureCanvas, callback=None):
        super().__init__(canvas)
        self.start_point = None
        self.selection_rect = None
        self.callback = callback

    def connect_events(self):
        """Connect mouse events."""
        self.connection_ids.append(
            self.canvas.mpl_connect('button_press_event', self.on_press)
        )
        self.connection_ids.append(
            self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        )
        self.connection_ids.append(
            self.canvas.mpl_connect('button_release_event', self.on_release)
        )

    def on_press(self, event):
        """Start selection."""
        if event.inaxes and event.button == 1:
            self.start_point = (event.xdata, event.ydata)

    def on_motion(self, event):
        """Update selection rectangle."""
        if self.start_point and event.inaxes and event.button == 1:
            x0, y0 = self.start_point
            x1, y1 = event.xdata, event.ydata

            # Remove old rectangle
            if self.selection_rect:
                self.selection_rect.remove()

            # Draw new rectangle
            width = x1 - x0
            height = y1 - y0
            self.selection_rect = Rectangle(
                (x0, y0), width, height,
                fill=True, alpha=0.2, color='blue',
                linestyle='--', linewidth=2, edgecolor='blue'
            )
            event.inaxes.add_patch(self.selection_rect)
            self.canvas.draw_idle()

    def on_release(self, event):
        """Complete selection."""
        if self.start_point and event.inaxes and event.button == 1:
            x0, y0 = self.start_point
            x1, y1 = event.xdata, event.ydata

            # Get selection bounds
            x_min, x_max = min(x0, x1), max(x0, x1)
            y_min, y_max = min(y0, y1), max(y0, y1)

            # Call callback with selection
            if self.callback:
                self.callback(x_min, x_max, y_min, y_max)

            # Clear
            if self.selection_rect:
                self.selection_rect.remove()
                self.selection_rect = None
            self.start_point = None
            self.canvas.draw_idle()


class AnnotationTool(BaseTool):
    """Tool for adding annotations to plots."""

    def __init__(self, canvas: FigureCanvas, text: str = "Note"):
        super().__init__(canvas)
        self.text = text

    def connect_events(self):
        """Connect click event."""
        self.connection_ids.append(
            self.canvas.mpl_connect('button_press_event', self.on_press)
        )

    def on_press(self, event):
        """Add annotation at click point."""
        if event.inaxes and event.button == 1:
            event.inaxes.annotate(
                self.text,
                xy=(event.xdata, event.ydata),
                xytext=(10, 10), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='red')
            )
            self.canvas.draw_idle()


class MeasurementTool(BaseTool):
    """Tool for measuring distances and slopes."""

    def __init__(self, canvas: FigureCanvas):
        super().__init__(canvas)
        self.point1 = None
        self.line = None
        self.annotation = None

    def connect_events(self):
        """Connect mouse events."""
        self.connection_ids.append(
            self.canvas.mpl_connect('button_press_event', self.on_press)
        )

    def on_press(self, event):
        """Measure between two clicks."""
        if event.inaxes and event.button == 1:
            if self.point1 is None:
                # First point
                self.point1 = (event.xdata, event.ydata)
                event.inaxes.plot(event.xdata, event.ydata, 'ro', markersize=8)
                self.canvas.draw_idle()
            else:
                # Second point - calculate distance
                point2 = (event.xdata, event.ydata)
                x1, y1 = self.point1
                x2, y2 = point2

                # Calculate distance
                distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                # Calculate slope
                if x2 != x1:
                    slope = (y2 - y1) / (x2 - x1)
                    slope_text = f"Slope: {slope:.3f}"
                else:
                    slope_text = "Slope: ∞"

                # Draw line
                event.inaxes.plot([x1, x2], [y1, y2], 'r-', linewidth=2)

                # Add annotation
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                event.inaxes.annotate(
                    f"Distance: {distance:.3f}\n{slope_text}",
                    xy=(mid_x, mid_y),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='lightblue', alpha=0.8),
                    fontsize=9
                )

                self.canvas.draw_idle()
                self.point1 = None


# ============================================================================
# COLLAPSIBLE PANEL WIDGET
# ============================================================================

class CollapsiblePanel(QWidget):
    """Collapsible panel for organizing controls."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_collapsed = False
        self._build_ui()

    def _build_ui(self):
        """Build panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        # Header button
        self.header_btn = QPushButton(f"▼ {self.title}")
        self.header_btn.setCheckable(True)
        self.header_btn.setChecked(True)
        self.header_btn.clicked.connect(self._toggle_collapse)
        self.header_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 4px;
                padding: 8px;
                text-align: left;
                font-weight: 600;
                color: #1F2937;
            }
            QPushButton:hover {
                background: #E5E7EB;
            }
            QPushButton:checked {
                background: #DBEAFE;
                border-color: #3B82F6;
                color: #1E40AF;
            }
        """)
        layout.addWidget(self.header_btn)

        # Content widget
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.content_widget)

    def _toggle_collapse(self):
        """Toggle panel collapse."""
        self.is_collapsed = not self.is_collapsed
        self.content_widget.setVisible(not self.is_collapsed)
        arrow = "▶" if self.is_collapsed else "▼"
        self.header_btn.setText(f"{arrow} {self.title}")

    def get_content_layout(self):
        """Get the content layout."""
        return self.content_layout


# ============================================================================
# DATA FILTER PIPELINE
# ============================================================================

class DataFilterPipeline:
    """Pipeline for applying filters to data."""

    def __init__(self, dataframe: pd.DataFrame):
        self.original_data = dataframe.copy()
        self.filtered_data = dataframe.copy()
        self.filters = []

    def add_time_range_filter(self, start_time, end_time, time_column='Time'):
        """Filter by time range."""
        if time_column in self.filtered_data.columns:
            self.filtered_data = self.filtered_data[
                (self.filtered_data[time_column] >= start_time) &
                (self.filtered_data[time_column] <= end_time)
            ]

    def add_value_range_filter(self, column: str, min_val: float, max_val: float):
        """Filter by value range."""
        if column in self.filtered_data.columns:
            self.filtered_data = self.filtered_data[
                (self.filtered_data[column] >= min_val) &
                (self.filtered_data[column] <= max_val)
            ]

    def remove_outliers(self, columns: List[str], n_sigma: float = 3.0):
        """Remove outliers beyond n standard deviations."""
        for column in columns:
            if column in self.filtered_data.columns:
                mean = self.filtered_data[column].mean()
                std = self.filtered_data[column].std()
                self.filtered_data = self.filtered_data[
                    (self.filtered_data[column] >= mean - n_sigma * std) &
                    (self.filtered_data[column] <= mean + n_sigma * std)
                ]

    def remove_nan(self, columns: List[str]):
        """Remove rows with NaN values."""
        self.filtered_data = self.filtered_data.dropna(subset=columns)

    def apply_moving_average(self, column: str, window: int = 10) -> pd.Series:
        """Apply moving average to column."""
        if column in self.filtered_data.columns:
            return self.filtered_data[column].rolling(window=window).mean()
        return None

    def reset(self):
        """Reset to original data."""
        self.filtered_data = self.original_data.copy()
        self.filters = []

    def get_filtered_data(self) -> pd.DataFrame:
        """Get the filtered dataframe."""
        return self.filtered_data


# Continue in next part...


# ============================================================================
# MAIN ENHANCED PLOTTER WINDOW
# ============================================================================

class EnhancedPlotterWindow(QMainWindow):
    """Enhanced plotter with report generation and interactive tools."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self._file_path = file_path
        self._dataframe: pd.DataFrame | None = None
        self._filter_pipeline: DataFilterPipeline | None = None
        self._current_tool: BaseTool | None = None
        self._main_plot_section: ReportPlot | None = None

        self.setWindowTitle(f"Enhanced Plotter - {self._file_path.name}")
        self.resize(1600, 1000)

        self._load_data()
        self._build_ui()
        self._create_initial_report()

    def _load_data(self) -> None:
        """Load data from file."""
        df = self._read_file(self._file_path)
        if df.empty:
            raise ValueError("The selected file did not contain any data to display.")
        self._dataframe = df
        self._filter_pipeline = DataFilterPipeline(df)

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

    def _build_ui(self) -> None:
        """Build main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(8)

        # LEFT PANEL: Scrollable Report
        self.report_area = ScrollableReport(self)
        self.report_area.setMinimumWidth(600)

        # RIGHT PANEL: Controls
        right_panel = self._create_right_panel()
        right_panel.setMaximumWidth(640)

        # Add to splitter
        self.main_splitter.addWidget(self.report_area)
        self.main_splitter.addWidget(right_panel)

        # Set stretch factors (60-40 split)
        self.main_splitter.setStretchFactor(0, 6)
        self.main_splitter.setStretchFactor(1, 4)

        main_layout.addWidget(self.main_splitter)

        # Apply global styling
        self.setStyleSheet("""
            QMainWindow {
                background: #F9FAFB;
            }
        """)

    def _create_right_panel(self) -> QWidget:
        """Create the right control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Scrollable controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(8)

        # Add control panels
        controls_layout.addWidget(self._create_data_selection_panel())
        controls_layout.addWidget(self._create_filter_panel())
        controls_layout.addWidget(self._create_style_panel())
        controls_layout.addWidget(self._create_analysis_panel())
        controls_layout.addStretch()

        scroll.setWidget(controls_widget)
        layout.addWidget(scroll)

        return panel

    def _create_toolbar(self) -> QToolBar:
        """Create the interactive toolbar."""
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setStyleSheet("""
            QToolBar {
                background: white;
                border-bottom: 2px solid #E5E7EB;
                padding: 8px;
                spacing: 8px;
            }
            QToolButton {
                background: transparent;
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 8px;
            }
            QToolButton:hover {
                background: #F3F4F6;
                border-color: #E5E7EB;
            }
            QToolButton:checked {
                background: #DBEAFE;
                border-color: #3B82F6;
            }
        """)

        # Selection tool
        select_action = QAction("🖱️ Select", self)
        select_action.setCheckable(True)
        select_action.triggered.connect(lambda: self._set_tool('select'))
        toolbar.addAction(select_action)

        # Annotation tool
        annotate_action = QAction("✏️ Annotate", self)
        annotate_action.setCheckable(True)
        annotate_action.triggered.connect(lambda: self._set_tool('annotate'))
        toolbar.addAction(annotate_action)

        # Measurement tool
        measure_action = QAction("📏 Measure", self)
        measure_action.setCheckable(True)
        measure_action.triggered.connect(lambda: self._set_tool('measure'))
        toolbar.addAction(measure_action)

        toolbar.addSeparator()

        # Export report
        export_action = QAction("📄 Export PDF", self)
        export_action.triggered.connect(self._export_report_pdf)
        toolbar.addAction(export_action)

        self.toolbar = toolbar
        return toolbar

    def _set_tool(self, tool_name: str):
        """Set the active tool."""
        # Deactivate current tool
        if self._current_tool:
            self._current_tool.deactivate()

        # Activate new tool
        if self._main_plot_section:
            canvas = self._main_plot_section.canvas

            if tool_name == 'select':
                self._current_tool = SelectionTool(canvas, self._on_selection)
            elif tool_name == 'annotate':
                text, ok = QInputDialog.getText(self, "Annotation", "Enter annotation text:")
                if ok and text:
                    self._current_tool = AnnotationTool(canvas, text)
            elif tool_name == 'measure':
                self._current_tool = MeasurementTool(canvas)

            if self._current_tool:
                self._current_tool.activate()

    def _on_selection(self, x_min, x_max, y_min, y_max):
        """Handle data selection."""
        msg = f"Selected region:\nX: [{x_min:.2f}, {x_max:.2f}]\nY: [{y_min:.2f}, {y_max:.2f}]"
        QMessageBox.information(self, "Selection", msg)

    def _create_data_selection_panel(self) -> CollapsiblePanel:
        """Create data selection panel."""
        panel = CollapsiblePanel("Data Selection")
        layout = panel.get_content_layout()

        # X-Axis selector
        layout.addWidget(QLabel("X-Axis:"))
        self.x_selector = QComboBox()
        self.x_selector.addItems(self._dataframe.columns.tolist())
        self.x_selector.currentTextChanged.connect(self._update_main_plot)
        layout.addWidget(self.x_selector)

        # Y-Axes selector
        layout.addWidget(QLabel("Y-Axes (Multi-select):"))
        self.y_selector = QListWidget()
        self.y_selector.setSelectionMode(QAbstractItemView.MultiSelection)
        numeric_cols = self._dataframe.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            self.y_selector.addItem(col)
        self.y_selector.itemSelectionChanged.connect(self._update_main_plot)
        layout.addWidget(self.y_selector)

        # Select first 2 by default
        for i in range(min(2, self.y_selector.count())):
            self.y_selector.item(i).setSelected(True)

        # Update button
        update_btn = QPushButton("Update Plot")
        update_btn.setStyleSheet("""
            QPushButton {
                background: #1D4ED8;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #1E40AF;
            }
        """)
        update_btn.clicked.connect(self._update_main_plot)
        layout.addWidget(update_btn)

        return panel

    def _create_filter_panel(self) -> CollapsiblePanel:
        """Create data filter panel."""
        panel = CollapsiblePanel("Data Filters")
        panel._toggle_collapse()  # Start collapsed
        layout = panel.get_content_layout()

        # Outlier removal
        self.outlier_check = QCheckBox("Remove Outliers (3σ)")
        layout.addWidget(self.outlier_check)

        # NaN removal
        self.nan_check = QCheckBox("Remove NaN Values")
        self.nan_check.setChecked(True)
        layout.addWidget(self.nan_check)

        # Apply filters button
        apply_btn = QPushButton("Apply Filters")
        apply_btn.clicked.connect(self._apply_filters)
        layout.addWidget(apply_btn)

        # Reset button
        reset_btn = QPushButton("Reset Filters")
        reset_btn.clicked.connect(self._reset_filters)
        layout.addWidget(reset_btn)

        return panel

    def _create_style_panel(self) -> CollapsiblePanel:
        """Create plot styling panel."""
        panel = CollapsiblePanel("Plot Styling")
        panel._toggle_collapse()  # Start collapsed
        layout = panel.get_content_layout()

        # Grid toggle
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self._update_main_plot)
        layout.addWidget(self.grid_check)

        # Legend toggle
        self.legend_check = QCheckBox("Show Legend")
        self.legend_check.setChecked(True)
        self.legend_check.stateChanged.connect(self._update_main_plot)
        layout.addWidget(self.legend_check)

        # Line width
        layout.addWidget(QLabel("Line Width:"))
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setMinimum(1)
        self.line_width_slider.setMaximum(5)
        self.line_width_slider.setValue(2)
        self.line_width_slider.valueChanged.connect(self._update_main_plot)
        layout.addWidget(self.line_width_slider)

        return panel

    def _create_analysis_panel(self) -> CollapsiblePanel:
        """Create analysis tools panel."""
        panel = CollapsiblePanel("Analysis Tools")
        panel._toggle_collapse()  # Start collapsed
        layout = panel.get_content_layout()

        # Moving average
        ma_group = QGroupBox("Moving Average")
        ma_layout = QVBoxLayout(ma_group)

        self.ma_check = QCheckBox("Apply Moving Average")
        ma_layout.addWidget(self.ma_check)

        ma_window_layout = QHBoxLayout()
        ma_window_layout.addWidget(QLabel("Window:"))
        self.ma_window = QSpinBox()
        self.ma_window.setMinimum(2)
        self.ma_window.setMaximum(100)
        self.ma_window.setValue(10)
        ma_window_layout.addWidget(self.ma_window)
        ma_layout.addLayout(ma_window_layout)

        layout.addWidget(ma_group)

        # Add statistics section
        stats_btn = QPushButton("Add Statistics to Report")
        stats_btn.clicked.connect(self._add_statistics_section)
        layout.addWidget(stats_btn)

        return panel

    def _apply_filters(self):
        """Apply selected filters to data."""
        self._filter_pipeline.reset()

        y_columns = [item.text() for item in self.y_selector.selectedItems()]

        if self.outlier_check.isChecked():
            self._filter_pipeline.remove_outliers(y_columns, n_sigma=3.0)

        if self.nan_check.isChecked():
            self._filter_pipeline.remove_nan(y_columns)

        self._update_main_plot()

        # Show info
        orig_rows = len(self._dataframe)
        filt_rows = len(self._filter_pipeline.get_filtered_data())
        QMessageBox.information(
            self,
            "Filters Applied",
            f"Original rows: {orig_rows:,}\nFiltered rows: {filt_rows:,}\nRemoved: {orig_rows - filt_rows:,}"
        )

    def _reset_filters(self):
        """Reset all filters."""
        self._filter_pipeline.reset()
        self.outlier_check.setChecked(False)
        self.nan_check.setChecked(True)
        self._update_main_plot()

    def _create_initial_report(self):
        """Create initial report sections."""
        # Header
        header = ReportHeader(self._file_path.name, self)
        self.report_area.add_section(header)

        # Executive summary
        summary = ReportText("Executive Summary", "Key findings and observations...", self)
        self.report_area.add_section(summary)

        # Data overview
        overview = ReportDataOverview(self._dataframe, self._file_path, self)
        self.report_area.add_section(overview)

        # Main plot
        self._main_plot_section = ReportPlot("Main Plot", self)
        self.report_area.add_section(self._main_plot_section)

        # Initial plot
        self._update_main_plot()

    def _update_main_plot(self):
        """Update the main plot."""
        if not self._main_plot_section:
            return

        x_column = self.x_selector.currentText()
        y_items = self.y_selector.selectedItems()

        if not y_items:
            return

        y_columns = [item.text() for item in y_items]

        try:
            self._plot_data(
                self._main_plot_section.get_figure(),
                x_column,
                y_columns
            )
            self._main_plot_section.canvas.draw()
        except Exception as e:
            print(f"Error updating plot: {e}")

    def _plot_data(self, figure: Figure, x_column: str, y_columns: List[str]):
        """Plot data on a figure."""
        df = self._filter_pipeline.get_filtered_data()

        figure.clear()
        ax = figure.add_subplot(111)

        try:
            x_data = pd.to_numeric(df[x_column], errors='coerce')
        except:
            x_data = df.index

        # Color palette
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        line_width = self.line_width_slider.value() if hasattr(self, 'line_width_slider') else 2

        for i, column in enumerate(y_columns):
            color = colors[i % len(colors)]
            y_data = pd.to_numeric(df[column], errors='coerce')

            valid = x_data.notna() & y_data.notna()

            if valid.any():
                # Apply moving average if enabled
                if hasattr(self, 'ma_check') and self.ma_check.isChecked():
                    window = self.ma_window.value()
                    y_plot = y_data[valid].rolling(window=window).mean()
                    ax.plot(x_data[valid], y_plot, color=color, label=f"{column} (MA{window})", linewidth=line_width, alpha=0.9)
                else:
                    ax.plot(x_data[valid], y_data[valid], color=color, label=column, linewidth=line_width, alpha=0.9)

        ax.set_xlabel(x_column, fontsize=11, fontweight='bold')
        ax.set_ylabel("Value", fontsize=11, fontweight='bold')

        if hasattr(self, 'grid_check') and self.grid_check.isChecked():
            ax.grid(True, alpha=0.3, linestyle='--')

        if hasattr(self, 'legend_check') and self.legend_check.isChecked():
            ax.legend(loc='best', fontsize=9)

        figure.tight_layout()

    def _add_statistics_section(self):
        """Add statistics section to report."""
        y_items = self.y_selector.selectedItems()
        if not y_items:
            return

        y_columns = [item.text() for item in y_items]
        df = self._filter_pipeline.get_filtered_data()

        stats_section = ReportStatistics(self)
        stats_section.update_stats(df[y_columns])
        self.report_area.add_section(stats_section)

    def _export_report_pdf(self):
        """Export report as PDF."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report as PDF",
            f"{self._file_path.stem}_report.pdf",
            "PDF Files (*.pdf)"
        )

        if filepath:
            success = self.report_area.export_to_pdf(filepath)
            if success:
                QMessageBox.information(self, "Export Success", f"Report exported to:\n{filepath}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export report. Check console for errors.")


# ============================================================================
# PUBLIC API FUNCTIONS
# ============================================================================

_open_windows: List[EnhancedPlotterWindow] = []


def run(file_path: Path | str) -> None:
    """Launch the enhanced plotter window.

    Args:
        file_path: Path to the file to plot
    """
    path = Path(file_path)
    if not path.exists():
        QMessageBox.warning(None, "Plotter", f"The file '{path}' could not be found.")
        return

    try:
        window = EnhancedPlotterWindow(path)
        window.show()
        window.raise_()
        window.activateWindow()
        _open_windows.append(window)
    except ValueError as exc:
        QMessageBox.warning(None, "Plotter", str(exc))
    except Exception as exc:
        QMessageBox.critical(None, "Plotter", f"Unable to open plotter: {exc}")
        import traceback
        traceback.print_exc()


def create_plotter_widget(file_path: Path) -> Optional[QWidget]:
    """Create embeddable plotter widget (legacy support).

    Args:
        file_path: Path to the file to plot

    Returns:
        QWidget containing basic plotter, or None if creation fails
    """
    # This function maintains backward compatibility
    # For new code, use run() to launch the full enhanced plotter
    try:
        window = EnhancedPlotterWindow(file_path)
        return window.centralWidget()
    except Exception as e:
        print(f"Error creating plotter widget: {e}")
        return None