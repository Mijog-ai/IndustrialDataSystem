"""Tabular preview widget used by the plotter."""

from __future__ import annotations

from typing import Optional

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class DataPreview(QGroupBox):
    """Render the first rows from a dataframe in a compact table."""

    def __init__(self, parent=None) -> None:
        super().__init__("Data Preview", parent)
        self.setObjectName("data-preview-group")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(12)

        self._message = QLabel("Load a dataset to view the first records.")
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setProperty("secondary", "true")
        layout.addWidget(self._message)

        self._table = QTableWidget(0, 0)
        self._table.setObjectName("data-preview-table")
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.hide()
        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_dataframe(self, df: Optional[pd.DataFrame], *, max_rows: int = 40) -> None:
        """Populate the preview table with the provided data."""

        if df is None or df.empty:
            self.clear()
            return

        subset = df.head(max_rows)
        self._table.setColumnCount(len(subset.columns))
        self._table.setHorizontalHeaderLabels([str(column) for column in subset.columns])
        self._table.setRowCount(len(subset.index))

        for row_index, (_, row) in enumerate(subset.iterrows()):
            for column_index, value in enumerate(row):
                item = QTableWidgetItem("" if pd.isna(value) else str(value))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self._table.setItem(row_index, column_index, item)

        self._table.resizeColumnsToContents()
        self._message.hide()
        self._table.show()

    def clear(self) -> None:
        self._table.clear()
        self._table.setRowCount(0)
        self._table.setColumnCount(0)
        self._table.hide()
        self._message.setText("Load a dataset to view the first records.")
        self._message.show()
