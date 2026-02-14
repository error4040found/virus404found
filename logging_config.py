"""
Logging configuration for the application
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

from config import LOGS_DIR, LOG_FORMAT, LOG_LEVEL_CONFIG


def setup_logging():
    """
    Configure logging for the entire application
    """
    # Create log file with current date
    log_file = LOGS_DIR / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL_CONFIG),
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    return logging.getLogger(__name__)


def get_logger(name: str):
    """
    Get a logger instance for a module

    Args:
        name: Name of the module

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
