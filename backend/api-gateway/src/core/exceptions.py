"""
Core Exceptions for API Gateway
Centralized exception definitions for the application
"""

from typing import Optional, Dict, Any, List
from fastapi import status


class BaseAPIException(Exception):
    """Base exception for all API exceptions"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize base API exception
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
            headers: Optional HTTP headers
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.headers = headers
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


# Authentication & Authorization Exceptions

class AuthenticationError(BaseAPIException):
    """Exception raised for authentication failures"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            headers={"WWW-Authenticate": "Bearer"}
        )


class InvalidCredentialsError(AuthenticationError):
    """Exception raised for invalid credentials"""
    
    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message)


class TokenExpiredError(AuthenticationError):
    """Exception raised when token has expired"""
    
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message)


class InvalidTokenError(AuthenticationError):
    """Exception raised for invalid tokens"""
    
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message)


class AuthorizationError(BaseAPIException):
    """Exception raised for authorization failures"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InsufficientPermissionsError(AuthorizationError):
    """Exception raised when user lacks required permissions"""
    
    def __init__(self, required_permission: str):
        super().__init__(
            message=f"Insufficient permissions. Required: {required_permission}",
            details={"required_permission": required_permission}
        )


# Validation Exceptions

class ValidationError(BaseAPIException):
    """Exception raised for validation errors"""
    
    def __init__(
        self,
        message: str = "Validation error",
        field: Optional[str] = None,
        errors: Optional[List[Dict[str, Any]]] = None
    ):
        details = {}
        if field:
            details["field"] = field
        if errors:
            details["errors"] = errors
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class InvalidInputError(ValidationError):
    """Exception raised for invalid input"""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Invalid input for field '{field}': {message}",
            field=field
        )


# Resource Exceptions

class ResourceNotFoundError(BaseAPIException):
    """Exception raised when resource is not found"""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        message: Optional[str] = None
    ):
        if message is None:
            if resource_id:
                message = f"{resource_type} with ID '{resource_id}' not found"
            else:
                message = f"{resource_type} not found"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            }
        )


class ResourceAlreadyExistsError(BaseAPIException):
    """Exception raised when resource already exists"""
    
    def __init__(
        self,
        resource_type: str,
        identifier: str,
        message: Optional[str] = None
    ):
        if message is None:
            message = f"{resource_type} with identifier '{identifier}' already exists"
        
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details={
                "resource_type": resource_type,
                "identifier": identifier
            }
        )


class ResourceConflictError(BaseAPIException):
    """Exception raised for resource conflicts"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


# Database Exceptions

class DatabaseError(BaseAPIException):
    """Exception raised for database errors"""
    
    def __init__(self, message: str = "Database error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DatabaseConnectionError(DatabaseError):
    """Exception raised for database connection errors"""
    
    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(message=message)


class DatabaseQueryError(DatabaseError):
    """Exception raised for database query errors"""
    
    def __init__(self, message: str, query: Optional[str] = None):
        details = {"query": query} if query else {}
        super().__init__(message=message, details=details)


# External Service Exceptions

class ExternalServiceError(BaseAPIException):
    """Exception raised for external service errors"""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        details: Optional[Dict[str, Any]] = None
    ):
        service_details = {"service": service_name}
        if details:
            service_details.update(details)
        
        super().__init__(
            message=f"{service_name}: {message}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=service_details
        )


class ExternalServiceTimeoutError(ExternalServiceError):
    """Exception raised when external service times out"""
    
    def __init__(self, service_name: str, timeout: int):
        super().__init__(
            service_name=service_name,
            message=f"Request timeout after {timeout}s",
            details={"timeout": timeout}
        )


class ExternalServiceUnavailableError(ExternalServiceError):
    """Exception raised when external service is unavailable"""
    
    def __init__(self, service_name: str):
        super().__init__(
            service_name=service_name,
            message="Service unavailable"
        )


# Rate Limiting Exceptions

class RateLimitExceededError(BaseAPIException):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(
        self,
        limit: int,
        period: int,
        retry_after: Optional[int] = None
    ):
        message = f"Rate limit exceeded: {limit} requests per {period} seconds"
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "limit": limit,
                "period": period,
                "retry_after": retry_after
            },
            headers=headers
        )


# Business Logic Exceptions

class BusinessLogicError(BaseAPIException):
    """Exception raised for business logic errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class InvalidOperationError(BusinessLogicError):
    """Exception raised for invalid operations"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Invalid operation '{operation}': {reason}",
            details={
                "operation": operation,
                "reason": reason
            }
        )


class PreconditionFailedError(BaseAPIException):
    """Exception raised when preconditions are not met"""
    
    def __init__(self, message: str, conditions: Optional[List[str]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            details={"failed_conditions": conditions} if conditions else {}
        )


# File & Upload Exceptions

class FileError(BaseAPIException):
    """Exception raised for file-related errors"""
    
    def __init__(self, message: str, filename: Optional[str] = None):
        details = {"filename": filename} if filename else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class FileTooLargeError(FileError):
    """Exception raised when file is too large"""
    
    def __init__(self, filename: str, max_size: int, actual_size: int):
        super().__init__(
            message=f"File '{filename}' exceeds maximum size of {max_size} bytes",
            filename=filename
        )
        self.details.update({
            "max_size": max_size,
            "actual_size": actual_size
        })


class InvalidFileTypeError(FileError):
    """Exception raised for invalid file types"""
    
    def __init__(self, filename: str, allowed_types: List[str]):
        super().__init__(
            message=f"Invalid file type for '{filename}'. Allowed: {', '.join(allowed_types)}",
            filename=filename
        )
        self.details["allowed_types"] = allowed_types


# Cache Exceptions

class CacheError(BaseAPIException):
    """Exception raised for cache errors"""
    
    def __init__(self, message: str = "Cache error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


# WebSocket Exceptions

class WebSocketError(BaseAPIException):
    """Exception raised for WebSocket errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


# Payment Exceptions

class PaymentError(BaseAPIException):
    """Exception raised for payment errors"""
    
    def __init__(self, message: str, transaction_id: Optional[str] = None):
        details = {"transaction_id": transaction_id} if transaction_id else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details=details
        )


class PaymentRequiredError(PaymentError):
    """Exception raised when payment is required"""
    
    def __init__(self, feature: str):
        super().__init__(
            message=f"Payment required to access '{feature}'",
        )
        self.details["feature"] = feature


# Generic HTTP Exceptions

class BadRequestError(BaseAPIException):
    """Exception for bad requests"""
    
    def __init__(self, message: str = "Bad request", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class InternalServerError(BaseAPIException):
    """Exception for internal server errors"""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ServiceUnavailableError(BaseAPIException):
    """Exception when service is unavailable"""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Export all exceptions
__all__ = [
    'BaseAPIException',
    'AuthenticationError',
    'InvalidCredentialsError',
    'TokenExpiredError',
    'InvalidTokenError',
    'AuthorizationError',
    'InsufficientPermissionsError',
    'ValidationError',
    'InvalidInputError',
    'ResourceNotFoundError',
    'ResourceAlreadyExistsError',
    'ResourceConflictError',
    'DatabaseError',
    'DatabaseConnectionError',
    'DatabaseQueryError',
    'ExternalServiceError',
    'ExternalServiceTimeoutError',
    'ExternalServiceUnavailableError',
    'RateLimitExceededError',
    'BusinessLogicError',
    'InvalidOperationError',
    'PreconditionFailedError',
    'FileError',
    'FileTooLargeError',
    'InvalidFileTypeError',
    'CacheError',
    'WebSocketError',
    'PaymentError',
    'PaymentRequiredError',
    'BadRequestError',
    'InternalServerError',
    'ServiceUnavailableError',
]
