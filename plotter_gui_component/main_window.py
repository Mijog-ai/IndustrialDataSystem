from PyQt5.QtWidgets import QMainWindow, QHBoxLayout, QWidget, QFileDialog, QMessageBox, QAction
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from gui.menu_bar import MenuBar
from gui.tool_bar import ToolBar
from gui.left_panel import LeftPanel
from gui.right_panel import RightPanel
from utils.asc_utils import load_and_process_asc_file, load_and_process_csv_file, load_and_process_tdms_file
import pandas as pd
import logging
import os
from gui.components.session_manager import SessionManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inline Analytical tool")
        self.setGeometry(100, 100, 1600, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        self.df = None
        self.original_df = None
        self.filtered_df = None
        self.unsaved_changes = False

        self.setup_menu_bar()
        self.setup_ui()
        self.setup_edit_actions()

        # Enable drag and drop
        self.setAcceptDrops(True)

        self.session_manager = SessionManager(self)
        self.current_file = None

    def setup_menu_bar(self):
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)

    def setup_ui(self):
        # self.menu_bar = MenuBar(self)
        # self.setMenuBar(self.menu_bar)

        self.tool_bar = ToolBar(self)
        self.addToolBar(self.tool_bar)

        self.left_panel = LeftPanel(self)
        self.right_panel = RightPanel(self)

        self.layout.addWidget(self.left_panel, 1)
        self.layout.addWidget(self.right_panel, 4)

    def clear_all_data(self):
        self.df = None
        self.original_df = None
        self.filtered_df = None
        self.unsaved_changes = False

    def reset_ui(self):
        # Reset LeftPanel
        self.left_panel.axis_selection.update_options([])
        self.left_panel.smoothing_options.reset()
        self.left_panel.limit_lines.clear_lines()
        self.left_panel.data_filter.reset()
        self.left_panel.curve_fitting.reset()
        self.left_panel.comment_box.clear()

        # Reset RightPanel
        self.right_panel.plot_area.clear_plot()
        self.right_panel.statistics_area.clear_stats()




    def load_file(self, file_path=None):
        print("load_file method called in MainWindow")
        logging.info("load_file method called in MainWindow")
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(self, "Open File", "",
                                                       "All Files (*);;ASC Files (*.asc);;CSV Files (*.csv);;TDMS Files (*.tdms)")
        if file_path:
            print(f"File selected: {file_path}")
            logging.info(f"File selected: {file_path}")
            try:
                logging.info(f"Attempting to load file: {file_path}")
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension == '.asc':
                    self.df = load_and_process_asc_file(file_path)
                elif file_extension == '.csv':
                    self.df = load_and_process_csv_file(file_path)
                elif file_extension == '.tdms':
                    self.df = load_and_process_tdms_file(file_path)
                else:
                    raise ValueError(f"Unsupported file type: {file_extension}")

                if self.df is None or self.df.empty:
                    raise ValueError("No data loaded from the file")

                self.original_df = self.df.copy()
                self.filtered_df = self.df.copy()
                self.update_ui_after_load()


                self.current_file = file_path
                self.tool_bar.update_file_name(self.current_file)
                logging.info(f"File loaded successfully. Shape: {self.df.shape}")
                QMessageBox.information(self, "Success", "File loaded successfully!")
            except Exception as e:
                logging.error(f"Error loading file: {str(e)}")
                QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")
        else:
            logging.info("File loading cancelled by user")


    def setup_edit_actions(self):
        self.show_limit_lines_action = (QAction
                                        ("Show Limit Lines", self, checkable=True))
        self.show_limit_lines_action.triggered.connect(self.toggle_limit_lines)

        self.show_smoothing_options_action = QAction('Smoothing_options', self, checkable=True)
        self.show_smoothing_options_action.triggered.connect(self.toggle_smoothing_options)

        self.show_comment_box_action = QAction('Add_Comment_plot', self, checkable=True)
        self.show_comment_box_action.triggered.connect(self.toggle_comment_box)

        self.show_data_filter_action = QAction('Data_Filter_plotter', self, checkable=True)
        self.show_data_filter_action.triggered.connect(self.toggle_data_filter)

        self.show_curve_fitting_action = QAction('Curve Fitting', self, checkable = True)
        self.show_curve_fitting_action.triggered.connect(self.toggle_curve_fitting)


        self.menu_bar.add_edit_actions(self.show_limit_lines_action,
                                       self.show_smoothing_options_action,
                                       self.show_comment_box_action,
                                       self.show_data_filter_action,
                                       self.show_curve_fitting_action)

    def toggle_limit_lines(self, checked):
        self.left_panel.limit_lines.setVisible(checked)

    def toggle_smoothing_options(self, checked):
        self.left_panel.smoothing_options.setVisible(checked)

    def toggle_comment_box(self, checked):
        self.left_panel.comment_box.setVisible(checked)

    def toggle_data_filter(self, checked):
        self.left_panel.data_filter.setVisible(checked)

    def toggle_curve_fitting(self, checked):
        self.left_panel.curve_fitting.setVisible(checked)


    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            self.load_file(file_path)

    def update_ui_after_load(self):
        if self.df is not None and not self.df.empty:
            columns = self.df.columns.tolist()
            self.left_panel.axis_selection.update_options(columns)
            self.left_panel.data_filter.update_columns(columns)
            self.right_panel.statistics_area.update_stats(self.filtered_df)
        else:
            logging.warning("DataFrame is None or empty after loading")

    def save_data(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to save. Please load a file first.")
            return

        default_name = os.path.splitext(os.path.basename(self.current_file))[0] if self.current_file else "data"
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Data",default_name, "CSV Files (*.csv);;Excel Files (*.xlsx)")
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    self.df.to_csv(file_name, sep=';', index=False)
                elif file_name.endswith('.xlsx'):
                    self.df.to_excel(file_name, index=False)
                QMessageBox.information(self, "Success", "Data saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the data: {str(e)}")

    def save_plot(self):
        if not hasattr(self.right_panel.plot_area, 'figure') or len(self.right_panel.plot_area.figure.axes) == 0:
            QMessageBox.warning(self, "Warning", "No plot to save. Please create a plot first.")
            return

        default_name = os.path.splitext(os.path.basename(self.current_file))[0] if self.current_file else "plot"
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Plot", default_name, "PNG Files (*.png);;PDF Files (*.pdf)")
        if file_name:
            try:
                fig = self.right_panel.plot_area.figure

                # Get comments from the comment box
                comments = self.left_panel.comment_box.get_comments()
                if comments:
                    fig.text(0.1, 0.01, comments, wrap=True, fontsize=8, va='bottom')

                # Save the figure
                fig.savefig(file_name, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", "Plot saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving the plot: {str(e)}")

    def export_table_to_excel(self):
        if self.df is None:
            QMessageBox.warning(self, "Warning", "No data to export. Please load a file first.")
            return

        default_name = os.path.splitext(os.path.basename(self.current_file))[0] if self.current_file else "data"
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Table to Excel", default_name, "Excel Files (*.xlsx)")
        if file_name:
            try:
                with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
                    # Write the main data
                    if self.filtered_df is not None and not self.filtered_df.empty:
                        self.filtered_df.to_excel(writer, sheet_name='Data', index=False)
                    else:
                        self.df.to_excel(writer, sheet_name='Data', index=False)

                    if self.filtered_df is not None and not self.filtered_df.empty:
                        stats = self.filtered_df.describe()
                        stats.to_excel(writer, sheet_name='Filtered Statistics')

                    else:
                        stats = self.df.describe()
                        stats.to_excel(writer, sheet_name='Original Statistics')

                    # Write current plot configuration
                    plot_config = pd.DataFrame({
                        'X-axis': [self.left_panel.axis_selection.x_combo.currentText()],
                        'Y-axes': [
                            ', '.join([item.text() for item in self.left_panel.axis_selection.y_list.selectedItems()])],
                        'Smoothing': [self.left_panel.smoothing_options.smooth_check.isChecked()],
                        'Smoothing Method': [self.left_panel.smoothing_options.smooth_method.currentText()],
                        'Window Size': [self.left_panel.smoothing_options.window_size.value()],
                        'Polynomial Order': [self.left_panel.smoothing_options.poly_order.value()],
                        'Gaussian Sigma': [self.left_panel.smoothing_options.sigma.value()],

                    })
                    plot_config.to_excel(writer, sheet_name='Plot Configuration', index=False)

                    # Write comments
                    comments = pd.DataFrame({'Comments': [self.left_panel.comment_box.get_comments()]})
                    comments.to_excel(writer, sheet_name='Comments', index=False)

                QMessageBox.information(self, "Success", "Table exported to Excel successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while exporting the table: {str(e)}")

    def apply_data_filter(self, column, min_val, max_val):


        try:

            logging.info(f"Applying data filter: column={column}, min={min_val}, max={max_val}")

            if self.original_df is None or column not in self.original_df.columns:
                raise ValueError(f"Column '{column}' not found in the dataframe")

            self.filtered_df = self.original_df.copy()

            if min_val is not None:
                self.filtered_df = self.filtered_df[self.filtered_df[column] >= min_val]
            if max_val is not None:
                self.filtered_df = self.filtered_df[self.filtered_df[column] <= max_val]

            if self.filtered_df.empty:
                raise ValueError("No data points in the selected range")

            logging.info(f"Filter applied. Rows before: {len(self.original_df)}, after: {len(self.filtered_df)}")

            # Applying statistics update over the applied filter
            self.update_statistics()

            self.update_plot(update_filter=False)
            QMessageBox.information(self, "Filter Applied", "Data filter applied successfully")
        except ValueError as e:
            logging.error(f"Error applying filter: {str(e)}")
            QMessageBox.warning(self, "Filter Error", str(e))
            self.filtered_df = self.original_df.copy()
        except Exception as e:
            logging.error(f"Unexpected error applying filter: {str(e)}")
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
            self.filtered_df = self.original_df.copy()


    def update_plot(self, update_filter=True):

        if self.filtered_df is not None and not self.filtered_df.empty:
            try:

                x_column = self.left_panel.axis_selection.x_combo.currentText()
                y_columns = [item.text() for item in self.left_panel.axis_selection.y_list.selectedItems()]
                smoothing_params = self.left_panel.smoothing_options.get_params()

                limit_lines = []
                if hasattr(self.left_panel, 'limit_lines') and hasattr(self.left_panel.limit_lines, 'get_limit_lines'):
                    limit_lines = self.left_panel.limit_lines.get_limit_lines()

                # Apply data filter if needed
                if update_filter:
                    filter_column = self.left_panel.data_filter.filter_column.currentText()
                    min_value = self.left_panel.data_filter.min_value.text()
                    max_value = self.left_panel.data_filter.max_value.text()

                    if filter_column and (min_value or max_value):
                        self.apply_data_filter(filter_column,
                                               float(min_value) if min_value else None,
                                               float(max_value) if max_value else None)

                self.right_panel.plot_area.plot_data(self.filtered_df, x_column, y_columns, smoothing_params,
                                                     limit_lines)
                self.update_statistics()
                self.unsaved_changes = True

            except Exception as e:
                logging.error(f"Error updating plot: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to update plot: {str(e)}")


        else:
            logging.warning("No data available to plot")



    def update_statistics(self):
        if self.filtered_df is not None and not self.filtered_df.empty:
            self.right_panel.statistics_area.update_stats(self.filtered_df)
        else:
            logging.warning("No filtered data available to update statistics")

    def setup_connections(self):
        # Connect the plot button to the PlotArea's update_plot method
        self.left_panel.axis_selection.plot_button.clicked.connect(self.update_plot)

    def update_plot_title(self, title):
        if self.right_panel.plot_area.last_plot_params:
            self.right_panel.plot_area.last_plot_params['title'] = title
            self.update_plot()
