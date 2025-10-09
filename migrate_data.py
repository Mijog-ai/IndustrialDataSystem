"""Comprehensive migration helper for moving legacy assets to local storage."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from auth import default_data_path
from auth import UploadHistoryStore
from config import get_config
from db_manager import DatabaseManager
from storage_manager import LocalStorageManager, StorageError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-dir",
        type=Path,
        help="Path containing previously downloaded files organised by test type.",
    )
    args = parser.parse_args()

    config = get_config()
    manager = DatabaseManager()
    storage = LocalStorageManager(config=config, database=manager)
    history_store = UploadHistoryStore(manager)

    history_path = default_data_path("upload_history.json")
    if not history_path.exists():
        print("No legacy upload history found; nothing to migrate.")
        return

    legacy_users: Dict[str, int] = {}
    for path_name in ("upload_users.json", "reader_users.json"):
        path = default_data_path(path_name)
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for legacy_id, payload in data.get("users", {}).items():
            email = payload.get("email")
            if not email:
                continue
            record = manager.get_user_by_email(email)
            if record:
                legacy_users[legacy_id] = record.id

    data = json.loads(history_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    print(f"Migrating {len(records)} upload history entries...")

    migrated = 0
    for record in records:
        test_type = record.get("test_type") or "General"
        filename = record.get("filename") or "unknown.dat"
        legacy_user_id = str(record.get("user_id") or "")
        user_id = legacy_users.get(legacy_user_id)
        if user_id is None:
            continue
        legacy_source: Path | None = None
        if args.legacy_dir:
            candidate = args.legacy_dir / "tests" / test_type / filename
            if candidate.exists():
                legacy_source = candidate

        stored_path: str
        file_size = None
        stored_filename = filename
        if legacy_source:
            try:
                stored = storage.upload_file(legacy_source, test_type, filename)
                stored_path = str(stored.relative_path)
                file_size = stored.size_bytes
                stored_filename = stored.absolute_path.name
            except StorageError as exc:
                print(f"Failed to copy {legacy_source}: {exc}")
                continue
        else:
            stored_path = f"tests/{test_type}/{filename}"

        existing = manager.find_upload(user_id=user_id, filename=filename, test_type=test_type)
        if existing:
            manager.update_upload(
                existing.id,
                filename=stored_filename,
                file_path=stored_path,
                file_size=file_size,
            )
        else:
            history_store.add_record(
                user_id=user_id,
                filename=stored_filename,
                file_path=stored_path,
                test_type=test_type,
                file_size=file_size,
            )
        migrated += 1

    print(f"Migration completed. {migrated} records imported.")


if __name__ == "__main__":
    main()
