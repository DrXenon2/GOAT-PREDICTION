"""
Validation Middleware for API Gateway
Validates requests and responses with enhanced security
"""

import json
import re
from typing import Callable, Optional, List, Dict, Any
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from ..core.exceptions import ValidationError, InvalidInputError

logger = logging.getLogger(__name__)


class ValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response validation and sanitization
    """
    
    def __init__(
        self,
        app,
        max_content_length: int = 10 * 1024 * 1024,  # 10MB
        validate_content_type: bool = True,
        sanitize_input: bool = True,
        check_sql_injection: bool = True,
        check_xss: bool = True,
        exclude_paths: Optional[List[str]] = None,
    ):
        """
        Initialize validation middleware
        
        Args:
            app: FastAPI application
            max_content_length: Maximum request body size in bytes
            validate_content_type: Validate Content-Type header
            sanitize_input: Sanitize user input
            check_sql_injection: Check for SQL injection attempts
            check_xss: Check for XSS attempts
            exclude_paths: Paths to exclude from validation
        """
        super().__init__(app)
        
        self.max_content_length = max_content_length
        self.validate_content_type = validate_content_type
        self.sanitize_input = sanitize_input
        self.check_sql_injection = check_sql_injection
        self.check_xss = check_xss
        self.exclude_paths = exclude_paths or ['/docs', '/redoc', '/openapi.json']
        
        # SQL injection patterns
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(--|#|\/\*|\*\/)",
            r"(\bOR\b.*=.*)",
            r"(\bAND\b.*=.*)",
            r"('|(--)|;|\||&)",
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe",
            r"<object",
            r"<embed",
        ]
        
        logger.info("Validation middleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through validation middleware
        
        Args:
            request: Incoming request
            call_next: Next handler
            
        Returns:
            Response
        """
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Validate request
            await self._validate_request(request)
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.message
            )
        except Exception as e:
            logger.error(f"Unexpected error in validation middleware: {str(e)}")
            raise
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from validation"""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    async def _validate_request(self, request: Request) -> None:
        """
        Validate incoming request
        
        Args:
            request: Request object
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate Content-Type
        if self.validate_content_type and request.method in ['POST', 'PUT', 'PATCH']:
            self._validate_content_type(request)
        
        # Validate Content-Length
        self._validate_content_length(request)
        
        # Validate query parameters
        if request.query_params:
            self._validate_query_params(request.query_params)
        
        # Validate request body
        if request.method in ['POST', 'PUT', 'PATCH']:
            await self._validate_body(request)
    
    def _validate_content_type(self, request: Request) -> None:
        """
        Validate Content-Type header
        
        Args:
            request: Request object
            
        Raises:
            ValidationError: If Content-Type is invalid
        """
        content_type = request.headers.get('Content-Type', '')
        
        allowed_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data',
        ]
        
        if not any(content_type.startswith(allowed) for allowed in allowed_types):
            raise ValidationError(
                message=f"Invalid Content-Type: {content_type}",
                details={"allowed_types": allowed_types}
            )
    
    def _validate_content_length(self, request: Request) -> None:
        """
        Validate Content-Length header
        
        Args:
            request: Request object
            
        Raises:
            ValidationError: If content too large
        """
        content_length = request.headers.get('Content-Length')
        
        if content_length:
            length = int(content_length)
            if length > self.max_content_length:
                raise ValidationError(
                    message=f"Request body too large: {length} bytes",
                    details={
                        "max_size": self.max_content_length,
                        "actual_size": length
                    }
                )
    
    def _validate_query_params(self, params: dict) -> None:
        """
        Validate query parameters
        
        Args:
            params: Query parameters
            
        Raises:
            ValidationError: If validation fails
        """
        for key, value in params.items():
            # Check for SQL injection
            if self.check_sql_injection:
                if self._contains_sql_injection(str(value)):
                    raise ValidationError(
                        message=f"Potential SQL injection detected in parameter: {key}",
                        field=key
                    )
            
            # Check for XSS
            if self.check_xss:
                if self._contains_xss(str(value)):
                    raise ValidationError(
                        message=f"Potential XSS detected in parameter: {key}",
                        field=key
                    )
            
            # Sanitize if enabled
            if self.sanitize_input:
                params[key] = self._sanitize_string(str(value))
    
    async def _validate_body(self, request: Request) -> None:
        """
        Validate request body
        
        Args:
            request: Request object
            
        Raises:
            ValidationError: If validation fails
        """
        content_type = request.headers.get('Content-Type', '')
        
        if content_type.startswith('application/json'):
            try:
                # Read and parse body
                body = await request.body()
                
                if body:
                    data = json.loads(body)
                    
                    # Validate JSON data recursively
                    self._validate_json_data(data)
                    
            except json.JSONDecodeError as e:
                raise ValidationError(
                    message="Invalid JSON in request body",
                    details={"error": str(e)}
                )
    
    def _validate_json_data(self, data: Any, path: str = "") -> None:
        """
        Recursively validate JSON data
        
        Args:
            data: Data to validate
            path: Current path in data structure
            
        Raises:
            ValidationError: If validation fails
        """
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Validate key
                if self.check_sql_injection and self._contains_sql_injection(key):
                    raise ValidationError(
                        message=f"Potential SQL injection in key: {current_path}",
                        field=current_path
                    )
                
                # Validate value
                self._validate_json_data(value, current_path)
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self._validate_json_data(item, current_path)
                
        elif isinstance(data, str):
            # Check string values
            if self.check_sql_injection and self._contains_sql_injection(data):
                raise ValidationError(
                    message=f"Potential SQL injection at: {path}",
                    field=path
                )
            
            if self.check_xss and self._contains_xss(data):
                raise ValidationError(
                    message=f"Potential XSS at: {path}",
                    field=path
                )
    
    def _contains_sql_injection(self, text: str) -> bool:
        """
        Check if text contains SQL injection patterns
        
        Args:
            text: Text to check
            
        Returns:
            True if potential SQL injection detected
        """
        text_upper = text.upper()
        
        for pattern in self.sql_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        
        return False
    
    def _contains_xss(self, text: str) -> bool:
        """
        Check if text contains XSS patterns
        
        Args:
            text: Text to check
            
        Returns:
            True if potential XSS detected
        """
        text_lower = text.lower()
        
        for pattern in self.xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _sanitize_string(self, text: str) -> str:
        """
        Sanitize string input
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
        
        # Trim whitespace
        text = text.strip()
        
        return text


# Utility functions for validation
def validate_email(email: str) -> bool:
    """
    Validate email address
    
    Args:
        email: Email address
        
    Returns:
        True if valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate UUID
    
    Args:
        uuid_string: UUID string
        
    Returns:
        True if valid
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_string.lower()))


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML content
    
    Args:
        html: HTML content
        
    Returns:
        Sanitized HTML
    """
    # Remove script tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove event handlers
    html = re.sub(r'\s*on\w+\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    # Remove javascript: protocol
    html = re.sub(r'javascript:', '', html, flags=re.IGNORECASE)
    
    return html


def validate_request(
    content_type: Optional[str] = None,
    max_length: Optional[int] = None,
):
    """
    Decorator for request validation
    
    Args:
        content_type: Required content type
        max_length: Maximum content length
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            # Validate content type
            if content_type:
                request_content_type = request.headers.get('Content-Type', '')
                if not request_content_type.startswith(content_type):
                    raise InvalidInputError(
                        "Content-Type",
                        f"Expected {content_type}"
                    )
            
            # Validate content length
            if max_length:
                content_length = request.headers.get('Content-Length')
                if content_length and int(content_length) > max_length:
                    raise ValidationError(
                        message=f"Request too large: max {max_length} bytes"
                    )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Export all
__all__ = [
    'ValidationMiddleware',
    'validate_email',
    'validate_url',
    'validate_uuid',
    'sanitize_html',
    'validate_request',
]
