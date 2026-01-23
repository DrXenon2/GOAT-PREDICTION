"""
Structured logging configuration for GOAT Prediction API Gateway.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.processors import (
    JSONRenderer,
    TimeStamper,
    add_log_level,
    format_exc_info,
    UnicodeDecoder,
)
from structlog.stdlib import (
    BoundLogger,
    ProcessorFormatter,
    add_logger_name,
    filter_by_level,
)
from structlog.types import EventDict, Processor


def setup_logging():
    """Configure structured logging for the application."""
    
    # Common processors for both structlog and standard logging
    timestamper = TimeStamper(fmt="iso", utc=True)
    
    # Structlog processors
    structlog_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # Custom processor to add request_id
        add_request_id,
        # Custom processor to add correlation_id
        add_correlation_id,
        # Remove excessive data in production
        clean_log_event,
        # Render as JSON
        structlog.processors.JSONRenderer(),
    ]
    
    # Configure structlog
    structlog.configure(
        processors=structlog_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=BoundLogger,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Get root logger and set level
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove all handlers
    root_logger.handlers.clear()
    
    # Add our custom handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Use ProcessorFormatter to format standard library logs as JSON
    handler.setFormatter(
        ProcessorFormatter(
            processor=JSONRenderer(),
            foreign_pre_chain=[
                add_log_level,
                add_logger_name,
                timestamper,
                format_exc_info,
                UnicodeDecoder(),
            ],
        )
    )
    
    root_logger.addHandler(handler)
    
    # Silence noisy loggers
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.error").handlers.clear()
    
    # Create our own uvicorn access logger
    uvicorn_access_logger = structlog.stdlib.get_logger("uvicorn.access")
    uvicorn_error_logger = structlog.stdlib.get_logger("uvicorn.error")
    
    # Redirect uvicorn logs through structlog
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]
    
    # Set log levels for specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aioredis").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def add_request_id(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request_id to log event if available."""
    import asyncio
    
    try:
        # Try to get request_id from asyncio context
        current_task = asyncio.current_task()
        if current_task:
            request_id = getattr(current_task, "request_id", None)
            if request_id:
                event_dict["request_id"] = request_id
    except (RuntimeError, AttributeError):
        pass
    
    return event_dict


def add_correlation_id(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation_id to log event if available."""
    import asyncio
    
    try:
        # Try to get correlation_id from asyncio context
        current_task = asyncio.current_task()
        if current_task:
            correlation_id = getattr(current_task, "correlation_id", None)
            if correlation_id:
                event_dict["correlation_id"] = correlation_id
    except (RuntimeError, AttributeError):
        pass
    
    return event_dict


def clean_log_event(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Clean and standardize log events."""
    
    # Remove excessive whitespace in messages
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = " ".join(event_dict["event"].split())
    
    # Ensure all values are JSON serializable
    for key, value in list(event_dict.items()):
        if isinstance(value, (set, tuple)):
            event_dict[key] = list(value)
        elif hasattr(value, "__dict__"):
            event_dict[key] = str(value)
    
    # Add service name
    event_dict["service"] = "goat-api-gateway"
    
    return event_dict


def get_logger(name: str = None) -> BoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


# Export the configured logger
log = get_logger(__name__)
