from PyQt5.QtWidgets import QGroupBox, QFormLayout, QComboBox, QLineEdit, QPushButton, QMessageBox, QMainWindow
import logging


class DataFilter(QGroupBox):
    def __init__(self, parent):
        super().__init__("Data Filter", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.filter_column = QComboBox()
        self.layout.addRow("Column:", self.filter_column)

        self.min_value = QLineEdit()
        self.layout.addRow("Min Value:", self.min_value)

        self.max_value = QLineEdit()
        self.layout.addRow("Max Value:", self.max_value)

        self.apply_filter_button = QPushButton("Apply Filter")
        self.apply_filter_button.clicked.connect(self.apply_filter)
        self.layout.addRow(self.apply_filter_button)

        self.setLayout(self.layout)

    def update_columns(self, columns):
        current_text = self.filter_column.currentText()
        self.filter_column.clear()
        self.filter_column.addItems(columns)
        if current_text in columns:
            self.filter_column.setCurrentText(current_text)

    def apply_filter(self):
        try:
            main_window = self.get_main_window()
            if not main_window:
                raise Exception("Could not find MainWindow")

            column = self.filter_column.currentText()
            min_val = float(self.min_value.text()) if self.min_value.text() else None
            max_val = float(self.max_value.text()) if self.max_value.text() else None

            logging.info(f"Applying filter on column: {column}, min: {min_val}, max: {max_val}")

            if not column:
                raise ValueError("Please select a column to filter")

            if not min_val and not max_val:
                raise ValueError("Please enter at least one filter value")

            min_val = float(min_val) if min_val else None
            max_val = float(max_val) if max_val else None

            if min_val is not None and max_val is not None and min_val > max_val:
                raise ValueError("Min value must be less than or equal to Max value")

            main_window.apply_data_filter(column, min_val, max_val)
        except ValueError as e:
            logging.error(f"Invalid input in DataFilter: {str(e)}")
            QMessageBox.warning(self, "Invalid Input", str(e))
        except Exception as e:
            logging.error(f"Unexpected error in DataFilter: {str(e)}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")

    def get_main_window(self):
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                return parent
            parent = parent.parent()
        return None


    def set_filter(self, column, min_value, max_value):
        if column in [self.filter_column.itemText(i) for i in range(self.filter_column.count())]:
            self.filter_column.setCurrentText(column)
        self.min_value.setText(str(min_value) if min_value is not None else "")
        self.max_value.setText(str(max_value) if max_value is not None else "")

    def reset(self):
        self.filter_column.clear()
        self.min_value.clear()
        self.max_value.clear()