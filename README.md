# Industrial Data System Desktop Application

A PyQt5 desktop application featuring admin-approved authentication, CSV previewing, and automatic uploads to OneDrive via Microsoft Graph.

## Features

- Login and registration workflow with admin approval.
- Admin panel for reviewing, approving, or rejecting pending accounts.
- CSV viewer with upload button and drag-and-drop support.
- OneDrive integration that stores uploads in user-specific folders under the configured app directory.
- Password hashing using bcrypt and environment-based configuration for secrets.

## Project Structure

```
project/
├── auth.py
├── database.py
├── main.py
├── onedrive_auth.py
├── onedrive_upload.py
├── requirements.txt
├── README.md
└── .env               # provide your own values before running
```

## Prerequisites

- Python 3.10+
- Azure AD application with `Files.ReadWrite`, `Files.ReadWrite.AppFolder`, `User.Read`, and `offline_access` permissions and admin consent granted.

## Installation

1. (Optional) create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env` and populate the values:

   ```bash
   cp .env .env.local
   # Edit .env.local and fill in CLIENT_ID, TENANT_ID, CLIENT_SECRET, etc.
   ```

   Set the `CLIENT_ID`, `TENANT_ID`, and `CLIENT_SECRET` from your Azure application.
   Optionally set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL` to bootstrap an approved admin on startup.

4. Export `IDS_DB_PATH` if you want to override the default SQLite database location (defaults to `app.db`).

## Usage

1. (Optional) export explicit admin credentials. When omitted, a default admin
   account (`admin` / `admin123`) is created automatically on first launch to
   allow registrations to be approved.

   ```bash
   export ADMIN_USERNAME="your-admin"
   export ADMIN_PASSWORD="change-me"
   export ADMIN_EMAIL="admin@example.com"  # optional override
   ```

2. Run the application:

   ```bash
   python main.py
   ```

3. Register a new user. The registration will be stored as `pending` until an admin approves it.
4. Log in as an admin and use the admin panel to approve or reject users.
5. Once approved, a user can log in to access the main interface:
   - **Upload CSV** button in the top-left corner opens a file dialog.
   - **Drag-and-drop box** in the bottom-right corner accepts `.csv` files.
   - The center table displays the CSV contents.
   - Uploads are automatically sent to OneDrive at `Apps/<ONEDRIVE_APP_FOLDER>/Users/<username>/`.

## Admin workflow

- The admin panel opens immediately after a successful admin login. Every
  registration that has not yet been reviewed appears in the list with status
  `pending`.
- Select a user and click **Approve** to grant access or **Reject** to deny the
  request. Use **Refresh** to retrieve the latest registrations from the
  database.
- End users can log in only after their account has been approved by an admin.

## Packaging

To build a standalone executable with PyInstaller:

```bash
pyinstaller --onefile --noconsole main.py
```

The resulting binary will be placed in the `dist/` directory.

## Troubleshooting

- **Missing configuration** – ensure `.env.local` (or `.env`) is present with valid Azure credentials before running the app.
- **Token acquisition errors** – confirm the Azure AD application has the required permissions and the secrets are correct.
- **OneDrive upload failures** – check network connectivity and that the signed-in application has access to the OneDrive account used for uploads.

## Security Notes

- Secrets should never be committed to source control. Use a local `.env` or environment variables.
- Passwords are hashed using bcrypt before being stored in SQLite.
- Delete or protect the SQLite database (`app.db`) if sensitive data is stored locally.
