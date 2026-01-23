"""
Exception handler middleware for GOAT Prediction API Gateway.
"""

import logging
from datetime import datetime
from typing import Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.exceptions import APIException
from ..core.logging import log

logger = structlog.get_logger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware to handle exceptions globally."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle exceptions."""
        
        try:
            # Process the request
            response = await call_next(request)
            return response
            
        except APIException as exc:
            # Handle custom API exceptions
            return self._handle_api_exception(request, exc)
            
        except Exception as exc:
            # Handle unexpected exceptions
            return self._handle_unexpected_exception(request, exc)
    
    def _handle_api_exception(self, request: Request, exc: APIException) -> JSONResponse:
        """Handle custom API exceptions."""
        
        # Log the exception
        logger.warning(
            "api_exception",
            path=request.url.path,
            method=request.method,
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
        )
        
        # Prepare error response
        error_response = {
            "error": exc.error_code,
            "message": exc.message,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "method": request.method,
        }
        
        # Add details if present
        if exc.details:
            error_response["details"] = exc.details
        
        # Add request ID if available
        if hasattr(request.state, "request_id"):
            error_response["request_id"] = request.state.request_id
        
        # Add correlation ID if available
        if hasattr(request.state, "correlation_id"):
            error_response["correlation_id"] = request.state.correlation_id
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=self._get_error_headers(request),
        )
    
    def _handle_unexpected_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        
        # Log the exception with full traceback
        logger.error(
            "unexpected_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
            exc_info=True,
        )
        
        # Prepare error response
        error_response = {
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path),
            "method": request.method,
        }
        
        # Add request ID if available
        if hasattr(request.state, "request_id"):
            error_response["request_id"] = request.state.request_id
        
        # Add correlation ID if available
        if hasattr(request.state, "correlation_id"):
            error_response["correlation_id"] = request.state.correlation_id
        
        # Include debug information in development
        from ..core.config import settings
        if settings.DEBUG:
            error_response["debug"] = {
                "error": str(exc),
                "type": type(exc).__name__,
            }
        
        return JSONResponse(
            status_code=500,
            content=error_response,
            headers=self._get_error_headers(request),
        )
    
    def _get_error_headers(self, request: Request) -> dict:
        """Get headers for error responses."""
        
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        
        # Add CORS headers if CORS is enabled
        from ..core.config import settings
        if settings.CORS_ENABLED:
            headers.update({
                "Access-Control-Allow-Origin": ", ".join(settings.CORS_ORIGINS),
                "Access-Control-Allow-Credentials": "true" if settings.CORS_ALLOW_CREDENTIALS else "false",
            })
        
        return headers
