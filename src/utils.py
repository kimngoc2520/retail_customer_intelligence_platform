"""
Shared utilities used across src/*.py:
  - get_logger(): single logger factory so every module logs to the
    same file/format instead of each rolling its own.
  - timer: decorator to log how long a pipeline step took.
  - save_model()/load_model(): thin joblib wrapper, one convention
    for reading/writing anything in models/.
  - set_random_seed(): one place to seed randomness for reproducibility.

This is a library module — no run() entrypoint, since nothing here
represents a standalone pipeline step (main.py never calls src.utils directly).
"""

import functools
import logging
import random
import time
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np

from src.config import LOGS_DIR, MODELS_DIR, RANDOM_STATE

_LOG_FILE = LOGS_DIR / "pipeline.log"


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured to write to logs/pipeline.log AND stdout.
    Safe to call multiple times with the same name — won't add duplicate handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # already configured (avoids duplicate handlers on re-import)
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def timer(func: Callable) -> Callable:
    """Decorator: logs how long the wrapped function took to run.
    Usage: put @timer directly above a function definition in src/*.py"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        log = get_logger(func.__module__)
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        log.info(f"{func.__name__} finished in {elapsed:.2f}s")
        return result
    return wrapper


def save_model(obj: Any, filename: str) -> Path:
    """Save any picklable object (model, scaler, list of columns...) to models/."""
    path = MODELS_DIR / filename
    joblib.dump(obj, path)
    get_logger(__name__).info(f"Saved {filename} to {path}")
    return path


def load_model(filename: str) -> Any:
    """Load an object previously saved with save_model().
    Raises FileNotFoundError with a clear next step if the file is missing."""
    path = MODELS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python -m src.segmentation` first "
            f"(or whichever step is supposed to produce {filename})."
        )
    return joblib.load(path)


def set_random_seed(seed: int = RANDOM_STATE) -> None:
    """Call once at the start of any script that uses randomness
    (segmentation, train/test splits, etc.) for reproducible results."""
    random.seed(seed)
    np.random.seed(seed)
