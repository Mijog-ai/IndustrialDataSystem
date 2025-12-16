# Code Quality Guidelines

This document outlines the code quality standards and practices for the Industrial Data System project.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Formatting](#code-formatting)
- [Type Hints](#type-hints)
- [Linting](#linting)
- [Error Handling](#error-handling)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Running Quality Checks](#running-quality-checks)

## Development Setup

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Install Pre-commit Hooks

```bash
pre-commit install
```

This will automatically run code quality checks before each commit.

## Code Formatting

### Black

We use [Black](https://black.readthedocs.io/) for code formatting with a line length of 100 characters.

**Run Black:**
```bash
black .
```

**Check without modifying:**
```bash
black --check .
```

### isort

We use [isort](https://pycqa.github.io/isort/) to sort imports alphabetically and automatically separate into sections.

**Run isort:**
```bash
isort .
```

**Check without modifying:**
```bash
isort --check-only .
```

## Type Hints

### Requirements

- **ALL functions must have type hints** for parameters and return values
- Use strict typing with mypy
- For complex types, import from `typing` module

### Examples

```python
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

def process_data(
    data: List[Dict[str, Union[int, float]]],
    threshold: float = 0.5,
    output_path: Optional[Path] = None
) -> Tuple[bool, str]:
    """Process data and return success status with message.

    Args:
        data: List of dictionaries containing numeric values
        threshold: Threshold value for filtering (default: 0.5)
        output_path: Optional path to save results

    Returns:
        Tuple of (success status, message)

    Raises:
        ValueError: If data is empty or invalid
    """
    if not data:
        raise ValueError("Data cannot be empty")

    # Processing logic here
    return True, "Processing completed successfully"
```

### Run Type Checking

```bash
mypy .
```

## Linting

### Flake8

We use [Flake8](https://flake8.pycqa.org/) for style guide enforcement.

**Run Flake8:**
```bash
flake8 .
```

### Pylint

We use [Pylint](https://pylint.org/) for comprehensive code analysis.

**Run Pylint:**
```bash
pylint industrial_data_system
```

**Run on specific file:**
```bash
pylint industrial_data_system/core/database.py
```

### Bandit

We use [Bandit](https://bandit.readthedocs.io/) for security issue detection.

**Run Bandit:**
```bash
bandit -r industrial_data_system
```

## Error Handling

### Principles

1. **Be Specific**: Catch specific exceptions, not broad `Exception`
2. **Fail Fast**: Validate inputs early and raise errors immediately
3. **Provide Context**: Include meaningful error messages
4. **Clean Up Resources**: Use context managers or try-finally
5. **Log Appropriately**: Log errors with sufficient context

### Standard Error Handling Patterns

#### Pattern 1: Input Validation

```python
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def validate_input(value: Optional[str]) -> str:
    """Validate input value.

    Args:
        value: Input value to validate

    Returns:
        Validated string value

    Raises:
        ValueError: If value is None or empty
    """
    if value is None:
        raise ValueError("Value cannot be None")

    if not value.strip():
        raise ValueError("Value cannot be empty")

    return value.strip()
```

#### Pattern 2: Resource Management

```python
from pathlib import Path
from typing import TextIO
import logging

logger = logging.getLogger(__name__)

def read_file_safely(file_path: Path) -> str:
    """Read file content with proper error handling.

    Args:
        file_path: Path to file to read

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
        IOError: For other file reading errors
    """
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File does not exist: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Successfully read file: {file_path}")
        return content
    except PermissionError as e:
        logger.error(f"Permission denied reading {file_path}: {e}")
        raise
    except IOError as e:
        logger.error(f"IO error reading {file_path}: {e}")
        raise
```

#### Pattern 3: Database Operations

```python
from typing import Optional, Dict, Any
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database operations."""
    pass

class ConnectionError(DatabaseError):
    """Exception for connection failures."""
    pass

class QueryError(DatabaseError):
    """Exception for query execution failures."""
    pass

@contextmanager
def database_connection(connection_string: str):
    """Context manager for database connections.

    Args:
        connection_string: Database connection string

    Yields:
        Database connection object

    Raises:
        ConnectionError: If connection fails
    """
    conn = None
    try:
        conn = create_connection(connection_string)
        logger.info("Database connection established")
        yield conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise ConnectionError(f"Failed to connect to database: {e}") from e
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")

def execute_query(conn: Any, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Execute database query with error handling.

    Args:
        conn: Database connection
        query: SQL query to execute
        params: Optional query parameters

    Returns:
        Query results

    Raises:
        QueryError: If query execution fails
    """
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or {})
        results = cursor.fetchall()
        logger.debug(f"Query executed successfully: {query[:50]}...")
        return results
    except Exception as e:
        logger.error(f"Query execution failed: {e}\nQuery: {query}")
        raise QueryError(f"Failed to execute query: {e}") from e
```

#### Pattern 4: API/Network Operations

```python
from typing import Dict, Any, Optional
import logging
from requests.exceptions import RequestException, Timeout, HTTPError

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API operations."""
    pass

def make_api_request(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Make API request with comprehensive error handling.

    Args:
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        data: Optional request data
        timeout: Request timeout in seconds

    Returns:
        API response as dictionary

    Raises:
        APIError: If request fails
        ValueError: If URL or method is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")

    if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
        raise ValueError(f"Invalid HTTP method: {method}")

    try:
        import requests
        response = requests.request(
            method=method,
            url=url,
            json=data,
            timeout=timeout
        )
        response.raise_for_status()
        logger.info(f"API request successful: {method} {url}")
        return response.json()

    except Timeout as e:
        logger.error(f"API request timeout: {url}")
        raise APIError(f"Request timed out after {timeout}s: {url}") from e

    except HTTPError as e:
        logger.error(f"API HTTP error {e.response.status_code}: {url}")
        raise APIError(
            f"HTTP {e.response.status_code} error: {e.response.text}"
        ) from e

    except RequestException as e:
        logger.error(f"API request failed: {url} - {e}")
        raise APIError(f"Request failed: {e}") from e
```

#### Pattern 5: GUI Error Handling (PyQt5)

```python
from typing import Callable, Any
from functools import wraps
import logging
from PyQt5.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)

def handle_gui_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for handling errors in GUI methods.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            QMessageBox.critical(
                None,
                "Error",
                f"An error occurred: {str(e)}\n\nPlease check the logs for details."
            )
            return None
    return wrapper

class MyWidget:
    @handle_gui_errors
    def on_button_click(self) -> None:
        """Handle button click with automatic error handling."""
        # This will automatically show error dialog if exception occurs
        self.process_data()
```

### Custom Exception Hierarchy

```python
class IndustrialDataSystemError(Exception):
    """Base exception for Industrial Data System."""
    pass

class ConfigurationError(IndustrialDataSystemError):
    """Exception for configuration issues."""
    pass

class DataValidationError(IndustrialDataSystemError):
    """Exception for data validation failures."""
    pass

class ProcessingError(IndustrialDataSystemError):
    """Exception for data processing failures."""
    pass

class StorageError(IndustrialDataSystemError):
    """Exception for storage operation failures."""
    pass
```

## Pre-commit Hooks

Pre-commit hooks automatically run quality checks before each commit.

### Manual Run

Run on all files:
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run black --all-files
pre-commit run flake8 --all-files
pre-commit run mypy --all-files
```

### Update Hooks

```bash
pre-commit autoupdate
```

## Running Quality Checks

### Quick Check (Format + Lint)

```bash
make check
```

or manually:
```bash
black --check .
isort --check-only .
flake8 .
mypy .
```

### Fix Formatting Issues

```bash
make format
```

or manually:
```bash
black .
isort .
```

### Full Quality Check

```bash
make quality
```

or manually:
```bash
black .
isort .
flake8 .
pylint industrial_data_system
mypy .
bandit -r industrial_data_system
```

### Security Scan

```bash
make security
```

or manually:
```bash
bandit -r industrial_data_system
safety check --full-report
```

## Continuous Integration

All code quality checks should pass before merging:

1. ✅ Black formatting
2. ✅ Import sorting (isort)
3. ✅ Flake8 linting
4. ✅ Pylint analysis
5. ✅ Type checking (mypy)
6. ✅ Security scan (bandit)
7. ✅ Tests passing with coverage

## IDE Integration

### VS Code

Add to `.vscode/settings.json`:

```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### PyCharm

1. Go to Settings → Tools → Black
2. Enable "On code reformat" and "On save"
3. Go to Settings → Editor → Inspections
4. Enable Pylint, Flake8, and Mypy

## Best Practices Summary

1. ✅ Run `pre-commit install` after cloning the repository
2. ✅ Use type hints for all functions
3. ✅ Follow the error handling patterns documented above
4. ✅ Run `make format` before committing
5. ✅ Run `make check` to verify code quality
6. ✅ Keep functions small and focused (max 50 lines)
7. ✅ Document complex logic with comments
8. ✅ Write docstrings for all public functions/classes
9. ✅ Catch specific exceptions, not broad `Exception`
10. ✅ Log errors with appropriate context
