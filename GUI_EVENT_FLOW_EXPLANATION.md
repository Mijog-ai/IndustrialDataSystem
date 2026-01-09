# GUI and Event Flow in Reader App - Beginner's Guide

## 🎯 Overview
The Reader App is a PyQt5 desktop application that lets users browse and download files. Here's how it works from start to finish.

---

## 📋 Table of Contents
1. [Application Startup](#1-application-startup)
2. [GUI Structure](#2-gui-structure)
3. [Event System (Signals & Slots)](#3-event-system-signals--slots)
4. [Data Flow](#4-data-flow)
5. [Key Functions Explained](#5-key-functions-explained)

---

## 1. Application Startup

### Entry Point (main.py)
```python
# When you run: python industrial_data_system/main.py
app = QApplication(sys.argv)  # Creates the application
reader_app = ReaderApp()      # Creates the main window
reader_app.show()             # Shows the window
sys.exit(app.exec_())         # Starts the event loop
```

### What Happens in `ReaderApp.__init__()`
```python
def __init__(self):
    # 1. Set up window properties
    self.setWindowTitle("Reader Portal")
    self.setMinimumSize(1100, 700)
    
    # 2. Initialize backend services
    self.db_manager = DatabaseManager()        # Database access
    self.storage_manager = LocalStorageManager()  # File management
    self.auth_store = LocalAuthStore()        # User authentication
    
    # 3. Create the UI pages
    self.login_page = ReaderLoginPage()       # Login screen
    self.dashboard = ReaderDashboard()        # Main dashboard
    
    # 4. Connect events (signals → slots)
    self.login_page.login_requested.connect(self.handle_login)
    self.dashboard.logout_requested.connect(self.handle_logout)
    # ... more connections
```

---

## 2. GUI Structure

### Visual Hierarchy
```
ReaderApp (Main Window)
├── QStackedWidget (switches between pages)
│   ├── ReaderLoginPage (Page 0)
│   │   ├── Email input
│   │   ├── Password input
│   │   ├── Security code input
│   │   └── Login button
│   │
│   └── ReaderDashboard (Page 1)
│       ├── Header (user info, logout button)
│       ├── QSplitter (divides left/right)
│       │   ├── LEFT: File Tree (QTreeWidget)
│       │   │   └── Shows folders and files
│       │   │
│       │   └── RIGHT: Preview Panel
│       │       ├── File preview (image/text/table)
│       │       ├── AI Tools buttons
│       │       └── Download button
│       │
│       └── Tool Tabs (QTabWidget)
│           └── Opens when you click AI tools
```

### Key Components

#### QTreeWidget (File Browser)
```python
self.tree = QTreeWidget()
self.tree.setHeaderLabels(["Name", "Type", "Series", "Path"])
# Columns:  [0]      [1]     [2]       [3]
```

#### QStackedWidget (Page Switcher)
```python
self.stack = QStackedWidget()
self.stack.addWidget(self.login_page)    # Index 0
self.stack.addWidget(self.dashboard)     # Index 1

# Switch pages:
self.stack.setCurrentWidget(self.login_page)   # Show login
self.stack.setCurrentWidget(self.dashboard)    # Show dashboard
```

---

## 3. Event System (Signals & Slots)

### What are Signals and Slots?
- **Signal**: An event that gets emitted (like "button clicked")
- **Slot**: A function that responds to the signal

### Example: Login Button Click

```python
# Step 1: Define a signal in ReaderLoginPage
class ReaderLoginPage(QWidget):
    login_requested = pyqtSignal(str, str, str)  # Signal with 3 string parameters
    
    def __init__(self):
        # Step 2: Connect button click to emit signal
        self.login_button.clicked.connect(self._on_login_clicked)
    
    def _on_login_clicked(self):
        email = self.email_input.text()
        password = self.password_input.text()
        security_code = self.security_input.text()
        
        # Step 3: Emit the signal with data
        self.login_requested.emit(email, password, security_code)

# Step 4: In ReaderApp, connect signal to handler
class ReaderApp(QMainWindow):
    def __init__(self):
        self.login_page.login_requested.connect(self.handle_login)
    
    # Step 5: Handler function (slot) receives the data
    def handle_login(self, email: str, password: str, security_code: str):
        # Authenticate user
        user = self.auth_store.authenticate(email, password)
        if user:
            self.show_dashboard()
```

### Common Event Connections

```python
# Button clicks
button.clicked.connect(function_to_call)

# Tree item selection
self.tree.currentItemChanged.connect(self._handle_selection)

# Timer events
self.timer.timeout.connect(self._check_something)

# Custom signals
self.my_signal.connect(self.my_handler)
```

---

## 4. Data Flow

### Complete Flow: From Login to Viewing Files

```
1. USER LOGS IN
   ↓
   Login button clicked
   ↓
   login_requested signal emitted
   ↓
   handle_login() called
   ↓
   Authenticate with database
   ↓
   Switch to dashboard page
   ↓
   refresh_resources() called

2. LOADING FILES
   ↓
   storage_manager.list_resources()
   ↓
   Returns list of LocalResource objects
   ↓
   dashboard.populate(resources) called
   ↓
   Creates QTreeWidgetItem for each file
   ↓
   Tree widget displays files

3. USER CLICKS FILE
   ↓
   currentItemChanged signal emitted
   ↓
   _handle_selection() called
   ↓
   Get selected file data
   ↓
   Load and preview file
   ↓
   Enable download button
```

---

## 5. Key Functions Explained

### `populate(resources)` - Fills the Tree Widget

```python
def populate(self, resources: Iterable[LocalResource]) -> None:
    """Populates the tree widget with files and folders."""
    
    self.clear()  # Clear existing items
    folders: Dict[str, QTreeWidgetItem] = {}
    root = self.tree.invisibleRootItem()
    
    for resource in resources:
        # Build folder structure
        parent = root
        path_so_far: List[str] = []
        parts = list(resource.relative_path.parts)
        
        # Create folder items
        for folder_name in parts[:-1]:
            path_so_far.append(folder_name)
            path_key = "/".join(path_so_far)
            
            if path_key not in folders:
                # Create new folder item
                folder_item = QTreeWidgetItem(
                    [folder_name, "Folder", "", "/".join(path_so_far[:-1])]
                    # [Name,       Type,     Series, Path]
                )
                folder_item.setData(0, Qt.UserRole, {"type": "folder"})
                parent.addChild(folder_item)
                folders[path_key] = folder_item
            
            parent = folders[path_key]
        
        # Create file item
        file_item = QTreeWidgetItem(
            [
                resource.display_name,    # Column 0: Name
                resource.absolute_path.suffix.replace(".", "").upper() or "File",  # Column 1: Type (ASC, CSV, etc.)
                resource.pump_series,     # Column 2: Series
                resource.folder,          # Column 3: Path
            ]
        )
        file_item.setData(0, Qt.UserRole, {"type": "file", "resource": resource})
        parent.addChild(file_item)
    
    self.tree.expandAll()
```

**What this does:**
1. Takes a list of file resources
2. Creates folder hierarchy in the tree
3. Adds each file under its folder
4. Stores file data in each item using `setData()`

### `_handle_selection()` - When User Clicks a File

```python
def _handle_selection(
    self, current: Optional[QTreeWidgetItem], _: Optional[QTreeWidgetItem]
) -> None:
    """Called when user selects an item in the tree."""
    
    if not current:
        self._current_resource = None
        self.download_button.setEnabled(False)
        self._show_message("Select a file to preview")
        return
    
    # Get stored data from the item
    data = current.data(0, Qt.UserRole)
    
    if data.get("type") == "folder":
        # It's a folder, not a file
        self._show_message("Select a file to preview")
        return
    
    # It's a file - get the resource object
    resource = data.get("resource")
    if resource:
        self._current_resource = resource
        self.download_button.setEnabled(True)
        self._preview_file(resource)
```

**What this does:**
1. Gets called automatically when tree selection changes
2. Retrieves the stored data from the selected item
3. Checks if it's a file or folder
4. Enables download button and shows preview

### Event Connection Pattern

```python
# Pattern 1: Direct connection
button.clicked.connect(self.my_function)

# Pattern 2: Lambda for parameters
button.clicked.connect(lambda: self.my_function("param1", "param2"))

# Pattern 3: Custom signal
class MyWidget(QWidget):
    my_signal = pyqtSignal(str, int)  # Define signal
    
    def some_action(self):
        self.my_signal.emit("hello", 42)  # Emit signal

# In parent:
widget.my_signal.connect(self.handle_signal)

def handle_signal(self, text: str, number: int):
    print(f"Received: {text}, {number}")
```

---

## 🎓 Quick Reference

### Adding a New Button with Event

```python
# 1. Create button
my_button = QPushButton("Click Me")

# 2. Connect to function
my_button.clicked.connect(self.on_button_clicked)

# 3. Define handler
def on_button_clicked(self):
    print("Button was clicked!")
    # Do something...
```

### Adding Items to Tree

```python
# Create item with columns
item = QTreeWidgetItem(["Name", "Type", "Info"])

# Store custom data
item.setData(0, Qt.UserRole, {"my_data": "value"})

# Add to tree
self.tree.addTopLevelItem(item)

# Or add as child
parent_item.addChild(item)
```

### Switching Pages

```python
# Add pages to stack
self.stack.addWidget(page1)  # Index 0
self.stack.addWidget(page2)  # Index 1

# Switch to page
self.stack.setCurrentWidget(page1)
# or
self.stack.setCurrentIndex(0)
```

---

## 🔍 Debugging Tips

1. **Print statements**: Add `print()` to see when functions are called
   ```python
   def handle_login(self, email, password, code):
       print(f"Login called with email: {email}")
   ```

2. **Check signal connections**: Make sure signals are connected
   ```python
   print(f"Signal connected: {self.button.clicked.receivers(self.button.clicked)}")
   ```

3. **Inspect tree items**: See what data is stored
   ```python
   item = self.tree.currentItem()
   print(f"Item data: {item.data(0, Qt.UserRole)}")
   ```

---

## 📚 Summary

1. **Application starts** → Creates main window → Shows login page
2. **User interacts** → Events (signals) are emitted
3. **Signals connected to slots** → Handler functions are called
4. **Handlers update UI** → Changes are displayed
5. **Event loop continues** → Waits for next interaction

The key concept: **Everything is event-driven**. User actions trigger signals, which call functions, which update the UI.
