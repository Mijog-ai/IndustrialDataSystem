from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QSplitter, QTabWidget, QVBoxLayout, QWidget

from plotter_gui_component.components.Plot_area import PlotArea
from plotter_gui_component.components.data_preview import DataPreview
from plotter_gui_component.components.statistics_area import StatisticsArea


class RightPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)
        self.setup_ui()

    def setup_ui(self):
        self.plot_area = PlotArea(self)
        self.statistics_area = StatisticsArea(self)
        self.data_preview = DataPreview(self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.data_preview, "Data Preview")
        self.tabs.addTab(self.statistics_area, "Statistics")
        self.tabs.setObjectName("plotter-tabs")

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.plot_area)
        splitter.addWidget(self.tabs)
        splitter.setSizes([720, 240])

        self.layout.addWidget(splitter)

    def update_preview(self, df):
        self.data_preview.show_dataframe(df)

    def clear_preview(self):
        self.data_preview.clear()
