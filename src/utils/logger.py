"""Logging utility for Industrial Data Upload System."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import DATA_DIR, load_app_config

LOG_FILE = DATA_DIR / "industrial_data_uploader.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    """Configure application logging with rotation."""

    config = load_app_config()
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    logging.basicConfig(level=log_level)
    logger = logging.getLogger()

    handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Avoid duplicate handlers during reconfiguration
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        logger.addHandler(handler)
