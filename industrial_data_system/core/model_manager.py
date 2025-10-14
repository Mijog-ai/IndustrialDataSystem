"""Model training and management utilities for incremental autoencoder models."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from industrial_data_system.core.config import AppConfig, get_config
from industrial_data_system.core.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ModelTrainingError(RuntimeError):
    """Raised when a dataset cannot be used for training."""


@dataclass
class ModelMetadata:
    """Metadata describing a trained autoencoder model version."""

    pump_series: str
    test_type: str
    file_type: str
    version: int
    trained_at: str
    file_count: int
    input_dim: int
    metrics: Dict[str, float]
    files: List[str]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class Autoencoder:
    """Lightweight autoencoder using NumPy for incremental training."""

    def __init__(self, input_dim: int, *, hidden_dim: Optional[int] = None, rng: Optional[np.random.Generator] = None) -> None:
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim or max(4, input_dim // 2)
        self.rng = rng or np.random.default_rng()
        scale = 1.0 / max(1, self.hidden_dim)
        self.W1 = self.rng.normal(scale=scale, size=(input_dim, self.hidden_dim))
        self.b1 = np.zeros(self.hidden_dim, dtype=np.float32)
        self.W2 = self.rng.normal(scale=scale, size=(self.hidden_dim, input_dim))
        self.b2 = np.zeros(input_dim, dtype=np.float32)

    def forward(self, features: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        hidden = features @ self.W1 + self.b1
        hidden = np.maximum(0.0, hidden)  # ReLU activation
        reconstructed = hidden @ self.W2 + self.b2
        return reconstructed, hidden

    def train_batch(self, batch: np.ndarray, *, learning_rate: float) -> float:
        reconstructed, hidden = self.forward(batch)
        error = reconstructed - batch
        loss = float(np.mean(error**2))

        grad_recon = (2.0 / batch.shape[0]) * error
        grad_W2 = hidden.T @ grad_recon
        grad_b2 = grad_recon.sum(axis=0)

        hidden_grad = grad_recon @ self.W2.T
        hidden_mask = (hidden > 0).astype(batch.dtype)
        grad_hidden = hidden_grad * hidden_mask

        grad_W1 = batch.T @ grad_hidden
        grad_b1 = grad_hidden.sum(axis=0)

        self.W2 -= learning_rate * grad_W2
        self.b2 -= learning_rate * grad_b2
        self.W1 -= learning_rate * grad_W1
        self.b1 -= learning_rate * grad_b1

        return loss

    def train(self, data: np.ndarray, *, epochs: int, batch_size: int, learning_rate: float) -> Dict[str, float]:
        batch_size = max(1, min(batch_size, len(data)))
        losses: List[float] = []
        for _ in range(epochs):
            indices = np.arange(len(data))
            self.rng.shuffle(indices)
            for start in range(0, len(data), batch_size):
                batch_idx = indices[start : start + batch_size]
                batch = data[batch_idx]
                losses.append(self.train_batch(batch, learning_rate=learning_rate))
        return {"training_loss": float(np.mean(losses)) if losses else 0.0}

    def reconstruction_error(self, data: np.ndarray) -> np.ndarray:
        reconstructed, _ = self.forward(data)
        return np.mean((reconstructed - data) ** 2, axis=1)

    def state_dict(self) -> Dict[str, np.ndarray]:
        return {
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "W1": self.W1,
            "b1": self.b1,
            "W2": self.W2,
            "b2": self.b2,
        }

    def load_state_dict(self, state: Dict[str, np.ndarray]) -> None:
        self.input_dim = int(state.get("input_dim", self.input_dim))
        self.hidden_dim = int(state.get("hidden_dim", self.hidden_dim))
        self.W1 = np.array(state["W1"], dtype=np.float32)
        self.b1 = np.array(state["b1"], dtype=np.float32)
        self.W2 = np.array(state["W2"], dtype=np.float32)
        self.b2 = np.array(state["b2"], dtype=np.float32)


class AutoencoderModelManager:
    """Manage datasets and incremental autoencoder model training."""

    SUPPORTED_EXTENSIONS = {".csv": "csv", ".parquet": "parquet"}

    def __init__(
        self,
        *,
        config: Optional[AppConfig] = None,
        database: Optional[DatabaseManager] = None,
        logger: Optional[logging.Logger] = None,
        max_epochs: int = 10,
        batch_size: int = 128,
        learning_rate: float = 1e-3,
    ) -> None:
        self.config = config or get_config()
        self.database = database or DatabaseManager()
        self.logger = logger or logging.getLogger(__name__)
        self.max_epochs = max_epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate

        self._root = self.config.shared_drive_path / "industrialDATA"
        self._files_root = self._root / "files"
        self._models_root = self._root / "models"
        for directory in (self._root, self._files_root, self._models_root):
            directory.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_new_dataset(self, dataset_path: Path | str, *, pump_series: str, test_type: str) -> ModelMetadata:
        """Register a new dataset file and trigger incremental training."""

        if not pump_series or not test_type:
            raise ModelTrainingError("Pump series and test type are required for training.")

        dataset_path = Path(dataset_path)
        if not dataset_path.is_file():
            raise ModelTrainingError(f"Dataset '{dataset_path}' does not exist.")

        file_type = self._resolve_file_type(dataset_path)
        stored_dataset = self._store_dataset(dataset_path, pump_series, test_type, file_type)

        numeric_chunks = list(self._load_numeric_chunks(stored_dataset, file_type))
        if not numeric_chunks:
            raise ModelTrainingError("Uploaded file does not contain numeric columns for training.")

        scaler, _ = self._load_or_create_scaler(pump_series, test_type, file_type)
        data_chunks = []
        for chunk in numeric_chunks:
            scaler.partial_fit(chunk)
            data_chunks.append(chunk)

        scaled_data = np.vstack([scaler.transform(chunk) for chunk in data_chunks])
        input_dim = scaled_data.shape[1]

        existing_record = self.database.get_latest_model_record(pump_series, test_type, file_type)
        model: Autoencoder
        base_file_count = 0
        version = 1
        if existing_record and existing_record.input_dim == input_dim:
            model = self._load_model(existing_record.model_path, input_dim)
            version = existing_record.version + 1
            base_file_count = existing_record.file_count
        else:
            if existing_record and existing_record.input_dim != input_dim:
                self.logger.warning(
                    "Input dimension changed for %s/%s/%s – resetting model architecture.",
                    pump_series,
                    test_type,
                    file_type,
                )
                version = (existing_record.version + 1) if existing_record else 1
                base_file_count = existing_record.file_count if existing_record else 0
            model = Autoencoder(input_dim)

        metrics = self._train_model(model, scaled_data)

        metadata = self._persist_model(
            model,
            scaler,
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            version=version,
            input_dim=input_dim,
            file_count=base_file_count + 1,
            metrics=metrics,
            files=[stored_dataset.name],
        )

        self.database.register_dataset_file(
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            file_path=str(stored_dataset),
            file_size=stored_dataset.stat().st_size,
            checksum=self._checksum(stored_dataset),
        )

        self.database.record_model_version(
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            version=metadata.version,
            model_path=str(self._model_file_path(pump_series, test_type, file_type)),
            scaler_path=str(self._scaler_file_path(pump_series, test_type, file_type)),
            metadata_path=str(self._metadata_file_path(pump_series, test_type, file_type)),
            file_count=metadata.file_count,
            input_dim=input_dim,
            metrics=metadata.metrics,
        )

        return metadata

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_file_type(self, dataset_path: Path) -> str:
        extension = dataset_path.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ModelTrainingError(
                f"Unsupported dataset format '{dataset_path.suffix}'. Supported: csv, parquet."
            )
        return self.SUPPORTED_EXTENSIONS[extension]

    def _files_directory(self, pump_series: str, test_type: str, file_type: str) -> Path:
        destination = self._files_root / pump_series / test_type / file_type
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def _models_directory(self, pump_series: str, test_type: str, file_type: str) -> Path:
        destination = self._models_root / pump_series / test_type / file_type
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    def _store_dataset(
        self,
        dataset_path: Path,
        pump_series: str,
        test_type: str,
        file_type: str,
    ) -> Path:
        target_dir = self._files_directory(pump_series, test_type, file_type)
        destination = target_dir / dataset_path.name
        if destination.exists():
            destination = self._unique_path(destination)
        shutil.copy2(dataset_path, destination)
        return destination

    def _unique_path(self, base_path: Path) -> Path:
        counter = 1
        while base_path.exists():
            base_path = base_path.with_name(f"{base_path.stem}_{counter}{base_path.suffix}")
            counter += 1
        return base_path

    def _load_numeric_chunks(self, dataset_path: Path, file_type: str) -> Iterable[np.ndarray]:
        if file_type == "csv":
            for chunk in pd.read_csv(dataset_path, chunksize=10_000):
                numeric = chunk.select_dtypes(include=["float", "int", "bool"]).apply(pd.to_numeric, errors="coerce")
                numeric = numeric.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").fillna(0.0)
                if numeric.empty:
                    continue
                yield numeric.to_numpy(dtype=np.float32)
        else:
            dataframe = pd.read_parquet(dataset_path).select_dtypes(include=["float", "int", "bool"]).apply(
                pd.to_numeric, errors="coerce"
            )
            dataframe = dataframe.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").fillna(0.0)
            if not dataframe.empty:
                yield dataframe.to_numpy(dtype=np.float32)

    def _load_or_create_scaler(
        self,
        pump_series: str,
        test_type: str,
        file_type: str,
    ) -> Tuple[StandardScaler, bool]:
        scaler_path = self._scaler_file_path(pump_series, test_type, file_type)
        if scaler_path.exists():
            try:
                scaler = joblib.load(scaler_path)
                if isinstance(scaler, StandardScaler):
                    return scaler, True
            except Exception as exc:  # pragma: no cover - defensive
                self.logger.warning("Failed to load scaler from %s: %s", scaler_path, exc)
        scaler = StandardScaler()
        return scaler, False

    def _train_model(self, model: Autoencoder, training_data: np.ndarray) -> Dict[str, float]:
        stats = model.train(
            training_data,
            epochs=self.max_epochs,
            batch_size=self.batch_size,
            learning_rate=self.learning_rate,
        )
        reconstruction_error = model.reconstruction_error(training_data)
        stats.update(
            {
                "reconstruction_error_mean": float(np.mean(reconstruction_error)),
                "reconstruction_error_std": float(np.std(reconstruction_error)),
            }
        )
        return stats

    def _persist_model(
        self,
        model: Autoencoder,
        scaler: StandardScaler,
        *,
        pump_series: str,
        test_type: str,
        file_type: str,
        version: int,
        input_dim: int,
        file_count: int,
        metrics: Dict[str, float],
        files: List[str],
    ) -> ModelMetadata:
        models_dir = self._models_directory(pump_series, test_type, file_type)
        versioned_model = models_dir / f"model_v{version:03d}.pkl"
        versioned_scaler = models_dir / f"scaler_v{version:03d}.pkl"
        versioned_metadata = models_dir / f"metadata_v{version:03d}.json"

        joblib.dump(model.state_dict(), versioned_model)
        joblib.dump(scaler, versioned_scaler)

        metadata = ModelMetadata(
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            version=version,
            trained_at=datetime.now(UTC).isoformat(),
            file_count=file_count,
            input_dim=input_dim,
            metrics=metrics,
            files=files,
        )
        versioned_metadata.write_text(metadata.to_json(), encoding="utf-8")

        # Update latest pointers
        joblib.dump(model.state_dict(), self._model_file_path(pump_series, test_type, file_type))
        joblib.dump(scaler, self._scaler_file_path(pump_series, test_type, file_type))
        self._metadata_file_path(pump_series, test_type, file_type).write_text(
            metadata.to_json(), encoding="utf-8"
        )

        return metadata

    def _model_file_path(self, pump_series: str, test_type: str, file_type: str) -> Path:
        return self._models_directory(pump_series, test_type, file_type) / "model.pkl"

    def _scaler_file_path(self, pump_series: str, test_type: str, file_type: str) -> Path:
        return self._models_directory(pump_series, test_type, file_type) / "scaler.pkl"

    def _metadata_file_path(self, pump_series: str, test_type: str, file_type: str) -> Path:
        return self._models_directory(pump_series, test_type, file_type) / "metadata.json"

    def _load_model(self, model_path: str, input_dim: int) -> Autoencoder:
        state = joblib.load(model_path)
        model = Autoencoder(input_dim)
        if isinstance(state, dict):
            model.load_state_dict(state)
        else:  # pragma: no cover - defensive
            raise ModelTrainingError(f"Invalid model state stored at {model_path}")
        return model

    def _checksum(self, file_path: Path) -> str:
        digest = sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


__all__ = ["AutoencoderModelManager", "ModelMetadata", "ModelTrainingError"]
