"""
Custom exceptions for GOAT Prediction API Gateway.
"""

from typing import Any, Dict, Optional


class APIException(Exception):
    """Base exception for all API errors."""
    
    def __init__(
        self,
        status_code: int = 500,
        error_code: str = "internal_error",
        message: str = "An error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Validation error."""
    
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(400, "validation_error", message, details)


class AuthenticationError(APIException):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(401, "authentication_error", message, details)


class AuthorizationError(APIException):
    """Authorization error."""
    
    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(403, "authorization_error", message, details)


class NotFoundError(APIException):
    """Resource not found error."""
    
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(404, "not_found", message, details)


class RateLimitError(APIException):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        super().__init__(429, "rate_limit_exceeded", message, details)


class BadRequestError(APIException):
    """Bad request error."""
    
    def __init__(self, message: str = "Bad request", details: Optional[Dict[str, Any]] = None):
        super().__init__(400, "bad_request", message, details)


class DatabaseError(APIException):
    """Database error."""
    
    def __init__(self, message: str = "Database error", details: Optional[Dict[str, Any]] = None):
        super().__init__(500, "database_error", message, details)


class ExternalServiceError(APIException):
    """External service error."""
    
    def __init__(self, message: str = "External service error", details: Optional[Dict[str, Any]] = None):
        super().__init__(502, "external_service_error", message, details)


class TimeoutError(APIException):
    """Request timeout error."""
    
    def __init__(self, message: str = "Request timeout", details: Optional[Dict[str, Any]] = None):
        super().__init__(504, "timeout_error", message, details)
