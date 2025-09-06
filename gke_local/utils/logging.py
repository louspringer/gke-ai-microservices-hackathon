"""Logging utilities for GKE Local."""

import logging
import sys
from typing import Optional
from ..config.models import LogLevel


def setup_logging(level: LogLevel = LogLevel.INFO, verbose: bool = False) -> logging.Logger:
    """Setup logging configuration.
    
    Args:
        level: Log level from configuration
        verbose: Enable verbose logging
        
    Returns:
        Configured logger instance
    """
    level_map = {
        LogLevel.DEBUG: logging.DEBUG,
        LogLevel.INFO: logging.INFO,
        LogLevel.WARNING: logging.WARNING,
        LogLevel.ERROR: logging.ERROR
    }
    
    log_level = level_map.get(level, logging.INFO)
    if verbose:
        log_level = logging.DEBUG
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)