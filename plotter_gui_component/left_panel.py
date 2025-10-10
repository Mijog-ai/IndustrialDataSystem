# left_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
from gui.components.axis_selection import AxisSelection
from gui.components.smoothing_options import SmoothingOptions
from gui.components.limit_lines import LimitLines
from gui.components.data_filter import DataFilter
from gui.components.curve_fitting import CurveFitting
from gui.components.comment_box import CommentBox
import logging
from PyQt5.QtCore import pyqtSignal, QObject

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



