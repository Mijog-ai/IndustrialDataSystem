from PyQt5.QtWidgets import QMenuBar, QAction
import logging

class MenuBar(QMenuBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.setup_menu()

    def setup_menu(self):
        self.file_menu = self.addMenu('File')



        load_action = QAction('Load File', self)
        load_action.triggered.connect(self.load_file_triggered)
        self.file_menu.addAction(load_action)

        save_data_action = QAction('Save Data', self)
        save_data_action.triggered.connect(self.main_window.save_data)
        self.file_menu.addAction(save_data_action)

        save_plot_action = QAction('Save Plot', self)
        save_plot_action.triggered.connect(self.main_window.save_plot)
        self.file_menu.addAction(save_plot_action)

        export_table_action = QAction('Export Table to Excel', self)
        export_table_action.triggered.connect(self.main_window.export_table_to_excel)
        self.file_menu.addAction(export_table_action)

        self.file_menu.addSeparator()

        # Add New Session action
        new_session_action = QAction('New Session', self)
        new_session_action.triggered.connect(self.new_session)
        self.file_menu.addAction(new_session_action)

        save_session_action = QAction('Save Session', self)
        save_session_action.triggered.connect(self.save_session)
        self.file_menu.addAction(save_session_action)

        load_session_action = QAction('Load Session', self)
        load_session_action.triggered.connect(self.load_session)
        self.file_menu.addAction(load_session_action)

        self.file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.main_window.close)
        self.file_menu.addAction(exit_action)

        self.edit_menu = self.addMenu('Edit')

    def add_edit_actions(self, limit_lines_action, smoothing_options_action, comment_box_action,data_filter_action,curve_fitting_action):
        self.edit_menu.addAction(limit_lines_action)
        self.edit_menu.addAction(smoothing_options_action)
        self.edit_menu.addAction(comment_box_action)
        self.edit_menu.addAction(data_filter_action)
        self.edit_menu.addAction(curve_fitting_action)

    def save_session(self):
        if hasattr(self.main_window, 'session_manager'):
            self.main_window.session_manager.save_session()
        else:
            print("Session manager not initialized")

    def load_session(self):
        if hasattr(self.main_window, 'session_manager'):
            self.main_window.session_manager.load_session()
        else:
            print("Session manager not initialized")

    def new_session(self):
        if hasattr(self.main_window, 'session_manager'):
            self.main_window.session_manager.new_session()
        else:
            print("Session manager not initialized")

    def load_file_triggered(self):
        print("Load File menu item clicked")
        logging.info("Load File menu item clicked")
        if hasattr(self.parent(), 'load_file'):
            self.parent().load_file()
        else:
            print("MainWindow does not have load_file method")
            logging.error("MainWindow does not have load_file method")
