# session_manager.py

import pickle
import logging
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt, QCoreApplication


class SessionManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def save_session(self):
        file_name, _ = QFileDialog.getSaveFileName(self.main_window, "Save Session", "",
                                                   "Inline Analytics Files (*.inlingh)")
        if file_name:
            if not file_name.endswith('.inlingh'):
                file_name += '.inlingh'
            try:
                progress = QProgressDialog("Saving session...", "Cancel", 0, 100, self.main_window)
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)

                session_data = {
                    'df': self.main_window.df,
                    'original_df': self.main_window.original_df,
                    'filtered_df': self.main_window.filtered_df,
                    'x_column': self.main_window.left_panel.axis_selection.x_combo.currentText(),
                    'y_columns': [item.text() for item in
                                  self.main_window.left_panel.axis_selection.y_list.selectedItems()],
                    'smoothing_params': self.main_window.left_panel.smoothing_options.get_params(),
                    'limit_lines': self.main_window.left_panel.limit_lines.get_limit_lines(),
                    'fit_type': self.main_window.left_panel.curve_fitting.fit_type.currentText(),
                    'comments': self.main_window.left_panel.comment_box.get_comments(),
                    'data_filter': {
                        'column': self.main_window.left_panel.data_filter.filter_column.currentText(),
                        'min_value': self.main_window.left_panel.data_filter.min_value.text(),
                        'max_value': self.main_window.left_panel.data_filter.max_value.text(),
                        'all_columns': [self.main_window.left_panel.data_filter.filter_column.itemText(i)
                                        for i in range(self.main_window.left_panel.data_filter.filter_column.count())]
                    },
                    'statistics': self.main_window.right_panel.statistics_area.get_stats(),
                    'show_original_data': self.main_window.right_panel.plot_area.get_show_original_state(),
                    'plot_title': self.main_window.left_panel.get_plot_title()
                }



                progress.setValue(50)
                QCoreApplication.processEvents()

                with open(file_name, 'wb') as f:
                    pickle.dump(session_data, f, protocol=pickle.HIGHEST_PROTOCOL)

                progress.setValue(100)
                logging.info(f"Session saved successfully to {file_name}")
                QMessageBox.information(self.main_window, "Success", "Session saved successfully!")
            except Exception as e:
                logging.error(f"Error saving session: {str(e)}")
                QMessageBox.critical(self.main_window, "Error", f"An error occurred while saving the session: {str(e)}")
            finally:
                progress.close()

    def load_session(self):
        file_name, _ = QFileDialog.getOpenFileName(self.main_window, "Load Session", "",
                                                   "Inline Analytics Files (*.inlingh)")
        if file_name:
            try:
                progress = QProgressDialog("Loading session...", "Cancel", 0, 100, self.main_window)
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.setValue(0)

                with open(file_name, 'rb') as f:
                    session_data = pickle.load(f)

                progress.setValue(50)
                QCoreApplication.processEvents()

                self.main_window.df = session_data['df']
                self.main_window.original_df = session_data['original_df']
                self.main_window.filtered_df = session_data['filtered_df']

                self.main_window.left_panel.axis_selection.update_options(self.main_window.df.columns)
                self.main_window.left_panel.axis_selection.x_combo.setCurrentText(session_data['x_column'])
                self.main_window.left_panel.axis_selection.y_list.clearSelection()
                for y_column in session_data['y_columns']:
                    items = self.main_window.left_panel.axis_selection.y_list.findItems(y_column, Qt.MatchExactly)
                    if items:
                        items[0].setSelected(True)

                self.main_window.left_panel.smoothing_options.set_params(session_data['smoothing_params'])
                self.main_window.left_panel.limit_lines.set_limit_lines(session_data['limit_lines'])
                self.main_window.left_panel.curve_fitting.fit_type.setCurrentText(session_data['fit_type'])
                self.main_window.left_panel.comment_box.set_comments(session_data['comments'])

                # Load data filter settings
                self.main_window.left_panel.data_filter.update_columns(session_data['data_filter']['all_columns'])
                self.main_window.left_panel.data_filter.set_filter(
                    session_data['data_filter']['column'],
                    session_data['data_filter']['min_value'],
                    session_data['data_filter']['max_value']
                )

                # Load statistics
                self.main_window.right_panel.statistics_area.set_stats(session_data['statistics'])

                self.main_window.right_panel.plot_area.set_show_original_state(
                    session_data.get('show_original_data', True))

                self.main_window.left_panel.set_plot_title(session_data.get('plot_title', ''))

                progress.setValue(90)
                QCoreApplication.processEvents()

                self.main_window.update_plot()
                progress.setValue(100)
                logging.info(f"Session loaded successfully from {file_name}")
                QMessageBox.information(self.main_window, "Success", "Session loaded successfully!")
            except Exception as e:
                logging.error(f"Error loading session: {str(e)}")
                QMessageBox.critical(self.main_window, "Error",
                                     f"An error occurred while loading the session: {str(e)}")
            finally:
                progress.close()

    def new_session(self):
        logging.info("Initiating new session")
        try:
            # Check if there's unsaved data
            if self.main_window.unsaved_changes:
                reply = QMessageBox.question(self.main_window, 'Save Changes?',
                                             "Do you want to save the current session before creating a new one?",
                                             QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

                if reply == QMessageBox.Yes:
                    self.save_session()
                elif reply == QMessageBox.Cancel:
                    return  # User cancelled, don't create a new session

            # Clear everything and create a new session
            self.main_window.clear_all_data()
            self.main_window.reset_ui()
            self.main_window.update_plot()

            QMessageBox.information(self.main_window, "New Session", "A new session has been created.")
            logging.info("New session created successfully")
        except Exception as e:
            logging.error(f"Error creating new session: {str(e)}")
            QMessageBox.critical(self.main_window, "Error", f"An error occurred while creating a new session: {str(e)}")
