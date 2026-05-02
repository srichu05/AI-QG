"""
utils.py
========
Shared utility functions used across the AI-QG application.
Provides logging setup, timing decorators, text cleaning helpers,
and UUID generation.
"""

import logging
import re
import time
import uuid
import functools
from pathlib import Path
from typing import Any, Callable

from config import LogConfig, LOG_DIR


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logger(name: str, log_file: Path | None = None) -> logging.Logger:
    """
    Create and configure a named logger.

    Parameters
    ----------
    name : str
        Logger name (usually __name__ of the calling module).
    log_file : Path, optional
        If provided, also logs to this file. Defaults to the app-wide log file.

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(getattr(logging, LogConfig.LEVEL, logging.INFO))

    formatter = logging.Formatter(LogConfig.FORMAT, datefmt=LogConfig.DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    target_file = log_file or LogConfig.FILE
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(target_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("Could not create log file at %s", target_file)

    return logger


# ---------------------------------------------------------------------------
# Timing decorator
# ---------------------------------------------------------------------------

def timed(func: Callable) -> Callable:
    """
    Decorator that logs the execution time of a function.
    """
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("%s completed in %.2fs", func.__qualname__, elapsed)
        return result

    return wrapper


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Normalise whitespace, strip control characters, and collapse blank lines.

    Parameters
    ----------
    text : str
        Raw text to clean.

    Returns
    -------
    str
        Cleaned text.
    """
    if not text:
        return ""

    # Replace common unicode artefacts
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u00a0", " ")  # non-breaking space

    # Remove control characters except newline / tab
    text = re.sub(r"[^\S \n\t]+", " ", text)

    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)

    return text.strip()


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace into single spaces and strip."""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# UUID helpers
# ---------------------------------------------------------------------------

def generate_uuid() -> str:
    """Return a new UUID4 string."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def get_file_extension(filename: str) -> str:
    """Return lowercased file extension without the dot."""
    return Path(filename).suffix.lstrip(".").lower()


def safe_filename(filename: str) -> str:
    """
    Sanitise a filename by removing potentially dangerous characters.
    """
    # Keep only alphanumeric, dashes, underscores, dots
    name = re.sub(r"[^\w.\-]", "_", filename)
    # Collapse multiple underscores
    name = re.sub(r"_{2,}", "_", name)
    return name
