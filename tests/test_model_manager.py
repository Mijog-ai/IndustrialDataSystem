import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from industrial_data_system.core import config as config_module
from industrial_data_system.core.database import SQLiteDatabase
from industrial_data_system.core.db_manager import DatabaseManager
from industrial_data_system.core.model_manager import AutoencoderModelManager, ModelTrainingError


@pytest.fixture()
def isolated_config(tmp_path, monkeypatch):
    shared = tmp_path / "shared"
    files = shared / "files"
    database_path = shared / "database" / "industrial.db"
    monkeypatch.setenv("SHARED_DRIVE_PATH", str(shared))
    monkeypatch.setenv("FILES_BASE_PATH", str(files))
    monkeypatch.setenv("DATABASE_PATH", str(database_path))

    # Reset cached config
    config_module._CONFIG_SINGLETON = None
    config_module._ENV_INITIALISED = False
    config = config_module.get_config()

    database = SQLiteDatabase(config.database_path)
    database.initialise()
    db_manager = DatabaseManager(database=database)

    yield config, db_manager

    # Cleanup singleton for subsequent tests
    config_module._CONFIG_SINGLETON = None
    config_module._ENV_INITIALISED = False


def _write_csv(path: Path, rows: int = 100, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    data = {
        "pressure": rng.normal(loc=10.0, scale=1.0, size=rows),
        "flow": rng.normal(loc=5.0, scale=0.5, size=rows),
        "temperature": rng.normal(loc=300.0, scale=10.0, size=rows),
    }
    df = pd.DataFrame(data)
    df.to_csv(path, index=False)


def test_initial_training_persists_files(isolated_config, tmp_path):
    config, db_manager = isolated_config
    trainer = AutoencoderModelManager(
        config=config,
        database=db_manager,
        max_epochs=2,
        batch_size=32,
    )

    dataset = tmp_path / "dataset.csv"
    _write_csv(dataset)

    metadata = trainer.handle_new_dataset(dataset, pump_series="P100", test_type="performance")

    models_dir = config.shared_drive_path / "industrialDATA" / "models" / "P100" / "performance" / "csv"
    files_dir = config.shared_drive_path / "industrialDATA" / "files" / "P100" / "performance" / "csv"

    assert (models_dir / "model.pkl").exists()
    assert (models_dir / "scaler.pkl").exists()
    assert (models_dir / "metadata.json").exists()
    assert metadata.version == 1
    assert metadata.file_count == 1
    assert metadata.input_dim == 3

    stored_files = list(files_dir.glob("*.csv"))
    assert stored_files, "raw dataset should be copied into managed storage"

    record = db_manager.get_latest_model_record("P100", "performance", "csv")
    assert record is not None
    assert record.version == 1
    assert json.loads(json.dumps(record.metrics)) == record.metrics


def test_incremental_training_updates_version(isolated_config, tmp_path):
    config, db_manager = isolated_config
    trainer = AutoencoderModelManager(
        config=config,
        database=db_manager,
        max_epochs=2,
        batch_size=32,
    )

    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_csv(first, seed=1)
    _write_csv(second, seed=2)

    trainer.handle_new_dataset(first, pump_series="V60N", test_type="vibration")
    metadata = trainer.handle_new_dataset(second, pump_series="V60N", test_type="vibration")

    assert metadata.version == 2
    assert metadata.file_count == 2

    record = db_manager.get_latest_model_record("V60N", "vibration", "csv")
    assert record is not None
    assert record.version == 2
    assert record.file_count == 2


def test_rejects_non_numeric_payload(isolated_config, tmp_path):
    config, db_manager = isolated_config
    trainer = AutoencoderModelManager(
        config=config,
        database=db_manager,
        max_epochs=1,
        batch_size=16,
    )

    dataset = tmp_path / "text.csv"
    pd.DataFrame({"name": ["a", "b"], "category": ["x", "y"]}).to_csv(dataset, index=False)

    with pytest.raises(ModelTrainingError):
        trainer.handle_new_dataset(dataset, pump_series="PX", test_type="string-test")
