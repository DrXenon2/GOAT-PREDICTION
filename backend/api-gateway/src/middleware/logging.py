"""
Logging Middleware for API Gateway
Request/Response logging with performance tracking
"""

import time
import uuid
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, StreamingResponse
import logging
import json
from datetime import datetime

from ..core.logging import log_request

logger = logging.getLogger(__name__)
access_logger = logging.getLogger('access')


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses
    """
    
    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_body: bool = False,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize logging middleware
        
        Args:
            app: FastAPI application
            log_requests: Log incoming requests
            log_responses: Log outgoing responses
            log_body: Log request/response bodies
            exclude_paths: Paths to exclude from logging
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_body = log_body
        self.exclude_paths = exclude_paths or ['/health', '/metrics']
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging
        
        Args:
            request: Incoming request
            call_next: Next handler
            
        Returns:
            Response
        """
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log incoming request
        if self.log_requests:
            await self._log_request(request, request_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Add headers to response
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Process-Time'] = f"{duration_ms:.2f}ms"
            
            # Log response
            if self.log_responses:
                await self._log_response(request, response, duration_ms, request_id)
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Error processing request {request_id}: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from logging"""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    async def _log_request(self, request: Request, request_id: str) -> None:
        """
        Log incoming request
        
        Args:
            request: Request object
            request_id: Request ID
        """
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Log request body if enabled
        if self.log_body:
            try:
                body = await request.body()
                if body:
                    log_data["body"] = body.decode('utf-8')
            except Exception:
                log_data["body"] = "[Unable to decode body]"
        
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={"extra_fields": log_data}
        )
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        request_id: str
    ) -> None:
        """
        Log outgoing response
        
        Args:
            request: Request object
            response: Response object
            duration_ms: Request duration
            request_id: Request ID
        """
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
        
        # Log to access logger
        access_logger.info(
            f"{request.method} {request.url.path} {response.status_code} - {duration_ms:.2f}ms"
        )
        
        # Determine log level based on status code
        if response.status_code >= 500:
            logger.error("Response (5xx)", extra={"extra_fields": log_data})
        elif response.status_code >= 400:
            logger.warning("Response (4xx)", extra={"extra_fields": log_data})
        else:
            logger.info("Response (2xx/3xx)", extra={"extra_fields": log_data})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging middleware with structured logging
    """
    
    def __init__(self, app, json_logs: bool = False):
        """
        Initialize request logging middleware
        
        Args:
            app: FastAPI application
            json_logs: Use JSON format for logs
        """
        super().__init__(app)
        self.json_logs = json_logs
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with structured logging"""
        # Generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Build request context
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "unknown"),
        }
        
        # Get user info if authenticated
        if hasattr(request.state, 'user'):
            context["user_id"] = request.state.user.get('sub')
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Update context with response info
            context.update({
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            })
            
            # Add headers
            response.headers['X-Request-ID'] = request_id
            response.headers['X-Correlation-ID'] = correlation_id
            
            # Log request
            self._log_request_complete(context)
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            context.update({
                "status_code": 500,
                "duration_ms": round(duration_ms, 2),
                "error": str(e),
                "error_type": type(e).__name__,
            })
            
            self._log_request_error(context)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
    def _log_request_complete(self, context: dict) -> None:
        """Log completed request"""
        if self.json_logs:
            logger.info(json.dumps(context))
        else:
            logger.info(
                f"{context['method']} {context['path']} {context['status_code']} - {context['duration_ms']}ms",
                extra={"extra_fields": context}
            )
        
        # Log to access logger
        access_logger.info(
            f"{context['client_ip']} - {context['method']} {context['path']} "
            f"{context['status_code']} - {context['duration_ms']}ms"
        )
    
    def _log_request_error(self, context: dict) -> None:
        """Log request error"""
        if self.json_logs:
            logger.error(json.dumps(context))
        else:
            logger.error(
                f"{context['method']} {context['path']} - Error: {context.get('error')}",
                extra={"extra_fields": context}
            )


# Performance tracking utilities
class PerformanceLogger:
    """Helper class for performance logging"""
    
    @staticmethod
    def log_slow_request(
        request: Request,
        duration_ms: float,
        threshold_ms: float = 1000
    ) -> None:
        """
        Log slow requests
        
        Args:
            request: Request object
            duration_ms: Request duration
            threshold_ms: Threshold for slow requests
        """
        if duration_ms > threshold_ms:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path}",
                extra={
                    "extra_fields": {
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                        "threshold_ms": threshold_ms,
                    }
                }
            )
    
    @staticmethod
    def log_database_query(query: str, duration_ms: float) -> None:
        """
        Log database query performance
        
        Args:
            query: SQL query
            duration_ms: Query duration
        """
        logger.debug(
            f"Database query executed in {duration_ms:.2f}ms",
            extra={
                "extra_fields": {
                    "query": query,
                    "duration_ms": duration_ms,
                }
            }
        )
    
    @staticmethod
    def log_external_api_call(
        service: str,
        endpoint: str,
        duration_ms: float,
        status_code: int
    ) -> None:
        """
        Log external API call performance
        
        Args:
            service: Service name
            endpoint: API endpoint
            duration_ms: Call duration
            status_code: Response status code
        """
        logger.info(
            f"External API call: {service} {endpoint}",
            extra={
                "extra_fields": {
                    "service": service,
                    "endpoint": endpoint,
                    "duration_ms": duration_ms,
                    "status_code": status_code,
                }
            }
        )


# Export all
__all__ = [
    'LoggingMiddleware',
    'RequestLoggingMiddleware',
    'PerformanceLogger',
]
