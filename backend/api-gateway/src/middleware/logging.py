"""
Advanced Logging Middleware for GOAT Prediction Ultimate.
Provides structured logging, request/response tracing, performance monitoring, and audit trails.
"""

import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from enum import Enum
import re
import inspect
import socket
import platform

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from pydantic import BaseModel, Field, validator

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger, StructuredLogger
from .base import BaseMiddleware

logger = get_logger(__name__)

# ======================
# DATA MODELS
# ======================

class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log format enumeration."""
    JSON = "json"
    TEXT = "text"
    GELF = "gelf"  # Graylog Extended Log Format


class LogDestination(str, Enum):
    """Log destination enumeration."""
    CONSOLE = "console"
    FILE = "file"
    SYSLOG = "syslog"
    HTTP = "http"
    KAFKA = "kafka"
    ELASTICSEARCH = "elasticsearch"


@dataclass
class LogContext:
    """Context information for logging."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    path_params: Optional[Dict[str, Any]] = None
    source_service: Optional[str] = None
    destination_service: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    level: LogLevel = LogLevel.INFO
    message: str = ""
    logger_name: str = "api_gateway"
    context: Optional[LogContext] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    
    def to_dict(self, format_type: LogFormat = LogFormat.JSON) -> Dict[str, Any]:
        """Convert to dictionary for specific format."""
        base_data = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "logger": self.logger_name,
        }
        
        # Add context
        if self.context:
            base_data.update({
                "request_id": self.context.request_id,
                "correlation_id": self.context.correlation_id,
                "user_id": self.context.user_id,
                "client_ip": self.context.client_ip,
                "endpoint": self.context.endpoint,
                "method": self.context.method,
            })
        
        # Add performance metrics
        if self.duration_ms is not None:
            base_data["duration_ms"] = self.duration_ms
        if self.memory_usage_mb is not None:
            base_data["memory_mb"] = self.memory_usage_mb
        if self.cpu_percent is not None:
            base_data["cpu_percent"] = self.cpu_percent
        
        # Add extra fields
        if self.extra:
            base_data.update(self.extra)
        
        # Add exception info
        if self.exception:
            base_data["exception"] = self.exception
        if self.stack_trace:
            base_data["stack_trace"] = self.stack_trace
        
        # Format-specific adjustments
        if format_type == LogFormat.GELF:
            # Convert to GELF format
            gelf_data = {
                "version": "1.1",
                "host": socket.gethostname(),
                "short_message": self.message,
                "full_message": self.message,
                "timestamp": self.timestamp.timestamp(),
                "level": self._get_gelf_level(),
                "_logger_name": self.logger_name,
            }
            
            # Add additional fields with underscore prefix
            for key, value in base_data.items():
                if key not in ["message", "timestamp", "level"]:
                    gelf_data[f"_{key}"] = value
            
            return gelf_data
        
        return base_data
    
    def _get_gelf_level(self) -> int:
        """Convert log level to GELF numeric level."""
        level_map = {
            LogLevel.DEBUG: 7,
            LogLevel.INFO: 6,
            LogLevel.WARNING: 4,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 2,
        }
        return level_map.get(self.level, 6)


@dataclass
class RequestLog:
    """Complete request/response log."""
    request_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    request: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    context: Optional[LogContext] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "request_id": self.request_id,
            "start_time": self.start_time.isoformat(),
            "duration_ms": self.duration_ms or 0,
        }
        
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        
        if self.request:
            data["request"] = self.request
        
        if self.response:
            data["response"] = self.response
        
        if self.error:
            data["error"] = self.error
        
        if self.performance:
            data["performance"] = self.performance
        
        if self.context:
            data.update(self.context.to_dict())
        
        return data


# ======================
# LOG PROCESSORS
# ======================

class LogProcessor:
    """Base class for log processors."""
    
    def process(self, log_entry: LogEntry) -> LogEntry:
        """Process a log entry."""
        return log_entry
    
    def should_process(self, log_entry: LogEntry) -> bool:
        """Determine if processor should process this entry."""
        return True


class SensitiveDataProcessor(LogProcessor):
    """Processor to redact sensitive data."""
    
    def __init__(self):
        # Patterns for sensitive data
        self.sensitive_patterns = [
            # JWT tokens
            r'Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+',
            
            # API keys
            r'api[_-]?key["\']?\s*[:=]\s*["\'][A-Za-z0-9\-_]+["\']',
            r'x-api-key["\']?\s*[:=]\s*["\'][A-Za-z0-9\-_]+["\']',
            
            # Passwords
            r'password["\']?\s*[:=]\s*["\'][^"\']*["\']',
            r'passwd["\']?\s*[:=]\s*["\'][^"\']*["\']',
            
            # Secrets
            r'secret["\']?\s*[:=]\s*["\'][^"\']*["\']',
            r'client_secret["\']?\s*[:=]\s*["\'][^"\']*["\']',
            
            # Tokens
            r'token["\']?\s*[:=]\s*["\'][^"\']*["\']',
            r'access_token["\']?\s*[:=]\s*["\'][^"\']*["\']',
            r'refresh_token["\']?\s*[:=]\s*["\'][^"\']*["\']',
            
            # Credit cards
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            
            # Social security numbers (US)
            r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            
            # Email addresses (redact partially)
            r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
        ]
        
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns
        ]
    
    def process(self, log_entry: LogEntry) -> LogEntry:
        """Redact sensitive data from log entry."""
        # Process message
        if log_entry.message:
            log_entry.message = self._redact_text(log_entry.message)
        
        # Process extra fields
        if log_entry.extra:
            log_entry.extra = self._redact_dict(log_entry.extra)
        
        # Process context if present
        if log_entry.context:
            # Don't redact context fields, they should already be safe
            pass
        
        return log_entry
    
    def _redact_text(self, text: str) -> str:
        """Redact sensitive data from text."""
        for pattern in self.compiled_patterns:
            # Special handling for emails
            if '@' in text and 'email' in pattern.pattern.lower():
                text = re.sub(pattern, r'\1@***REDACTED***', text)
            else:
                text = pattern.sub('***REDACTED***', text)
        return text
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from dictionary."""
        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self._redact_text(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted


class PerformanceProcessor(LogProcessor):
    """Processor to add performance metrics."""
    
    def __init__(self):
        self.last_memory_check = None
        self.last_cpu_check = None
        self.memory_info = {}
        self.cpu_percent = 0
    
    def process(self, log_entry: LogEntry) -> LogEntry:
        """Add performance metrics to log entry."""
        # Add memory usage
        log_entry.memory_usage_mb = self._get_memory_usage()
        
        # Add CPU usage (sampled less frequently)
        if self._should_sample_cpu():
            log_entry.cpu_percent = self._get_cpu_percent()
        
        return log_entry
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _get_cpu_percent(self) -> float:
        """Get current CPU usage percentage."""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def _should_sample_cpu(self) -> bool:
        """Determine if CPU should be sampled."""
        if self.last_cpu_check is None:
            self.last_cpu_check = datetime.utcnow()
            return True
        
        if datetime.utcnow() - self.last_cpu_check > timedelta(seconds=5):
            self.last_cpu_check = datetime.utcnow()
            return True
        
        return False


class ContextEnricher(LogProcessor):
    """Processor to enrich logs with context information."""
    
    def __init__(self):
        self.request_context: ContextVar[Optional[LogContext]] = ContextVar(
            'request_context', default=None
        )
    
    def process(self, log_entry: LogEntry) -> LogEntry:
        """Enrich log entry with context."""
        # Get context from current request
        context = self.request_context.get()
        if context and not log_entry.context:
            log_entry.context = context
        
        # Add service information
        if not log_entry.extra.get('service'):
            log_entry.extra['service'] = {
                'name': 'goat-prediction-api',
                'version': config.get('app.version', '1.0.0'),
                'environment': config.get('environment', 'development'),
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
            }
        
        return log_entry
    
    def set_request_context(self, context: LogContext) -> None:
        """Set request context for current execution."""
        self.request_context.set(context)


class SamplingProcessor(LogProcessor):
    """Processor to implement log sampling."""
    
    def __init__(self, sample_rate: float = 1.0):
        """
        Initialize sampling processor.
        
        Args:
            sample_rate: Rate of logs to keep (0.0 to 1.0)
        """
        self.sample_rate = min(max(sample_rate, 0.0), 1.0)
        self.counter = 0
    
    def should_process(self, log_entry: LogEntry) -> bool:
        """Determine if log should be processed based on sampling rate."""
        if self.sample_rate >= 1.0:
            return True
        
        self.counter += 1
        return (self.counter % int(1 / self.sample_rate)) == 0
    
    def process(self, log_entry: LogEntry) -> LogEntry:
        """Add sampling information to log."""
        log_entry.extra['sampled'] = self.sample_rate < 1.0
        log_entry.extra['sample_rate'] = self.sample_rate
        return log_entry


# ======================
# LOG HANDLERS
# ======================

class LogHandler:
    """Base class for log handlers."""
    
    def __init__(self, level: LogLevel = LogLevel.INFO):
        self.level = level
        self.processors: List[LogProcessor] = []
    
    def add_processor(self, processor: LogProcessor) -> None:
        """Add a log processor."""
        self.processors.append(processor)
    
    def handle(self, log_entry: LogEntry) -> bool:
        """
        Handle a log entry.
        
        Returns:
            True if log was handled successfully
        """
        # Check log level
        if not self._should_handle(log_entry):
            return False
        
        # Process through all processors
        processed_entry = log_entry
        for processor in self.processors:
            if processor.should_process(processed_entry):
                processed_entry = processor.process(processed_entry)
        
        # Write the log
        return self._write(processed_entry)
    
    def _should_handle(self, log_entry: LogEntry) -> bool:
        """Determine if handler should handle this log entry."""
        level_order = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        
        return level_order.get(log_entry.level, 0) >= level_order.get(self.level, 0)
    
    def _write(self, log_entry: LogEntry) -> bool:
        """Write log entry (to be implemented by subclasses)."""
        raise NotImplementedError


class ConsoleHandler(LogHandler):
    """Handler for console output."""
    
    def __init__(self, level: LogLevel = LogLevel.INFO, format_type: LogFormat = LogFormat.TEXT):
        super().__init__(level)
        self.format_type = format_type
    
    def _write(self, log_entry: LogEntry) -> bool:
        """Write log entry to console."""
        try:
            log_dict = log_entry.to_dict(self.format_type)
            
            if self.format_type == LogFormat.JSON:
                output = json.dumps(log_dict, ensure_ascii=False)
            else:
                # Text format
                timestamp = log_dict['timestamp']
                level = log_dict['level']
                message = log_dict['message']
                request_id = log_dict.get('request_id', 'N/A')
                endpoint = log_dict.get('endpoint', 'N/A')
                
                output = f"[{timestamp}] {level:8} {request_id:36} {endpoint:30} {message}"
            
            print(output)
            return True
            
        except Exception as e:
            print(f"Console log handler error: {e}")
            return False


class FileHandler(LogHandler):
    """Handler for file output."""
    
    def __init__(
        self,
        file_path: str,
        level: LogLevel = LogLevel.INFO,
        format_type: LogFormat = LogFormat.JSON,
        max_size_mb: int = 100,
        backup_count: int = 5
    ):
        super().__init__(level)
        self.file_path = file_path
        self.format_type = format_type
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """Ensure log directory exists."""
        import os
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    def _write(self, log_entry: LogEntry) -> bool:
        """Write log entry to file."""
        try:
            log_dict = log_entry.to_dict(self.format_type)
            
            if self.format_type == LogFormat.JSON:
                line = json.dumps(log_dict, ensure_ascii=False)
            else:
                # Text format
                timestamp = log_dict['timestamp']
                level = log_dict['level']
                message = log_dict['message']
                line = f"[{timestamp}] {level} {message}"
            
            # Write to file
            with open(self.file_path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
            
            # Rotate if needed
            self._rotate_if_needed()
            
            return True
            
        except Exception as e:
            print(f"File log handler error: {e}")
            return False
    
    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        import os
        import shutil
        
        if not os.path.exists(self.file_path):
            return
        
        if os.path.getsize(self.file_path) < self.max_size_bytes:
            return
        
        # Rotate files
        for i in range(self.backup_count - 1, 0, -1):
            src = f"{self.file_path}.{i}"
            dst = f"{self.file_path}.{i + 1}"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        
        # Rotate current file
        dst = f"{self.file_path}.1"
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(self.file_path, dst)


class HTTPHandler(LogHandler):
    """Handler for HTTP endpoint output."""
    
    def __init__(
        self,
        url: str,
        level: LogLevel = LogLevel.INFO,
        format_type: LogFormat = LogFormat.JSON,
        batch_size: int = 100,
        batch_timeout: float = 5.0
    ):
        super().__init__(level)
        self.url = url
        self.format_type = format_type
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch_buffer: List[Dict[str, Any]] = []
        self.last_flush = datetime.utcnow()
        self.session = None
    
    def _write(self, log_entry: LogEntry) -> bool:
        """Write log entry to HTTP endpoint."""
        try:
            log_dict = log_entry.to_dict(self.format_type)
            self.batch_buffer.append(log_dict)
            
            # Flush if buffer is full or timeout reached
            if (len(self.batch_buffer) >= self.batch_size or 
                (datetime.utcnow() - self.last_flush).total_seconds() >= self.batch_timeout):
                return self._flush_buffer()
            
            return True
            
        except Exception as e:
            print(f"HTTP log handler error: {e}")
            return False
    
    def _flush_buffer(self) -> bool:
        """Flush buffer to HTTP endpoint."""
        if not self.batch_buffer:
            return True
        
        try:
            import aiohttp
            import asyncio
            
            # Create session if needed
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Send batch
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_batch_async())
            else:
                loop.run_until_complete(self._send_batch_async())
            
            # Clear buffer
            self.batch_buffer.clear()
            self.last_flush = datetime.utcnow()
            
            return True
            
        except Exception as e:
            print(f"HTTP log flush error: {e}")
            return False
    
    async def _send_batch_async(self) -> None:
        """Send batch asynchronously."""
        try:
            async with self.session.post(
                self.url,
                json={"logs": self.batch_buffer},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    print(f"HTTP log endpoint returned {response.status}")
        except Exception as e:
            print(f"HTTP log send error: {e}")


# ======================
# LOG MANAGER
# ======================

class LogManager:
    """Centralized log management."""
    
    def __init__(self):
        self.handlers: List[LogHandler] = []
        self.context_enricher = ContextEnricher()
        self.request_logs: Dict[str, RequestLog] = {}
        self.max_request_logs = 1000
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "logs_by_level": {},
            "logs_by_endpoint": {},
            "average_duration_ms": 0,
            "error_rate": 0,
        }
        
        # Initialize default handlers
        self._initialize_default_handlers()
    
    def _initialize_default_handlers(self) -> None:
        """Initialize default log handlers from config."""
        cfg = get_config()
        
        # Get logging config
        log_config = cfg.get("logging", {})
        level = LogLevel(log_config.get("level", "INFO"))
        format_type = LogFormat(log_config.get("format", "json"))
        
        # Console handler (always enabled)
        console_handler = ConsoleHandler(level, format_type)
        console_handler.add_processor(self.context_enricher)
        console_handler.add_processor(SensitiveDataProcessor())
        self.add_handler(console_handler)
        
        # File handler if enabled
        if log_config.get("file_enabled", True):
            file_path = log_config.get("file_path", "logs/api-gateway.log")
            max_size = log_config.get("file_max_size", 10)  # MB
            backup_count = log_config.get("file_backup_count", 5)
            
            file_handler = FileHandler(
                file_path, level, format_type, max_size, backup_count
            )
            file_handler.add_processor(self.context_enricher)
            file_handler.add_processor(SensitiveDataProcessor())
            file_handler.add_processor(PerformanceProcessor())
            self.add_handler(file_handler)
        
        # HTTP handler if enabled (for external logging services)
        if log_config.get("http_enabled", False):
            http_url = log_config.get("http_url")
            if http_url:
                http_handler = HTTPHandler(http_url, level, format_type)
                http_handler.add_processor(self.context_enricher)
                http_handler.add_processor(SensitiveDataProcessor())
                self.add_handler(http_handler)
    
    def add_handler(self, handler: LogHandler) -> None:
        """Add a log handler."""
        self.handlers.append(handler)
    
    def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> str:
        """
        Log a message.
        
        Returns:
            Log entry ID
        """
        # Create log entry
        log_entry = LogEntry(
            level=level,
            message=message,
            context=context,
            extra=extra or {},
        )
        
        # Add exception info
        if exception:
            log_entry.exception = str(exception)
            import traceback
            log_entry.stack_trace = traceback.format_exc()
        
        # Process through all handlers
        for handler in self.handlers:
            handler.handle(log_entry)
        
        # Update statistics
        self._update_stats(log_entry)
        
        return log_entry.timestamp.isoformat()
    
    def start_request_log(
        self,
        request_id: str,
        context: LogContext
    ) -> None:
        """Start logging for a request."""
        self.context_enricher.set_request_context(context)
        
        request_log = RequestLog(
            request_id=request_id,
            start_time=datetime.utcnow(),
            context=context
        )
        
        self.request_logs[request_id] = request_log
        
        # Log request start
        self.log(
            LogLevel.INFO,
            f"Request started: {context.method} {context.endpoint}",
            context=context,
            extra={
                "event": "request_start",
                "client_ip": context.client_ip,
                "user_agent": context.user_agent,
            }
        )
    
    def end_request_log(
        self,
        request_id: str,
        status_code: int,
        response_size: int,
        error: Optional[Dict[str, Any]] = None
    ) -> Optional[RequestLog]:
        """End logging for a request."""
        if request_id not in self.request_logs:
            return None
        
        request_log = self.request_logs[request_id]
        request_log.end_time = datetime.utcnow()
        request_log.duration_ms = (
            request_log.end_time - request_log.start_time
        ).total_seconds() * 1000
        
        # Build response info
        request_log.response = {
            "status_code": status_code,
            "size_bytes": response_size,
        }
        
        if error:
            request_log.error = error
        
        # Add performance metrics
        request_log.performance = {
            "duration_ms": request_log.duration_ms,
        }
        
        # Log request completion
        log_level = LogLevel.ERROR if status_code >= 500 else LogLevel.INFO
        self.log(
            log_level,
            f"Request completed: {status_code} in {request_log.duration_ms:.2f}ms",
            context=request_log.context,
            extra={
                "event": "request_end",
                "status_code": status_code,
                "duration_ms": request_log.duration_ms,
                "response_size": response_size,
            }
        )
        
        # Clean up old logs
        if len(self.request_logs) > self.max_request_logs:
            self._cleanup_old_logs()
        
        return request_log
    
    def _update_stats(self, log_entry: LogEntry) -> None:
        """Update log statistics."""
        self.stats["total_logs"] += 1
        
        # Update level stats
        level = log_entry.level.value
        self.stats["logs_by_level"][level] = (
            self.stats["logs_by_level"].get(level, 0) + 1
        )
        
        # Update endpoint stats
        if log_entry.context and log_entry.context.endpoint:
            endpoint = log_entry.context.endpoint
            self.stats["logs_by_endpoint"][endpoint] = (
                self.stats["logs_by_endpoint"].get(endpoint, 0) + 1
            )
    
    def _cleanup_old_logs(self) -> None:
        """Clean up old request logs."""
        # Keep only the most recent logs
        if len(self.request_logs) > self.max_request_logs:
            # Sort by start time and keep newest
            sorted_logs = sorted(
                self.request_logs.items(),
                key=lambda x: x[1].start_time,
                reverse=True
            )
            
            self.request_logs = dict(sorted_logs[:self.max_request_logs])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get log statistics."""
        # Calculate average duration
        durations = [
            log.duration_ms for log in self.request_logs.values()
            if log.duration_ms is not None
        ]
        
        if durations:
            self.stats["average_duration_ms"] = sum(durations) / len(durations)
        
        # Calculate error rate (errors per minute)
        error_logs = self.stats["logs_by_level"].get(LogLevel.ERROR.value, 0)
        total_logs = self.stats["total_logs"]
        
        if total_logs > 0:
            self.stats["error_rate"] = (error_logs / total_logs) * 100
        
        return {
            **self.stats,
            "active_requests": len([
                log for log in self.request_logs.values()
                if log.end_time is None
            ]),
            "total_requests": len(self.request_logs),
            "handlers_count": len(self.handlers),
        }
    
    def get_request_log(self, request_id: str) -> Optional[RequestLog]:
        """Get request log by ID."""
        return self.request_logs.get(request_id)
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request logs."""
        sorted_logs = sorted(
            self.request_logs.values(),
            key=lambda x: x.start_time,
            reverse=True
        )
        
        return [log.to_dict() for log in sorted_logs[:limit]]
    
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.request_logs.clear()
        self.stats = {
            "total_logs": 0,
            "logs_by_level": {},
            "logs_by_endpoint": {},
            "average_duration_ms": 0,
            "error_rate": 0,
        }
        logger.info("Logs cleared")


# ======================
# LOGGING MIDDLEWARE
# ======================

class LoggingMiddleware(BaseMiddleware):
    """
    Advanced Logging Middleware.
    
    Features:
    - Structured request/response logging
    - Performance monitoring
    - Audit trails
    - Error tracking
    - Custom log processors
    - Multiple output destinations
    - Real-time statistics
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        
        # Configuration
        self.config = self._load_configuration(kwargs)
        self.log_level = LogLevel(self.config.get("log_level", "INFO"))
        self.exclude_paths = set(self.config.get("exclude_paths", []))
        self.log_headers = self.config.get("log_headers", False)
        self.log_body = self.config.get("log_body", False)
        self.max_body_size = self.config.get("max_body_size", 1024)  # bytes
        self.slow_request_threshold = self.config.get("slow_request_threshold", 1000)  # ms
        
        # Initialize log manager
        self.log_manager = LogManager()
        
        # Request tracking
        self.active_requests: Dict[str, datetime] = {}
        
        logger.info("Logging middleware initialized")
    
    def _load_configuration(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Load logging configuration."""
        # Get from middleware kwargs
        config_dict = {
            "log_level": kwargs.get("log_level"),
            "exclude_paths": kwargs.get("exclude_paths", []),
            "log_headers": kwargs.get("log_headers", False),
            "log_body": kwargs.get("log_body", False),
            "max_body_size": kwargs.get("max_body_size", 1024),
            "slow_request_threshold": kwargs.get("slow_request_threshold", 1000),
        }
        
        # Merge with app config
        app_config = get_config().get("logging", {})
        config_dict.update(app_config)
        
        return config_dict
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip logging for excluded paths
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Generate request ID if not present
        request_id = self._get_request_id(request)
        request.state.request_id = request_id
        
        # Create log context
        context = self._create_log_context(request, request_id)
        
        # Start request logging
        self.log_manager.start_request_log(request_id, context)
        self.active_requests[request_id] = datetime.utcnow()
        
        # Capture request body if needed
        request_body = None
        if self.log_body and self._should_log_body(request):
            request_body = await self._capture_request_body(request)
        
        try:
            # Process request
            start_time = time.time()
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log slow requests
            if duration_ms > self.slow_request_threshold:
                self._log_slow_request(request_id, context, duration_ms)
            
            # Get response info
            response_size = self._get_response_size(response)
            
            # End request logging
            self.log_manager.end_request_log(
                request_id,
                response.status_code,
                response_size
            )
            
            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as exc:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            self._log_error(request_id, context, exc, duration_ms)
            
            # Re-raise the exception
            raise
        
        finally:
            # Clean up active request
            if request_id in self.active_requests:
                del self.active_requests[request_id]
    
    def _should_skip_logging(self, request: Request) -> bool:
        """Check if logging should be skipped for this request."""
        path = request.url.path
        
        # Check exact matches
        if path in self.exclude_paths:
            return True
        
        # Check prefix matches
        for exclude_path in self.exclude_paths:
            if exclude_path.endswith('*') and path.startswith(exclude_path[:-1]):
                return True
        
        # Skip health checks and metrics
        if path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return True
        
        return False
    
    def _get_request_id(self, request: Request) -> str:
        """Get or generate request ID."""
        # Check headers
        request_id = request.headers.get("X-Request-ID")
        
        # Check if already set
        if hasattr(request.state, 'request_id'):
            request_id = request.state.request_id
        
        # Generate if not present
        if not request_id:
            request_id = str(uuid.uuid4())
        
        return request_id
    
    def _create_log_context(self, request: Request, request_id: str) -> LogContext:
        """Create log context from request."""
        # Get client info
        client = request.client
        client_ip = client.host if client else None
        
        # Get user info from request state
        user_id = getattr(request.state, 'user_id', None)
        session_id = getattr(request.state, 'session_id', None)
        
        # Get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        
        return LogContext(
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            correlation_id=correlation_id,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
            endpoint=str(request.url.path),
            method=request.method,
            query_params=dict(request.query_params),
            path_params=dict(request.path_params) if hasattr(request, 'path_params') else None,
        )
    
    def _should_log_body(self, request: Request) -> bool:
        """Check if request body should be logged."""
        content_type = request.headers.get("content-type", "").lower()
        
        # Only log JSON and form data
        return (
            "application/json" in content_type or
            "application/x-www-form-urlencoded" in content_type or
            "multipart/form-data" in content_type
        )
    
    async def _capture_request_body(self, request: Request) -> Optional[str]:
        """Capture request body for logging."""
        try:
            body_bytes = await request.body()
            
            # Limit size
            if len(body_bytes) > self.max_body_size:
                return f"[Body truncated: {len(body_bytes)} bytes]"
            
            # Decode and return
            body_text = body_bytes.decode('utf-8', errors='ignore')
            
            # Redact sensitive data
            processor = SensitiveDataProcessor()
            return processor._redact_text(body_text)
            
        except Exception:
            return None
    
    def _get_response_size(self, response: Response) -> int:
        """Get response size in bytes."""
        try:
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    return len(body)
                elif isinstance(body, str):
                    return len(body.encode('utf-8'))
        except Exception:
            pass
        
        return 0
    
    def _log_slow_request(self, request_id: str, context: LogContext, duration_ms: float) -> None:
        """Log slow request warning."""
        self.log_manager.log(
            LogLevel.WARNING,
            f"Slow request: {duration_ms:.2f}ms",
            context=context,
            extra={
                "event": "slow_request",
                "duration_ms": duration_ms,
                "threshold_ms": self.slow_request_threshold,
            }
        )
    
    def _log_error(self, request_id: str, context: LogContext, exc: Exception, duration_ms: float) -> None:
        """Log request error."""
        error_info = {
            "exception_type": exc.__class__.__name__,
            "exception_message": str(exc),
            "duration_ms": duration_ms,
        }
        
        self.log_manager.end_request_log(
            request_id,
            status_code=500,  # Default to 500 for unhandled exceptions
            response_size=0,
            error=error_info
        )
        
        # Log the error
        self.log_manager.log(
            LogLevel.ERROR,
            f"Request error: {exc}",
            context=context,
            extra={
                "event": "request_error",
                "duration_ms": duration_ms,
            },
            exception=exc
        )
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        return self.log_manager.get_stats()
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent request logs."""
        return self.log_manager.get_recent_logs(limit)
    
    def get_active_requests(self) -> List[Dict[str, Any]]:
        """Get currently active requests."""
        active = []
        now = datetime.utcnow()
        
        for request_id, start_time in self.active_requests.items():
            duration = (now - start_time).total_seconds() * 1000
            active.append({
                "request_id": request_id,
                "start_time": start_time.isoformat(),
                "duration_ms": duration,
            })
        
        return active
    
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.log_manager.clear_logs()
        self.active_requests.clear()


# ======================
# LOGGING UTILITIES
# ======================

def setup_logging_middleware(
    app: FastAPI,
    config: Optional[Dict[str, Any]] = None
) -> LoggingMiddleware:
    """
    Setup logging middleware on FastAPI app.
    
    Args:
        app: FastAPI application
        config: Logging configuration
        
    Returns:
        LoggingMiddleware instance
    """
    if config is None:
        # Get default config
        cfg = get_config()
        config = {
            "log_level": cfg.get("logging.level", "INFO"),
            "exclude_paths": ["/health", "/metrics", "/docs", "/redoc"],
            "log_headers": False,
            "log_body": False,
            "max_body_size": 1024,
            "slow_request_threshold": 1000,
        }
    
    # Create middleware
    middleware = LoggingMiddleware(app, **config)
    
    # Add middleware to app
    from ..middleware import MiddlewareManager
    manager = MiddlewareManager(app)
    manager.register("logging", LoggingMiddleware, config)
    manager.setup_app()
    
    # Add logging endpoints
    @app.get("/logging/stats", include_in_schema=False)
    async def get_logging_stats() -> Dict[str, Any]:
        """Get logging statistics."""
        return {
            "stats": middleware.get_log_stats(),
            "active_requests": middleware.get_active_requests(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/logging/recent", include_in_schema=False)
    async def get_recent_logs(limit: int = 100) -> Dict[str, Any]:
        """Get recent logs."""
        return {
            "logs": middleware.get_recent_logs(limit),
            "count": len(middleware.get_recent_logs(limit)),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.post("/logging/clear", include_in_schema=False)
    async def clear_logs() -> Dict[str, Any]:
        """Clear all logs (requires authentication)."""
        middleware.clear_logs()
        return {
            "message": "Logs cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    logger.info("Logging middleware setup complete")
    return middleware


def create_structured_logger(
    name: str,
    context: Optional[LogContext] = None
) -> Callable:
    """
    Create a structured logger function.
    
    Args:
        name: Logger name
        context: Log context
        
    Returns:
        Logger function
    """
    log_manager = LogManager()
    
    def logger_func(
        level: Union[LogLevel, str],
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ) -> str:
        """Log a message."""
        if isinstance(level, str):
            level = LogLevel(level.upper())
        
        return log_manager.log(
            level=level,
            message=message,
            context=context,
            extra=extra or {},
            exception=exception
        )
    
    return logger_func


# ======================
# LOGGING DECORATORS
# ======================

def log_execution_time(level: LogLevel = LogLevel.DEBUG):
    """
    Decorator to log function execution time.
    
    Args:
        level: Log level
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log execution time
                logger.debug(
                    f"{func.__name__} executed in {duration_ms:.2f}ms",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                    }
                )
                
                return result
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{func.__name__} failed after {duration_ms:.2f}ms: {exc}",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                        "exception": str(exc),
                    },
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"{func.__name__} executed in {duration_ms:.2f}ms",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                    }
                )
                
                return result
            except Exception as exc:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"{func.__name__} failed after {duration_ms:.2f}ms: {exc}",
                    extra={
                        "function": func.__name__,
                        "module": func.__module__,
                        "duration_ms": duration_ms,
                        "exception": str(exc),
                    },
                    exc_info=True
                )
                raise
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def log_arguments(level: LogLevel = LogLevel.DEBUG):
    """
    Decorator to log function arguments.
    
    Args:
        level: Log level
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Log arguments
            arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
            arg_dict = {name: value for name, value in zip(arg_names, args)}
            arg_dict.update(kwargs)
            
            # Redact sensitive data
            processor = SensitiveDataProcessor()
            safe_args = processor._redact_dict(arg_dict)
            
            logger.log(
                level.value,
                f"{func.__name__} called with arguments",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "arguments": safe_args,
                }
            )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Log arguments
            arg_names = func.__code__.co_varnames[:func.__code__.co_argcount]
            arg_dict = {name: value for name, value in zip(arg_names, args)}
            arg_dict.update(kwargs)
            
            # Redact sensitive data
            processor = SensitiveDataProcessor()
            safe_args = processor._redact_dict(arg_dict)
            
            logger.log(
                level.value,
                f"{func.__name__} called with arguments",
                extra={
                    "function": func.__name__,
                    "module": func.__module__,
                    "arguments": safe_args,
                }
            )
            
            return func(*args, **kwargs)
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ======================
# EXPORTS
# ======================

__all__ = [
    # Main middleware
    "LoggingMiddleware",
    "setup_logging_middleware",
    
    # Models
    "LogLevel",
    "LogFormat",
    "LogDestination",
    "LogContext",
    "LogEntry",
    "RequestLog",
    
    # Processors
    "LogProcessor",
    "SensitiveDataProcessor",
    "PerformanceProcessor",
    "ContextEnricher",
    "SamplingProcessor",
    
    # Handlers
    "LogHandler",
    "ConsoleHandler",
    "FileHandler",
    "HTTPHandler",
    
    # Manager
    "LogManager",
    
    # Utilities
    "create_structured_logger",
    
    # Decorators
    "log_execution_time",
    "log_arguments",
]


if __name__ == "__main__":
    # Test the logging middleware
    import asyncio
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    print("📝 Logging Middleware Test")
    print("=" * 50)
    
    # Create test app
    app = FastAPI()
    
    # Setup logging middleware
    middleware = setup_logging_middleware(app, {
        "log_level": "DEBUG",
        "exclude_paths": ["/health"],
        "log_body": False,
        "slow_request_threshold": 50,
    })
    
    # Add test endpoints
    @app.get("/test/fast")
    async def test_fast():
        return {"message": "Fast response"}
    
    @app.get("/test/slow")
    async def test_slow():
        await asyncio.sleep(0.1)  # 100ms delay
        return {"message": "Slow response"}
    
    @app.get("/test/error")
    async def test_error():
        raise ValueError("Test error")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    # Test with test client
    client = TestClient(app)
    
    print("\n1. Testing fast request...")
    response = client.get("/test/fast")
    print(f"   Status: {response.status_code}")
    print(f"   Request ID: {response.headers.get('X-Request-ID')}")
    print(f"   Response Time: {response.headers.get('X-Response-Time')}")
    
    print("\n2. Testing slow request (warning expected)...")
    response = client.get("/test/slow")
    print(f"   Status: {response.status_code}")
    
    print("\n3. Testing error request...")
    response = client.get("/test/error")
    print(f"   Status: {response.status_code}")
    
    print("\n4. Testing excluded path...")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Has Request ID: {'X-Request-ID' in response.headers}")
    
    print("\n5. Testing log statistics...")
    stats = middleware.get_log_stats()
    print(f"   Total logs: {stats.get('total_logs', 0)}")
    print(f"   Active requests: {len(middleware.get_active_requests())}")
    
    print("\n6. Testing recent logs...")
    recent_logs = middleware.get_recent_logs(5)
    print(f"   Recent logs count: {len(recent_logs)}")
    
    # Test structured logging
    print("\n7. Testing structured logging...")
    structured_logger = create_structured_logger("test_logger")
    
    log_id = structured_logger(
        "INFO",
        "Test structured log message",
        extra={"test_field": "test_value"}
    )
    print(f"   Log ID: {log_id}")
    
    # Test decorators
    print("\n8. Testing logging decorators...")
    
    @log_execution_time("DEBUG")
    @log_arguments("DEBUG")
    async def test_function(arg1: str, arg2: int = 42):
        await asyncio.sleep(0.01)
        return f"Result: {arg1}-{arg2}"
    
    # Run test function
    asyncio.run(test_function("test", 123))
    
    print("\n✅ All logging tests completed successfully!")
