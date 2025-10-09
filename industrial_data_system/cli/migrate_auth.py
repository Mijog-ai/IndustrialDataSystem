"""Migrate legacy JSON authentication files into the SQLite database."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from industrial_data_system.core.auth import default_data_path
from industrial_data_system.core.database import migrate_from_json


def _backup_file(path: Path) -> None:
    if not path.exists():
        return
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_path = path.with_suffix(path.suffix + f".backup-{timestamp}")
    shutil.copy2(path, backup_path)


def main() -> None:
    upload_users = default_data_path("upload_users.json")
    reader_users = default_data_path("reader_users.json")
    upload_history = default_data_path("upload_history.json")

    print("Starting authentication data migration...")
    counts = migrate_from_json(
        upload_users_path=upload_users,
        reader_users_path=reader_users,
        upload_history_path=upload_history,
    )

    for path in (upload_users, reader_users, upload_history):
        _backup_file(path)

    print("Migration complete.")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
