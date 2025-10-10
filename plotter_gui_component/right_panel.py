from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter
from gui.components.Plot_area import PlotArea
from gui.components.statistics_area import StatisticsArea
from PyQt5.QtCore import Qt
class RightPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.plot_area = PlotArea(self)
        self.statistics_area = StatisticsArea(self)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.plot_area)
        splitter.addWidget(self.statistics_area)
        splitter.setSizes([700, 200])

        self.layout.addWidget(splitter)