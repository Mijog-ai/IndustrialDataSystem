# Industrial Data System – Shared Drive Setup Guide

This document outlines how to provision the shared drive and supporting
infrastructure required for the Industrial Data System.

## 1. Prepare the Shared Drive

1. **Create the network share**
   - **Windows**: Use File Explorer to create `C:\IndustrialData`, right-click
     the folder, choose *Give access to* → *Specific people…*, and share it as
     `IndustrialData`. Note the UNC path (e.g. `\\Server\IndustrialData`).
   - **Linux**: Export a directory using Samba or NFS. For Samba, add an entry
     to `/etc/samba/smb.conf` and restart `smbd`. For NFS, configure `/etc/exports`.
   - **macOS**: Enable *File Sharing* in System Preferences and share the target
     folder.

2. **Subfolders**
   Inside the shared directory create:
   - `files/` – base location for uploaded files.
   - `files/tests/` – parent for all test-type folders.
   - `database/` – destination for `industrial_data.db`.

3. **Permissions**
   - Grant read/write access to the user accounts running the Upload App.
   - Provide read-only access to Reader App users if required.
   - Ensure the share allows long file paths and retains file metadata.

## 2. Map or Mount the Share on Client Machines

- **Windows**: Map the UNC path as a network drive (e.g. `Z:`) via *This PC* →
  *Map network drive*.
- **Linux/macOS**: Mount the share under `/mnt/shared/IndustrialData` using
  `mount.cifs` (Samba) or `mount -t nfs` (NFS). Configure `/etc/fstab` for
  automatic mounting on boot.

Record the mounted path—you will reference it in the `.env` file.

## 3. Configure the Application

1. Copy `.env` to each workstation and adjust:

   ```ini
   SHARED_DRIVE_PATH=\\\\Server\\IndustrialData
   DATABASE_PATH=\\\\Server\\IndustrialData\\database\\industrial_data.db
   FILES_BASE_PATH=\\\\Server\\IndustrialData\\files
   STORAGE_LIMIT_MB=10240
   ```

2. Run `python setup_test_data.py` to initialise the database and populate
   sample records. Verify that `industrial_data.db` is created under the
   `database/` folder.

3. Launch `python main.py` and sign in using the sample credentials created by
   the setup script (`sample_uploader@example.com` / `sample`). Confirm that
   sample files appear in both the Upload and Reader dashboards.

## 4. Optional: Run Migration Scripts

If you have existing JSON data from earlier versions:

```bash
python -m industrial_data_system.cli.migrate_auth
python -m industrial_data_system.cli.migrate_data --legacy-dir /path/to/exported/files
```

Both scripts leave timestamped backups of the original JSON files in the `data/`
folder for reference.

## 5. Routine Maintenance

- Schedule regular database backups via `python -m industrial_data_system.cli.admin backup-db`.
- Monitor shared-drive capacity with `python -m industrial_data_system.cli.admin storage-report`.
- Keep the `.env` file consistent across workstations so paths remain valid.

Following these steps ensures the applications operate against a consistent,
fully local infrastructure without any cloud dependencies.
