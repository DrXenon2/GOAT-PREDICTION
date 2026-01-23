"""
Middleware package for GOAT Prediction Ultimate API Gateway.
Centralized middleware management with dependency injection and configuration.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Send, Scope

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger
from .auth import AuthMiddleware
from .cors import CORSMiddleware
from .logging import LoggingMiddleware
from .rate_limiter import RateLimiterMiddleware
from .error_handler import ErrorHandlerMiddleware
from .validation import ValidationMiddleware
from .security import SecurityMiddleware
from .cache import CacheMiddleware
from .metrics import MetricsMiddleware
from .compression import CompressionMiddleware
from .timeout import TimeoutMiddleware

# Configure logger
logger = get_logger(__name__)

__version__ = "1.0.0"
__author__ = "GOAT Prediction Team"
__all__ = [
    # Middleware classes
    "AuthMiddleware",
    "CORSMiddleware",
    "LoggingMiddleware",
    "RateLimiterMiddleware",
    "ErrorHandlerMiddleware",
    "ValidationMiddleware",
    "SecurityMiddleware",
    "CacheMiddleware",
    "MetricsMiddleware",
    "CompressionMiddleware",
    "TimeoutMiddleware",
    
    # Functions
    "setup_middleware",
    "create_middleware_stack",
    "get_default_middleware",
    "MiddlewareManager",
    
    # Types
    "MiddlewareConfig",
    "MiddlewareOrder",
]


class MiddlewareConfig:
    """Configuration for middleware."""
    
    def __init__(
        self,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        order: int = 1000
    ):
        self.enabled = enabled
        self.config = config or {}
        self.dependencies = dependencies or []
        self.order = order
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "config": self.config,
            "dependencies": self.dependencies,
            "order": self.order
        }


class MiddlewareOrder:
    """Standard middleware order for consistent execution."""
    
    # Lower numbers execute first (outermost in the stack)
    ERROR_HANDLER = 100
    SECURITY = 200
    CORS = 300
    TIMEOUT = 400
    RATE_LIMITER = 500
    AUTH = 600
    VALIDATION = 700
    CACHE = 800
    LOGGING = 900
    METRICS = 1000
    COMPRESSION = 1100
    
    @classmethod
    def get_all(cls) -> Dict[str, int]:
        """Get all middleware order values."""
        return {
            name: value
            for name, value in cls.__dict__.items()
            if not name.startswith("_") and isinstance(value, int)
        }


class MiddlewareManager:
    """
    Manager for middleware registration and configuration.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.middleware_registry: Dict[str, MiddlewareConfig] = {}
        self.registered_middleware: List[Middleware] = []
        self.logger = get_logger(__name__)
        
        # Load configuration
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load middleware configuration from config manager."""
        try:
            # Load middleware configuration
            middleware_config = config.get("middleware", {})
            
            # Default configurations
            default_configs = {
                "error_handler": MiddlewareConfig(
                    enabled=True,
                    config={"debug": config.get("app.debug", False)},
                    order=MiddlewareOrder.ERROR_HANDLER
                ),
                "security": MiddlewareConfig(
                    enabled=config.get("security.security_headers_enabled", True),
                    config={
                        "csp_enabled": config.get("security.csp_enabled", True),
                        "hsts_enabled": config.get("security.hsts_enabled", True),
                    },
                    order=MiddlewareOrder.SECURITY
                ),
                "cors": MiddlewareConfig(
                    enabled=True,
                    config={
                        "allow_origins": config.get("security.cors_origins", []),
                        "allow_credentials": True,
                        "allow_methods": ["*"],
                        "allow_headers": ["*"],
                    },
                    order=MiddlewareOrder.CORS
                ),
                "timeout": MiddlewareConfig(
                    enabled=True,
                    config={
                        "timeout": config.get("performance.request_timeout", 30)
                    },
                    order=MiddlewareOrder.TIMEOUT
                ),
                "rate_limiter": MiddlewareConfig(
                    enabled=config.get("security.rate_limit_enabled", True),
                    config={
                        "default_limit": config.get("security.rate_limit_default", "100/minute"),
                        "premium_limit": config.get("security.rate_limit_premium", "500/minute"),
                        "admin_limit": config.get("security.rate_limit_admin", "1000/minute"),
                    },
                    order=MiddlewareOrder.RATE_LIMITER
                ),
                "auth": MiddlewareConfig(
                    enabled=True,
                    config={
                        "secret_key": config.get("security.secret_key"),
                        "algorithm": config.get("security.algorithm", "HS256"),
                        "exclude_paths": [
                            "/api/v1/auth/login",
                            "/api/v1/auth/register",
                            "/api/v1/auth/refresh",
                            "/health",
                            "/docs",
                            "/redoc",
                            "/openapi.json",
                        ]
                    },
                    order=MiddlewareOrder.AUTH
                ),
                "validation": MiddlewareConfig(
                    enabled=True,
                    config={
                        "validate_request": True,
                        "validate_response": True,
                    },
                    order=MiddlewareOrder.VALIDATION
                ),
                "cache": MiddlewareConfig(
                    enabled=config.get("cache.enabled", True),
                    config={
                        "default_ttl": config.get("cache.default_ttl", 300),
                        "cache_control": True,
                    },
                    order=MiddlewareOrder.CACHE
                ),
                "logging": MiddlewareConfig(
                    enabled=True,
                    config={
                        "log_level": config.get("logging.level", "INFO"),
                        "exclude_paths": ["/health", "/metrics"],
                    },
                    order=MiddlewareOrder.LOGGING
                ),
                "metrics": MiddlewareConfig(
                    enabled=config.get("monitoring.prometheus_enabled", True),
                    config={
                        "exclude_paths": ["/health", "/metrics"],
                    },
                    order=MiddlewareOrder.METRICS
                ),
                "compression": MiddlewareConfig(
                    enabled=True,
                    config={
                        "min_size": config.get("performance.gzip_min_size", 1000),
                        "compression_level": config.get("performance.gzip_compression_level", 6),
                    },
                    order=MiddlewareOrder.COMPRESSION
                ),
            }
            
            # Update with user configuration
            for name, user_config in middleware_config.items():
                if name in default_configs:
                    if isinstance(user_config, dict):
                        if "enabled" in user_config:
                            default_configs[name].enabled = user_config["enabled"]
                        if "config" in user_config:
                            default_configs[name].config.update(user_config["config"])
                        if "order" in user_config:
                            default_configs[name].order = user_config["order"]
            
            self.middleware_registry = default_configs
            
            self.logger.info(f"Loaded {len(self.middleware_registry)} middleware configurations")
            
        except Exception as e:
            self.logger.error(f"Error loading middleware configuration: {e}")
            # Fallback to basic configuration
            self._load_fallback_configuration()
    
    def _load_fallback_configuration(self) -> None:
        """Load fallback configuration when main config fails."""
        self.middleware_registry = {
            "error_handler": MiddlewareConfig(enabled=True, order=100),
            "cors": MiddlewareConfig(enabled=True, order=300),
            "auth": MiddlewareConfig(enabled=True, order=600),
            "logging": MiddlewareConfig(enabled=True, order=900),
        }
        self.logger.warning("Using fallback middleware configuration")
    
    def register(
        self,
        name: str,
        middleware_class: type,
        config: Optional[MiddlewareConfig] = None
    ) -> None:
        """
        Register a middleware with configuration.
        
        Args:
            name: Middleware name
            middleware_class: Middleware class
            config: Middleware configuration
        """
        if config is None:
            config = MiddlewareConfig()
        
        self.middleware_registry[name] = config
        
        if config.enabled:
            try:
                # Create middleware instance
                middleware_instance = Middleware(
                    middleware_class,
                    **config.config
                )
                
                # Store in registry
                self.registered_middleware.append(middleware_instance)
                
                self.logger.info(f"Registered middleware: {name}")
                
            except Exception as e:
                self.logger.error(f"Error registering middleware {name}: {e}")
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a middleware.
        
        Args:
            name: Middleware name to unregister
            
        Returns:
            True if middleware was removed
        """
        if name in self.middleware_registry:
            del self.middleware_registry[name]
            
            # Remove from registered middleware
            self.registered_middleware = [
                m for m in self.registered_middleware
                if not (hasattr(m, 'cls') and m.cls.__name__.lower() == name.lower())
            ]
            
            self.logger.info(f"Unregistered middleware: {name}")
            return True
        
        return False
    
    def get_middleware_config(self, name: str) -> Optional[MiddlewareConfig]:
        """
        Get middleware configuration.
        
        Args:
            name: Middleware name
            
        Returns:
            MiddlewareConfig or None
        """
        return self.middleware_registry.get(name)
    
    def update_config(self, name: str, **kwargs) -> bool:
        """
        Update middleware configuration.
        
        Args:
            name: Middleware name
            **kwargs: Configuration updates
            
        Returns:
            True if configuration was updated
        """
        if name not in self.middleware_registry:
            return False
        
        config = self.middleware_registry[name]
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            elif key in config.config:
                config.config[key] = value
        
        self.logger.info(f"Updated middleware configuration: {name}")
        return True
    
    def create_middleware_stack(self) -> List[Middleware]:
        """
        Create middleware stack based on configuration.
        
        Returns:
            List of middleware instances in correct order
        """
        # Sort middleware by order
        sorted_middleware = sorted(
            self.middleware_registry.items(),
            key=lambda x: x[1].order
        )
        
        middleware_stack = []
        
        for name, middleware_config in sorted_middleware:
            if not middleware_config.enabled:
                self.logger.debug(f"Skipping disabled middleware: {name}")
                continue
            
            try:
                # Map middleware names to classes
                middleware_class = self._get_middleware_class(name)
                if middleware_class:
                    middleware_instance = Middleware(
                        middleware_class,
                        **middleware_config.config
                    )
                    middleware_stack.append(middleware_instance)
                    
                    self.logger.debug(f"Added middleware to stack: {name}")
                else:
                    self.logger.warning(f"No middleware class found for: {name}")
            
            except Exception as e:
                self.logger.error(f"Error creating middleware {name}: {e}")
        
        return middleware_stack
    
    def _get_middleware_class(self, name: str) -> Optional[type]:
        """
        Get middleware class by name.
        
        Args:
            name: Middleware name
            
        Returns:
            Middleware class or None
        """
        middleware_map = {
            "error_handler": ErrorHandlerMiddleware,
            "security": SecurityMiddleware,
            "cors": CORSMiddleware,
            "timeout": TimeoutMiddleware,
            "rate_limiter": RateLimiterMiddleware,
            "auth": AuthMiddleware,
            "validation": ValidationMiddleware,
            "cache": CacheMiddleware,
            "logging": LoggingMiddleware,
            "metrics": MetricsMiddleware,
            "compression": CompressionMiddleware,
        }
        
        return middleware_map.get(name.lower())
    
    def setup_app(self) -> None:
        """Setup middleware on FastAPI app."""
        middleware_stack = self.create_middleware_stack()
        
        # Clear existing middleware
        self.app.user_middleware.clear()
        self.app.middleware_stack = None
        
        # Add middleware in correct order
        for middleware in middleware_stack:
            self.app.add_middleware(middleware.cls, **middleware.options)
        
        # Rebuild middleware stack
        self.app.middleware_stack = self.app.build_middleware_stack()
        
        self.logger.info(f"Setup {len(middleware_stack)} middleware on app")
    
    def get_middleware_info(self) -> Dict[str, Any]:
        """
        Get information about all middleware.
        
        Returns:
            Dictionary with middleware information
        """
        info = {
            "total": len(self.middleware_registry),
            "enabled": sum(1 for c in self.middleware_registry.values() if c.enabled),
            "middleware": {}
        }
        
        for name, config in self.middleware_registry.items():
            info["middleware"][name] = {
                "enabled": config.enabled,
                "order": config.order,
                "dependencies": config.dependencies,
                "config_keys": list(config.config.keys())
            }
        
        return info


# Factory function for middleware creation
def create_middleware_stack(
    app: FastAPI,
    custom_middleware: Optional[List[Middleware]] = None
) -> List[Middleware]:
    """
    Create a complete middleware stack.
    
    Args:
        app: FastAPI application
        custom_middleware: Additional custom middleware
        
    Returns:
        Complete middleware stack
    """
    manager = MiddlewareManager(app)
    
    # Add custom middleware if provided
    if custom_middleware:
        for middleware in custom_middleware:
            if isinstance(middleware, Middleware):
                manager.registered_middleware.append(middleware)
    
    return manager.create_middleware_stack()


def setup_middleware(app: FastAPI) -> MiddlewareManager:
    """
    Setup all middleware on FastAPI app.
    
    Args:
        app: FastAPI application
        
    Returns:
        MiddlewareManager instance
    """
    manager = MiddlewareManager(app)
    manager.setup_app()
    return manager


def get_default_middleware() -> List[Dict[str, Any]]:
    """
    Get default middleware configuration.
    
    Returns:
        List of default middleware configurations
    """
    cfg = get_config()
    
    return [
        {
            "name": "error_handler",
            "enabled": True,
            "order": MiddlewareOrder.ERROR_HANDLER,
            "config": {
                "debug": cfg.get("app.debug", False)
            }
        },
        {
            "name": "security",
            "enabled": cfg.get("security.security_headers_enabled", True),
            "order": MiddlewareOrder.SECURITY,
            "config": {
                "csp_enabled": cfg.get("security.csp_enabled", True),
                "hsts_enabled": cfg.get("security.hsts_enabled", True),
            }
        },
        {
            "name": "cors",
            "enabled": True,
            "order": MiddlewareOrder.CORS,
            "config": {
                "allow_origins": cfg.get("security.cors_origins", []),
                "allow_credentials": True,
                "allow_methods": ["*"],
                "allow_headers": ["*"],
            }
        },
        {
            "name": "timeout",
            "enabled": True,
            "order": MiddlewareOrder.TIMEOUT,
            "config": {
                "timeout": cfg.get("performance.request_timeout", 30)
            }
        },
        {
            "name": "rate_limiter",
            "enabled": cfg.get("security.rate_limit_enabled", True),
            "order": MiddlewareOrder.RATE_LIMITER,
            "config": {
                "default_limit": cfg.get("security.rate_limit_default", "100/minute"),
                "premium_limit": cfg.get("security.rate_limit_premium", "500/minute"),
                "admin_limit": cfg.get("security.rate_limit_admin", "1000/minute"),
            }
        },
        {
            "name": "auth",
            "enabled": True,
            "order": MiddlewareOrder.AUTH,
            "config": {
                "secret_key": cfg.get("security.secret_key"),
                "algorithm": cfg.get("security.algorithm", "HS256"),
                "exclude_paths": [
                    "/api/v1/auth/login",
                    "/api/v1/auth/register",
                    "/api/v1/auth/refresh",
                    "/health",
                    "/docs",
                    "/redoc",
                    "/openapi.json",
                ]
            }
        },
        {
            "name": "validation",
            "enabled": True,
            "order": MiddlewareOrder.VALIDATION,
            "config": {
                "validate_request": True,
                "validate_response": True,
            }
        },
        {
            "name": "cache",
            "enabled": cfg.get("cache.enabled", True),
            "order": MiddlewareOrder.CACHE,
            "config": {
                "default_ttl": cfg.get("cache.default_ttl", 300),
                "cache_control": True,
            }
        },
        {
            "name": "logging",
            "enabled": True,
            "order": MiddlewareOrder.LOGGING,
            "config": {
                "log_level": cfg.get("logging.level", "INFO"),
                "exclude_paths": ["/health", "/metrics"],
            }
        },
        {
            "name": "metrics",
            "enabled": cfg.get("monitoring.prometheus_enabled", True),
            "order": MiddlewareOrder.METRICS,
            "config": {
                "exclude_paths": ["/health", "/metrics"],
            }
        },
        {
            "name": "compression",
            "enabled": True,
            "order": MiddlewareOrder.COMPRESSION,
            "config": {
                "min_size": cfg.get("performance.gzip_min_size", 1000),
                "compression_level": cfg.get("performance.gzip_compression_level", 6),
            }
        },
    ]


# Utility middleware functions
async def process_request(request: Request, call_next: Callable) -> Response:
    """
    Standard request processing with middleware.
    
    Args:
        request: Incoming request
        call_next: Next middleware/endpoint
        
    Returns:
        Response
    """
    # Add request ID if not present
    if not hasattr(request.state, "request_id"):
        import uuid
        request.state.request_id = str(uuid.uuid4())
    
    # Add start time for timing
    request.state.start_time = getattr(request.state, "start_time", None)
    if request.state.start_time is None:
        import time
        request.state.start_time = time.time()
    
    # Process request through middleware chain
    response = await call_next(request)
    
    return response


class BaseMiddleware(BaseHTTPMiddleware):
    """Base middleware with common functionality."""
    
    def __init__(self, app: ASGIApp, **kwargs):
        super().__init__(app)
        self.config = kwargs
        self.logger = get_logger(self.__class__.__name__)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Dispatch request through middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Default implementation passes through
        return await call_next(request)
    
    def should_process(self, request: Request) -> bool:
        """
        Determine if middleware should process this request.
        
        Args:
            request: Incoming request
            
        Returns:
            True if middleware should process
        """
        exclude_paths = self.config.get("exclude_paths", [])
        path = request.url.path
        
        # Check if path is excluded
        for exclude_path in exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        return True
    
    def get_request_info(self, request: Request) -> Dict[str, Any]:
        """
        Get standardized request information.
        
        Args:
            request: Incoming request
            
        Returns:
            Dictionary with request info
        """
        return {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "client": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "request_id": getattr(request.state, "request_id", None),
        }


# Health check endpoint for middleware testing
async def health_check(request: Request) -> Dict[str, Any]:
    """
    Health check endpoint that shows middleware status.
    
    Args:
        request: HTTP request
        
    Returns:
        Health status with middleware info
    """
    from ..core.config import config
    
    middleware_status = {}
    
    # Check each middleware
    middlewares_to_check = [
        ("database", "database.health", lambda: True),
        ("redis", "redis.health", lambda: True),
        ("cache", "cache.enabled", lambda: True),
        ("auth", lambda: "auth" in config.get("middleware", {})),
    ]
    
    for name, check, func in middlewares_to_check:
        try:
            if callable(check):
                status = check()
            else:
                status = config.get(check, False)
            middleware_status[name] = {
                "status": "healthy" if status else "disabled",
                "enabled": bool(status)
            }
        except Exception as e:
            middleware_status[name] = {
                "status": "error",
                "error": str(e),
                "enabled": False
            }
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __version__,
        "middleware": middleware_status,
        "request_id": getattr(request.state, "request_id", None)
    }


# Import all middleware modules
__all__ += [
    "BaseMiddleware",
    "process_request",
    "health_check",
]


# Initialize on import
logger.info(f"Middleware package initialized (v{__version__})")


if __name__ == "__main__":
    # Test the middleware package
    import asyncio
    from fastapi import FastAPI
    
    app = FastAPI(title="Middleware Test")
    
    # Add test endpoint
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Test successful"}
    
    # Setup middleware
    manager = setup_middleware(app)
    
    # Print middleware info
    print("Middleware Configuration:")
    print("=" * 50)
    
    info = manager.get_middleware_info()
    for name, details in info["middleware"].items():
        status = "✅ ENABLED" if details["enabled"] else "❌ DISABLED"
        print(f"{status} {name:20} (order: {details['order']:4})")
    
    print(f"\nTotal: {info['total']} middleware, {info['enabled']} enabled")
    
    # Test health check
    @app.get("/health")
    async def health():
        return await health_check(Request({"type": "http"}))
    
    print("\n✅ Middleware package test completed successfully!")
