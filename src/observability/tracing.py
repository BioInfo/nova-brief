"""
Tracing and event emission for research agent operations.
Provides structured event tracking for debugging and monitoring.
"""

import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class TraceEvent:
    """Structured trace event for agent operations."""
    event_id: str
    timestamp: float
    event_type: str
    component: str
    operation: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    parent_id: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class TraceCollector:
    """Collects and manages trace events."""
    
    def __init__(self):
        self.events = []
        self.active_spans = {}
    
    def start_span(self, operation: str, component: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new trace span.
        
        Args:
            operation: Operation name
            component: Component name
            data: Additional data
        
        Returns:
            Span ID
        """
        span_id = str(uuid.uuid4())
        self.active_spans[span_id] = {
            "start_time": time.time(),
            "operation": operation,
            "component": component,
            "data": data or {}
        }
        return span_id
    
    def end_span(self, span_id: str, success: bool = True, error: Optional[str] = None, 
                 additional_data: Optional[Dict[str, Any]] = None):
        """
        End a trace span and emit event.
        
        Args:
            span_id: Span ID from start_span
            success: Whether operation succeeded
            error: Error message if failed
            additional_data: Additional data to include
        """
        if span_id not in self.active_spans:
            logger.warning(f"Attempted to end unknown span: {span_id}")
            return
        
        span = self.active_spans.pop(span_id)
        end_time = time.time()
        duration_ms = (end_time - span["start_time"]) * 1000
        
        # Merge data
        event_data = span["data"].copy()
        if additional_data:
            event_data.update(additional_data)
        
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            timestamp=end_time,
            event_type="span",
            component=span["component"],
            operation=span["operation"],
            data=event_data,
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        
        self.emit_event(event)
    
    def emit_event(self, event: TraceEvent):
        """
        Emit a trace event.
        
        Args:
            event: TraceEvent to emit
        """
        self.events.append(event)
        
        # Log the event
        logger.info(
            f"TRACE: {event.component}.{event.operation}",
            extra={
                "trace_event": asdict(event),
                "event_id": event.event_id,
                "component": event.component,
                "operation": event.operation,
                "duration_ms": event.duration_ms,
                "success": event.success
            }
        )
    
    def get_events(self) -> list:
        """Get all collected events."""
        return self.events.copy()
    
    def clear_events(self):
        """Clear all collected events."""
        self.events.clear()


# Global trace collector
trace_collector = TraceCollector()


def emit_event(event_type: str, component: str, operation: str, data: Dict[str, Any], 
               success: bool = True, error: Optional[str] = None) -> str:
    """
    Emit a standalone trace event.
    
    Args:
        event_type: Type of event
        component: Component name
        operation: Operation name
        data: Event data
        success: Whether operation succeeded
        error: Error message if failed
    
    Returns:
        Event ID
    """
    event = TraceEvent(
        event_id=str(uuid.uuid4()),
        timestamp=time.time(),
        event_type=event_type,
        component=component,
        operation=operation,
        data=data,
        success=success,
        error=error
    )
    
    trace_collector.emit_event(event)
    return event.event_id


def start_span(operation: str, component: str, data: Optional[Dict[str, Any]] = None) -> str:
    """Start a trace span."""
    return trace_collector.start_span(operation, component, data)


def end_span(span_id: str, success: bool = True, error: Optional[str] = None, 
             additional_data: Optional[Dict[str, Any]] = None):
    """End a trace span."""
    trace_collector.end_span(span_id, success, error, additional_data)


def get_trace_events() -> list:
    """Get all trace events."""
    return trace_collector.get_events()


def clear_trace_events():
    """Clear all trace events."""
    trace_collector.clear_events()