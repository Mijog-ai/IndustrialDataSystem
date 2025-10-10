"""Data processor tool that converts ASC files to Parquet format."""

from __future__ import annotations



"""Data processor tool that converts ASC files to Parquet format in parallel."""


import os
import sys
import traceback
from pathlib import Path
from typing import List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add the project root to the path to ensure imports work
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def _process_single_file(args: Tuple[Path, Path]) -> Tuple[str, str]:
    """Worker function to process a single ASC file (run in a separate process)."""
    asc_file, base_path = args
    try:
        from industrial_data_system.utils.asc_utils import load_and_process_asc_file
        import pandas as pd

        relative_path = asc_file.relative_to(base_path) if asc_file.is_relative_to(base_path) else asc_file
        log = [f"\nProcessing: {relative_path}"]

        # Skip if unreadable
        if not asc_file.exists() or not os.access(asc_file, os.R_OK):
            log.append("  ✗ Error: File not found or not readable")
            return "\n".join(log), "failed"

        parquet_file = asc_file.with_suffix(".parquet")
        if parquet_file.exists():
            log.append(f"  → Skipped (Parquet already exists: {parquet_file.name})")
            return "\n".join(log), "skipped"

        log.append(f"  → Loading ASC file ({asc_file.stat().st_size / 1024:.2f} KB)...")
        df = load_and_process_asc_file(str(asc_file))
        if df is None or df.empty:
            log.append("  ✗ Warning: File contains no data")
            return "\n".join(log), "failed"

        log.append(f"  → Converting to Parquet... ({df.shape[0]} rows, {df.shape[1]} columns)")
        df.to_parquet(parquet_file, engine="pyarrow", compression="snappy", index=False)

        if not parquet_file.exists():
            log.append("  ✗ Error: Failed to create Parquet file")
            return "\n".join(log), "failed"

        parquet_size = parquet_file.stat().st_size / 1024
        log.append(f"  → Parquet file created ({parquet_size:.2f} KB)")

        try:
            asc_file.unlink()
            log.append("  → Original ASC file removed")
        except Exception as e:
            log.append(f"  → Warning: Could not delete ASC file: {e}")

        log.append("  ✓ Successfully processed")
        return "\n".join(log), "success"

    except Exception as e:
        details = traceback.format_exc(limit=5)
        return f"\nProcessing: {asc_file}\n  ✗ Error: {e}\n  Details: {details}", "failed"


def run(max_workers: int = os.cpu_count() or 4) -> str:
    """Process all ASC files in parallel and convert them to Parquet format."""
    try:
        from industrial_data_system.core.config import get_config
        from industrial_data_system.core.db_manager import DatabaseManager
        from industrial_data_system.core.storage import LocalStorageManager

        config = get_config()
        db_manager = DatabaseManager()
        storage_manager = LocalStorageManager(config=config, database=db_manager)

        base_path = storage_manager.base_path
        if not base_path.exists():
            return f"Error: Storage directory not accessible at {base_path}"

        asc_files = list({f for ext in ("*.asc", "*.ASC") for f in base_path.rglob(ext)})
        if not asc_files:
            return f"No ASC files found in storage directory: {base_path}"

        results = [f"Storage directory: {base_path}",
                   f"Found {len(asc_files)} ASC file(s) to process.\n",
                   "=" * 60]

        # Use multiprocessing for parallel file conversion
        processed_count = failed_count = skipped_count = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_process_single_file, (f, base_path)): f for f in asc_files}
            for future in as_completed(futures):
                log_text, status = future.result()
                results.append(log_text)
                if status == "success":
                    processed_count += 1
                elif status == "failed":
                    failed_count += 1
                elif status == "skipped":
                    skipped_count += 1

        # Summary
        results += [
            "\n" + "=" * 60,
            "\nProcessing Summary:",
            f"  Successfully processed: {processed_count}",
            f"  Skipped (already exists): {skipped_count}",
            f"  Failed: {failed_count}",
            f"  Total: {len(asc_files)}",
        ]

        if processed_count:
            results.append(f"\n✓ Processing complete! {processed_count} file(s) converted to Parquet format.")

        return "\n".join(results)

    except Exception as e:
        return f"Fatal error during processing: {e}\n\n{traceback.format_exc(limit=8)}"



def _update_database_path(db_manager, old_path: str, new_path: str) -> None:
    """Update the file path in the database if the record exists."""
    try:
        # Get all uploads and check if this file is tracked
        uploads = db_manager.list_uploads()
        for upload in uploads:
            if upload.file_path == old_path:
                # Update the file path in the database
                cursor = db_manager.connection.cursor()
                cursor.execute(
                    "UPDATE uploads SET file_path = ? WHERE file_path = ?",
                    (new_path, old_path)
                )
                db_manager.connection.commit()
                break
    except Exception as e:
        # If database update fails, raise it so we can log it
        raise Exception(f"Database update failed: {str(e)}")