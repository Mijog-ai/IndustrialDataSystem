# tool_bar.py
import logging
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QAction, QLabel, QStyle, QToolBar


class ToolBar(QToolBar):
    def __init__(self, parent):
        super().__init__('Main', parent)
        self.setMovable(False)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setIconSize(QSize(20, 20))
        self.setup_toolbar()

    def setup_toolbar(self):
        style = self.style()

        load_action = QAction(style.standardIcon(QStyle.SP_DialogOpenButton), 'Load Data', self)
        load_action.triggered.connect(self.load_file_triggered)
        self.addAction(load_action)

        save_data_action = QAction(style.standardIcon(QStyle.SP_DialogSaveButton), 'Save Data', self)
        save_data_action.triggered.connect(self.parent().save_data)
        self.addAction(save_data_action)

        save_plot_action = QAction(style.standardIcon(QStyle.SP_DriveFDIcon), 'Save Plot', self)
        save_plot_action.triggered.connect(self.parent().save_plot)
        self.addAction(save_plot_action)

        # Add a label to indicate drag and drop functionality
        self.addSeparator()
        # Replace the drag and drop label with a file name label
        self.file_label = QLabel("No file loaded")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setObjectName("toolbar-file-label")
        self.addWidget(self.file_label)

    def update_file_name(self, file_path):
        if file_path:
            file_name = os.path.basename(file_path)
            self.file_label.setText(f"Loaded file: {file_name}")
        else:
            self.file_label.setText("No file loaded")

    def load_file_triggered(self):
        print("Load File menu item clicked")
        logging.info("Load File menu item clicked")
        if hasattr(self.parent(), 'load_file'):
            self.parent().load_file()
        else:
            print("MainWindow does not have load_file method")
            logging.error("MainWindow does not have load_file method")
