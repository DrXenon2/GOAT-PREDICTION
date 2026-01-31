"""
CORS Middleware for API Gateway
Handles Cross-Origin Resource Sharing configuration
"""

import os
from typing import List, Optional, Sequence
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with additional security features
    """
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Optional[List[str]] = None,
        allow_credentials: bool = True,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600,
        allow_origin_regex: Optional[str] = None,
    ):
        """
        Initialize CORS middleware
        
        Args:
            app: ASGI application
            allow_origins: List of allowed origins
            allow_credentials: Allow credentials
            allow_methods: Allowed HTTP methods
            allow_headers: Allowed headers
            expose_headers: Headers to expose
            max_age: Preflight cache duration
            allow_origin_regex: Regex pattern for allowed origins
        """
        super().__init__(app)
        
        # Get from environment or use defaults
        self.allow_origins = allow_origins or self._get_allowed_origins()
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        self.allow_headers = allow_headers or ['*']
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        self.allow_origin_regex = allow_origin_regex
        
        logger.info(f"CORS middleware initialized with origins: {self.allow_origins}")
    
    def _get_allowed_origins(self) -> List[str]:
        """
        Get allowed origins from environment
        
        Returns:
            List of allowed origins
        """
        env = os.getenv('ENVIRONMENT', 'development').lower()
        
        if env == 'production':
            origins_str = os.getenv('CORS_ORIGINS', '')
            if origins_str:
                return [origin.strip() for origin in origins_str.split(',')]
            return []
        elif env == 'staging':
            return [
                'https://staging.goat-prediction.com',
                'https://staging-admin.goat-prediction.com',
            ]
        else:  # development
            return [
                'http://localhost:3000',
                'http://localhost:3001',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:3001',
            ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through CORS middleware
        
        Args:
            request: Incoming request
            call_next: Next handler
            
        Returns:
            Response with CORS headers
        """
        origin = request.headers.get('origin')
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(origin)
        
        # Process normal request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin:
            self._add_cors_headers(response, origin)
        
        return response
    
    def _handle_preflight(self, origin: Optional[str]) -> Response:
        """
        Handle CORS preflight request
        
        Args:
            origin: Request origin
            
        Returns:
            Preflight response
        """
        response = Response(status_code=204)
        
        if origin and self._is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            
            if self.allow_credentials:
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            response.headers['Access-Control-Allow-Methods'] = ', '.join(self.allow_methods)
            response.headers['Access-Control-Allow-Headers'] = ', '.join(self.allow_headers)
            response.headers['Access-Control-Max-Age'] = str(self.max_age)
        
        return response
    
    def _add_cors_headers(self, response: Response, origin: str) -> None:
        """
        Add CORS headers to response
        
        Args:
            response: Response object
            origin: Request origin
        """
        if self._is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin
            
            if self.allow_credentials:
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            if self.expose_headers:
                response.headers['Access-Control-Expose-Headers'] = ', '.join(self.expose_headers)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed
        
        Args:
            origin: Request origin
            
        Returns:
            True if allowed
        """
        # Allow all origins if wildcard is set
        if '*' in self.allow_origins:
            return True
        
        # Check exact match
        if origin in self.allow_origins:
            return True
        
        # Check regex pattern if configured
        if self.allow_origin_regex:
            import re
            if re.match(self.allow_origin_regex, origin):
                return True
        
        return False


def configure_cors(
    app: FastAPI,
    allow_origins: Optional[List[str]] = None,
    allow_credentials: bool = True,
    allow_methods: Optional[List[str]] = None,
    allow_headers: Optional[List[str]] = None,
    expose_headers: Optional[List[str]] = None,
    max_age: int = 600,
) -> None:
    """
    Configure CORS for FastAPI application
    
    Args:
        app: FastAPI application
        allow_origins: Allowed origins
        allow_credentials: Allow credentials
        allow_methods: Allowed methods
        allow_headers: Allowed headers
        expose_headers: Exposed headers
        max_age: Max age for preflight cache
    """
    # Get environment-specific origins
    if allow_origins is None:
        env = os.getenv('ENVIRONMENT', 'development').lower()
        
        if env == 'production':
            origins_str = os.getenv('CORS_ORIGINS', '')
            allow_origins = [origin.strip() for origin in origins_str.split(',')] if origins_str else []
        elif env == 'staging':
            allow_origins = [
                'https://staging.goat-prediction.com',
                'https://staging-admin.goat-prediction.com',
            ]
        else:  # development
            allow_origins = [
                'http://localhost:3000',
                'http://localhost:3001',
                'http://127.0.0.1:3000',
                'http://127.0.0.1:3001',
            ]
    
    # Set default methods if not provided
    if allow_methods is None:
        allow_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD']
    
    # Set default headers if not provided
    if allow_headers is None:
        allow_headers = [
            'Accept',
            'Accept-Language',
            'Content-Type',
            'Authorization',
            'X-Request-ID',
            'X-Correlation-ID',
        ]
    
    # Add CORS middleware
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers or [],
        max_age=max_age,
    )
    
    logger.info(f"CORS configured with origins: {allow_origins}")


def get_cors_settings() -> dict:
    """
    Get CORS settings based on environment
    
    Returns:
        CORS configuration dictionary
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    settings = {
        'allow_credentials': True,
        'allow_methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'],
        'allow_headers': [
            'Accept',
            'Accept-Language',
            'Content-Type',
            'Authorization',
            'X-Request-ID',
            'X-Correlation-ID',
        ],
        'expose_headers': [
            'X-Request-ID',
            'X-Total-Count',
            'X-Page',
            'X-Per-Page',
        ],
        'max_age': 600,
    }
    
    if env == 'production':
        origins_str = os.getenv('CORS_ORIGINS', '')
        settings['allow_origins'] = [
            origin.strip() for origin in origins_str.split(',')
        ] if origins_str else []
    elif env == 'staging':
        settings['allow_origins'] = [
            'https://staging.goat-prediction.com',
            'https://staging-admin.goat-prediction.com',
        ]
    else:  # development/testing
        settings['allow_origins'] = [
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001',
        ]
    
    return settings


def validate_origin(origin: str, allowed_origins: List[str]) -> bool:
    """
    Validate if origin is allowed
    
    Args:
        origin: Origin to validate
        allowed_origins: List of allowed origins
        
    Returns:
        True if valid
    """
    # Allow all if wildcard present
    if '*' in allowed_origins:
        return True
    
    # Direct match
    if origin in allowed_origins:
        return True
    
    # Protocol-agnostic match (http/https)
    for allowed in allowed_origins:
        if allowed.replace('https://', '').replace('http://', '') == \
           origin.replace('https://', '').replace('http://', ''):
            return True
    
    return False


# Security headers helper
def add_security_headers(response: Response) -> None:
    """
    Add security headers to response
    
    Args:
        response: Response object
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy
    csp = [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "frame-ancestors 'none'",
    ]
    response.headers['Content-Security-Policy'] = '; '.join(csp)


# Export all
__all__ = [
    'CORSMiddleware',
    'configure_cors',
    'get_cors_settings',
    'validate_origin',
    'add_security_headers',
]
