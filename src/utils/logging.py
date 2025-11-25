"""
Logging configuration for the book recommendation system.

Provides structured logging with file rotation, color-coded console output,
and configurable log levels for different environments.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color-coded log levels for console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        """Format log record with colors for console output."""
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: Optional[str] = "logs",
    console: bool = True,
    file_logging: bool = True
) -> logging.Logger:
    """
    Set up a logger with console and file handlers.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (default: "logs")
        console: Enable console output (default: True)
        file_logging: Enable file logging (default: True)

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Application started")
        >>> logger.debug("Debug information", extra={"user_id": 123})
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    colored_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler with colors
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(colored_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if file_logging and log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Main log file with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            log_path / f"{name.replace('.', '_')}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

        # Error log file (errors only)
        error_handler = RotatingFileHandler(
            log_path / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with default configuration.

    This is a convenience function that uses standard settings.
    For custom configuration, use setup_logger() directly.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance

    Example:
        >>> from src.utils.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Process started")
    """
    logger = logging.getLogger(name)

    # If logger already configured, return it
    if logger.handlers:
        return logger

    # Otherwise set up with defaults
    return setup_logger(name)


# Pre-configured loggers for common use cases
def setup_production_logging():
    """
    Configure logging for production environment.

    - Console: INFO level only
    - File: DEBUG level with rotation
    - Errors: Separate error.log file
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]
    )


def setup_development_logging():
    """
    Configure logging for development environment.

    - Console: DEBUG level with colors
    - File: DEBUG level with detailed format
    """
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
        handlers=[]
    )


def disable_external_loggers():
    """
    Disable or reduce verbosity of external library loggers.

    Useful to reduce noise from chromadb, openai, etc.
    """
    # Reduce chromadb verbosity
    logging.getLogger('chromadb').setLevel(logging.WARNING)

    # Reduce OpenAI API verbosity
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

    # Reduce other common noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
