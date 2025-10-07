# Industrial Data Upload System Using Python GUI and OneDrive

This project delivers a Tkinter-based desktop solution that allows industrial operators to upload, create, and edit production data files while storing everything in a centralized administrator-owned OneDrive hierarchy. The implementation bundles a local mock of OneDrive interactions so the application can be exercised without live credentials, while keeping interfaces ready for Microsoft Graph integration.

## Features

- **User Authentication** – Operators sign in with a user ID (and optional password) validated against `config/users_db.json`. Sessions persist for eight hours by default.
- **Centralized Storage** – A single admin connection (mocked locally) maintains the canonical `IndustrialDataSystem` folder tree with per-user directories for CSV, images, Excel files, and logs.
- **Direct Uploads** – Drag-and-drop style workflow to upload CSV, Excel, and image files directly into the operator's OneDrive space while recording metadata.
- **Excel Editing Suite** – Create spreadsheets from templates or edit existing files using an in-app grid editor backed by pandas. Save locally or upload to OneDrive in one click.
- **Metadata Tracking** – All file actions append structured records to `Metadata/upload_metadata.xlsx`, following the provided schema. Entries include upload method, timestamps, edit counts, and storage paths.
- **Quota Ready** – User profiles declare storage quotas, allowing future enforcement hooks.
- **Extensible Cloud Layer** – Cloud helpers (authentication, uploader, downloader, folder management) are encapsulated to ease replacement of the local mock with real Microsoft Graph calls.

## Project Structure

```
industrial-data-uploader/
├── config/
│   ├── settings.py
│   ├── admin_auth_config.json
│   ├── users_db.json
│   └── excel_templates.json
├── src/
│   ├── main.py
│   ├── gui/
│   ├── auth/
│   ├── cloud/
│   ├── excel/
│   ├── metadata/
│   └── utils/
├── data/
│   ├── admin_tokens.json
│   ├── sessions/
│   ├── cache/
│   └── temp_excel/
├── templates/
├── docs/
├── tests/
└── assets/
```

The source modules mirror the functional requirements—GUI panels in `src/gui`, authentication helpers in `src/auth`, storage orchestration in `src/cloud`, and Excel tooling in `src/excel`.

## Prerequisites

Install the required packages:

```bash
pip install -r requirements.txt
```

> **Note:** The project ships with a local OneDrive mock. To connect to a real tenant, populate the environment variables described in `config/settings.py` and implement the Microsoft Graph upload/download requests inside the cloud modules.

## Usage

```bash
python -m src.main
```

1. Enter a registered User ID (optional password) from `config/users_db.json`.
2. Upload files or work with Excel sheets through the tabbed interface.
3. Review created files inside the **My Files** tab. Metadata updates are saved to `data/mock_onedrive/IndustrialDataSystem/Metadata/upload_metadata.xlsx`.

## Configuration

Environment variables:

- `ADMIN_CLIENT_ID`
- `ADMIN_TENANT_ID`
- `ADMIN_REDIRECT_URI`
- `ONEDRIVE_ROOT_FOLDER`
- `METADATA_FILE_NAME`
- `USER_ACTIVITY_FILE_NAME`
- `DEFAULT_USER_QUOTA_MB`
- `ENABLE_QUOTA_CHECK`
- `SESSION_TIMEOUT_HOURS`
- `ENCRYPTION_KEY`
- `LOG_LEVEL`
- `AUTO_CREATE_USER_FOLDERS`

Update templates or add new ones in the `templates/` directory and reference them inside `config/excel_templates.json`.

## Testing

Automated tests can be added under `tests/`. GUI-based workflows are best exercised manually.
