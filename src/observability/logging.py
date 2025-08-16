"""Logging configuration and utilities for Nova Brief."""

import logging
import os
import sys
from typing import Any, Dict, Optional


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        _configure_logger(logger)
    
    return logger


def _configure_logger(logger: logging.Logger) -> None:
    """Configure logger with appropriate handlers and formatting."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)
    
    # Structured format
    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False


def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive information from log data.
    
    Args:
        data: Dictionary that may contain sensitive information
    
    Returns:
        Dictionary with sensitive data redacted
    """
    sensitive_keys = {
        "api_key", "openrouter_api_key", "password", "token", 
        "secret", "key", "auth", "authorization"
    }
    
    redacted = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        else:
            redacted[key] = value
    
    return redacted


def log_function_call(
    logger: logging.Logger,
    function_name: str,
    args: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log a function call with structured data.
    
    Args:
        logger: Logger instance
        function_name: Name of the function being called
        args: Function arguments (will be redacted for sensitive data)
        duration_ms: Duration of the function call in milliseconds
    """
    log_data: Dict[str, Any] = {
        "event": "function_call",
        "function": function_name,
    }
    
    if args:
        log_data["args"] = redact_sensitive_data(args)
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    logger.info(f"Function call: {function_name}", extra=log_data)