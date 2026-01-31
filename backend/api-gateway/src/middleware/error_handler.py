"""
Error Handler Middleware for API Gateway
Centralized error handling and formatting
"""

import sys
import traceback
from typing import Callable, Dict, Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from pydantic import ValidationError
import logging

from ..core.exceptions import BaseAPIException

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling
    """
    
    def __init__(
        self,
        app,
        debug: bool = False,
        include_traceback: bool = False
    ):
        """
        Initialize error handler middleware
        
        Args:
            app: FastAPI application
            debug: Enable debug mode
            include_traceback: Include traceback in error responses
        """
        super().__init__(app)
        self.debug = debug
        self.include_traceback = include_traceback
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with error handling
        
        Args:
            request: Incoming request
            call_next: Next handler
            
        Returns:
            Response
        """
        try:
            response = await call_next(request)
            return response
            
        except BaseAPIException as e:
            # Handle custom API exceptions
            return await self._handle_api_exception(request, e)
            
        except RequestValidationError as e:
            # Handle FastAPI validation errors
            return await self._handle_validation_error(request, e)
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            return await self._handle_pydantic_error(request, e)
            
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(request, e)
    
    async def _handle_api_exception(
        self,
        request: Request,
        exc: BaseAPIException
    ) -> JSONResponse:
        """
        Handle custom API exceptions
        
        Args:
            request: Request object
            exc: API exception
            
        Returns:
            JSON error response
        """
        logger.warning(
            f"API Exception: {exc.__class__.__name__} - {exc.message}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
            }
        )
        
        error_response = {
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
        
        # Add details if available
        if exc.details:
            error_response["details"] = exc.details
        
        # Add traceback in debug mode
        if self.debug and self.include_traceback:
            error_response["traceback"] = self._format_traceback()
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=exc.headers
        )
    
    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle FastAPI request validation errors
        
        Args:
            request: Request object
            exc: Validation error
            
        Returns:
            JSON error response
        """
        logger.warning(
            f"Validation Error: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        # Format validation errors
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        
        error_response = {
            "error": "ValidationError",
            "message": "Request validation failed",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "path": request.url.path,
            "method": request.method,
            "details": {
                "errors": errors
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_pydantic_error(
        self,
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic validation errors
        
        Args:
            request: Request object
            exc: Pydantic validation error
            
        Returns:
            JSON error response
        """
        logger.warning(
            f"Pydantic Validation Error: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error.get("loc", [])),
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        
        error_response = {
            "error": "ValidationError",
            "message": "Data validation failed",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "path": request.url.path,
            "method": request.method,
            "details": {
                "errors": errors
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )
    
    async def _handle_unexpected_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Handle unexpected exceptions
        
        Args:
            request: Request object
            exc: Exception
            
        Returns:
            JSON error response
        """
        logger.error(
            f"Unexpected Exception: {exc.__class__.__name__} - {str(exc)}",
            exc_info=exc,
            extra={
                "path": request.url.path,
                "method": request.method,
            }
        )
        
        error_response = {
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "path": request.url.path,
            "method": request.method,
        }
        
        # Include exception details in debug mode
        if self.debug:
            error_response["details"] = {
                "exception_type": exc.__class__.__name__,
                "exception_message": str(exc),
            }
            
            if self.include_traceback:
                error_response["traceback"] = self._format_traceback()
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    def _format_traceback(self) -> list:
        """
        Format current traceback
        
        Returns:
            List of traceback lines
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        return traceback.format_exception(exc_type, exc_value, exc_traceback)


# Global error handlers for FastAPI
def error_handler(debug: bool = False):
    """
    Decorator factory for error handlers
    
    Args:
        debug: Enable debug mode
        
    Returns:
        Error handler decorator
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseAPIException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content=e.to_dict(),
                    headers=e.headers
                )
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=e)
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={
                        "error": "InternalServerError",
                        "message": "An unexpected error occurred"
                    }
                )
        return wrapper
    return decorator


# Exception handlers for specific error types
async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle HTTP exceptions
    
    Args:
        request: Request object
        exc: Exception
        
    Returns:
        JSON response
    """
    from fastapi.exceptions import HTTPException
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path,
            },
            headers=exc.headers
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred"
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle validation exceptions
    
    Args:
        request: Request object
        exc: Validation error
        
    Returns:
        JSON response
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg", ""),
            "type": error.get("type", ""),
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": {"errors": errors}
        }
    )


def format_error_response(
    error: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format error response
    
    Args:
        error: Error type
        message: Error message
        status_code: HTTP status code
        details: Additional details
        
    Returns:
        Formatted error dictionary
    """
    response = {
        "error": error,
        "message": message,
        "status_code": status_code,
    }
    
    if details:
        response["details"] = details
    
    return response


def register_error_handlers(app):
    """
    Register error handlers with FastAPI app
    
    Args:
        app: FastAPI application
    """
    from fastapi.exceptions import HTTPException
    
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(BaseAPIException, lambda req, exc: JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
        headers=exc.headers
    ))
    
    logger.info("Error handlers registered")


# Export all
__all__ = [
    'ErrorHandlerMiddleware',
    'error_handler',
    'http_exception_handler',
    'validation_exception_handler',
    'format_error_response',
    'register_error_handlers',
]
