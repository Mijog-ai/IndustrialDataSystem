from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem

class StatisticsArea(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setup_ui()

    def setup_ui(self):
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels(["Statistic", "Max", "Mean", "Min", "Std"])
        self.layout.addWidget(self.stats_table)

    def update_stats(self, df):
        if df is not None:
            stats = df.describe().transpose()
            self.stats_table.setRowCount(len(stats))
            for i, (index, row) in enumerate(stats.iterrows()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(str(index)))
                self.stats_table.setItem(i, 1, QTableWidgetItem(str(row['max'])))
                self.stats_table.setItem(i, 2, QTableWidgetItem(str(row['mean'])))
                self.stats_table.setItem(i, 3, QTableWidgetItem(str(row['min'])))
                self.stats_table.setItem(i, 4, QTableWidgetItem(str(row['std'])))
            self.stats_table.resizeColumnsToContents()

    def get_stats(self):
        stats = {}
        for i in range(self.stats_table.rowCount()):
            statistic = self.stats_table.item(i, 0).text()
            stats[statistic] = {
                'mean': self.stats_table.item(i, 1).text(),
                'max': self.stats_table.item(i, 2).text(),
                'min': self.stats_table.item(i, 3).text(),
                'std': self.stats_table.item(i, 4).text()
            }
        return stats

    def set_stats(self, stats):
        self.stats_table.setRowCount(len(stats))
        for i, (statistic, values) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, QTableWidgetItem(str(statistic)))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(values['mean'])))
            self.stats_table.setItem(i, 2, QTableWidgetItem(str(values['max'])))
            self.stats_table.setItem(i, 3, QTableWidgetItem(str(values['min'])))
            self.stats_table.setItem(i, 4, QTableWidgetItem(str(values['std'])))
        self.stats_table.resizeColumnsToContents()

    def clear_stats(self):
        self.stats_table.setRowCount(0)