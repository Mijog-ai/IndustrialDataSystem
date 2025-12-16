"""Enhanced model training that stores models alongside data files."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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
    is_new_model: bool  # True if created from scratch, False if fine-tuned

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


class Autoencoder:
    """Lightweight autoencoder using NumPy for incremental training."""

    def __init__(
        self,
        input_dim: int,
        *,
        hidden_dim: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
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

    def train(
        self, data: np.ndarray, *, epochs: int, batch_size: int, learning_rate: float
    ) -> Dict[str, float]:
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


class EnhancedModelManager:
    """Manage models stored alongside data files in test folders."""

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

        self._files_root = self.config.files_base_path

    def handle_new_dataset(
        self, dataset_path: Path | str, *, pump_series: str, test_type: str
    ) -> ModelMetadata:
        """Train or fine-tune model when new data is uploaded.

        Args:
            dataset_path: Path to the uploaded data file
            pump_series: Pump series name
            test_type: Test type name

        Returns:
            ModelMetadata with training information
        """
        if not pump_series or not test_type:
            raise ModelTrainingError("Pump series and test type are required for training.")

        dataset_path = Path(dataset_path)
        if not dataset_path.is_file():
            raise ModelTrainingError(f"Dataset '{dataset_path}' does not exist.")

        file_type = self._resolve_file_type(dataset_path)

        # Load numeric data
        numeric_chunks = list(self._load_numeric_chunks(dataset_path, file_type))
        if not numeric_chunks:
            raise ModelTrainingError("Uploaded file does not contain numeric columns for training.")

        # Get test folder where data and models are stored
        test_folder = self._get_test_folder(pump_series, test_type)

        # Load or create scaler
        scaler, scaler_existed = self._load_or_create_scaler(test_folder, file_type)
        data_chunks = []
        for chunk in numeric_chunks:
            # Check if existing scaler has incompatible feature count
            if scaler_existed and hasattr(scaler, "n_features_in_"):
                if scaler.n_features_in_ != chunk.shape[1]:
                    self.logger.warning(
                        f"Feature count changed from {scaler.n_features_in_} to {chunk.shape[1]} "
                        f"for {pump_series}/{test_type} - creating new scaler"
                    )
                    scaler = StandardScaler()
                    scaler_existed = False
            scaler.partial_fit(chunk)
            data_chunks.append(chunk)

        scaled_data = np.vstack([scaler.transform(chunk) for chunk in data_chunks])
        input_dim = scaled_data.shape[1]

        # Check for existing model in the test folder
        model_path = self._get_model_path(test_folder, file_type)
        model: Autoencoder
        is_new_model = True
        base_file_count = 0
        version = 1

        if model_path.exists():
            # Model exists - fine-tune it
            try:
                existing_record = self.database.get_latest_model_record(
                    pump_series, test_type, file_type
                )

                if existing_record and existing_record.input_dim == input_dim:
                    model = self._load_model(str(model_path), input_dim)
                    is_new_model = False
                    version = existing_record.version + 1
                    base_file_count = existing_record.file_count
                    self.logger.info(
                        f"Fine-tuning existing model for {pump_series}/{test_type} "
                        f"(version {version})"
                    )
                else:
                    # Input dimension changed - create new model
                    model = Autoencoder(input_dim)
                    if existing_record:
                        version = existing_record.version + 1
                        base_file_count = existing_record.file_count
                        self.logger.warning(
                            f"Input dimension changed for {pump_series}/{test_type} - "
                            f"creating new model architecture"
                        )
            except Exception as exc:
                self.logger.warning(
                    f"Failed to load existing model from {model_path}: {exc}. "
                    f"Creating new model."
                )
                model = Autoencoder(input_dim)
        else:
            # No model exists - create new one
            model = Autoencoder(input_dim)
            self.logger.info(
                f"Creating new model for {pump_series}/{test_type} (version {version})"
            )

        # Train the model
        metrics = self._train_model(model, scaled_data)

        # Persist model, scaler, and metadata in test folder
        metadata = self._persist_model(
            model,
            scaler,
            test_folder=test_folder,
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            version=version,
            input_dim=input_dim,
            file_count=base_file_count + 1,
            metrics=metrics,
            files=[dataset_path.name],
            is_new_model=is_new_model,
        )

        # Register in database
        self.database.record_model_version(
            pump_series=pump_series,
            test_type=test_type,
            file_type=file_type,
            version=metadata.version,
            model_path=str(model_path),
            scaler_path=str(self._get_scaler_path(test_folder, file_type)),
            metadata_path=str(self._get_metadata_path(test_folder, file_type)),
            file_count=metadata.file_count,
            input_dim=input_dim,
            metrics=metadata.metrics,
        )

        return metadata

    def _get_test_folder(self, pump_series: str, test_type: str) -> Path:
        """Get the test folder where data and models are stored."""
        test_folder = self._files_root / pump_series / "tests" / test_type
        test_folder.mkdir(parents=True, exist_ok=True)
        return test_folder

    def _get_model_path(self, test_folder: Path, file_type: str) -> Path:
        """Get path to model file in test folder."""
        return test_folder / f"model_{file_type}.pkl"

    def _get_scaler_path(self, test_folder: Path, file_type: str) -> Path:
        """Get path to scaler file in test folder."""
        return test_folder / f"scaler_{file_type}.pkl"

    def _get_metadata_path(self, test_folder: Path, file_type: str) -> Path:
        """Get path to metadata file in test folder."""
        return test_folder / f"metadata_{file_type}.json"

    def _resolve_file_type(self, dataset_path: Path) -> str:
        extension = dataset_path.suffix.lower()
        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ModelTrainingError(
                f"Unsupported dataset format '{dataset_path.suffix}'. " f"Supported: csv, parquet."
            )
        return self.SUPPORTED_EXTENSIONS[extension]

    def _load_numeric_chunks(self, dataset_path: Path, file_type: str) -> Iterable[np.ndarray]:
        if file_type == "csv":
            for chunk in pd.read_csv(dataset_path, chunksize=10_000):
                numeric = chunk.select_dtypes(include=["float", "int", "bool"]).apply(
                    pd.to_numeric, errors="coerce"
                )
                numeric = (
                    numeric.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").fillna(0.0)
                )
                if numeric.empty:
                    continue
                yield numeric.to_numpy(dtype=np.float32)
        else:
            dataframe = (
                pd.read_parquet(dataset_path)
                .select_dtypes(include=["float", "int", "bool"])
                .apply(pd.to_numeric, errors="coerce")
            )
            dataframe = (
                dataframe.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how="all").fillna(0.0)
            )
            if not dataframe.empty:
                yield dataframe.to_numpy(dtype=np.float32)

    def _load_or_create_scaler(
        self,
        test_folder: Path,
        file_type: str,
    ) -> Tuple[StandardScaler, bool]:
        scaler_path = self._get_scaler_path(test_folder, file_type)
        if scaler_path.exists():
            try:
                scaler = joblib.load(scaler_path)
                if isinstance(scaler, StandardScaler):
                    return scaler, True
            except Exception as exc:
                self.logger.warning(f"Failed to load scaler from {scaler_path}: {exc}")
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
        test_folder: Path,
        pump_series: str,
        test_type: str,
        file_type: str,
        version: int,
        input_dim: int,
        file_count: int,
        metrics: Dict[str, float],
        files: List[str],
        is_new_model: bool,
    ) -> ModelMetadata:
        """Save model, scaler, and metadata in the test folder."""

        # Save current model
        model_path = self._get_model_path(test_folder, file_type)
        scaler_path = self._get_scaler_path(test_folder, file_type)
        metadata_path = self._get_metadata_path(test_folder, file_type)

        joblib.dump(model.state_dict(), model_path)
        joblib.dump(scaler, scaler_path)

        # Create metadata
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
            is_new_model=is_new_model,
        )
        metadata_path.write_text(metadata.to_json(), encoding="utf-8")

        # Also save versioned copies for history
        versioned_model = test_folder / f"model_{file_type}_v{version:03d}.pkl"
        versioned_scaler = test_folder / f"scaler_{file_type}_v{version:03d}.pkl"
        versioned_metadata = test_folder / f"metadata_{file_type}_v{version:03d}.json"

        joblib.dump(model.state_dict(), versioned_model)
        joblib.dump(scaler, versioned_scaler)
        versioned_metadata.write_text(metadata.to_json(), encoding="utf-8")

        self.logger.info(
            f"Saved {'new' if is_new_model else 'fine-tuned'} model to {model_path} "
            f"(version {version})"
        )

        return metadata

    def _load_model(self, model_path: str, input_dim: int) -> Autoencoder:
        state = joblib.load(model_path)
        model = Autoencoder(input_dim)
        if isinstance(state, dict):
            model.load_state_dict(state)
        else:
            raise ModelTrainingError(f"Invalid model state stored at {model_path}")
        return model


__all__ = ["EnhancedModelManager", "ModelMetadata", "ModelTrainingError"]
