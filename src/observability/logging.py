"""
Logging configuration and utilities for the research agent.
Provides structured logging with request IDs and sensitive data redaction.
"""

import logging
import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON-like logging."""
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'message', 'exc_info', 'exc_text',
                          'stack_info']:
                log_entry[key] = value
        
        return str(log_entry)


def configure_logging():
    """Configure application-wide logging settings."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Set formatter
    formatter = StructuredFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive information from log data.
    
    Args:
        data: Dictionary that may contain sensitive data
    
    Returns:
        Dictionary with sensitive fields redacted
    """
    sensitive_keys = {
        "api_key", "token", "password", "secret", "auth", "authorization",
        "x-api-key", "x-auth-token"
    }
    
    redacted_data = {}
    for key, value in data.items():
        if key.lower() in sensitive_keys:
            redacted_data[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted_data[key] = redact_sensitive_data(value)
        else:
            redacted_data[key] = value
    
    return redacted_data


# Configure logging on module import
configure_logging()