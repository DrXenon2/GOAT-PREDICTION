"""
Logging configuration for GOAT Prediction API Gateway.
Structured logging with JSON format, log levels, and comprehensive context.
"""

import logging
import logging.config
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
from structlog.types import EventDict, Processor, WrappedLogger

from . import settings
from .constants import LogLevel, LOG_FIELDS, LOG_FORMATS


class CustomJSONRenderer:
    """Custom JSON renderer with enhanced formatting."""
    
    def __init__(self, sort_keys: bool = True, indent: Optional[int] = None):
        self.sort_keys = sort_keys
        self.indent = indent
        self._json_renderer = JSONRenderer(sort_keys=sort_keys, indent=indent)
    
    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> str:
        """Render event dict as JSON with custom formatting."""
        
        # Ensure all values are JSON serializable
        event_dict = self._ensure_serializable(event_dict)
        
        # Add service context
        event_dict = self._add_service_context(event_dict)
        
        # Format timestamp
        event_dict = self._format_timestamp(event_dict)
        
        # Clean up event dictionary
        event_dict = self._clean_event_dict(event_dict)
        
        return self._json_renderer(logger, name, event_dict)
    
    def _ensure_serializable(self, event_dict: EventDict) -> EventDict:
        """Ensure all values in event dict are JSON serializable."""
        serializable_dict = {}
        
        for key, value in event_dict.items():
            if isinstance(value, (datetime,)):
                serializable_dict[key] = value.isoformat()
            elif hasattr(value, "__dict__"):
                serializable_dict[key] = str(value)
            elif isinstance(value, (set, tuple)):
                serializable_dict[key] = list(value)
            else:
                serializable_dict[key] = value
        
        return serializable_dict
    
    def _add_service_context(self, event_dict: EventDict) -> EventDict:
        """Add service context to log events."""
        
        # Add service name and version
        event_dict["service"] = settings.APP_NAME
        event_dict["service_version"] = settings.APP_VERSION
        event_dict["environment"] = settings.ENVIRONMENT
        
        # Add deployment context
        if settings.BUILD_NUMBER:
            event_dict["build_number"] = settings.BUILD_NUMBER
        
        if settings.COMMIT_HASH:
            event_dict["commit_hash"] = settings.COMMIT_HASH
        
        return event_dict
    
    def _format_timestamp(self, event_dict: EventDict) -> EventDict:
        """Format timestamp consistently."""
        
        if "timestamp" in event_dict:
            timestamp = event_dict["timestamp"]
            
            # Ensure timestamp is in ISO format
            if isinstance(timestamp, datetime):
                event_dict["timestamp"] = timestamp.isoformat()
            elif isinstance(timestamp, str):
                # Try to parse and reformat
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    event_dict["timestamp"] = dt.isoformat()
                except ValueError:
                    # Keep original if parsing fails
                    pass
        
        return event_dict
    
    def _clean_event_dict(self, event_dict: EventDict) -> EventDict:
        """Clean and standardize event dictionary."""
        
        # Remove None values
        event_dict = {k: v for k, v in event_dict.items() if v is not None}
        
        # Ensure event field is present
        if "event" not in event_dict and "msg" in event_dict:
            event_dict["event"] = event_dict.pop("msg")
        elif "event" not in event_dict and "message" in event_dict:
            event_dict["event"] = event_dict.pop("message")
        
        # Ensure event is a string
        if "event" in event_dict and not isinstance(event_dict["event"], str):
            event_dict["event"] = str(event_dict["event"])
        
        # Trim whitespace from event
        if "event" in event_dict and isinstance(event_dict["event"], str):
            event_dict["event"] = event_dict["event"].strip()
        
        # Add log_type if not present
        if "log_type" not in event_dict:
            # Determine log type from event
            event_lower = event_dict.get("event", "").lower()
            if any(word in event_lower for word in ["error", "exception", "failed"]):
                event_dict["log_type"] = "error"
            elif any(word in event_lower for word in ["warning", "warn"]):
                event_dict["log_type"] = "warning"
            elif any(word in event_lower for word in ["request", "response"]):
                event_dict["log_type"] = "http"
            elif any(word in event_lower for word in ["database", "query"]):
                event_dict["log_type"] = "database"
            elif any(word in event_lower for word in ["cache", "redis"]):
                event_dict["log_type"] = "cache"
            else:
                event_dict["log_type"] = "application"
        
        return event_dict


class ContextInjector:
    """Inject contextual information into log events."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context = context or {}
        self._context_stack: List[Dict[str, Any]] = []
    
    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
        """Inject context into event dict."""
        
        # Add global context
        event_dict.update(self.context)
        
        # Add stack context
        for ctx in self._context_stack:
            event_dict.update(ctx)
        
        return event_dict
    
    def push_context(self, **kwargs):
        """Push context onto stack."""
        self._context_stack.append(kwargs)
    
    def pop_context(self) -> Optional[Dict[str, Any]]:
        """Pop context from stack."""
        if self._context_stack:
            return self._context_stack.pop()
        return None
    
    def clear_context(self):
        """Clear all context."""
        self._context_stack.clear()


class RequestContextFilter(logging.Filter):
    """Filter to add request context to log records."""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self._context = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record."""
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            record.request_id = getattr(record, "request_id")
        
        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            record.correlation_id = getattr(record, "correlation_id")
        
        # Add user ID if available
        if hasattr(record, "user_id"):
            record.user_id = getattr(record, "user_id")
        
        # Add custom context
        for key, value in self._context.items():
            setattr(record, key, value)
        
        return True
    
    def set_context(self, **kwargs):
        """Set context for the filter."""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear context from the filter."""
        self._context.clear()


class StructuredLogFormatter(logging.Formatter):
    """Structured log formatter for traditional logging."""
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        super().__init__(fmt, datefmt)
        self._json_renderer = CustomJSONRenderer()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        
        # Build event dictionary from log record
        event_dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }
        
        # Add exception info if present
        if record.exc_info:
            event_dict["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                "args", "asctime", "created", "exc_info", "exc_text", 
                "filename", "funcName", "levelname", "levelno", "lineno",
                "module", "msecs", "message", "msg", "name", "pathname",
                "process", "processName", "relativeCreated", "stack_info", "thread", "threadName"
            ]:
                event_dict[key] = value
        
        # Render as JSON
        return self._json_renderer(None, None, event_dict)


def setup_logging():
    """
    Setup structured logging for the application.
    
    This function:
    1. Configures structlog for structured logging
    2. Sets up traditional logging to use structlog
    3. Configures log levels and handlers
    4. Sets up file and console logging
    """
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine log format
    log_format = settings.LOG_FORMAT if hasattr(settings, "LOG_FORMAT") else "json"
    
    # Configure structlog processors
    processors = get_structlog_processors(log_format)
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=BoundLogger,
    )
    
    # Configure traditional logging
    logging_config = get_logging_config(log_format, log_dir)
    logging.config.dictConfig(logging_config)
    
    # Configure specific loggers
    configure_logger_levels()
    
    # Create root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add our handlers
    if log_format == "json":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ProcessorFormatter(
            processor=CustomJSONRenderer(),
            foreign_pre_chain=[
                add_log_level,
                add_logger_name,
                TimeStamper(fmt="iso", utc=True),
                format_exc_info,
                UnicodeDecoder(),
            ],
        ))
        root_logger.addHandler(handler)
    else:
        # Use basic format for non-JSON logging
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=settings.LOG_DATEFMT,
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # Add file handler if enabled
    if getattr(settings, "FILE_LOGGING_ENABLED", False):
        file_handler = get_file_handler(log_dir, log_format)
        root_logger.addHandler(file_handler)
    
    # Silence noisy loggers
    silence_noisy_loggers()
    
    # Get initial logger
    logger = structlog.get_logger(__name__)
    
    logger.info(
        "logging_configured",
        log_level=settings.LOG_LEVEL,
        log_format=log_format,
        environment=settings.ENVIRONMENT,
        file_logging=getattr(settings, "FILE_LOGGING_ENABLED", False),
    )


def get_structlog_processors(log_format: str) -> List[Processor]:
    """Get structlog processors based on log format."""
    
    # Common processors for all formats
    processors = [
        # Add log level and logger name
        add_log_level,
        add_logger_name,
        
        # Add timestamp
        TimeStamper(fmt="iso", utc=True),
        
        # Add stack info and format exceptions
        structlog.processors.StackInfoRenderer(),
        format_exc_info,
        
        # Decode unicode
        UnicodeDecoder(),
        
        # Add request context
        add_request_context,
        
        # Add correlation context
        add_correlation_context,
        
        # Clean up log events
        clean_log_event,
    ]
    
    # Add format-specific processor
    if log_format == "json":
        processors.append(CustomJSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    return processors


def get_logging_config(log_format: str, log_dir: Path) -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "json" if log_format == "json" else "simple",
            "stream": sys.stdout,
        }
    }
    
    # Add file handler if enabled
    if getattr(settings, "FILE_LOGGING_ENABLED", False):
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.LOG_LEVEL,
            "formatter": "json" if log_format == "json" else "simple",
            "filename": str(log_dir / "app.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        }
        
        # Add error file handler
        handlers["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json" if log_format == "json" else "simple",
            "filename": str(log_dir / "error.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        }
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": StructuredLogFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": settings.LOG_DATEFMT,
            },
        },
        "handlers": handlers,
        "loggers": {
            "": {  # Root logger
                "handlers": list(handlers.keys()),
                "level": settings.LOG_LEVEL,
                "propagate": False,
            },
        },
    }


def configure_logger_levels():
    """Configure log levels for specific loggers."""
    
    # Default log levels for specific libraries
    logger_levels = {
        "uvicorn": "INFO",
        "uvicorn.access": "INFO" if getattr(settings, "ACCESS_LOG", True) else "WARNING",
        "uvicorn.error": "INFO",
        "sqlalchemy.engine": "WARNING",
        "sqlalchemy.pool": "WARNING",
        "aioredis": "WARNING",
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "asyncio": "WARNING",
        "aiohttp": "WARNING",
        "redis": "WARNING",
        "kafka": "WARNING",
        "confluent_kafka": "WARNING",
        "botocore": "WARNING",
        "boto3": "WARNING",
        "requests": "WARNING",
        "urllib3": "WARNING",
        "celery": "WARNING",
        "gunicorn": "INFO",
        "watchdog": "WARNING",
        "PIL": "WARNING",
    }
    
    # Apply log levels
    for logger_name, level in logger_levels.items():
        logging.getLogger(logger_name).setLevel(level)


def silence_noisy_loggers():
    """Silence noisy loggers."""
    
    noisy_loggers = [
        "MARKDOWN",
        "matplotlib",
        "faker",
        "factory",
        "selenium",
        "werkzeug",
        "parso",
        "asyncio.coroutines",
        "distributed",
        "tornado",
        "pika",
    ]
    
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_file_handler(log_dir: Path, log_format: str) -> logging.Handler:
    """Get file handler for logging."""
    
    # Create rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_dir / "application.log"),
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    
    # Set formatter based on log format
    if log_format == "json":
        handler.setFormatter(StructuredLogFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt=settings.LOG_DATEFMT,
        ))
    
    return handler


def add_request_context(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add request context to log events."""
    
    import asyncio
    
    try:
        # Try to get request context from asyncio context
        current_task = asyncio.current_task()
        
        if current_task:
            # Request ID
            request_id = getattr(current_task, "request_id", None)
            if request_id:
                event_dict["request_id"] = request_id
            
            # Correlation ID
            correlation_id = getattr(current_task, "correlation_id", None)
            if correlation_id:
                event_dict["correlation_id"] = correlation_id
            
            # User ID
            user_id = getattr(current_task, "user_id", None)
            if user_id:
                event_dict["user_id"] = user_id
            
            # Session ID
            session_id = getattr(current_task, "session_id", None)
            if session_id:
                event_dict["session_id"] = session_id
            
            # Client IP
            client_ip = getattr(current_task, "client_ip", None)
            if client_ip:
                event_dict["client_ip"] = client_ip
            
            # User agent
            user_agent = getattr(current_task, "user_agent", None)
            if user_agent:
                event_dict["user_agent"] = user_agent
            
            # HTTP method and path
            http_method = getattr(current_task, "http_method", None)
            if http_method:
                event_dict["http_method"] = http_method
            
            http_path = getattr(current_task, "http_path", None)
            if http_path:
                event_dict["http_path"] = http_path
            
            # Response status
            response_status = getattr(current_task, "response_status", None)
            if response_status:
                event_dict["response_status"] = response_status
            
            # Response time
            response_time = getattr(current_task, "response_time", None)
            if response_time:
                event_dict["response_time_ms"] = response_time * 1000  # Convert to ms
        
    except (RuntimeError, AttributeError):
        # No task context available
        pass
    
    return event_dict


def add_correlation_context(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add correlation context to log events."""
    
    # Try to get correlation ID from various sources
    correlation_id = None
    
    # Check event_dict first
    if "correlation_id" in event_dict:
        correlation_id = event_dict["correlation_id"]
    
    # Check thread local storage
    try:
        import threading
        thread_local = threading.local()
        if hasattr(thread_local, "correlation_id"):
            correlation_id = thread_local.correlation_id
    except AttributeError:
        pass
    
    # Set correlation ID if found
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    
    return event_dict


def clean_log_event(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Clean and standardize log events."""
    
    # Remove excessive whitespace in messages
    if "event" in event_dict and isinstance(event_dict["event"], str):
        event_dict["event"] = " ".join(event_dict["event"].split())
    
    # Truncate very long messages
    if "event" in event_dict and isinstance(event_dict["event"], str):
        if len(event_dict["event"]) > 10000:
            event_dict["event"] = event_dict["event"][:10000] + "... [TRUNCATED]"
    
    # Remove sensitive data
    event_dict = remove_sensitive_data(event_dict)
    
    # Ensure all values are JSON serializable
    for key, value in list(event_dict.items()):
        if isinstance(value, (set, tuple)):
            event_dict[key] = list(value)
        elif hasattr(value, "__dict__"):
            event_dict[key] = str(value)
    
    # Add service context
    event_dict["service"] = settings.APP_NAME
    event_dict["service_version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    
    return event_dict


def remove_sensitive_data(event_dict: EventDict) -> EventDict:
    """Remove sensitive data from log events."""
    
    sensitive_keys = [
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "cookie",
        "credit_card",
        "ssn",
        "social_security",
        "phone",
        "email",
        "address",
    ]
    
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    
    # Also check in nested structures
    def redact_nested(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(sensitive in k.lower() for sensitive in sensitive_keys):
                    obj[k] = "***REDACTED***"
                elif isinstance(v, (dict, list)):
                    redact_nested(v)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    redact_nested(item)
    
    redact_nested(event_dict)
    
    return event_dict


class LogContext:
    """Context manager for adding context to logs."""
    
    def __init__(self, **context):
        self.context = context
        self._old_context = {}
    
    def __enter__(self):
        """Enter context and bind context variables."""
        logger = structlog.get_logger()
        
        # Store old context
        self._old_context = logger._context.copy()
        
        # Bind new context
        logger = logger.bind(**self.context)
        
        return logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore old context."""
        logger = structlog.get_logger()
        
        # Restore old context
        logger._context.clear()
        logger._context.update(self._old_context)


def get_logger(name: Optional[str] = None) -> BoundLogger:
    """
    Get a structlog logger instance.
    
    Args:
        name: Logger name (optional)
    
    Returns:
        BoundLogger instance
    """
    return structlog.get_logger(name)


def log_exception(
    logger: BoundLogger,
    exception: Exception,
    event: str = "exception_occurred",
    level: str = "error",
    **context
):
    """
    Log an exception with full context.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        event: Log event message
        level: Log level
        **context: Additional context
    """
    
    # Build exception context
    exception_context = {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "exception": exception,
        "exc_info": True,
    }
    
    # Add additional context
    exception_context.update(context)
    
    # Log at appropriate level
    log_method = getattr(logger, level, logger.error)
    log_method(event, **exception_context)


def log_performance(
    logger: BoundLogger,
    operation: str,
    duration_seconds: float,
    level: str = "info",
    **context
):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration_seconds: Duration in seconds
        level: Log level
        **context: Additional context
    """
    
    # Convert to milliseconds
    duration_ms = duration_seconds * 1000
    
    # Performance context
    perf_context = {
        "operation": operation,
        "duration_seconds": duration_seconds,
        "duration_milliseconds": duration_ms,
        "performance_metric": True,
    }
    
    # Add additional context
    perf_context.update(context)
    
    # Determine level based on duration
    if duration_ms > 10000:  # > 10 seconds
        level = "error"
    elif duration_ms > 1000:  # > 1 second
        level = "warning"
    elif duration_ms > 100:  # > 100ms
        level = "info"
    else:
        level = "debug"
    
    # Log performance
    log_method = getattr(logger, level, logger.info)
    log_method(f"performance_{operation}", **perf_context)


def log_http_request(
    logger: BoundLogger,
    request_id: str,
    method: str,
    path: str,
    client_ip: str,
    user_agent: Optional[str] = None,
    user_id: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    status_code: Optional[int] = None,
    level: str = "info",
    **context
):
    """
    Log HTTP request details.
    
    Args:
        logger: Logger instance
        request_id: Request ID
        method: HTTP method
        path: Request path
        client_ip: Client IP address
        user_agent: User agent string (optional)
        user_id: User ID (optional)
        duration_seconds: Request duration in seconds (optional)
        status_code: HTTP status code (optional)
        level: Log level
        **context: Additional context
    """
    
    # HTTP context
    http_context = {
        "request_id": request_id,
        "http_method": method,
        "http_path": path,
        "client_ip": client_ip,
        "http_request": True,
    }
    
    # Optional fields
    if user_agent:
        http_context["user_agent"] = user_agent
    
    if user_id:
        http_context["user_id"] = user_id
    
    if duration_seconds is not None:
        http_context["duration_seconds"] = duration_seconds
        http_context["duration_milliseconds"] = duration_seconds * 1000
    
    if status_code is not None:
        http_context["status_code"] = status_code
        
        # Determine level based on status code
        if status_code >= 500:
            level = "error"
        elif status_code >= 400:
            level = "warning"
        elif status_code >= 300:
            level = "info"
        else:
            level = "info"
    
    # Add additional context
    http_context.update(context)
    
    # Log HTTP request
    log_method = getattr(logger, level, logger.info)
    log_method("http_request", **http_context)


def log_database_query(
    logger: BoundLogger,
    query: str,
    duration_seconds: float,
    parameters: Optional[Dict] = None,
    level: str = "debug",
    **context
):
    """
    Log database query details.
    
    Args:
        logger: Logger instance
        query: SQL query
        duration_seconds: Query duration in seconds
        parameters: Query parameters (optional)
        level: Log level
        **context: Additional context
    """
    
    # Database context
    db_context = {
        "query": query,
        "duration_seconds": duration_seconds,
        "duration_milliseconds": duration_seconds * 1000,
        "database_query": True,
    }
    
    # Add parameters (redacted if sensitive)
    if parameters:
        redacted_params = remove_sensitive_data({"parameters": parameters})
        db_context["parameters"] = redacted_params.get("parameters", {})
    
    # Add additional context
    db_context.update(context)
    
    # Determine level based on duration
    if duration_seconds > 10:  # > 10 seconds
        level = "error"
    elif duration_seconds > 1:  # > 1 second
        level = "warning"
    elif duration_seconds > 0.1:  # > 100ms
        level = "info"
    else:
        level = "debug"
    
    # Log database query
    log_method = getattr(logger, level, logger.debug)
    log_method("database_query", **db_context)


def log_cache_operation(
    logger: BoundLogger,
    operation: str,
    key: str,
    duration_seconds: float,
    success: bool = True,
    level: str = "debug",
    **context
):
    """
    Log cache operation details.
    
    Args:
        logger: Logger instance
        operation: Cache operation (get, set, delete, etc.)
        key: Cache key
        duration_seconds: Operation duration in seconds
        success: Whether operation was successful
        level: Log level
        **context: Additional context
    """
    
    # Cache context
    cache_context = {
        "cache_operation": operation,
        "cache_key": key,
        "duration_seconds": duration_seconds,
        "duration_milliseconds": duration_seconds * 1000,
        "cache_success": success,
        "cache_operation_log": True,
    }
    
    # Add additional context
    cache_context.update(context)
    
    # Determine level based on duration
    if duration_seconds > 1:  # > 1 second
        level = "warning"
    elif duration_seconds > 0.1:  # > 100ms
        level = "info"
    
    # Log cache operation
    log_method = getattr(logger, level, logger.debug)
    log_method(f"cache_{operation}", **cache_context)


# Export the configured logger and utilities
log = get_logger(__name__)

__all__ = [
    "setup_logging",
    "get_logger",
    "log",
    "LogContext",
    "log_exception",
    "log_performance",
    "log_http_request",
    "log_database_query",
    "log_cache_operation",
    "CustomJSONRenderer",
    "ContextInjector",
    "RequestContextFilter",
    "StructuredLogFormatter",
]
