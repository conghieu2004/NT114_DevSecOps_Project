import logging
import os
from logging.handlers import RotatingFileHandler

def get_logger(name):
    """Get logger instance with consistent formatting"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler only (to avoid conflicts with gunicorn)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

def setup_logger():
    """Setup root logger"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

# New: helper functions to ease testing/logger control
def has_handlers(name):
    """Return True if the logger has any handlers attached."""
    return bool(logging.getLogger(name).handlers)

def reset_logger(name):
    """Remove all handlers of a logger (useful for tests)."""
    logger = logging.getLogger(name)
    for h in list(logger.handlers):
        logger.removeHandler(h)
    return logger

def add_rotating_file_handler(logger, file_path, level=logging.INFO, max_bytes=1024 * 1024, backup_count=1):
    """Attach a RotatingFileHandler to a logger and return the handler."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    handler = RotatingFileHandler(file_path, maxBytes=max_bytes, backupCount=backup_count)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return handler