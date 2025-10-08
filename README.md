# Industrial Data System Desktop Application

A PyQt5 desktop application featuring admin-approved authentication, CSV previewing, and uploads to Cloudinary. The project now uses PostgreSQL (or any SQLAlchemy-compatible RDBMS) with Alembic migrations, secure JWT-backed sessions, and a complete password reset workflow.

## Features

- Login, registration, and admin approval workflow backed by SQLAlchemy.
- JWT-based user sessions with explicit logout controls for end users and administrators.
- "Forgot password" flow with email dispatch (via SMTP) or on-screen reset tokens for development.
- Admin panel for reviewing, approving, or rejecting pending accounts.
- CSV viewer with upload button and drag-and-drop support.
- Cloudinary integration for storing uploads in user-specific folders.
- Environment-based configuration using `.env` for database, JWT, SMTP, and Cloudinary credentials.

## Project Structure

```
project/
├── alembic.ini
├── auth.py
├── cloudinary_upload.py
├── database.py
├── main.py
├── migrations/
│   ├── env.py
│   ├── README
│   └── versions/
│       └── 20240401_0001_initial.py
├── requirements.txt
├── README.md
└── .env.example        # copy to .env and fill in secrets
```

## Prerequisites

- Python 3.10+
- A PostgreSQL instance (local Docker container, managed service, etc.). SQLAlchemy URLs for other engines such as MySQL are supported, but PostgreSQL is recommended.
- Cloudinary account (free tier is sufficient) with API credentials.
- Optional: SMTP account for sending password reset emails.

## Installation & Configuration

1. **Create and activate a virtual environment (optional but recommended).**

2. **Install dependencies.**
   ```bash
   pip install -r requirements.txt
   ```

3. **Copy the example environment file and populate values.**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and provide at minimum:
   - `DATABASE_URL` – e.g. `postgresql://user:password@localhost:5432/industrial_data`
   - `IDS_JWT_SECRET` – a long random secret used for signing JWT session tokens.
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`

   Optional but recommended entries:
   - `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` – bootstrap an approved admin on first launch.
   - `SMTP_*` values (host, port, username, password, TLS flag, and `MAIL_DEFAULT_SENDER`) to enable email-based password reset delivery.
   - `IDS_SESSION_TTL_MINUTES` and `IDS_RESET_TOKEN_TTL_MINUTES` to adjust session/token lifetimes.

4. **Create the application database.** For PostgreSQL, from a shell with appropriate credentials:
   ```bash
   createdb industrial_data
   ```
   (Adjust the database name or create it via your hosting provider’s console as needed.)

5. **Run database migrations.**
   ```bash
   alembic upgrade head
   ```
   This creates the `users` and `password_reset_tokens` tables using the connection string specified in `DATABASE_URL`.

6. **Run the application.**
   ```bash
   python main.py
   ```

## Usage

1. Optionally export explicit admin credentials if you did not set them in `.env`:
   ```bash
   export ADMIN_USERNAME="your-admin"
   export ADMIN_PASSWORD="change-me"
   export ADMIN_EMAIL="admin@example.com"
   ```
2. Launch the app with `python main.py`.
3. Register a new user. The registration will be stored as `pending` until an admin approves it.
4. Log in as an admin and use the admin panel to approve or reject users. Admins can log out directly from the panel.
5. Once approved, a user can log in to access the main interface:
   - **Upload CSV** button opens a file dialog.
   - **Drag-and-drop box** accepts `.csv` files.
   - The table displays the CSV contents.
   - After previewing the CSV, confirm the Cloudinary upload prompt to store the file.
6. **Logout** – The main window includes a logout button which revokes the in-memory JWT and returns to the login screen. Closing the window also logs the user out.

## Password Reset Flow

1. Click **Forgot Password?** on the login screen and submit the email associated with your account.
2. If SMTP is configured, the app sends an email containing a one-time token. When email is not configured (development mode), the token is displayed in-app so you can copy it manually.
3. Use the **Reset Password** view to paste the token and choose a new password.
4. After a successful reset, return to the login screen and authenticate with the updated credentials.

## Cloudinary Setup

1. Create a free account at [Cloudinary](https://cloudinary.com/).
2. From the dashboard, copy your **Cloud name**, **API Key**, and **API Secret**.
3. Add them to your `.env` file and restart the application if it was running.
4. Run the application and confirm the Cloudinary upload prompt after selecting or dropping a file.

## Database Migrations

- Generate a new migration when models change:
  ```bash
  alembic revision --autogenerate -m "describe change"
  ```
- Apply migrations:
  ```bash
  alembic upgrade head
  ```
- Downgrade if required:
  ```bash
  alembic downgrade -1
  ```

## Packaging

To build a standalone executable with PyInstaller:

```bash
pyinstaller --onefile --noconsole main.py
```

The resulting binary will be placed in the `dist/` directory.

## Troubleshooting

- **Missing configuration** – ensure `.env` is present with valid database, JWT secret, and Cloudinary credentials before running the app.
- **Database connectivity issues** – confirm that the database server is reachable from your machine and that `DATABASE_URL` is correct.
- **Cloudinary upload failures** – verify that your API credentials are correct and the account allows the selected resource type.
- **Password reset email not received** – double-check SMTP configuration. Tokens always display in-app when email is disabled to support local testing.

## Security Notes

- Secrets should never be committed to source control. Use a local `.env` or environment variables.
- Passwords are hashed using bcrypt before being stored in the database.
- JWT session tokens are signed using `IDS_JWT_SECRET`; rotate this secret regularly and keep it private.
- PostgreSQL (or your chosen backend) should enforce SSL/TLS in production and restrict inbound connections.
