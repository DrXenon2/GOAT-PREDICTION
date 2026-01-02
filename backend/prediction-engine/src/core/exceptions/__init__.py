"""
Custom exceptions for the application.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class GoatException(Exception):
    """Base exception for GOAT Prediction."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(GoatException):
    """Authentication related errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR", status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(GoatException):
    """Authorization related errors."""
    
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, "AUTHORIZATION_ERROR", status.HTTP_403_FORBIDDEN)


class NotFoundError(GoatException):
    """Resource not found errors."""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", "NOT_FOUND", status.HTTP_404_NOT_FOUND)


class ValidationError(GoatException):
    """Validation errors."""
    
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, "VALIDATION_ERROR", status.HTTP_422_UNPROCESSABLE_ENTITY)


class RateLimitError(GoatException):
    """Rate limit errors."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", status.HTTP_429_TOO_MANY_REQUESTS)


class DatabaseError(GoatException):
    """Database errors."""
    
    def __init__(self, message: str = "Database error occurred"):
        super().__init__(message, "DATABASE_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExternalServiceError(GoatException):
    """External service errors."""
    
    def __init__(self, service: str, message: str = "Service error"):
        super().__init__(f"{service}: {message}", "EXTERNAL_SERVICE_ERROR", status.HTTP_502_BAD_GATEWAY)


def handle_goat_exception(exc: GoatException) -> Dict[str, Any]:
    """Handle GOAT exceptions and return appropriate response."""
    return {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "status_code": exc.status_code,
        }
    }
