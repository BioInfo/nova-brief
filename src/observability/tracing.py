"""Tracing and event emission for Nova Brief."""

import time
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraceEvent:
    """Represents a trace event with structured data."""
    
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    trace_id: Optional[str] = None


def emit_event(
    event_type: str,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
    parent_id: Optional[str] = None,
    trace_id: Optional[str] = None
) -> None:
    """
    Emit a trace event.
    
    Args:
        event_type: Type of event (e.g., "search_start", "fetch_complete")
        metadata: Additional structured data
        duration_ms: Duration of the operation in milliseconds
        parent_id: ID of parent span/event
        trace_id: ID of the overall trace
    """
    event = TraceEvent(
        event_type=event_type,
        metadata=metadata or {},
        duration_ms=duration_ms,
        parent_id=parent_id,
        trace_id=trace_id
    )
    
    # For MVP, log events as structured logs
    # In Stage 3+, this would emit to OpenTelemetry
    logger.info(
        f"Trace event: {event_type}",
        extra={
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "duration_ms": duration_ms,
            "metadata": metadata or {},
            "parent_id": parent_id,
            "trace_id": trace_id
        }
    )


def start_span(span_name: str, parent_id: Optional[str] = None) -> str:
    """
    Start a new span for timing operations.
    
    Args:
        span_name: Name of the span
        parent_id: ID of parent span
    
    Returns:
        Span ID for tracking
    """
    span_id = f"{span_name}_{int(time.time() * 1000)}"
    
    emit_event(
        "span_start",
        metadata={"span_name": span_name, "span_id": span_id},
        parent_id=parent_id
    )
    
    return span_id


def end_span(span_id: str, start_time: float, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    End a span and emit duration.
    
    Args:
        span_id: ID of the span to end
        start_time: Start time from time.time()
        metadata: Additional metadata to include
    """
    duration_ms = (time.time() - start_time) * 1000
    
    emit_event(
        "span_end",
        metadata={
            "span_id": span_id,
            **(metadata or {})
        },
        duration_ms=duration_ms
    )


class TimedOperation:
    """Context manager for timing operations with automatic span management."""
    
    def __init__(self, operation_name: str, parent_id: Optional[str] = None):
        self.operation_name = operation_name
        self.parent_id = parent_id
        self.span_id: Optional[str] = None
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> "TimedOperation":
        self.start_time = time.time()
        self.span_id = start_span(self.operation_name, self.parent_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.span_id and self.start_time:
            metadata = {}
            if exc_type:
                metadata["error"] = str(exc_val)
                metadata["error_type"] = exc_type.__name__
            
            end_span(self.span_id, self.start_time, metadata)