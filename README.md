# Industrial Data System (Cloudinary Desktop Suite)

This project bundles two PyQt5 desktop applications that integrate with
Cloudinary. The Upload App lets operators organise and upload structured data,
while the Read & Process App provides a secure, read-only view of existing
assets. Both apps use lightweight JSON files to store credentials locally so the
only external dependency is Cloudinary itself.

## Features

- Local authentication for the Upload App with CSV/Excel previews and
  Cloudinary uploads organised by test type.
- Dedicated Read & Process App with its own credentials and security code gate
  (`123321`) for browsing Cloudinary assets.
- Cloudinary folder discovery under `tests/` with inline previews for supported
  formats and secure file downloads.
- Environment-driven configuration via `.env` powered by `python-dotenv`.

## Prerequisites

- Python 3.10+
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
   | `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud/tenant name. |
   | `CLOUDINARY_API_KEY` | Cloudinary API key. |
   | `CLOUDINARY_API_SECRET` | Cloudinary API secret. |
   | `CLOUDINARY_READER_ROOT` | Optional Cloudinary folder prefix (defaults to `tests`). |

3. **Launch the desktop gateway**

   ```bash
   python main.py
   ```

   A PyQt5 window appears with buttons for the **Upload App** and the
   **Read & Process App**. Each tool opens in its own window while the gateway
   stays hidden in the background.

## Usage

1. Launch `python main.py` and select the desired application from the gateway.
2. The **Upload App** maintains its own credentials in
   `data/upload_users.json`. Use the Sign Up tab to create a short username and
   password (six characters or fewer), then upload CSV/Excel files to
   Cloudinary. Uploaded file metadata is tracked locally in
   `data/upload_history.json`.
3. The **Read & Process App** uses a separate credential store in
   `data/reader_users.json` and requires the security code `123321` during
   sign-up and sign-in. After authentication it lists all assets under the
   `tests/` folder in Cloudinary, allows previewing supported files, and lets
   you download them via their secure URLs.
4. Closing an application window returns you to the gateway so you can launch
   the other tool.

## Development Notes

- User accounts and upload history are stored as JSON files inside the `data/`
  directory next to the application code. These files are created on first run.
- All file uploads are streamed directly to Cloudinary; no data is stored on the
  local file system beyond the metadata JSON files.
- To customize styles, edit `static/css/styles.css`.

## Deployment

Deploy the desktop applications on any system with Python and Qt available or bundle them with PyInstaller as described below. Ensure the `.env` file with Cloudinary credentials ships alongside the binaries.

## Packaging the app as a Windows executable

You can create a standalone Windows executable with [PyInstaller](https://pyinstaller.org/). The repository includes a ready-made `IndustrialDataSystem.spec` file that bundles the dynamic PyQt5 and Cloudinary dependencies detected during development. The steps below assume you are working on Windows and have Python and the project dependencies installed.

1. **Install PyInstaller** (inside your virtual environment if you use one)

   ```bash
   pip install pyinstaller
   ```

2. **Build the executable**

   From the project root, run:

   ```bash
   pyinstaller IndustrialDataSystem.spec
   ```

   The spec file pulls in the PyQt5 and Cloudinary packages that need to be explicitly collected when freezing the application and produces a single `IndustrialDataSystem.exe` file in the `dist` folder.

3. **Provide environment variables at runtime**

   The executable still needs the same Cloudinary environment variables. The application looks for a `.env` file next to the executable, inside the unpacked PyInstaller directory, or in the current working directory. Alternatively, set the variables in the Windows environment before launching the app.

4. **Run the executable**

   Double-click the generated `IndustrialDataSystem.exe` or start it from a terminal. The PyQt gateway window will appear just like when running `python main.py`.

For custom icons or splash screens, consult the [PyInstaller documentation](https://pyinstaller.org/en/stable/). If you need to ship additional assets (for example, SSL certificates), add more `--add-data` entries pointing to those files.
