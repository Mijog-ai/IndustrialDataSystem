# left_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout

from plotter_gui_component.components.axis_selection import AxisSelection
from plotter_gui_component.components.smoothing_options import SmoothingOptions
from plotter_gui_component.components.limit_lines import LimitLines
from plotter_gui_component.components.data_filter import DataFilter
from plotter_gui_component.components.curve_fitting import CurveFitting
from plotter_gui_component.components.comment_box import CommentBox
from PyQt5.QtCore import pyqtSignal

class LeftPanel(QWidget):
    title_changed = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.axis_selection = AxisSelection(self)
        # self.sampling_options = SamplingOptions(self)
        self.smoothing_options = SmoothingOptions(self)
        self.limit_lines = LimitLines(self)
        self.data_filter = DataFilter(self)
        self.curve_fitting = CurveFitting(self)
        self.comment_box = CommentBox(self)

        self.layout.addWidget(self.axis_selection)
        # self.layout.addWidget(self.sampling_options)
        self.layout.addWidget(self.data_filter)
        self.layout.addWidget(self.smoothing_options)
        self.layout.addWidget(self.limit_lines)
        self.layout.addWidget(self.curve_fitting)
        self.layout.addWidget(self.comment_box)
        self.layout.addStretch(1)



        # Initialize components as hidden
        self.smoothing_options.hide()
        self.limit_lines.hide()
        self.comment_box.hide()
        self.data_filter.hide()
        self.curve_fitting.hide()
        # Connect sampling options to main window
        # self.sampling_options.enable_sampling.stateChanged.connect(self.parent().update_sampling)
        # self.sampling_options.sampling_rate.valueChanged.connect(self.parent().update_sampling)

    def update_options(self, columns):
        self.axis_selection.update_options(columns)
        self.data_filter.update_columns(columns)

    def _plot_area(self):
        parent = self.parent()
        if parent and hasattr(parent, "right_panel"):
            return getattr(parent.right_panel, "plot_area", None)
        return None

    def get_plot_title(self):
        plot_area = self._plot_area()
        if plot_area is not None:
            return getattr(plot_area, "current_title", "")
        return ""

    def set_plot_title(self, title):
        plot_area = self._plot_area()
        if plot_area is not None:
            plot_area.title_input.setText(title)
            plot_area.current_title = title
            plot_area.update_plot()



