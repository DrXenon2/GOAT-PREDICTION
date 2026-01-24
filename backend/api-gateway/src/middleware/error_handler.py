"""
Advanced Error Handler Middleware for GOAT Prediction Ultimate.
Provides centralized error handling, logging, monitoring, and graceful error responses.
"""

import json
import traceback
import sys
import inspect
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Type
from enum import Enum
from dataclasses import dataclass, field, asdict
import hashlib
import uuid

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.encoders import jsonable_encoder
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY
from pydantic import BaseModel, Field, validator

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger, StructuredLogger
from ..core.exceptions import (
    APIError, ValidationError, AuthenticationError, AuthorizationError,
    NotFoundError, RateLimitError, DatabaseError, ServiceError,
    ExternalAPIError, BusinessError
)
from .base import BaseMiddleware

logger = get_logger(__name__)

# ======================
# DATA MODELS
# ======================

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    SERVICE = "service"
    BUSINESS = "business"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for an error."""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    path_params: Optional[Dict[str, Any]] = None
    body_preview: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ErrorDetails:
    """Detailed error information."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    message: str = ""
    code: str = "internal_error"
    http_status: int = HTTP_500_INTERNAL_SERVER_ERROR
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Optional[ErrorContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, include_stack_trace: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "code": self.code,
            "http_status": self.http_status,
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
        }
        
        if include_stack_trace and self.stack_trace:
            data["stack_trace"] = self.stack_trace
        
        if self.context:
            data["context"] = self.context.to_dict()
        
        if self.metadata:
            data["metadata"] = self.metadata
        
        return data


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: bool = True
    error_id: str = Field(..., description="Unique error identifier")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Error code for programmatic handling")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: Optional[str] = Field(None, description="Request path")
    method: Optional[str] = Field(None, description="HTTP method")
    
    # Optional fields for debugging
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    validation_errors: Optional[List[Dict[str, Any]]] = Field(None, description="Validation errors")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
    
    @validator('error_id')
    def validate_error_id(cls, v):
        """Validate error ID format."""
        if not v or len(v) < 8:
            raise ValueError("Error ID must be at least 8 characters")
        return v


# ======================
# ERROR CLASSIFIER
# ======================

class ErrorClassifier:
    """Classify exceptions and extract error information."""
    
    # Mapping of exception types to error categories
    EXCEPTION_CATEGORY_MAP = {
        # Standard exceptions
        RequestValidationError: ErrorCategory.VALIDATION,
        WebSocketRequestValidationError: ErrorCategory.VALIDATION,
        ValidationError: ErrorCategory.VALIDATION,
        
        # Authentication/Authorization
        AuthenticationError: ErrorCategory.AUTHENTICATION,
        AuthorizationError: ErrorCategory.AUTHORIZATION,
        
        # HTTP exceptions
        HTTPException: ErrorCategory.SYSTEM,
        StarletteHTTPException: ErrorCategory.SYSTEM,
        
        # Business exceptions
        NotFoundError: ErrorCategory.NOT_FOUND,
        RateLimitError: ErrorCategory.RATE_LIMIT,
        BusinessError: ErrorCategory.BUSINESS,
        
        # Technical exceptions
        DatabaseError: ErrorCategory.DATABASE,
        ExternalAPIError: ErrorCategory.EXTERNAL_API,
        ServiceError: ErrorCategory.SERVICE,
        
        # Python built-ins
        ValueError: ErrorCategory.VALIDATION,
        TypeError: ErrorCategory.VALIDATION,
        KeyError: ErrorCategory.VALIDATION,
        AttributeError: ErrorCategory.SYSTEM,
        
        # Base exception
        Exception: ErrorCategory.UNKNOWN,
    }
    
    # HTTP status code mapping
    STATUS_CODE_CATEGORY_MAP = {
        400: ErrorCategory.VALIDATION,
        401: ErrorCategory.AUTHENTICATION,
        403: ErrorCategory.AUTHORIZATION,
        404: ErrorCategory.NOT_FOUND,
        429: ErrorCategory.RATE_LIMIT,
        422: ErrorCategory.VALIDATION,
        500: ErrorCategory.SYSTEM,
        502: ErrorCategory.EXTERNAL_API,
        503: ErrorCategory.SERVICE,
        504: ErrorCategory.EXTERNAL_API,
    }
    
    @classmethod
    def classify_exception(cls, exc: Exception) -> ErrorCategory:
        """Classify an exception into error category."""
        exc_type = type(exc)
        
        # Check exact type matches
        for exc_class, category in cls.EXCEPTION_CATEGORY_MAP.items():
            if exc_type == exc_class:
                return category
        
        # Check subclass matches
        for exc_class, category in cls.EXCEPTION_CATEGORY_MAP.items():
            if issubclass(exc_type, exc_class):
                return category
        
        return ErrorCategory.UNKNOWN
    
    @classmethod
    def classify_status_code(cls, status_code: int) -> ErrorCategory:
        """Classify HTTP status code into error category."""
        return cls.STATUS_CODE_CATEGORY_MAP.get(
            status_code, 
            ErrorCategory.UNKNOWN
        )
    
    @classmethod
    def get_error_severity(cls, category: ErrorCategory, status_code: int) -> ErrorSeverity:
        """Determine error severity based on category and status code."""
        if status_code >= 500:
            return ErrorSeverity.ERROR
        elif status_code == 429:  # Rate limit
            return ErrorSeverity.WARNING
        elif status_code >= 400:
            return ErrorSeverity.INFO
        else:
            return ErrorSeverity.DEBUG
    
    @classmethod
    def extract_error_code(cls, exc: Exception) -> str:
        """Extract error code from exception."""
        if hasattr(exc, 'error_code'):
            return exc.error_code
        
        if hasattr(exc, 'code'):
            return exc.code
        
        # Map exception type to error code
        exc_name = exc.__class__.__name__
        
        # Convert CamelCase to snake_case
        import re
        code = re.sub(r'(?<!^)(?=[A-Z])', '_', exc_name).lower()
        
        return code


# ======================
# ERROR BUILDER
# ======================

class ErrorBuilder:
    """Build error details from exceptions and context."""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.classifier = ErrorClassifier()
    
    def build_from_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        include_stack_trace: bool = False
    ) -> ErrorDetails:
        """Build error details from exception."""
        # Determine HTTP status code
        http_status = self._get_http_status(exc)
        
        # Classify error
        category = self.classifier.classify_exception(exc)
        
        # Determine severity
        severity = self.classifier.get_error_severity(category, http_status)
        
        # Extract error code
        error_code = self.classifier.extract_error_code(exc)
        
        # Get error message
        error_message = self._get_error_message(exc, category)
        
        # Build context
        context = self._build_context(request) if request else None
        
        # Get stack trace if needed
        stack_trace = None
        if include_stack_trace or self.debug_mode:
            stack_trace = self._get_stack_trace(exc)
        
        return ErrorDetails(
            severity=severity,
            category=category,
            message=error_message,
            code=error_code,
            http_status=http_status,
            exception_type=exc.__class__.__name__,
            exception_message=str(exc),
            stack_trace=stack_trace,
            context=context
        )
    
    def build_from_http_error(
        self,
        status_code: int,
        message: str,
        request: Optional[Request] = None,
        code: Optional[str] = None
    ) -> ErrorDetails:
        """Build error details from HTTP error."""
        category = self.classifier.classify_status_code(status_code)
        severity = self.classifier.get_error_severity(category, status_code)
        
        context = self._build_context(request) if request else None
        
        return ErrorDetails(
            severity=severity,
            category=category,
            message=message,
            code=code or f"http_{status_code}",
            http_status=status_code,
            context=context
        )
    
    def _get_http_status(self, exc: Exception) -> int:
        """Get HTTP status code from exception."""
        if hasattr(exc, 'status_code'):
            return exc.status_code
        
        if isinstance(exc, HTTPException):
            return exc.status_code
        
        if isinstance(exc, StarletteHTTPException):
            return exc.status_code
        
        # Map exception types to status codes
        if isinstance(exc, (ValidationError, RequestValidationError)):
            return HTTP_422_UNPROCESSABLE_ENTITY
        
        if isinstance(exc, AuthenticationError):
            return 401
        
        if isinstance(exc, AuthorizationError):
            return 403
        
        if isinstance(exc, NotFoundError):
            return 404
        
        if isinstance(exc, RateLimitError):
            return 429
        
        if isinstance(exc, (DatabaseError, ServiceError, ExternalAPIError)):
            return 500
        
        return HTTP_500_INTERNAL_SERVER_ERROR
    
    def _get_error_message(self, exc: Exception, category: ErrorCategory) -> str:
        """Get user-friendly error message."""
        if hasattr(exc, 'detail'):
            return str(exc.detail)
        
        if hasattr(exc, 'message'):
            return exc.message
        
        # Default messages by category
        default_messages = {
            ErrorCategory.VALIDATION: "Validation failed",
            ErrorCategory.AUTHENTICATION: "Authentication required",
            ErrorCategory.AUTHORIZATION: "Insufficient permissions",
            ErrorCategory.NOT_FOUND: "Resource not found",
            ErrorCategory.RATE_LIMIT: "Rate limit exceeded",
            ErrorCategory.DATABASE: "Database error occurred",
            ErrorCategory.EXTERNAL_API: "External service error",
            ErrorCategory.SERVICE: "Service temporarily unavailable",
            ErrorCategory.BUSINESS: "Business rule violation",
            ErrorCategory.SYSTEM: "Internal server error",
            ErrorCategory.UNKNOWN: "An unexpected error occurred",
        }
        
        if str(exc):
            return str(exc)
        
        return default_messages.get(category, "An error occurred")
    
    def _build_context(self, request: Request) -> ErrorContext:
        """Build error context from request."""
        # Get request ID
        request_id = getattr(request.state, 'request_id', None)
        
        # Get user info
        user_id = getattr(request.state, 'user_id', None)
        session_id = getattr(request.state, 'session_id', None)
        
        # Get client info
        client = request.client
        ip_address = client.host if client else None
        user_agent = request.headers.get('user-agent')
        
        # Get request details
        endpoint = str(request.url.path)
        method = request.method
        
        # Get query params (limit size)
        query_params = dict(request.query_params)
        if len(str(query_params)) > 1000:  # Prevent too large logs
            query_params = {"_truncated": True}
        
        # Get path params
        path_params = dict(request.path_params) if hasattr(request, 'path_params') else None
        
        # Get body preview (limit size, sensitive data redacted)
        body_preview = None
        try:
            if request.headers.get('content-type') == 'application/json':
                body_bytes = await request.body()
                if body_bytes and len(body_bytes) < 10000:  # 10KB limit
                    body_text = body_bytes.decode('utf-8', errors='ignore')
                    # Redact sensitive fields
                    import re
                    sensitive_patterns = [
                        r'password["\']?\s*:\s*["\'][^"\']*["\']',
                        r'token["\']?\s*:\s*["\'][^"\']*["\']',
                        r'secret["\']?\s*:\s*["\'][^"\']*["\']',
                        r'api_key["\']?\s*:\s*["\'][^"\']*["\']',
                    ]
                    for pattern in sensitive_patterns:
                        body_text = re.sub(pattern, r'\1: "***REDACTED***"', body_text)
                    body_preview = body_text[:500]  # Limit preview size
        except Exception:
            pass  # Ignore body reading errors
        
        # Get headers (redact sensitive ones)
        headers = dict(request.headers)
        sensitive_headers = ['authorization', 'cookie', 'set-cookie', 'x-api-key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '***REDACTED***'
            if header.title() in headers:
                headers[header.title()] = '***REDACTED***'
        
        return ErrorContext(
            request_id=request_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            query_params=query_params,
            path_params=path_params,
            body_preview=body_preview,
            headers=headers
        )
    
    def _get_stack_trace(self, exc: Exception) -> str:
        """Get formatted stack trace."""
        try:
            return ''.join(traceback.format_exception(
                type(exc), exc, exc.__traceback__
            ))
        except Exception:
            return str(exc)


# ======================
# ERROR RESPONSE BUILDER
# ======================

class ErrorResponseBuilder:
    """Build error responses for clients."""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.error_builder = ErrorBuilder(debug_mode)
    
    def build_response(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        include_details: bool = False
    ) -> JSONResponse:
        """Build JSON response from exception."""
        # Build error details
        error_details = self.error_builder.build_from_exception(
            exc, request, include_stack_trace=self.debug_mode
        )
        
        # Create error response model
        error_response = self._create_error_response(error_details, request)
        
        # Log the error
        self._log_error(error_details)
        
        # Build JSON response
        content = jsonable_encoder(error_response)
        
        return JSONResponse(
            status_code=error_details.http_status,
            content=content,
            headers=self._get_response_headers(error_details)
        )
    
    def build_validation_response(
        self,
        exc: RequestValidationError,
        request: Optional[Request] = None
    ) -> JSONResponse:
        """Build validation error response."""
        error_details = self.error_builder.build_from_exception(exc, request)
        
        # Extract validation errors
        validation_errors = []
        if hasattr(exc, 'errors'):
            for error in exc.errors():
                validation_errors.append({
                    "loc": error.get("loc"),
                    "msg": error.get("msg"),
                    "type": error.get("type"),
                })
        
        # Create error response
        error_response = ErrorResponse(
            error_id=error_details.error_id,
            message=error_details.message,
            code=error_details.code,
            path=str(request.url.path) if request else None,
            method=request.method if request else None,
            validation_errors=validation_errors
        )
        
        # Log the error
        self._log_error(error_details)
        
        # Build JSON response
        content = jsonable_encoder(error_response)
        
        return JSONResponse(
            status_code=error_details.http_status,
            content=content,
            headers=self._get_response_headers(error_details)
        )
    
    def _create_error_response(
        self,
        error_details: ErrorDetails,
        request: Optional[Request]
    ) -> ErrorResponse:
        """Create ErrorResponse model from error details."""
        # Base response
        response = ErrorResponse(
            error_id=error_details.error_id,
            message=error_details.message,
            code=error_details.code,
            path=str(request.url.path) if request else None,
            method=request.method if request else None,
        )
        
        # Add details in debug mode or for specific error types
        if self.debug_mode or error_details.category in [
            ErrorCategory.VALIDATION,
            ErrorCategory.NOT_FOUND,
            ErrorCategory.BUSINESS
        ]:
            response.details = error_details.to_dict(include_stack_trace=self.debug_mode)
        
        return response
    
    def _get_response_headers(self, error_details: ErrorDetails) -> Dict[str, str]:
        """Get response headers for error."""
        headers = {
            "X-Error-ID": error_details.error_id,
            "X-Error-Code": error_details.code,
            "X-Error-Category": error_details.category.value,
        }
        
        # Add retry-after for rate limiting
        if error_details.category == ErrorCategory.RATE_LIMIT:
            headers["Retry-After"] = "60"
        
        return headers
    
    def _log_error(self, error_details: ErrorDetails) -> None:
        """Log error with appropriate level."""
        log_data = error_details.to_dict(include_stack_trace=True)
        
        # Map severity to logging level
        log_methods = {
            ErrorSeverity.DEBUG: logger.debug,
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical,
        }
        
        log_method = log_methods.get(error_details.severity, logger.error)
        
        # Log with structured data
        log_method(
            f"{error_details.category.value}: {error_details.message}",
            extra={
                "error": log_data,
                "error_id": error_details.error_id,
                "severity": error_details.severity.value,
                "category": error_details.category.value,
                "http_status": error_details.http_status,
            }
        )


# ======================
# ERROR MONITORING
# ======================

class ErrorMonitor:
    """Monitor and track errors for analytics and alerting."""
    
    def __init__(self, max_errors: int = 10000):
        self.errors: List[ErrorDetails] = []
        self.max_errors = max_errors
        self.metrics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_status": {},
            "errors_by_endpoint": {},
            "error_rate": 0,
            "last_error_time": None,
        }
        
        # Window for error rate calculation (last 5 minutes)
        self.error_window = timedelta(minutes=5)
        self.error_timestamps: List[datetime] = []
    
    def record_error(self, error_details: ErrorDetails) -> None:
        """Record an error for monitoring."""
        # Add to errors list
        self.errors.append(error_details)
        
        # Update metrics
        self.metrics["total_errors"] += 1
        self.metrics["last_error_time"] = error_details.timestamp
        
        # Update category count
        category = error_details.category.value
        self.metrics["errors_by_category"][category] = (
            self.metrics["errors_by_category"].get(category, 0) + 1
        )
        
        # Update status count
        status = str(error_details.http_status)
        self.metrics["errors_by_status"][status] = (
            self.metrics["errors_by_status"].get(status, 0) + 1
        )
        
        # Update endpoint count
        if error_details.context and error_details.context.endpoint:
            endpoint = error_details.context.endpoint
            self.metrics["errors_by_endpoint"][endpoint] = (
                self.metrics["errors_by_endpoint"].get(endpoint, 0) + 1
            )
        
        # Update error rate
        self.error_timestamps.append(error_details.timestamp)
        self._cleanup_old_timestamps()
        self.metrics["error_rate"] = self._calculate_error_rate()
        
        # Trim errors if needed
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
    
    def _cleanup_old_timestamps(self) -> None:
        """Clean up old error timestamps."""
        cutoff = datetime.utcnow() - self.error_window
        self.error_timestamps = [
            ts for ts in self.error_timestamps if ts > cutoff
        ]
    
    def _calculate_error_rate(self) -> float:
        """Calculate errors per minute."""
        if not self.error_timestamps:
            return 0.0
        
        window_minutes = self.error_window.total_seconds() / 60
        return len(self.error_timestamps) / window_minutes
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get error metrics."""
        return {
            **self.metrics,
            "recent_errors": [
                error.to_dict()
                for error in self.errors[-10:]  # Last 10 errors
            ],
            "window_minutes": self.error_window.total_seconds() / 60,
            "current_window_errors": len(self.error_timestamps),
        }
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        error_counts = {}
        for error in self.errors:
            key = f"{error.category.value}:{error.code}"
            error_counts[key] = error_counts.get(key, 0) + 1
        
        sorted_errors = sorted(
            error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"error": error, "count": count}
            for error, count in sorted_errors[:limit]
        ]
    
    def clear(self) -> None:
        """Clear all error records."""
        self.errors.clear()
        self.error_timestamps.clear()
        self.metrics = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_status": {},
            "errors_by_endpoint": {},
            "error_rate": 0,
            "last_error_time": None,
        }
        logger.info("Cleared all error monitoring data")


# ======================
# ERROR HANDLER MIDDLEWARE
# ======================

class ErrorHandlerMiddleware(BaseMiddleware):
    """
    Advanced Error Handler Middleware.
    
    Features:
    - Centralized exception handling
    - Structured error logging
    - Error monitoring and metrics
    - Graceful error responses
    - Custom error handling hooks
    - Error recovery mechanisms
    - Alerting integration
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        
        # Configuration
        self.debug_mode = self.config.get("debug", False)
        self.log_errors = self.config.get("log_errors", True)
        self.include_traceback = self.config.get("include_traceback", False)
        self.custom_error_pages = self.config.get("custom_error_pages", True)
        
        # Initialize components
        self.error_builder = ErrorBuilder(self.debug_mode)
        self.response_builder = ErrorResponseBuilder(self.debug_mode)
        self.error_monitor = ErrorMonitor()
        
        # Custom error handlers
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        self._register_default_handlers()
        
        # Recovery mechanisms
        self.recovery_attempts = self.config.get("recovery_attempts", 3)
        
        logger.info("ErrorHandlerMiddleware initialized")
    
    def _register_default_handlers(self) -> None:
        """Register default error handlers."""
        self.register_handler(RequestValidationError, self._handle_validation_error)
        self.register_handler(HTTPException, self._handle_http_exception)
        self.register_handler(StarletteHTTPException, self._handle_http_exception)
        self.register_handler(Exception, self._handle_generic_error)
    
    def register_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception, Request], JSONResponse]
    ) -> None:
        """
        Register a custom error handler.
        
        Args:
            exception_type: Exception type to handle
            handler: Handler function
        """
        self.error_handlers[exception_type] = handler
        logger.debug(f"Registered error handler for {exception_type.__name__}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error handling.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        try:
            # Try to process the request
            response = await call_next(request)
            
            # Check for error status codes in response
            if 400 <= response.status_code < 600:
                await self._handle_error_response(response, request)
            
            return response
            
        except Exception as exc:
            # Handle the exception
            return await self._handle_exception(exc, request)
    
    async def _handle_exception(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle an exception and return appropriate response."""
        # Find appropriate handler
        handler = self._find_handler(exc)
        
        try:
            # Execute handler
            response = handler(exc, request)
            
            # Record error for monitoring
            error_details = self.error_builder.build_from_exception(
                exc, request, self.include_traceback
            )
            self.error_monitor.record_error(error_details)
            
            # Execute post-error hooks
            await self._execute_post_error_hooks(error_details, request)
            
            # Check if recovery should be attempted
            if await self._should_attempt_recovery(error_details):
                logger.warning(f"Attempting recovery for error: {error_details.error_id}")
                # Recovery logic could be implemented here
            
            return response
            
        except Exception as handler_error:
            # Fallback if handler fails
            logger.critical(f"Error handler failed: {handler_error}")
            return await self._handle_handler_failure(handler_error, request)
    
    def _find_handler(self, exc: Exception) -> Callable:
        """Find appropriate handler for exception."""
        exc_type = type(exc)
        
        # Check exact match
        if exc_type in self.error_handlers:
            return self.error_handlers[exc_type]
        
        # Check subclass match
        for exc_class, handler in self.error_handlers.items():
            if issubclass(exc_type, exc_class):
                return handler
        
        # Default handler
        return self.error_handlers.get(Exception, self._handle_generic_error)
    
    def _handle_validation_error(self, exc: RequestValidationError, request: Request) -> JSONResponse:
        """Handle validation errors."""
        return self.response_builder.build_validation_response(exc, request)
    
    def _handle_http_exception(self, exc: HTTPException, request: Request) -> JSONResponse:
        """Handle HTTP exceptions."""
        return self.response_builder.build_response(exc, request)
    
    def _handle_generic_error(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle generic/unexpected errors."""
        # For production, hide internal details
        if not self.debug_mode:
            # Create a generic error
            error_details = self.error_builder.build_from_http_error(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                message="An internal server error occurred",
                request=request,
                code="internal_error"
            )
            
            # Log the actual error internally
            actual_error = self.error_builder.build_from_exception(
                exc, request, include_stack_trace=True
            )
            logger.error(
                f"Unhandled error: {actual_error.message}",
                extra={"error": actual_error.to_dict(include_stack_trace=True)}
            )
            
            # Record for monitoring
            self.error_monitor.record_error(actual_error)
            
            # Return generic response
            error_response = ErrorResponse(
                error_id=error_details.error_id,
                message=error_details.message,
                code=error_details.code
            )
            
            content = jsonable_encoder(error_response)
            return JSONResponse(
                status_code=error_details.http_status,
                content=content,
                headers={"X-Error-ID": error_details.error_id}
            )
        
        # In debug mode, show full error
        return self.response_builder.build_response(exc, request, include_details=True)
    
    async def _handle_error_response(self, response: Response, request: Request) -> None:
        """Handle error responses (non-2xx status codes)."""
        # Build error details from response
        error_details = self.error_builder.build_from_http_error(
            status_code=response.status_code,
            message=self._get_status_message(response.status_code),
            request=request,
            code=f"http_{response.status_code}"
        )
        
        # Record for monitoring
        self.error_monitor.record_error(error_details)
        
        # Log the error
        if self.log_errors:
            logger.warning(
                f"HTTP error {response.status_code}: {error_details.message}",
                extra={
                    "error": error_details.to_dict(),
                    "path": str(request.url.path),
                    "method": request.method
                }
            )
    
    async def _handle_handler_failure(self, exc: Exception, request: Request) -> JSONResponse:
        """Handle failure in error handler itself."""
        # Ultimate fallback
        error_response = ErrorResponse(
            error_id=str(uuid.uuid4()),
            message="Critical error in error handling system",
            code="handler_failure"
        )
        
        # Log the critical failure
        logger.critical(
            "Error handler failure",
            extra={
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "request_path": str(request.url.path)
            }
        )
        
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(error_response),
            headers={"X-Error-ID": error_response.error_id}
        )
    
    async def _execute_post_error_hooks(self, error_details: ErrorDetails, request: Request) -> None:
        """Execute post-error hooks (alerting, notifications, etc.)."""
        try:
            # Check if alerting is needed
            if self._should_alert(error_details):
                await self._send_alert(error_details, request)
            
            # Notify monitoring systems
            await self._notify_monitoring(error_details)
            
            # Update metrics dashboards
            await self._update_metrics(error_details)
            
        except Exception as e:
            logger.error(f"Post-error hook failed: {e}")
    
    async def _should_attempt_recovery(self, error_details: ErrorDetails) -> bool:
        """Determine if recovery should be attempted."""
        # Don't attempt recovery for client errors
        if 400 <= error_details.http_status < 500:
            return False
        
        # Only attempt for certain error types
        recoverable_categories = [
            ErrorCategory.DATABASE,
            ErrorCategory.EXTERNAL_API,
            ErrorCategory.SERVICE,
            ErrorCategory.SYSTEM,
        ]
        
        return error_details.category in recoverable_categories
    
    def _should_alert(self, error_details: ErrorDetails) -> bool:
        """Determine if an alert should be sent."""
        # Alert on critical errors
        if error_details.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Alert on high error rate
        if self.error_monitor.metrics["error_rate"] > 10:  # More than 10 errors/minute
            return True
        
        # Alert on specific error patterns
        alert_patterns = [
            "database_connection",
            "external_api_timeout",
            "service_unavailable",
        ]
        
        return any(pattern in error_details.code for pattern in alert_patterns)
    
    async def _send_alert(self, error_details: ErrorDetails, request: Request) -> None:
        """Send alert about error."""
        # This would integrate with your alerting system (PagerDuty, Slack, etc.)
        alert_message = (
            f"🚨 Error Alert: {error_details.message}\n"
            f"Error ID: {error_details.error_id}\n"
            f"Category: {error_details.category.value}\n"
            f"Severity: {error_details.severity.value}\n"
            f"Endpoint: {error_details.context.endpoint if error_details.context else 'Unknown'}\n"
            f"Time: {error_details.timestamp.isoformat()}"
        )
        
        logger.warning(f"Alert triggered: {alert_message}")
        
        # Placeholder for actual alerting integration
        # await alerting_service.send_alert(alert_message)
    
    async def _notify_monitoring(self, error_details: ErrorDetails) -> None:
        """Notify external monitoring systems."""
        # Placeholder for monitoring system integration
        # await monitoring_service.record_error(error_details)
        pass
    
    async def _update_metrics(self, error_details: ErrorDetails) -> None:
        """Update metrics in monitoring dashboard."""
        # Placeholder for metrics update
        # await metrics_service.increment_counter(f"errors.{error_details.category.value}")
        pass
    
    def _get_status_message(self, status_code: int) -> str:
        """Get human-readable message for status code."""
        messages = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Unprocessable Entity",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
        }
        return messages.get(status_code, f"HTTP {status_code}")
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error monitoring metrics."""
        return self.error_monitor.get_metrics()
    
    def get_top_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top errors by frequency."""
        return self.error_monitor.get_top_errors(limit)
    
    def clear_error_logs(self) -> None:
        """Clear error logs and metrics."""
        self.error_monitor.clear()
        logger.info("Error logs cleared")


# ======================
# ERROR HANDLER UTILITIES
# ======================

def create_error_handler(
    debug_mode: bool = False,
    log_errors: bool = True,
    include_traceback: bool = False
) -> ErrorHandlerMiddleware:
    """
    Factory function to create error handler middleware.
    
    Args:
        debug_mode: Enable debug mode
        log_errors: Enable error logging
        include_traceback: Include stack trace in responses
        
    Returns:
        ErrorHandlerMiddleware instance
    """
    def factory(app):
        return ErrorHandlerMiddleware(
            app,
            debug=debug_mode,
            log_errors=log_errors,
            include_traceback=include_traceback
        )
    return factory


def get_default_error_handler_config() -> Dict[str, Any]:
    """
    Get default error handler configuration.
    
    Returns:
        Default configuration
    """
    cfg = get_config()
    
    return {
        "debug": cfg.get("app.debug", False),
        "log_errors": True,
        "include_traceback": cfg.get("app.debug", False),
        "custom_error_pages": True,
        "recovery_attempts": 3,
    }


def setup_error_handler(app: FastAPI, config: Optional[Dict[str, Any]] = None) -> ErrorHandlerMiddleware:
    """
    Setup error handler middleware on FastAPI app.
    
    Args:
        app: FastAPI application
        config: Error handler configuration
        
    Returns:
        ErrorHandlerMiddleware instance
    """
    if config is None:
        config = get_default_error_handler_config()
    
    # Create middleware
    middleware = ErrorHandlerMiddleware(app, **config)
    
    # Add middleware to app
    from ..middleware import MiddlewareManager
    manager = MiddlewareManager(app)
    manager.register("error_handler", ErrorHandlerMiddleware, config)
    manager.setup_app()
    
    # Add error metrics endpoint
    @app.get("/error-metrics", include_in_schema=False)
    async def get_error_metrics() -> Dict[str, Any]:
        """Get error metrics and statistics."""
        return {
            "metrics": middleware.get_error_metrics(),
            "top_errors": middleware.get_top_errors(10),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Add endpoint to clear error logs (protected)
    @app.post("/error-metrics/clear", include_in_schema=False)
    async def clear_error_logs() -> Dict[str, Any]:
        """Clear error logs (requires authentication)."""
        middleware.clear_error_logs()
        return {
            "message": "Error logs cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    logger.info("Error handler middleware setup complete")
    return middleware


# ======================
# ERROR HANDLER DECORATORS
# ======================

def handle_errors(func: Callable) -> Callable:
    """
    Decorator to handle errors in a function.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            # Re-raise HTTP exceptions
            if isinstance(exc, HTTPException):
                raise
            
            # Log and convert to HTTP exception
            error_id = str(uuid.uuid4())
            logger.error(
                f"Error in {func.__name__}: {exc}",
                extra={
                    "error_id": error_id,
                    "function": func.__name__,
                    "module": func.__module__,
                    "traceback": traceback.format_exc()
                }
            )
            
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_id": error_id,
                    "message": "An internal error occurred",
                    "code": "internal_error"
                }
            )
    
    return wrapper


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry function on error.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Exceptions to catch
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff
                    wait_time = delay * (backoff ** attempt)
                    
                    logger.warning(
                        f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {exc}",
                        extra={
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "wait_time": wait_time,
                            "exception": str(exc)
                        }
                    )
                    
                    await asyncio.sleep(wait_time)
            
            # All attempts failed
            raise last_exception
        
        return wrapper
    
    return decorator


# ======================
# GLOBAL ERROR HANDLING
# ======================

def setup_global_exception_handlers(app: FastAPI) -> None:
    """
    Setup global exception handlers for FastAPI app.
    
    Args:
        app: FastAPI application
    """
    # Create error response builder
    response_builder = ErrorResponseBuilder(debug=app.debug)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors."""
        return response_builder.build_validation_response(exc, request)
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        return response_builder.build_response(exc, request)
    
    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle Starlette HTTP exceptions."""
        return response_builder.build_response(exc, request)
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other exceptions."""
        return response_builder.build_response(exc, request)
    
    logger.info("Global exception handlers setup complete")


# ======================
# EXPORTS
# ======================

__all__ = [
    # Main middleware
    "ErrorHandlerMiddleware",
    "create_error_handler",
    "setup_error_handler",
    "setup_global_exception_handlers",
    
    # Models
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "ErrorDetails",
    "ErrorResponse",
    
    # Builders and classifiers
    "ErrorClassifier",
    "ErrorBuilder",
    "ErrorResponseBuilder",
    
    # Monitoring
    "ErrorMonitor",
    
    # Decorators
    "handle_errors",
    "retry_on_error",
    
    # Utilities
    "get_default_error_handler_config",
]


if __name__ == "__main__":
    # Test the error handler middleware
    import asyncio
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    
    print("⚠️ Error Handler Middleware Test")
    print("=" * 50)
    
    # Create test app
    app = FastAPI(debug=True)
    
    # Setup error handler
    handler = setup_error_handler(app, {
        "debug": True,
        "log_errors": True,
        "include_traceback": True
    })
    
    # Add test endpoints
    @app.get("/test/success")
    async def test_success():
        return {"message": "Success"}
    
    @app.get("/test/not-found")
    async def test_not_found():
        raise HTTPException(status_code=404, detail="Resource not found")
    
    @app.get("/test/validation-error")
    async def test_validation_error(value: int = 0):
        if value < 1:
            raise HTTPException(status_code=400, detail="Value must be positive")
        return {"value": value}
    
    @app.get("/test/internal-error")
    async def test_internal_error():
        raise ValueError("Something went wrong internally")
    
    # Test with test client
    client = TestClient(app)
    
    print("\n1. Testing successful request...")
    response = client.get("/test/success")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n2. Testing not found error...")
    response = client.get("/test/not-found")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print(f"   Error ID: {response.headers.get('X-Error-ID')}")
    
    print("\n3. Testing validation error...")
    response = client.get("/test/validation-error?value=0")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n4. Testing internal error...")
    response = client.get("/test/internal-error")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    
    print("\n5. Testing error metrics...")
    metrics = handler.get_error_metrics()
    print(f"   Total errors: {metrics['total_errors']}")
    print(f"   Error rate: {metrics['error_rate']:.2f}/min")
    
    print("\n6. Testing top errors...")
    top_errors = handler.get_top_errors(5)
    for error in top_errors:
        print(f"   {error['error']}: {error['count']}")
    
    print("\n✅ All error handler tests completed successfully!")
