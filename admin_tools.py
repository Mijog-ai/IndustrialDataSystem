"""Administrative utilities for the Industrial Data System."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from auth import LocalAuthStore
from config import get_config
from db_manager import DatabaseManager
from storage_manager import LocalStorageManager


def backup_database(destination: Path) -> Path:
    config = get_config()
    source = config.database_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def restore_database(source: Path) -> None:
    config = get_config()
    shutil.copy2(source, config.database_path)


def list_users() -> None:
    store = LocalAuthStore(DatabaseManager())
    users = store.list_users()
    print(json.dumps([
        {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "metadata": user.metadata,
            "created_at": user.created_at,
        }
        for user in users
    ], indent=2))


def storage_report() -> None:
    manager = DatabaseManager()
    storage = LocalStorageManager(database=manager)
    usage_bytes = manager.get_storage_usage()
    limit_bytes = storage.config.storage_limit_mb * 1024 * 1024
    available = max(limit_bytes - usage_bytes, 0)
    print(json.dumps({
        "used_bytes": usage_bytes,
        "limit_bytes": limit_bytes,
        "available_bytes": available,
        "drive_available": storage.is_drive_available(),
    }, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command")

    backup_parser = sub.add_parser("backup-db", help="Create a timestamped database backup.")
    backup_parser.add_argument("--output", type=Path, help="Destination file", default=None)

    restore_parser = sub.add_parser("restore-db", help="Restore the database from a backup file.")
    restore_parser.add_argument("path", type=Path)

    sub.add_parser("list-users", help="Show all accounts in the database.")
    sub.add_parser("storage-report", help="Print storage usage statistics.")

    args = parser.parse_args()

    if args.command == "backup-db":
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        output = args.output or (get_config().database_path.with_name(f"industrial_data_{timestamp}.db"))
        path = backup_database(output)
        print(f"Backup created at {path}")
    elif args.command == "restore-db":
        restore_database(args.path)
        print("Database restored.")
    elif args.command == "list-users":
        list_users()
    elif args.command == "storage-report":
        storage_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
