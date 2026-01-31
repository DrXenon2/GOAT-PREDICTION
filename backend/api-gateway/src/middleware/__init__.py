"""
Middleware Module for API Gateway
Provides various middleware components for request/response processing
"""

from .auth import AuthMiddleware, get_current_user, verify_token
from .cors import CORSMiddleware, configure_cors
from .error_handler import ErrorHandlerMiddleware, error_handler
from .logging import LoggingMiddleware, RequestLoggingMiddleware
from .middleware_manager import MiddlewareManager, register_middleware
from .rate_limiter import RateLimiterMiddleware, rate_limit
from .validation import ValidationMiddleware, validate_request

__all__ = [
    # Auth
    'AuthMiddleware',
    'get_current_user',
    'verify_token',
    
    # CORS
    'CORSMiddleware',
    'configure_cors',
    
    # Error Handler
    'ErrorHandlerMiddleware',
    'error_handler',
    
    # Logging
    'LoggingMiddleware',
    'RequestLoggingMiddleware',
    
    # Manager
    'MiddlewareManager',
    'register_middleware',
    
    # Rate Limiter
    'RateLimiterMiddleware',
    'rate_limit',
    
    # Validation
    'ValidationMiddleware',
    'validate_request',
]

__version__ = '1.0.0'
