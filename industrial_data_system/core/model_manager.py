"""Autoencoder training management triggered by dataset uploads."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import dump, load
from sklearn.metrics import mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


LOGGER = logging.getLogger(__name__)


class ModelTrainingError(RuntimeError):
    """Raised when training a model cannot be completed."""


@dataclass
class _TrainingData:
    """Container describing the aggregated training dataset."""

    frame: pd.DataFrame
    sources: List[Dict[str, object]]


class AutoencoderModelManager:
    """Orchestrate autoencoder training for uploaded datasets."""

    #: Supported file extensions and their respective pandas readers.
    _READERS = {
        ".csv": pd.read_csv,
        ".parquet": pd.read_parquet,
        ".feather": pd.read_feather,
        ".xlsx": pd.read_excel,
        ".xls": pd.read_excel,
        ".xlsm": pd.read_excel,
    }

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or LOGGER

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def handle_new_dataset(self, dataset_path: Path, *, pump_series: str, test_type: str) -> None:
        """Train or retrain an autoencoder for the provided dataset.

        Parameters
        ----------
        dataset_path:
            Absolute path to the uploaded dataset file.
        pump_series / test_type:
            Metadata used for logging and metadata files.
        """

        test_folder = dataset_path.parent
        models_dir = test_folder / "models"
        logs_dir = test_folder / "logs"
        models_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        training_data = self._collect_training_data(test_folder)
        if training_data is None:
            raise ModelTrainingError(
                f"No numeric data available to train autoencoder for '{pump_series}/{test_type}'."
            )

        previous_bundle = self._load_latest_model_bundle(models_dir)
        hidden_layers = self._resolve_hidden_layers(previous_bundle, training_data.frame.shape[1])

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        version_name = f"model_{timestamp}"
        version_dir = models_dir / version_name
        log_dir = logs_dir / version_name
        version_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)

        scaler = StandardScaler()
        numeric_frame = training_data.frame.astype(float)
        scaled_values = scaler.fit_transform(numeric_frame)

        autoencoder = self._initialise_model(previous_bundle, hidden_layers)
        autoencoder.fit(scaled_values, scaled_values)

        reconstructions = autoencoder.predict(scaled_values)
        reconstruction_error = float(mean_squared_error(scaled_values, reconstructions))

        bundle = {
            "model": autoencoder,
            "scaler": scaler,
            "feature_names": numeric_frame.columns.tolist(),
            "hidden_layer_sizes": autoencoder.hidden_layer_sizes,
            "trained_at": timestamp,
            "pump_series": pump_series,
            "test_type": test_type,
            "num_samples": int(numeric_frame.shape[0]),
            "num_features": int(numeric_frame.shape[1]),
            "based_on": previous_bundle.get("version") if previous_bundle else None,
            "version": version_name,
        }
        dump(bundle, version_dir / "autoencoder.joblib")

        metadata = {
            "pump_series": pump_series,
            "test_type": test_type,
            "created_at_utc": timestamp,
            "num_samples": int(numeric_frame.shape[0]),
            "num_features": int(numeric_frame.shape[1]),
            "reconstruction_mse": reconstruction_error,
            "feature_names": numeric_frame.columns.tolist(),
            "data_sources": training_data.sources,
            "based_on": previous_bundle.get("version") if previous_bundle else None,
        }
        (version_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        log_payload = {
            "pump_series": pump_series,
            "test_type": test_type,
            "version": version_name,
            "trained_at_utc": timestamp,
            "num_samples": int(numeric_frame.shape[0]),
            "num_features": int(numeric_frame.shape[1]),
            "reconstruction_mse": reconstruction_error,
        }
        (log_dir / "metrics.json").write_text(json.dumps(log_payload, indent=2), encoding="utf-8")

        self._logger.info(
            "Autoencoder model trained for %s/%s - version %s (MSE=%.6f)",
            pump_series,
            test_type,
            version_name,
            reconstruction_error,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _collect_training_data(self, test_folder: Path) -> Optional[_TrainingData]:
        data_frames: List[pd.DataFrame] = []
        sources: List[Dict[str, object]] = []

        for path in sorted(test_folder.iterdir()):
            if path.is_dir():
                continue
            loader = self._READERS.get(path.suffix.lower())
            if loader is None:
                continue
            try:
                frame = loader(path)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover - defensive
                self._logger.warning("Failed to read dataset '%s': %s", path.name, exc)
                continue

            numeric = frame.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
            numeric = numeric.dropna(axis=0, how="any")
            if numeric.empty:
                continue

            data_frames.append(numeric)
            sources.append(
                {
                    "file": path.name,
                    "rows": int(numeric.shape[0]),
                    "columns": numeric.columns.tolist(),
                }
            )

        if not data_frames:
            return None

        combined = pd.concat(data_frames, axis=0, ignore_index=True)
        if combined.empty:
            return None

        # Limit to a reasonable sample size to avoid memory blow-ups.
        max_rows = 100_000
        if combined.shape[0] > max_rows:
            combined = combined.sample(max_rows, random_state=42).reset_index(drop=True)

        return _TrainingData(frame=combined, sources=sources)

    def _load_latest_model_bundle(self, models_dir: Path) -> Optional[Dict[str, object]]:
        if not models_dir.exists():
            return None

        version_dirs = [path for path in models_dir.iterdir() if path.is_dir() and path.name.startswith("model_")]
        if not version_dirs:
            return None

        latest_dir = max(version_dirs, key=lambda item: item.name)
        bundle_path = latest_dir / "autoencoder.joblib"
        if not bundle_path.is_file():
            return None

        try:
            bundle: Dict[str, object] = load(bundle_path)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Unable to load previous model bundle '%s': %s", bundle_path, exc)
            return None

        bundle["version"] = latest_dir.name
        return bundle

    def _resolve_hidden_layers(
        self, previous_bundle: Optional[Dict[str, object]], num_features: int
    ) -> Tuple[int, ...]:
        if previous_bundle and "hidden_layer_sizes" in previous_bundle:
            sizes = previous_bundle["hidden_layer_sizes"]
            if isinstance(sizes, tuple):
                return sizes
            if isinstance(sizes, list):
                return tuple(int(s) for s in sizes)

        # Default to a single bottleneck layer with half the number of features.
        bottleneck = max(2, min(128, max(1, num_features // 2)))
        return (bottleneck,)

    def _initialise_model(
        self, previous_bundle: Optional[Dict[str, object]], hidden_layers: Tuple[int, ...]
    ) -> MLPRegressor:
        if previous_bundle and "model" in previous_bundle:
            model = previous_bundle["model"]
            if isinstance(model, MLPRegressor):
                model.hidden_layer_sizes = hidden_layers
                model.random_state = 42
                model.max_iter = 500
                model.warm_start = True
                model.early_stopping = True
                model.n_iter_ = 0
                return model

        return MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            solver="adam",
            max_iter=500,
            random_state=42,
            early_stopping=True,
            warm_start=True,
        )


__all__ = ["AutoencoderModelManager", "ModelTrainingError"]
