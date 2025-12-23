import logging
import sys
from typing import Optional


_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """
    Configure structured logging once per process.
    Safe to call multiple times.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )

    _LOGGING_CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a named logger.
    If name is None, returns root logger.
    """
    return logging.getLogger(name)
