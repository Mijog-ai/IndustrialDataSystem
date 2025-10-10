from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QInputDialog, QMessageBox
import logging

class LimitLines(QGroupBox):
    def __init__(self, parent):
        super().__init__("Limit Lines", parent)
        self.layout = QVBoxLayout()
        self.limit_lines = []
        self.setup_ui()

    def setup_ui(self):
        self.add_vline_button = QPushButton("Add Vertical Line")
        self.add_vline_button.clicked.connect(lambda: self.add_limit_line('vertical'))
        self.layout.addWidget(self.add_vline_button)

        self.add_hline_button = QPushButton("Add Horizontal Line")
        self.add_hline_button.clicked.connect(lambda: self.add_limit_line('horizontal'))
        self.layout.addWidget(self.add_hline_button)

        self.clear_lines_button = QPushButton("Clear All Lines")
        self.clear_lines_button.clicked.connect(self.clear_limit_lines)
        self.layout.addWidget(self.clear_lines_button)

        self.setLayout(self.layout)

    def add_limit_line(self, line_type):
        value, ok = QInputDialog.getDouble(self, f"Add {line_type.capitalize()} Line", "Enter value:")
        if ok:
            self.limit_lines.append({'type': line_type, 'value': value})
            self.update_plot()
            logging.info(f"Added {line_type} limit line at {value}")

    def clear_limit_lines(self):
        self.limit_lines.clear()
        self.update_plot()
        logging.info("Cleared all limit lines")

    def get_limit_lines(self):
        return self.limit_lines

    def update_plot(self):
        main_window = self.window()
        if hasattr(main_window, 'update_plot'):
            main_window.update_plot()
        else:
            QMessageBox.warning(self, "Error", "Unable to update plot")

    def set_limit_lines(self, limit_lines):
        self.limit_lines = limit_lines

    def clear_lines(self):
        self.limit_lines = []