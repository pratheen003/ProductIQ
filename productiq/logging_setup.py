"""
ProductIQ Logging Setup
-----------------------
Configures structured logging for the application.
NEVER logs API keys, secrets, or sensitive configuration values.
"""
import io
import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Configure root logger for ProductIQ.

    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured root logger.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Use UTF-8 / safe stream wrapper on stdout
    stream = sys.stdout
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger("productiq")
    root_logger.setLevel(numeric_level)

    # Avoid adding duplicate handlers on repeated calls
    if not root_logger.handlers:
        root_logger.addHandler(handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger under the 'productiq' namespace."""
    return logging.getLogger(f"productiq.{name}")
