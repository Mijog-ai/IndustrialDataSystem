import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QTextOption
from PyQt5.QtWidgets import (
QApplication,
QWidget,
QVBoxLayout,
QTextEdit

)
import sys

class EnhancedTestAPP(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16,16,16,16)
        layout.setSpacing(12)
def run_test_app():
    """
    This is test run
    """
    try:
        window = EnhancedTestAPP()
        return window
    except Exception as e:
        print(f"Error creating plotter widget: {e}")
        import traceback
        traceback.print_exc()
        return None


# Standalone execution
def main():
    """Run as standalone application."""
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))

    window = EnhancedTestAPP()
    window.setWindowTitle("Enhanced Test App")
    window.setMinimumSize(500, 400)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()