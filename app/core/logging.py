"""Logging configuration for the application"""
import logging
import sys
from pathlib import Path

from app.core.config import config


def setup_logging():
    """Configure application logging"""
    
    # Configure root logger
    log_level = logging.DEBUG if config.DEBUG else logging.INFO
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(levelname)s: %(message)s'
    )
    
    # Console handler (always enabled - works on App Engine)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(detailed_formatter if not config.DEBUG else simple_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Only add file handlers in development (App Engine filesystem is read-only)
    if config.DEBUG:
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # File handler (errors only)
            error_file_handler = logging.FileHandler(log_dir / 'error.log')
            error_file_handler.setLevel(logging.ERROR)
            error_file_handler.setFormatter(detailed_formatter)
            
            # File handler (all logs)
            file_handler = logging.FileHandler(log_dir / 'app.log')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(detailed_formatter)
            
            root_logger.addHandler(error_file_handler)
            root_logger.addHandler(file_handler)
        except OSError:
            # Filesystem is read-only (e.g., App Engine), skip file logging
            pass
    
    # Silence noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
