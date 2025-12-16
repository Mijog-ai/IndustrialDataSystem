"""Background workers for long-running tasks"""

from pathlib import Path
from typing import List

from PyQt5.QtCore import QThread, pyqtSignal


class FileUploadWorker(QThread):
    """Upload files in background thread"""

    progress = pyqtSignal(int, str)  # progress percentage, current file
    finished = pyqtSignal(list, list)  # successful, failed
    error = pyqtSignal(str)

    def __init__(
        self,
        file_paths: List[str],
        pump_series: str,
        test_type: str,
        storage_manager,
        history_store,
        user_id: int,
    ):
        super().__init__()
        self.file_paths = file_paths
        self.pump_series = pump_series
        self.test_type = test_type
        self.storage_manager = storage_manager
        self.history_store = history_store
        self.user_id = user_id

    def run(self):
        successful = []
        failed = []

        for i, file_path in enumerate(self.file_paths):
            try:
                # Emit progress
                progress_pct = int((i / len(self.file_paths)) * 100)
                self.progress.emit(progress_pct, Path(file_path).name)

                # Upload file
                stored = self.storage_manager.upload_file(
                    file_path, self.pump_series, self.test_type
                )

                # Record in database
                self.history_store.add_record(
                    user_id=self.user_id,
                    filename=stored.absolute_path.name,
                    file_path=str(stored.relative_path),
                    pump_series=self.pump_series,
                    test_type=self.test_type,
                    file_size=stored.size_bytes,
                )

                successful.append(file_path)

            except Exception as e:
                failed.append((file_path, str(e)))

        # Final progress
        self.progress.emit(100, "Complete")
        self.finished.emit(successful, failed)
