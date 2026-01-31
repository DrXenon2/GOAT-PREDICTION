"""
Middleware Manager for API Gateway
Centralized middleware configuration and management
"""

import os
from typing import List, Optional, Callable
from fastapi import FastAPI
import logging

from .auth import AuthMiddleware
from .cors import configure_cors
from .error_handler import ErrorHandlerMiddleware, register_error_handlers
from .logging import LoggingMiddleware, RequestLoggingMiddleware
from .rate_limiter import RateLimiterMiddleware
from .validation import ValidationMiddleware

logger = logging.getLogger(__name__)


class MiddlewareManager:
    """
    Manager for configuring and registering middlewares
    """
    
    def __init__(self, app: FastAPI):
        """
        Initialize middleware manager
        
        Args:
            app: FastAPI application
        """
        self.app = app
        self.middlewares: List[tuple] = []
        self._configured = False
    
    def configure_all(
        self,
        enable_cors: bool = True,
        enable_auth: bool = True,
        enable_logging: bool = True,
        enable_error_handler: bool = True,
        enable_rate_limiter: bool = True,
        enable_validation: bool = True,
    ) -> None:
        """
        Configure all middlewares
        
        Args:
            enable_cors: Enable CORS middleware
            enable_auth: Enable authentication middleware
            enable_logging: Enable logging middleware
            enable_error_handler: Enable error handler middleware
            enable_rate_limiter: Enable rate limiter middleware
            enable_validation: Enable validation middleware
        """
        if self._configured:
            logger.warning("Middlewares already configured")
            return
        
        env = os.getenv('ENVIRONMENT', 'development').lower()
        debug = env in ['development', 'testing']
        
        logger.info(f"Configuring middlewares for environment: {env}")
        
        # Order matters! Middlewares are executed in reverse order of registration
        # Last registered = first executed
        
        # 1. Error Handler (should catch all errors)
        if enable_error_handler:
            self.add_error_handler(debug=debug)
        
        # 2. Logging (log all requests)
        if enable_logging:
            self.add_logging(json_logs=env == 'production')
        
        # 3. CORS (handle CORS before other processing)
        if enable_cors:
            self.add_cors()
        
        # 4. Rate Limiting (protect endpoints)
        if enable_rate_limiter and env == 'production':
            self.add_rate_limiter()
        
        # 5. Authentication (validate tokens)
        if enable_auth:
            self.add_auth()
        
        # 6. Validation (validate requests)
        if enable_validation:
            self.add_validation()
        
        self._configured = True
        logger.info(f"Configured {len(self.middlewares)} middlewares")
    
    def add_cors(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
    ) -> None:
        """
        Add CORS middleware
        
        Args:
            allow_origins: Allowed origins
            allow_credentials: Allow credentials
            allow_methods: Allowed methods
            allow_headers: Allowed headers
        """
        configure_cors(
            self.app,
            allow_origins=allow_origins,
            allow_credentials=allow_credentials,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
        )
        self.middlewares.append(('CORS', None))
        logger.info("CORS middleware added")
    
    def add_auth(
        self,
        secret_key: Optional[str] = None,
        exclude_paths: Optional[List[str]] = None,
    ) -> None:
        """
        Add authentication middleware
        
        Args:
            secret_key: JWT secret key
            exclude_paths: Paths to exclude from authentication
        """
        self.app.add_middleware(
            AuthMiddleware,
            secret_key=secret_key,
            exclude_paths=exclude_paths,
        )
        self.middlewares.append(('Auth', AuthMiddleware))
        logger.info("Authentication middleware added")
    
    def add_logging(
        self,
        json_logs: bool = False,
        log_body: bool = False,
        exclude_paths: Optional[List[str]] = None,
    ) -> None:
        """
        Add logging middleware
        
        Args:
            json_logs: Use JSON format
            log_body: Log request/response bodies
            exclude_paths: Paths to exclude from logging
        """
        self.app.add_middleware(
            RequestLoggingMiddleware,
            json_logs=json_logs,
        )
        self.middlewares.append(('Logging', RequestLoggingMiddleware))
        logger.info("Logging middleware added")
    
    def add_error_handler(self, debug: bool = False) -> None:
        """
        Add error handler middleware
        
        Args:
            debug: Enable debug mode
        """
        self.app.add_middleware(
            ErrorHandlerMiddleware,
            debug=debug,
            include_traceback=debug,
        )
        
        # Register exception handlers
        register_error_handlers(self.app)
        
        self.middlewares.append(('ErrorHandler', ErrorHandlerMiddleware))
        logger.info("Error handler middleware added")
    
    def add_rate_limiter(
        self,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None,
    ) -> None:
        """
        Add rate limiter middleware
        
        Args:
            requests_per_minute: Requests allowed per minute
            burst_size: Burst size
        """
        self.app.add_middleware(
            RateLimiterMiddleware,
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
        )
        self.middlewares.append(('RateLimiter', RateLimiterMiddleware))
        logger.info("Rate limiter middleware added")
    
    def add_validation(self) -> None:
        """Add validation middleware"""
        self.app.add_middleware(ValidationMiddleware)
        self.middlewares.append(('Validation', ValidationMiddleware))
        logger.info("Validation middleware added")
    
    def add_custom_middleware(
        self,
        middleware_class,
        name: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Add custom middleware
        
        Args:
            middleware_class: Middleware class
            name: Middleware name
            **kwargs: Additional arguments for middleware
        """
        self.app.add_middleware(middleware_class, **kwargs)
        middleware_name = name or middleware_class.__name__
        self.middlewares.append((middleware_name, middleware_class))
        logger.info(f"Custom middleware '{middleware_name}' added")
    
    def get_configured_middlewares(self) -> List[str]:
        """
        Get list of configured middleware names
        
        Returns:
            List of middleware names
        """
        return [name for name, _ in self.middlewares]
    
    def is_configured(self) -> bool:
        """Check if middlewares are configured"""
        return self._configured
    
    def __repr__(self) -> str:
        """String representation"""
        return f"MiddlewareManager(middlewares={len(self.middlewares)})"


# Global middleware manager instance
_middleware_manager: Optional[MiddlewareManager] = None


def get_middleware_manager(app: Optional[FastAPI] = None) -> MiddlewareManager:
    """
    Get middleware manager instance
    
    Args:
        app: FastAPI application
        
    Returns:
        MiddlewareManager instance
    """
    global _middleware_manager
    
    if _middleware_manager is None:
        if app is None:
            raise ValueError("FastAPI app required for first initialization")
        _middleware_manager = MiddlewareManager(app)
    
    return _middleware_manager


def register_middleware(
    app: FastAPI,
    enable_cors: bool = True,
    enable_auth: bool = True,
    enable_logging: bool = True,
    enable_error_handler: bool = True,
    enable_rate_limiter: bool = True,
    enable_validation: bool = True,
) -> MiddlewareManager:
    """
    Register all middlewares with FastAPI app
    
    Args:
        app: FastAPI application
        enable_cors: Enable CORS
        enable_auth: Enable authentication
        enable_logging: Enable logging
        enable_error_handler: Enable error handler
        enable_rate_limiter: Enable rate limiter
        enable_validation: Enable validation
        
    Returns:
        MiddlewareManager instance
    """
    manager = get_middleware_manager(app)
    
    manager.configure_all(
        enable_cors=enable_cors,
        enable_auth=enable_auth,
        enable_logging=enable_logging,
        enable_error_handler=enable_error_handler,
        enable_rate_limiter=enable_rate_limiter,
        enable_validation=enable_validation,
    )
    
    return manager


def configure_middleware_for_environment(app: FastAPI) -> MiddlewareManager:
    """
    Configure middlewares based on environment
    
    Args:
        app: FastAPI application
        
    Returns:
        MiddlewareManager instance
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env == 'production':
        return register_middleware(
            app,
            enable_cors=True,
            enable_auth=True,
            enable_logging=True,
            enable_error_handler=True,
            enable_rate_limiter=True,
            enable_validation=True,
        )
    elif env == 'staging':
        return register_middleware(
            app,
            enable_cors=True,
            enable_auth=True,
            enable_logging=True,
            enable_error_handler=True,
            enable_rate_limiter=True,
            enable_validation=True,
        )
    elif env == 'testing':
        return register_middleware(
            app,
            enable_cors=True,
            enable_auth=False,  # Disable auth in tests
            enable_logging=False,  # Disable logging in tests
            enable_error_handler=True,
            enable_rate_limiter=False,  # Disable rate limiting in tests
            enable_validation=True,
        )
    else:  # development
        return register_middleware(
            app,
            enable_cors=True,
            enable_auth=True,
            enable_logging=True,
            enable_error_handler=True,
            enable_rate_limiter=False,  # Disable in development
            enable_validation=True,
        )


# Export all
__all__ = [
    'MiddlewareManager',
    'get_middleware_manager',
    'register_middleware',
    'configure_middleware_for_environment',
]
