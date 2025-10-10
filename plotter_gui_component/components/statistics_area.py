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
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setObjectName("statistics-table")
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
            statistic_item = self.stats_table.item(i, 0)
            if statistic_item is None:
                continue
            stats[statistic_item.text()] = {
                'max': self._get_item_text(i, 1),
                'mean': self._get_item_text(i, 2),
                'min': self._get_item_text(i, 3),
                'std': self._get_item_text(i, 4),
            }
        return stats

    def set_stats(self, stats):
        self.stats_table.setRowCount(len(stats))
        for i, (statistic, values) in enumerate(stats.items()):
            self.stats_table.setItem(i, 0, QTableWidgetItem(str(statistic)))
            self.stats_table.setItem(i, 1, QTableWidgetItem(str(values.get('max', ''))))
            self.stats_table.setItem(i, 2, QTableWidgetItem(str(values.get('mean', ''))))
            self.stats_table.setItem(i, 3, QTableWidgetItem(str(values.get('min', ''))))
            self.stats_table.setItem(i, 4, QTableWidgetItem(str(values.get('std', ''))))
        self.stats_table.resizeColumnsToContents()

    def clear_stats(self):
        self.stats_table.setRowCount(0)

    def _get_item_text(self, row, column):
        item = self.stats_table.item(row, column)
        return item.text() if item else ""