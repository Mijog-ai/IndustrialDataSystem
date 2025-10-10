import traceback

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QListWidget, QPushButton, QMessageBox, QMainWindow
import logging


class AxisSelection(QGroupBox):
    def __init__(self, parent):
        super().__init__("Axis Selection", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.x_combo = QComboBox()
        self.layout.addRow("X-axis:", self.x_combo)

        self.y_list = QListWidget()
        self.y_list.setSelectionMode(QListWidget.MultiSelection)
        self.layout.addRow("Y-axis (select up to 3):", self.y_list)

        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot)
        self.layout.addRow(self.plot_button)

        self.setLayout(self.layout)

    def update_options(self, columns):
        self.x_combo.clear()
        self.y_list.clear()
        self.x_combo.addItems(columns)
        self.y_list.addItems(columns)

    def plot(self):
        try:
            logging.info("Plot button clicked")

            # Traverse up the widget hierarchy to find the MainWindow
            main_window = self.get_main_window()
            if not main_window:
                raise Exception("Could not find MainWindow")

            x_column = self.x_combo.currentText()
            y_columns = [item.text() for item in self.y_list.selectedItems()]

            if not x_column or not y_columns:
                QMessageBox.warning(main_window, "Warning", "Please select X and Y axes.")
                return

            logging.debug(f"Selected axes - X: {x_column}, Y: {y_columns}")
            smoothing_params = main_window.left_panel.smoothing_options.get_params()
            logging.debug(f"Smoothing params: {smoothing_params}")

            main_window.right_panel.plot_area.plot_data(main_window.df, x_column, y_columns, smoothing_params)
        except Exception as e:
            logging.error(f"Error in plot method: {str(e)}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while preparing to plot: {str(e)}")

    def get_main_window(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                return parent
            parent = parent.parent()
        return None

    def reset(self):
        self.x_combo.setCurrentIndex(0)
        self.y_list.clearSelection()