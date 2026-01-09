# Feature Development Flowchart

## 🎯 Decision Tree: Where Should I Add My Feature?

```
START: I want to add a new feature
│
├─ Is it a UI element (button, panel, dialog)?
│  │
│  YES → Go to apps/desktop/
│  │     │
│  │     ├─ Reader-related? → reader.py
│  │     └─ Uploader-related? → uploader.py
│  │
│  NO → Continue
│
├─ Is it an AI tool or analysis feature?
│  │
│  YES → Go to Integrations/
│  │     │
│  │     ├─ Data analysis? → Integrations/analysis/
│  │     ├─ Anomaly detection? → Integrations/anomaly_detection/
│  │     ├─ Model training? → Integrations/training/
│  │     └─ Visualization? → Integrations/visualization/
│  │
│  NO → Continue
│
├─ Is it database-related (new table, queries)?
│  │
│  YES → Go to core/
│  │     │
│  │     ├─ New table schema? → core/database.py
│  │     └─ Database operations? → core/db_manager.py
│  │
│  NO → Continue
│
├─ Is it file processing (loading, converting)?
│  │
│  YES → Go to utils/asc_utils.py
│  │
│  NO → Continue
│
└─ Is it configuration or settings?
   │
   YES → Go to core/config.py
   │
   NO → Ask for help! 😊
```

---

## 🔄 Development Workflow

```
1. PLAN
   │
   ├─ What does the feature do?
   ├─ Where does it fit in the architecture?
   ├─ What files need to be modified?
   └─ What dependencies are needed?
   │
   ↓
2. CREATE
   │
   ├─ Write the core functionality
   ├─ Add error handling
   ├─ Add logging
   └─ Write docstrings
   │
   ↓
3. INTEGRATE
   │
   ├─ Connect to UI (if needed)
   ├─ Register in toolkit (if AI tool)
   ├─ Add database operations (if needed)
   └─ Update imports
   │
   ↓
4. TEST
   │
   ├─ Run the application
   ├─ Test happy path
   ├─ Test error cases
   ├─ Test edge cases
   └─ Check console for errors
   │
   ↓
5. DOCUMENT
   │
   ├─ Add code comments
   ├─ Update docstrings
   ├─ Add tooltips (UI)
   └─ Update README (if major feature)
   │
   ↓
6. DONE! 🎉
```

---

## 🏗️ Common Feature Patterns

### Pattern 1: Add a Button with Action

```
Step 1: Create Button
   ↓
Step 2: Connect Signal
   ↓
Step 3: Create Handler
   ↓
Step 4: Implement Logic
   ↓
Step 5: Update UI State
```

**Example:**
```python
# Step 1: Create
self.my_button = QPushButton("Do Something")

# Step 2: Connect
self.my_button.clicked.connect(self.do_something)

# Step 3 & 4: Handler + Logic
def do_something(self):
    try:
        result = perform_action()
        # Step 5: Update UI
        self.show_success(result)
    except Exception as e:
        self.show_error(str(e))
```

---

### Pattern 2: Add an AI Tool

```
Step 1: Create Tool Module
   ↓
Step 2: Implement Widget Class
   ↓
Step 3: Add create_widget() function
   ↓
Step 4: Add run_standalone() function
   ↓
Step 5: Register in toolkit.py
   ↓
Step 6: Add Button in Reader
   ↓
Step 7: Connect Button to Tool
```

**File Structure:**
```
Integrations/
└── my_tool/
    ├── __init__.py
    └── my_tool.py  ← Your tool code
```

---

### Pattern 3: Add Database Feature

```
Step 1: Design Table Schema
   ↓
Step 2: Add CREATE TABLE in database.py
   ↓
Step 3: Create Dataclass for Record
   ↓
Step 4: Add CRUD Methods in db_manager.py
   │
   ├─ create_*()
   ├─ get_*()
   ├─ update_*()
   └─ delete_*()
   ↓
Step 5: Add _row_to_*() converter
   ↓
Step 6: Use in Your Feature
```

---

### Pattern 4: Add File Type Support

```
Step 1: Add Loader Function
   ↓
Step 2: Update File Type Detection
   ↓
Step 3: Update Preview Logic
   ↓
Step 4: Update Export Logic (if needed)
   ↓
Step 5: Test with Sample Files
```

---

## 🎨 UI Component Hierarchy

```
QMainWindow (ReaderApp)
│
└── QStackedWidget (page switcher)
    │
    ├── Page 0: Login
    │   └── QWidget (ReaderLoginPage)
    │       ├── QLineEdit (email)
    │       ├── QLineEdit (password)
    │       ├── QLineEdit (security code)
    │       └── QPushButton (login)
    │
    └── Page 1: Dashboard
        └── QWidget (ReaderDashboard)
            ├── QLabel (header)
            ├── QPushButton (logout)
            │
            └── QSplitter (left/right split)
                │
                ├── LEFT: Tree Panel
                │   ├── QLabel (title)
                │   └── QTreeWidget (file tree)
                │       └── QTreeWidgetItem (files/folders)
                │
                └── RIGHT: Preview Panel
                    ├── Preview Area
                    │   ├── QLabel (image preview)
                    │   ├── QPlainTextEdit (text preview)
                    │   └── QTableWidget (table preview)
                    │
                    ├── Tools Panel
                    │   ├── QPushButton (Plotter)
                    │   ├── QPushButton (Anomaly Detector)
                    │   └── QPushButton (Your New Tool)
                    │
                    └── Action Buttons
                        ├── QPushButton (Download)
                        └── QPushButton (Your New Button)
```

---

## 🔌 Signal/Slot Connection Patterns

### Pattern A: Direct Connection
```python
button.clicked.connect(self.handler)
```

### Pattern B: Lambda with Parameters
```python
button.clicked.connect(lambda: self.handler("param1", 123))
```

### Pattern C: Custom Signal
```python
# Define signal
my_signal = pyqtSignal(str, int)

# Emit signal
self.my_signal.emit("data", 42)

# Connect signal
widget.my_signal.connect(self.handle_signal)
```

### Pattern D: Multiple Connections
```python
# One signal → multiple slots
button.clicked.connect(self.handler1)
button.clicked.connect(self.handler2)

# Multiple signals → one slot
button1.clicked.connect(self.common_handler)
button2.clicked.connect(self.common_handler)
```

---

## 📦 Module Import Pattern

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict

# Third-party
import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QWidget, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

# Local imports - absolute paths
from industrial_data_system.core.db_manager import DatabaseManager
from industrial_data_system.utils.asc_utils import load_and_process_asc_file
from industrial_data_system.Integrations.toolkit import create_plotter_widget
```

---

## 🐛 Debugging Checklist

When something doesn't work:

```
□ Check console for error messages
□ Verify imports are correct
□ Check if signal is connected
□ Verify function is being called (add print)
□ Check if button is enabled
□ Verify data is not None
□ Check file paths are correct
□ Verify database connection
□ Check for typos in variable names
□ Restart the application
```

---

## 📝 Code Review Checklist

Before considering your feature "done":

```
□ Code follows existing patterns
□ Error handling is in place
□ Logging is added for important actions
□ Docstrings are written
□ UI elements are properly styled
□ Buttons are enabled/disabled correctly
□ Feature works with different inputs
□ No hardcoded paths or values
□ Code is commented where complex
□ Feature has been tested manually
```

---

## 🚀 Quick Start Templates

### Template 1: New Button
```python
# In __init__
self.my_button = QPushButton("My Action")
self.my_button.setProperty("primary", True)  # or "secondary"
self.my_button.setEnabled(False)
self.my_button.clicked.connect(self.my_handler)
layout.addWidget(self.my_button)

# Handler
def my_handler(self):
    """Handle button click."""
    try:
        # Your logic here
        result = do_something()
        QMessageBox.information(self, "Success", f"Done: {result}")
    except Exception as e:
        QMessageBox.critical(self, "Error", str(e))
```

### Template 2: New Tool Widget
```python
class MyToolWidget(QWidget):
    def __init__(self, file_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self._init_ui()
        
        if file_path:
            self.process_file(file_path)
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Add your UI elements
        self.result_label = QLabel("Results will appear here")
        layout.addWidget(self.result_label)
        
        self.action_button = QPushButton("Process")
        self.action_button.clicked.connect(self.process)
        layout.addWidget(self.action_button)
    
    def process_file(self, file_path: Path):
        """Process the file."""
        try:
            # Your processing logic
            result = analyze_file(file_path)
            self.result_label.setText(f"Result: {result}")
        except Exception as e:
            self.result_label.setText(f"Error: {e}")

def create_my_tool_widget(file_path: Optional[Path] = None):
    """Factory function for creating the widget."""
    return MyToolWidget(file_path)
```

### Template 3: Database Operations
```python
# In db_manager.py

def create_my_record(self, **kwargs) -> MyRecord:
    """Create a new record."""
    with self.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO my_table (col1, col2) VALUES (?, ?)",
            (kwargs['col1'], kwargs['col2'])
        )
        record_id = cursor.lastrowid
        cursor.execute("SELECT * FROM my_table WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        cursor.close()
    
    return self._row_to_my_record(row)

def get_my_records(self, filter_value: str) -> List[MyRecord]:
    """Get records matching filter."""
    rows = self._execute(
        "SELECT * FROM my_table WHERE col1 = ? ORDER BY created_at DESC",
        (filter_value,),
        fetchall=True
    )
    
    if not rows:
        return []
    
    return [self._row_to_my_record(row) for row in rows]

def _row_to_my_record(self, row) -> MyRecord:
    """Convert database row to record object."""
    return MyRecord(
        id=row["id"],
        col1=row["col1"],
        col2=row["col2"],
        created_at=row["created_at"]
    )
```

---

## 🎯 Summary

**Remember the 3 Key Questions:**
1. **What** am I building?
2. **Where** does it go?
3. **How** do I connect it?

**Follow the Pattern:**
1. Look at existing similar features
2. Copy the structure
3. Modify for your needs
4. Test thoroughly

**When Stuck:**
1. Check the error message
2. Review similar code
3. Add debug prints
4. Test in small steps
5. Ask for help!

Good luck with your development! 🚀
