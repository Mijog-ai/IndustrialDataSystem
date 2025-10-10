

from PyQt5.QtWidgets import QGroupBox, QFormLayout, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox

class SmoothingOptions(QGroupBox):
    def __init__(self, parent):
        super().__init__("Smoothing Options", parent)
        self.layout = QFormLayout()
        self.setup_ui()

    def setup_ui(self):
        self.smooth_check = QCheckBox("Apply Smoothing")
        self.layout.addRow(self.smooth_check)

        self.smooth_method = QComboBox()
        self.smooth_method.addItems(['Mean Line', 'Savitzky-Golay', 'Gaussian Filter'])
        self.layout.addRow("Smoothing Method:", self.smooth_method)

        self.window_size = QSpinBox()
        self.window_size.setRange(5, 500)
        self.window_size.setValue(51)
        self.layout.addRow("Window Size:", self.window_size)
        self.poly_order = QSpinBox()
        self.poly_order.setRange(1, 5)
        self.poly_order.setValue(3)
        self.layout.addRow("Polynomial Order:", self.poly_order)

        self.sigma = QDoubleSpinBox()
        self.sigma.setRange(0.1, 10.0)
        self.sigma.setValue(2.0)
        self.sigma.setSingleStep(0.1)
        self.layout.addRow("Gaussian Sigma:", self.sigma)

        self.setLayout(self.layout)

    def get_params(self):
        return {
            'apply': self.smooth_check.isChecked(),
            'method': self.smooth_method.currentText().lower().replace(' ', '_'),
            'window_length': self.window_size.value(),
            'poly_order': self.poly_order.value(),
            'sigma': self.sigma.value()
        }

    def clear(self):
        self.text_edit.clear()

    def set_params(self, params):
        self.smooth_check.setChecked(params['apply'])
        self.smooth_method.setCurrentText(params['method'])
        self.window_size.setValue(params['window_length'])
        self.poly_order.setValue(params['poly_order'])
        self.sigma.setValue(params['sigma'])

    def reset(self):
        self.smooth_check.setChecked(False)
        self.smooth_method.setCurrentIndex(0)  # Set to first item ('Mean Line')
        self.window_size.setValue(51)
        self.poly_order.setValue(3)
        self.sigma.setValue(2.0)
