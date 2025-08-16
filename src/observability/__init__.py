"""
Observability package for Nova Brief research agent.
Provides logging, tracing, and monitoring capabilities.
"""

from .logging import get_logger, configure_logging, redact_sensitive_data
from .tracing import emit_event, TraceEvent

__all__ = ["get_logger", "configure_logging", "redact_sensitive_data", "emit_event", "TraceEvent"]