# Industrial Data System (Supabase + Cloudinary)

This project provides a lightweight Flask dashboard that connects to Supabase for
authentication and structured data and uses Cloudinary for file storage. The
application no longer relies on any local database or file system state – every
piece of data lives in managed cloud services.

## Features

- Supabase authentication for secure login and password reset workflows.
- Dashboard for uploading files directly to Cloudinary.
- File metadata stored in a Supabase table for easy listing and management.
- Environment-driven configuration via `.env` powered by `python-dotenv`.

## Prerequisites

- Python 3.10+
- Supabase project with Email/Password auth enabled and a `files` table similar
  to:
  ```sql
  create table files (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null,
    filename text not null,
    url text not null,
    created_at timestamp with time zone default now()
  );
  ```
- Cloudinary account (free tier works great).

## Installation

1. **Clone and install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file**

   Copy `.env.example` to `.env` and fill in your project values:
   ```bash
   cp .env.example .env
   ```

   | Variable | Description |
   | --- | --- |
   | `SUPABASE_URL` | Supabase project URL, e.g. `https://your-project-id.supabase.co`. |
   | `SUPABASE_KEY` | Supabase service-role API key. |
   | `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud/tenant name. |
   | `CLOUDINARY_API_KEY` | Cloudinary API key. |
   | `CLOUDINARY_API_SECRET` | Cloudinary API secret. |
   | `FLASK_SECRET_KEY` | Secret key used by Flask for session signing (generate a random string). |

3. **Run the application**

   ```bash
   flask --app app run
   ```

   The app listens on <http://127.0.0.1:5000> by default. Ensure the Supabase
   and Cloudinary credentials allow calls from your environment.

## Usage

1. Navigate to `/login` and sign in using a Supabase user account.
2. From the dashboard you can upload files. The file is uploaded to Cloudinary
   and metadata (file name, secure URL, and owning user) is written to Supabase.
3. Uploaded files are listed on the dashboard with links to the Cloudinary
   asset.
4. Use the **Forgot password?** link on the login page to trigger Supabase's
   password reset email flow.
5. Click the **Logout** button in the navigation bar to end the session.

## Development Notes

- The Flask server stores the Supabase access and refresh token inside the
  session cookie. Logging out clears the session and calls `supabase.auth.sign_out()`.
- All file uploads are streamed directly to Cloudinary; no data is stored on the
  local file system.
- To customize styles, edit `static/css/styles.css`.

## Deployment

Deploy the app to any environment capable of running Flask (Render, Fly.io,
Railway, etc.). Remember to set all required environment variables and supply a
`SECRET_KEY` for Flask sessions in production.

## Packaging the app as a Windows executable

You can create a standalone Windows executable with
[PyInstaller](https://pyinstaller.org/). The repository includes a ready-made
`IndustrialDataSystem.spec` file that bundles the dynamic Supabase and
Cloudinary dependencies detected during development. The steps below assume you
are working on Windows and have Python and the project dependencies installed.

1. **Install PyInstaller** (inside your virtual environment if you use one)

   ```bash
   pip install pyinstaller
   ```

2. **Build the executable**

   From the project root, run:

   ```bash
   pyinstaller IndustrialDataSystem.spec
   ```

   The spec file pulls in the Supabase, Cloudinary, and Werkzeug packages that
   need to be explicitly collected when freezing the application and produces a
   single `IndustrialDataSystem.exe` file in the `dist` folder.

3. **Provide environment variables at runtime**

   The executable still needs the same Supabase and Cloudinary environment
   variables. The application now looks for a `.env` file next to the
   executable, inside the unpacked PyInstaller directory, or in the current
   working directory. Alternatively, set the variables in the Windows
   environment before launching the app.

4. **Run the executable**

   Double-click the generated `IndustrialDataSystem.exe` or start it from a
   terminal. Flask will bind to `http://127.0.0.1:5000` by default.

For custom icons or splash screens, consult the [PyInstaller documentation](https://pyinstaller.org/en/stable/). If you
need to ship additional assets (for example, SSL certificates), add more
`--add-data` entries pointing to those files.
