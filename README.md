# Industrial Data System Desktop Application

A PyQt5 desktop application featuring admin-approved authentication, CSV previewing, and uploads to Cloudinary.

## Features

- Login and registration workflow with admin approval.
- Admin panel for reviewing, approving, or rejecting pending accounts.
- CSV viewer with upload button and drag-and-drop support.
- Cloudinary integration for storing uploads in user-specific folders.
- Password hashing using bcrypt and environment-based configuration for secrets.

## Project Structure

```
project/
├── auth.py
├── database.py
├── main.py
├── cloudinary_upload.py
├── requirements.txt
├── README.md
└── .env               # provide your own values before running
```

## Prerequisites

- Python 3.10+
- Cloudinary account (free tier is sufficient) with API credentials.

## Installation

1. (Optional) create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` and populate the values:

   ```bash
   cp .env.example .env
   # Edit .env and fill in the Cloudinary credentials.
   ```

   Set the `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` from your Cloudinary dashboard. Optionally set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_EMAIL` to bootstrap an approved admin on startup.

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
   - After previewing the CSV, confirm the Cloudinary upload prompt to store the file in your configured account.

## Cloudinary Setup

1. Create a free account at [Cloudinary](https://cloudinary.com/).
2. From the dashboard, copy your **Cloud name**, **API Key**, and **API Secret**.
3. Add them to your `.env` file:

   ```ini
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_key
   CLOUDINARY_API_SECRET=your_secret
   ```

4. Run the application and confirm the Cloudinary upload prompt after selecting or dropping a file.

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

- **Missing configuration** – ensure `.env` is present with valid Cloudinary credentials before running the app.
- **Cloudinary upload failures** – verify that your API credentials are correct and the account allows the selected resource type.

## Security Notes

- Secrets should never be committed to source control. Use a local `.env` or environment variables.
- Passwords are hashed using bcrypt before being stored in SQLite.
- Delete or protect the SQLite database (`app.db`) if sensitive data is stored locally.
