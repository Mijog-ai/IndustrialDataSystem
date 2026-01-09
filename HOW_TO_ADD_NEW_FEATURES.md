# How to Add New Features - Complete Guide

## 🎯 Overview
This guide teaches you how to add new functionality to the Industrial Data System, step by step, with real examples.

---

## 📋 Table of Contents
1. [Understanding the Architecture](#1-understanding-the-architecture)
2. [Example 1: Add a New Button to Reader Dashboard](#2-example-1-add-a-new-button-to-reader-dashboard)
3. [Example 2: Add a New AI Tool/Integration](#3-example-2-add-a-new-ai-toolintegration)
4. [Example 3: Add a New Database Table](#4-example-3-add-a-new-database-table)
5. [Example 4: Add a New File Type Support](#5-example-4-add-a-new-file-type-support)
6. [Best Practices](#6-best-practices)
7. [Testing Your Changes](#7-testing-your-changes)

---

## 1. Understanding the Architecture

### Project Structure
```
industrial_data_system/
├── apps/                    # GUI applications
│   └── desktop/
│       ├── reader.py       # Reader app
│       └── uploader.py     # Uploader app
│
├── core/                    # Core functionality
│   ├── db_manager.py       # Database operations
│   ├── config.py           # Configuration
│   ├── auth.py             # Authentication
│   └── storage.py          # File storage
│
├── Integrations/            # AI tools and analysis
│   ├── analysis/           # Data analysis tools
│   ├── anomaly_detection/  # Anomaly detection
│   ├── training/           # Model training
│   ├── visualization/      # Plotting tools
│   └── toolkit.py          # Convenience imports
│
├── utils/                   # Utility functions
│   └── asc_utils.py        # File processing
│
└── main.py                  # Application entry point
```

### When to Add Where?

| What You're Adding | Where to Put It |
|-------------------|-----------------|
| New GUI feature | `apps/desktop/` |
| New AI tool | `Integrations/` |
| Database operations | `core/db_manager.py` |
| File processing | `utils/` |
| Configuration | `core/config.py` |

---

## 2. Example 1: Add a New Button to Reader Dashboard

### Goal: Add an "Export to CSV" button

### Step 1: Locate the UI Code
Open `industrial_data_system/apps/desktop/reader.py` and find the `ReaderDashboard` class.

### Step 2: Add the Button to the UI

```python
class ReaderDashboard(QWidget):
    def __init__(self):
        # ... existing code ...
        
        # Find where other buttons are created (around line 450)
        self.download_button = QPushButton("Download")
        self.download_button.setProperty("primary", True)
        self.download_button.setEnabled(False)
        preview_layout.addWidget(self.download_button)
        
        # ADD YOUR NEW BUTTON HERE
        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.setProperty("secondary", True)  # Use secondary style
        self.export_csv_button.setEnabled(False)  # Disabled until file selected
        preview_layout.addWidget(self.export_csv_button)
```

### Step 3: Connect Button to Handler Function

```python
class ReaderDashboard(QWidget):
    def __init__(self):
        # ... existing code ...
        
        # Find where connections are made (around line 470)
        self.tree.currentItemChanged.connect(self._handle_selection)
        
        # ADD YOUR CONNECTION HERE
        self.export_csv_button.clicked.connect(self._export_to_csv)
```

### Step 4: Create the Handler Function

```python
class ReaderDashboard(QWidget):
    # ... existing code ...
    
    def _export_to_csv(self) -> None:
        """Export current file data to CSV format."""
        if not self._current_resource:
            QMessageBox.warning(self, "Export", "No file selected")
            return
        
        # Ask user where to save
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export to CSV",
            f"{self._current_resource.name}.csv",
            "CSV Files (*.csv)"
        )
        
        if not save_path:
            return  # User cancelled
        
        try:
            # Load the file
            from industrial_data_system.utils.asc_utils import load_and_process_asc_file
            import pandas as pd
            
            file_path = self._current_resource.absolute_path
            
            # Check file type and load accordingly
            if file_path.suffix.lower() == '.asc':
                df = load_and_process_asc_file(str(file_path))
            elif file_path.suffix.lower() == '.parquet':
                df = pd.read_parquet(file_path)
            else:
                QMessageBox.warning(self, "Export", "Unsupported file type")
                return
            
            # Export to CSV
            df.to_csv(save_path, index=False)
            
            QMessageBox.information(
                self,
                "Export Successful",
                f"File exported to:\n{save_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Error exporting file:\n{str(e)}"
            )
```

### Step 5: Enable/Disable Button Based on Selection

```python
class ReaderDashboard(QWidget):
    def _handle_selection(
        self, current: Optional[QTreeWidgetItem], _: Optional[QTreeWidgetItem]
    ) -> None:
        """Called when user selects an item in the tree."""
        if not current:
            self._current_resource = None
            self.download_button.setEnabled(False)
            self.export_csv_button.setEnabled(False)  # ADD THIS
            self._show_message("Select a file to preview")
            return
        
        data = current.data(0, Qt.UserRole)
        
        if data.get("type") == "folder":
            self._show_message("Select a file to preview")
            self.download_button.setEnabled(False)
            self.export_csv_button.setEnabled(False)  # ADD THIS
            return
        
        resource = data.get("resource")
        if resource:
            self._current_resource = resource
            self.download_button.setEnabled(True)
            self.export_csv_button.setEnabled(True)  # ADD THIS
            self._preview_file(resource)
```

### Step 6: Test Your Changes

```bash
python industrial_data_system/main.py
```

1. Login to the reader
2. Select a file
3. Click "Export to CSV"
4. Verify the CSV file is created

---

## 3. Example 2: Add a New AI Tool/Integration

### Goal: Add a "Data Statistics" tool

### Step 1: Create the Integration Module

Create a new file: `industrial_data_system/Integrations/analysis/statistics.py`

```python
"""Statistical analysis tool for industrial data."""

from pathlib import Path
from typing import Optional
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from PyQt5.QtCore import Qt


class StatisticsWidget(QWidget):
    """Widget for displaying statistical analysis."""
    
    def __init__(self, file_path: Optional[Path] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.file_path = file_path
        self._init_ui()
        
        if file_path:
            self.analyze_file(file_path)
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Statistical Analysis")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        layout.addWidget(self.results_text)
        
        # Refresh button
        self.refresh_button = QPushButton("Refresh Analysis")
        self.refresh_button.clicked.connect(self._refresh)
        layout.addWidget(self.refresh_button)
    
    def analyze_file(self, file_path: Path):
        """Perform statistical analysis on the file."""
        try:
            # Load data
            if file_path.suffix.lower() == '.parquet':
                df = pd.read_parquet(file_path)
            elif file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            elif file_path.suffix.lower() == '.asc':
                from industrial_data_system.utils.asc_utils import load_and_process_asc_file
                df = load_and_process_asc_file(str(file_path))
            else:
                self.results_text.setText("Unsupported file format")
                return
            
            # Calculate statistics
            stats = self._calculate_statistics(df)
            
            # Display results
            self._display_statistics(stats)
            
        except Exception as e:
            self.results_text.setText(f"Error analyzing file:\n{str(e)}")
    
    def _calculate_statistics(self, df: pd.DataFrame) -> dict:
        """Calculate various statistics."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'numeric_columns': len(numeric_cols),
            'memory_usage': df.memory_usage(deep=True).sum() / 1024**2,  # MB
            'column_stats': {}
        }
        
        # Per-column statistics
        for col in numeric_cols[:10]:  # Limit to first 10 numeric columns
            stats['column_stats'][col] = {
                'mean': df[col].mean(),
                'std': df[col].std(),
                'min': df[col].min(),
                'max': df[col].max(),
                'median': df[col].median(),
                'missing': df[col].isna().sum()
            }
        
        return stats
    
    def _display_statistics(self, stats: dict):
        """Format and display statistics."""
        output = []
        output.append("=" * 60)
        output.append("STATISTICAL ANALYSIS REPORT")
        output.append("=" * 60)
        output.append("")
        output.append(f"Total Rows: {stats['total_rows']:,}")
        output.append(f"Total Columns: {stats['total_columns']}")
        output.append(f"Numeric Columns: {stats['numeric_columns']}")
        output.append(f"Memory Usage: {stats['memory_usage']:.2f} MB")
        output.append("")
        output.append("=" * 60)
        output.append("COLUMN STATISTICS")
        output.append("=" * 60)
        
        for col_name, col_stats in stats['column_stats'].items():
            output.append("")
            output.append(f"Column: {col_name}")
            output.append(f"  Mean:    {col_stats['mean']:.4f}")
            output.append(f"  Std Dev: {col_stats['std']:.4f}")
            output.append(f"  Min:     {col_stats['min']:.4f}")
            output.append(f"  Max:     {col_stats['max']:.4f}")
            output.append(f"  Median:  {col_stats['median']:.4f}")
            output.append(f"  Missing: {col_stats['missing']}")
        
        self.results_text.setText("\n".join(output))
    
    def _refresh(self):
        """Refresh the analysis."""
        if self.file_path:
            self.analyze_file(self.file_path)


def create_statistics_widget(file_path: Optional[Path] = None) -> Optional[QWidget]:
    """Create an embeddable statistics widget.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        StatisticsWidget instance or None if creation fails
    """
    try:
        return StatisticsWidget(file_path)
    except Exception as e:
        print(f"Error creating statistics widget: {e}")
        return None


def run_standalone(file_path: Optional[Path] = None):
    """Run the statistics tool as a standalone window."""
    from PyQt5.QtWidgets import QApplication, QMainWindow
    import sys
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Data Statistics")
    window.setMinimumSize(600, 500)
    
    widget = StatisticsWidget(file_path)
    window.setCentralWidget(widget)
    
    window.show()
    
    if not QApplication.instance():
        sys.exit(app.exec_())


# Convenience alias
run = run_standalone
```

### Step 2: Register in Toolkit

Edit `industrial_data_system/Integrations/toolkit.py`:

```python
"""Convenience accessors for AI tooling used across applications."""

from industrial_data_system.Integrations.analysis.data_study import run as run_ai_data_study
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import run as run_anomaly_detector
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import run_standalone as run_anomaly_detector_standalone
from industrial_data_system.Integrations.anomaly_detection.anomaly_detector import create_anomaly_widget
from industrial_data_system.Integrations.training.simulator import run as run_training_simulation
from industrial_data_system.Integrations.visualization.plotter import run as run_plotter
from industrial_data_system.Integrations.visualization.plotter import create_plotter_widget

# ADD YOUR NEW TOOL HERE
from industrial_data_system.Integrations.analysis.statistics import run_standalone as run_statistics
from industrial_data_system.Integrations.analysis.statistics import create_statistics_widget

__all__ = [
    "run_ai_data_study",
    "run_plotter",
    "run_training_simulation",
    "run_anomaly_detector",
    "run_anomaly_detector_standalone",
    "create_plotter_widget",
    "create_anomaly_widget",
    # ADD TO EXPORTS
    "run_statistics",
    "create_statistics_widget",
]
```

### Step 3: Add Button to Reader Dashboard

Edit `industrial_data_system/apps/desktop/reader.py`:

```python
# At the top, update imports
from industrial_data_system.Integrations.toolkit import (
    run_anomaly_detector_standalone,
    create_plotter_widget,
    create_statistics_widget,  # ADD THIS
)

class ReaderDashboard(QWidget):
    def __init__(self):
        # ... existing code ...
        
        # Find the tools panel section (around line 430)
        self.plotter_button = QPushButton("Plotter")
        self.plotter_button.setProperty("secondary", True)
        self.plotter_button.clicked.connect(lambda: self._launch_tool("Plotter", create_plotter_widget, True))
        tools_layout.addWidget(self.plotter_button)

        self.anomaly_button = QPushButton("Anomaly Detector")
        self.anomaly_button.setProperty("secondary", True)
        self.anomaly_button.clicked.connect(lambda: self._launch_tool("Anomaly Detector", run_anomaly_detector_standalone, False))
        tools_layout.addWidget(self.anomaly_button)
        
        # ADD YOUR NEW BUTTON HERE
        self.statistics_button = QPushButton("Statistics")
        self.statistics_button.setProperty("secondary", True)
        self.statistics_button.clicked.connect(lambda: self._launch_tool("Statistics", create_statistics_widget, True))
        tools_layout.addWidget(self.statistics_button)
```

### Step 4: Test Your New Tool

```bash
python industrial_data_system/main.py
```

1. Login to reader
2. Select a file
3. Click "Statistics" button
4. View the statistical analysis

---

## 4. Example 3: Add a New Database Table

### Goal: Add a "favorites" table to track user's favorite files

### Step 1: Update Database Schema

Edit `industrial_data_system/core/database.py`:

```python
def initialise(self) -> None:
    with self.connection() as connection:
        _apply_pragma(connection)
        connection.executescript(
            """
            -- ... existing tables ...
            
            -- ADD YOUR NEW TABLE HERE
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                added_at TEXT DEFAULT (datetime('now')),
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, file_path)
            );
            
            CREATE INDEX IF NOT EXISTS idx_favorites_user 
            ON favorites(user_id);
            """
        )
```

### Step 2: Add Database Operations

Edit `industrial_data_system/core/db_manager.py`:

```python
# Add a dataclass for the record
@dataclass
class FavoriteRecord:
    id: int
    user_id: int
    file_path: str
    file_name: str
    added_at: str
    notes: Optional[str]


class DatabaseManager:
    # ... existing code ...
    
    # ADD YOUR NEW METHODS HERE
    
    def add_favorite(
        self,
        user_id: int,
        file_path: str,
        file_name: str,
        notes: Optional[str] = None
    ) -> FavoriteRecord:
        """Add a file to user's favorites."""
        with self.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO favorites (user_id, file_path, file_name, notes)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, file_path, file_name, notes)
            )
            favorite_id = cursor.lastrowid
            cursor.execute("SELECT * FROM favorites WHERE id = ?", (favorite_id,))
            row = cursor.fetchone()
            cursor.close()
        
        if row is None:
            raise RuntimeError("Failed to create favorite")
        
        return self._row_to_favorite(row)
    
    def remove_favorite(self, user_id: int, file_path: str) -> None:
        """Remove a file from user's favorites."""
        self._execute(
            "DELETE FROM favorites WHERE user_id = ? AND file_path = ?",
            (user_id, file_path)
        )
    
    def get_user_favorites(self, user_id: int) -> List[FavoriteRecord]:
        """Get all favorites for a user."""
        rows = self._execute(
            """
            SELECT * FROM favorites 
            WHERE user_id = ? 
            ORDER BY added_at DESC
            """,
            (user_id,),
            fetchall=True
        )
        
        if not rows:
            return []
        
        return [self._row_to_favorite(row) for row in rows]
    
    def is_favorite(self, user_id: int, file_path: str) -> bool:
        """Check if a file is in user's favorites."""
        row = self._execute(
            "SELECT id FROM favorites WHERE user_id = ? AND file_path = ?",
            (user_id, file_path),
            fetchone=True
        )
        return row is not None
    
    def _row_to_favorite(self, row) -> FavoriteRecord:
        """Convert database row to FavoriteRecord."""
        return FavoriteRecord(
            id=row["id"],
            user_id=row["user_id"],
            file_path=row["file_path"],
            file_name=row["file_name"],
            added_at=row["added_at"],
            notes=row["notes"]
        )
```

### Step 3: Add UI for Favorites

In `reader.py`, add a "Add to Favorites" button:

```python
class ReaderDashboard(QWidget):
    def __init__(self):
        # ... existing code ...
        
        # Add favorite button
        self.favorite_button = QPushButton("⭐ Add to Favorites")
        self.favorite_button.setProperty("secondary", True)
        self.favorite_button.setEnabled(False)
        self.favorite_button.clicked.connect(self._toggle_favorite)
        preview_layout.addWidget(self.favorite_button)
    
    def _toggle_favorite(self):
        """Add or remove file from favorites."""
        if not self._current_resource:
            return
        
        # Get current user from parent ReaderApp
        user_id = self.parent().current_user.id if hasattr(self.parent(), 'current_user') else None
        if not user_id:
            QMessageBox.warning(self, "Favorites", "User not logged in")
            return
        
        db_manager = self.parent().db_manager
        file_path = str(self._current_resource.absolute_path)
        
        # Check if already favorite
        if db_manager.is_favorite(user_id, file_path):
            # Remove from favorites
            db_manager.remove_favorite(user_id, file_path)
            self.favorite_button.setText("⭐ Add to Favorites")
            QMessageBox.information(self, "Favorites", "Removed from favorites")
        else:
            # Add to favorites
            db_manager.add_favorite(
                user_id=user_id,
                file_path=file_path,
                file_name=self._current_resource.name
            )
            self.favorite_button.setText("★ Remove from Favorites")
            QMessageBox.information(self, "Favorites", "Added to favorites")
    
    def _handle_selection(self, current, _):
        """Update favorite button when selection changes."""
        # ... existing code ...
        
        if resource:
            self._current_resource = resource
            self.download_button.setEnabled(True)
            self.favorite_button.setEnabled(True)
            
            # Update button text based on favorite status
            user_id = self.parent().current_user.id if hasattr(self.parent(), 'current_user') else None
            if user_id:
                db_manager = self.parent().db_manager
                if db_manager.is_favorite(user_id, str(resource.absolute_path)):
                    self.favorite_button.setText("★ Remove from Favorites")
                else:
                    self.favorite_button.setText("⭐ Add to Favorites")
```

---

## 5. Example 4: Add a New File Type Support

### Goal: Add support for Excel (.xlsx) files

### Step 1: Add Loading Function

Edit `industrial_data_system/utils/asc_utils.py`:

```python
def load_and_process_excel_file(file_name: str) -> pd.DataFrame:
    """Load Excel file and return DataFrame.
    
    Args:
        file_name: Path to the Excel file
        
    Returns:
        DataFrame with the Excel data
    """
    try:
        # Read Excel file (first sheet by default)
        df = pd.read_excel(file_name, engine='openpyxl')
        
        # Fill NaN to maintain consistency
        df = df.fillna(0.0)
        
        logging.info(f"Successfully loaded Excel file. Shape: {df.shape}")
        logging.info(f"Columns: {df.columns.tolist()}")
        
        return df
        
    except Exception as e:
        logging.error(f"Error loading Excel file: {str(e)}")
        raise
```

### Step 2: Update File Preview Logic

In `reader.py`, update the preview function:

```python
def _preview_file(self, resource: LocalResource):
    """Preview the selected file."""
    file_path = resource.absolute_path
    suffix = file_path.suffix.lower()
    
    # ... existing code for other file types ...
    
    # ADD EXCEL SUPPORT
    elif suffix in ['.xlsx', '.xls']:
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            
            # Show in table
            self._show_table(df)
            self.table_preview.show()
            self.image_preview.hide()
            self.text_preview.hide()
            self.message_label.hide()
            
        except Exception as e:
            self._show_message(f"Error loading Excel file: {str(e)}")
```

### Step 3: Update File Type Detection

```python
# In the populate() function or wherever file types are determined
file_type = resource.absolute_path.suffix.replace(".", "").upper()

# Map common extensions
type_mapping = {
    'XLSX': 'Excel',
    'XLS': 'Excel',
    'ASC': 'ASC',
    'PARQUET': 'Parquet',
    'CSV': 'CSV'
}

display_type = type_mapping.get(file_type, file_type)
```

---

## 6. Best Practices

### Code Organization

1. **One feature per file** - Don't cram everything into one file
2. **Use descriptive names** - `calculate_statistics()` not `calc()`
3. **Add docstrings** - Explain what functions do
4. **Keep functions small** - Each function should do one thing

### Error Handling

```python
def my_function():
    try:
        # Your code here
        result = do_something()
        return result
    except SpecificException as e:
        # Handle specific errors
        logging.error(f"Specific error: {e}")
        QMessageBox.warning(self, "Error", str(e))
    except Exception as e:
        # Catch-all for unexpected errors
        logging.error(f"Unexpected error: {e}")
        QMessageBox.critical(self, "Error", f"Unexpected error: {str(e)}")
```

### UI/UX Guidelines

1. **Disable buttons when not applicable**
2. **Show loading indicators for long operations**
3. **Provide clear error messages**
4. **Use consistent styling** (IndustrialTheme)
5. **Add tooltips for complex features**

```python
button.setToolTip("Click to export the current file to CSV format")
```

### Database Best Practices

1. **Always use transactions for writes**
2. **Add indexes for frequently queried columns**
3. **Use foreign keys for relationships**
4. **Handle unique constraints**

---

## 7. Testing Your Changes

### Manual Testing Checklist

- [ ] Feature works as expected
- [ ] Error cases are handled gracefully
- [ ] UI updates correctly
- [ ] No console errors
- [ ] Works with different file types
- [ ] Works for different users
- [ ] Database changes persist after restart

### Testing Commands

```bash
# Run the application
python industrial_data_system/main.py

# Check for Python errors
python -m py_compile industrial_data_system/apps/desktop/reader.py

# Run with verbose logging
python industrial_data_system/main.py --verbose
```

### Debugging Tips

```python
# Add print statements
print(f"DEBUG: Variable value = {my_variable}")

# Use logging
import logging
logging.info(f"Function called with: {param}")
logging.error(f"Error occurred: {error}")

# Inspect objects
print(f"Object type: {type(obj)}")
print(f"Object attributes: {dir(obj)}")
```

---

## 🎓 Quick Reference

### Adding a Button
1. Create button in `__init__`
2. Connect to handler: `button.clicked.connect(self.handler)`
3. Create handler function
4. Enable/disable based on state

### Adding a Tool
1. Create module in `Integrations/`
2. Add to `toolkit.py`
3. Add button in reader
4. Connect button to tool

### Adding Database Table
1. Update schema in `database.py`
2. Add operations in `db_manager.py`
3. Use in your feature

### Adding File Type
1. Add loader in `utils/asc_utils.py`
2. Update preview logic
3. Update file type detection

---

## 📚 Summary

**The Process:**
1. **Plan** - What are you adding? Where does it fit?
2. **Code** - Write the functionality
3. **Integrate** - Connect to existing systems
4. **Test** - Make sure it works
5. **Document** - Add comments and docstrings

**Remember:**
- Start small and test often
- Follow existing patterns
- Handle errors gracefully
- Keep code organized
- Ask for help when stuck!

---

## 🔗 Related Files

- `GUI_EVENT_FLOW_EXPLANATION.md` - Understanding the event system
- `industrial_data_system/apps/desktop/reader.py` - Main reader app
- `industrial_data_system/core/db_manager.py` - Database operations
- `industrial_data_system/Integrations/toolkit.py` - AI tools registry
