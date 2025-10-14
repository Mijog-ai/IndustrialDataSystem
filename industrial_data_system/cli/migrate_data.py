"""Comprehensive migration helper for moving legacy assets to local storage."""
from __future__ import annotations

import argparse
from pathlib import Path

from industrial_data_system.pipelines import migrate_upload_history


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-dir",
        type=Path,
        help="Path containing previously downloaded files organised by test type.",
    )
    args = parser.parse_args()

    result = migrate_upload_history(args.legacy_dir)
    if result["total_records"] == 0:
        print("No legacy upload history found; nothing to migrate.")
        return

    print(
        "Migration completed. "
        f"{result['migrated_records']} of {result['total_records']} records imported."
    )


if __name__ == "__main__":
    main()
