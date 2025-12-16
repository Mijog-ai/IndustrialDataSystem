
# Industrial Data System (Shared Drive Edition)

This repository contains two PyQt5 desktop applications for managing
industrial test data. The Upload App allows operators to preview CSV/Excel
files and publish them to a shared network drive, while the Reader App provides
read-only access to the stored files with inline previews and download tools.
Both applications now rely on a central SQLite database for authentication and
metadata tracking—no cloud services are required.

## Features

- **Shared drive storage** – Files are organised under `<pump_series>/tests/<test_type>`
  on a configurable network share. The application gracefully handles drive
  availability checks, pump series hierarchies, and name collisions.
- **SQLite-backed authentication** – Uploaders and readers share a single
  credential store managed through `DatabaseManager`. Passwords are hashed with
  per-user salts.
- **Rich upload workflow** – CSV and Excel files are previewed in-app before
  being copied to the shared drive. Upload history (including file size and
  test type) is automatically recorded.
- **Reader experience** – The Reader App browses the shared drive hierarchy,
  previews images and text-based files locally, and lets users copy or download
  artefacts without leaving the network.
- **Environment-driven configuration** – Paths and storage limits are managed
  through a `.env` file interpreted by `industrial_data_system/core/config.py`.

## Repository Layout

The source code is organised into a Python package to separate the UI, core
services, and command-line utilities:

- `industrial_data_system/apps/` – PyQt5 desktop applications (upload and reader).
- `industrial_data_system/core/` – Shared services including configuration,
  database access, authentication, and storage helpers.
- `industrial_data_system/cli/` – Administrative and migration scripts that can
  be launched with `python -m industrial_data_system.cli.<module>`.

Legacy Flask dashboard assets have been removed so the repository now focuses
solely on the PyQt5 desktop tools and shared services.
- `main.py` – Lightweight launcher that lets operators open either desktop app.

## Prerequisites

- Python 3.12+
- Access to the shared drive defined in your `.env`
- Optional: PyInstaller for packaging the applications

## Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file (or edit the one provided) with values that match your
   environment. Example:

   ```ini
   SHARED_DRIVE_PATH=\\\\SharedDrive\\IndustrialData
   # Linux/Mac alternative:
   # SHARED_DRIVE_PATH=/mnt/shared/IndustrialData
   DATABASE_PATH=\\\\SharedDrive\\IndustrialData\\database\\industrial_data.db
   FILES_BASE_PATH=\\\\SharedDrive\\IndustrialData\\files
   STORAGE_LIMIT_MB=10240
   ```

   | Variable | Description |
   | --- | --- |
   | `SHARED_DRIVE_PATH` | Root of the network share used for both the database and files. |
   | `DATABASE_PATH` | Full path to the SQLite database file. |
   | `FILES_BASE_PATH` | Directory where uploaded files are stored. |
   | `STORAGE_LIMIT_MB` | Maximum total storage (in MB) allowed for uploads. |

3. **Launch the gateway**
   ```bash
   python main.py
   ```
   The launcher window lets you open either the Upload App or the Reader App.

## Usage

### Upload App

1. Sign up or sign in using the Upload tab. Accounts are stored in the SQLite
   database—passwords remain local.
2. Choose a pump series and then a test type from the dashboard. Create new
   pump series or test types to generate the matching folder structure on the
   shared drive.
3. Select a CSV or Excel file. The preview panel displays up to the first 100
   rows before uploading.
4. On upload, the file is copied to the shared drive, metadata is recorded in
   the database, and the dashboard lists the new entry. The table offers quick
   access to open the file, open its folder, copy the path, or view properties.

### Reader App

1. Sign in with a reader account (the default security code remains `123321`).
2. The tree view mirrors the shared drive hierarchy. Selecting a file shows an
   inline preview for images or text-based formats, and the Download button
   copies the file to a user-selected location.
3. Reader accounts can be created from the login screen or managed through the
   admin tools described below.

## Migration and Test Utilities

- **`industrial_data_system/cli/migrate_auth.py`** – Imports existing JSON credential and upload history
  files into the SQLite database while leaving timestamped backups.
- **`industrial_data_system/cli/migrate_data.py`** – Replays legacy upload history and optionally copies
  files from an exported directory into the new shared-drive structure.
- **`industrial_data_system/cli/setup_test_data.py`** – Generates sample users, test types, and files for
  local testing.

## Administrative Helpers

`industrial_data_system/cli/admin.py` provides several maintenance commands:

```bash
python -m industrial_data_system.cli.admin backup-db [--output PATH]
python -m industrial_data_system.cli.admin restore-db PATH
python -m industrial_data_system.cli.admin list-users
python -m industrial_data_system.cli.admin storage-report
```

These commands create database backups, restore from snapshots, list users, and
report on shared-drive usage.

## Packaging with PyInstaller

A refreshed `IndustrialDataSystem.spec` is included. It removes Cloudinary
hooks and bundles the `.env` file. Build the executable with:

```bash
pyinstaller IndustrialDataSystem.spec
```

Ensure the shared drive is accessible when launching the packaged application.

## Testing

Before distributing a build, run a quick byte-compilation check to catch syntax
errors:

```bash
python -m compileall .
```

For a full end-to-end verification, exercise the upload and reader workflows
against a real shared drive to confirm connectivity, preview rendering, and the
database migration scripts.

## Development Setup

### Prerequisites for Development

- Python 3.12+
- Git
- Access to the shared drive defined in your `.env`

### Setting Up Development Environment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd IndustrialDataSystem
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # Install production dependencies
   pip install -r requirements.txt

   # Install development dependencies
   pip install -r requirements-dev.txt
   ```

4. **Set up pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Code Quality Tools

This project uses multiple tools to maintain code quality:

#### Code Formatting

- **Black**: Automatic code formatting
  ```bash
  black industrial_data_system/
  ```

- **isort**: Import statement sorting
  ```bash
  isort industrial_data_system/
  ```

- **autoflake**: Remove unused imports and variables
  ```bash
  autoflake --in-place --remove-all-unused-imports -r industrial_data_system/
  ```

#### Linting

- **Flake8**: Style guide enforcement
  ```bash
  flake8 industrial_data_system/
  ```

- **Pylint**: Comprehensive code analysis
  ```bash
  pylint industrial_data_system/
  ```

- **Ruff**: Fast Python linter (alternative to flake8)
  ```bash
  ruff check industrial_data_system/
  ```

#### Type Checking

- **mypy**: Static type checking
  ```bash
  mypy industrial_data_system/
  ```

#### Security Scanning

- **Bandit**: Security issue detection
  ```bash
  bandit -r industrial_data_system/
  ```

- **Safety**: Dependency vulnerability scanning
  ```bash
  safety check --json
  ```

### Running All Checks

Run all quality checks before committing:

```bash
# Format code
black industrial_data_system/
isort industrial_data_system/

# Run linters
flake8 industrial_data_system/
pylint industrial_data_system/
ruff check industrial_data_system/

# Type checking
mypy industrial_data_system/

# Security checks
bandit -r industrial_data_system/

# Run tests (when available)
pytest tests/
```

Or use pre-commit to run all checks:

```bash
pre-commit run --all-files
```

### Configuration Files

- `pyproject.toml`: Configuration for Black, isort, mypy, pytest, coverage, and pylint
- `.flake8`: Flake8 configuration
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `requirements-dev.txt`: Development dependencies

### Development Workflow

1. Create a new branch for your feature/fix
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure code quality
   ```bash
   # Format and check code
   black industrial_data_system/
   isort industrial_data_system/
   pre-commit run --all-files
   ```

3. Run tests (when available)
   ```bash
   pytest tests/
   ```

4. Commit your changes
   ```bash
   git add .
   git commit -m "Your descriptive commit message"
   ```

   Pre-commit hooks will automatically run and fix issues before the commit.

5. Push to your branch
   ```bash
   git push origin feature/your-feature-name
   ```

### Continuous Integration

Pre-commit hooks will automatically run on every commit to ensure:
- Code is properly formatted (Black, isort)
- No linting errors (Flake8, Ruff, Pylint)
- Type hints are correct (mypy)
- No security issues (Bandit, Safety)
- No secrets in code (detect-secrets)
- Documentation standards met (pydocstyle)

### IDE Setup

#### VS Code

Recommended extensions:
- Python (Microsoft)
- Pylance
- Ruff
- Black Formatter
- isort

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "python.sortImports.args": ["--profile", "black"],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. Enable Black formatter: Settings → Tools → Black → Enable
2. Enable isort: Settings → Tools → External Tools → Add isort
3. Enable Flake8: Settings → Editor → Inspections → Flake8
4. Enable mypy: Settings → Editor → Inspections → Mypy

