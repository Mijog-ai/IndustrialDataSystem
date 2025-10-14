
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

- Python 3.10+
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

