"""Populate the database and shared drive with sample data for testing."""
from __future__ import annotations

from pathlib import Path

from industrial_data_system.core.auth import LocalAuthStore, UploadHistoryStore
from industrial_data_system.core.config import get_config
from industrial_data_system.core.db_manager import DatabaseManager
from industrial_data_system.core.storage import LocalStorageManager, StorageError


def main() -> None:
    config = get_config()
    manager = DatabaseManager()
    storage = LocalStorageManager(config=config, database=manager)
    auth_store = LocalAuthStore(manager)
    history_store = UploadHistoryStore(manager)

    print("Setting up sample test data...")
    sample_user_email = "sample_uploader@example.com"
    try:
        user = auth_store.create_user(sample_user_email, "sample", metadata={"display_name": "Sample Uploader"})
        print(f"Created sample user: {sample_user_email}")
    except ValueError:
        user = auth_store.authenticate(sample_user_email, "sample")
        if not user:
            raise SystemExit("Unable to create or load sample user")
        print(f"Using existing sample user: {sample_user_email}")

    sample_types = {
        "Vibration": "Vibration analysis data",
        "Temperature": "Temperature monitoring",
    }

    base_dir = Path(__file__).resolve().parent / "sample_data"
    base_dir.mkdir(exist_ok=True)

    for name, description in sample_types.items():
        manager.ensure_test_type(name, description)

    for test_type, description in sample_types.items():
        sample_file = base_dir / f"{test_type.lower()}_sample.csv"
        sample_file.write_text("timestamp,value\n2024-01-01T00:00:00Z,42\n", encoding="utf-8")
        try:
            stored = storage.upload_file(sample_file, test_type)
        except StorageError as exc:
            print(f"Failed to stage sample file for {test_type}: {exc}")
            continue
        history_store.add_record(
            user_id=user.id,
            filename=stored.absolute_path.name,
            file_path=str(stored.relative_path),
            test_type=test_type,
            file_size=stored.size_bytes,
            description=description,
        )
        print(f"Created sample upload for {test_type}: {stored.absolute_path}")

    print("Sample data setup complete.")


if __name__ == "__main__":
    main()
