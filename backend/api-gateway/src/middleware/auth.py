"""
Authentication Middleware for API Gateway
Handles JWT token validation and user authentication
"""

import os
import jwt
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from ..core.exceptions import (
    AuthenticationError,
    TokenExpiredError,
    InvalidTokenError,
    AuthorizationError
)

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation
    """
    
    def __init__(
        self,
        app,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize authentication middleware
        
        Args:
            app: FastAPI application
            secret_key: JWT secret key
            algorithm: JWT algorithm
            exclude_paths: Paths to exclude from authentication
        """
        super().__init__(app)
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
        self.algorithm = algorithm
        self.exclude_paths = exclude_paths or [
            '/docs',
            '/redoc',
            '/openapi.json',
            '/health',
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/auth/refresh',
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Extract token from header
            token = self._extract_token(request)
            
            if not token:
                raise AuthenticationError("Missing authentication token")
            
            # Verify and decode token
            payload = self._verify_token(token)
            
            # Attach user info to request state
            request.state.user = payload
            request.state.user_id = payload.get('sub')
            request.state.token = token
            
            logger.debug(f"Authenticated user: {payload.get('sub')}")
            
            # Continue to next middleware/handler
            response = await call_next(request)
            return response
            
        except (AuthenticationError, TokenExpiredError, InvalidTokenError) as e:
            logger.warning(f"Authentication failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            logger.error(f"Unexpected error in auth middleware: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication
        
        Args:
            path: Request path
            
        Returns:
            True if excluded
        """
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from request
        
        Args:
            request: Request object
            
        Returns:
            JWT token or None
        """
        # Try Authorization header first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # Try cookie as fallback
        token = request.cookies.get('access_token')
        if token:
            return token
        
        return None
    
    def _verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token
            
        Returns:
            Decoded payload
            
        Raises:
            TokenExpiredError: If token is expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check expiration
            exp = payload.get('exp')
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise TokenExpiredError()
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")


# Dependency for route protection
async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current authenticated user from request
    
    Args:
        request: Request object
        
    Returns:
        User payload
        
    Raises:
        AuthenticationError: If user not authenticated
    """
    if not hasattr(request.state, 'user'):
        raise AuthenticationError("Not authenticated")
    
    return request.state.user


async def get_current_active_user(request: Request) -> Dict[str, Any]:
    """
    Get current active user
    
    Args:
        request: Request object
        
    Returns:
        User payload
        
    Raises:
        AuthenticationError: If user not authenticated or inactive
    """
    user = await get_current_user(request)
    
    if not user.get('is_active', True):
        raise AuthenticationError("Inactive user")
    
    return user


async def get_current_admin_user(request: Request) -> Dict[str, Any]:
    """
    Get current admin user
    
    Args:
        request: Request object
        
    Returns:
        User payload
        
    Raises:
        AuthorizationError: If user is not admin
    """
    user = await get_current_active_user(request)
    
    if user.get('role') != 'admin':
        raise AuthorizationError("Admin access required")
    
    return user


# Token generation utilities
def create_access_token(
    data: Dict[str, Any],
    secret_key: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        secret_key: JWT secret key
        expires_delta: Token expiration time
        
    Returns:
        JWT token
    """
    secret = secret_key or os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode.update({
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'access'
    })
    
    encoded_jwt = jwt.encode(to_encode, secret, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    secret_key: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Token payload data
        secret_key: JWT secret key
        expires_delta: Token expiration time
        
    Returns:
        JWT refresh token
    """
    secret = secret_key or os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({
        'exp': expire,
        'iat': datetime.utcnow(),
        'type': 'refresh'
    })
    
    encoded_jwt = jwt.encode(to_encode, secret, algorithm="HS256")
    return encoded_jwt


def verify_token(
    token: str,
    secret_key: Optional[str] = None,
    token_type: str = 'access'
) -> Dict[str, Any]:
    """
    Verify JWT token
    
    Args:
        token: JWT token
        secret_key: JWT secret key
        token_type: Expected token type
        
    Returns:
        Decoded payload
        
    Raises:
        TokenExpiredError: If token expired
        InvalidTokenError: If token invalid
    """
    secret = secret_key or os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Verify token type
        if payload.get('type') != token_type:
            raise InvalidTokenError(f"Invalid token type. Expected {token_type}")
        
        # Check expiration
        exp = payload.get('exp')
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise TokenExpiredError()
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


# Role-based access control decorator
def require_role(allowed_roles: list):
    """
    Decorator to require specific roles
    
    Args:
        allowed_roles: List of allowed roles
        
    Returns:
        Decorated function
    """
    async def wrapper(request: Request):
        user = await get_current_user(request)
        user_role = user.get('role', 'user')
        
        if user_role not in allowed_roles:
            raise AuthorizationError(
                f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        
        return user
    
    return wrapper


# Permission-based access control
def require_permission(permission: str):
    """
    Decorator to require specific permission
    
    Args:
        permission: Required permission
        
    Returns:
        Decorated function
    """
    async def wrapper(request: Request):
        user = await get_current_user(request)
        user_permissions = user.get('permissions', [])
        
        if permission not in user_permissions:
            raise AuthorizationError(
                f"Access denied. Required permission: {permission}"
            )
        
        return user
    
    return wrapper


# Export all
__all__ = [
    'AuthMiddleware',
    'get_current_user',
    'get_current_active_user',
    'get_current_admin_user',
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'require_role',
    'require_permission',
]
