# curve_fitting.py

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QPushButton, QMessageBox, QComboBox
import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
import logging


class CurveFitting(QGroupBox):
    def __init__(self, parent):
        super().__init__("Curve Fitting", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.fit_type = QComboBox()
        self.fit_type.addItems(['Linear', 'Quadratic', 'Exponential'])
        self.layout.addRow("Fit Type:", self.fit_type)

        self.apply_fit_button = QPushButton("Apply Fit")
        self.apply_fit_button.clicked.connect(self.apply_fit)
        self.layout.addRow(self.apply_fit_button)

        self.setLayout(self.layout)

    def apply_fit(self):
        logging.info("Starting curve fitting process")
        main_window = self.window()

        try:
            # Check if data is available
            if main_window.filtered_df is None or main_window.filtered_df.empty:
                raise ValueError("No data available for fitting")

            # Get selected columns
            x_column = main_window.left_panel.axis_selection.x_combo.currentText()
            y_items = main_window.left_panel.axis_selection.y_list.selectedItems()

            if not y_items:
                raise ValueError("No Y-axis selected")

            y_column = y_items[0].text()

            logging.info(f"Selected columns - X: {x_column}, Y: {y_column}")

            # Get data
            x_data = main_window.filtered_df[x_column].values
            y_data = main_window.filtered_df[y_column].values

            # Remove any NaN or infinite values
            mask = np.isfinite(x_data) & np.isfinite(y_data)
            x_data = x_data[mask]
            y_data = y_data[mask]

            if len(x_data) == 0 or len(y_data) == 0:
                raise ValueError("No valid data points for fitting after removing NaN/inf values")

            fit_type = self.fit_type.currentText()

            if fit_type == 'Linear':
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_data, y_data)
                fit_func = lambda x: slope * x + intercept
                equation = f"y = {slope:.4f}x + {intercept:.4f}"
                r_squared = r_value ** 2
            elif fit_type == 'Quadratic':
                popt, _ = curve_fit(self.quadratic_func, x_data, y_data)
                fit_func = lambda x: self.quadratic_func(x, *popt)
                equation = f"y = {popt[0]:.4f}x^2 + {popt[1]:.4f}x + {popt[2]:.4f}"
                r_squared = self.calculate_r_squared(y_data, fit_func(x_data))
            elif fit_type == 'Exponential':
                popt, _ = curve_fit(self.exponential_func, x_data, y_data, p0=[1, 0.1])
                fit_func = lambda x: self.exponential_func(x, *popt)
                equation = f"y = {popt[0]:.4f} * e^({popt[1]:.4f}x)"
                r_squared = self.calculate_r_squared(y_data, fit_func(x_data))

            logging.info(f"{fit_type} fit successful. Equation: {equation}")

            # Plot the results
            main_window.right_panel.plot_area.apply_curve_fitting(x_data, y_data, fit_func, equation, fit_type)

            QMessageBox.information(self, "Fit Applied",
                                    f"Applied {fit_type} fit:\n{equation}\nR-squared: {r_squared:.4f}")

        except Exception as e:
            logging.exception(f"Error during curve fitting: {str(e)}")
            QMessageBox.warning(self, "Fit Error", f"Error applying fit: {str(e)}")

    @staticmethod
    def quadratic_func(x, a, b, c):
        return a * x ** 2 + b * x + c

    @staticmethod
    def exponential_func(x, a, b):
        return a * np.exp(b * x)

    @staticmethod
    def calculate_r_squared(y_true, y_pred):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        if ss_tot == 0:
            return 1.0
        return 1 - (ss_res / ss_tot)

    def reset(self):
        self.fit_type.setCurrentIndex(0)