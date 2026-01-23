"""
Advanced JWT Authentication Middleware for GOAT Prediction Ultimate.
Supports multiple authentication strategies, token refresh, and granular permissions.
"""

import jwt
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
from functools import wraps
import redis
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from pydantic import BaseModel, Field, validator

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger
from ..core.exceptions import AuthenticationError, AuthorizationError, TokenExpiredError
from .base import BaseMiddleware

logger = get_logger(__name__)

# ======================
# DATA MODELS
# ======================

class TokenPayload(BaseModel):
    """JWT Token payload model."""
    sub: str = Field(..., description="Subject (user ID)")
    email: Optional[str] = Field(None, description="User email")
    role: str = Field("user", description="User role")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    iss: str = Field("goat-prediction", description="Issuer")
    aud: str = Field("goat-prediction-api", description="Audience")
    iat: int = Field(default_factory=lambda: int(time.time()), description="Issued at")
    exp: int = Field(..., description="Expiration time")
    jti: str = Field(default_factory=lambda: str(uuid.uuid4()), description="JWT ID")
    token_type: str = Field("access", description="Token type")
    refresh_token_id: Optional[str] = Field(None, description="Associated refresh token ID")
    
    @validator('exp')
    def validate_expiration(cls, v):
        """Validate expiration is in the future."""
        if v <= time.time():
            raise ValueError("Token has expired")
        return v
    
    class Config:
        extra = "forbid"


class UserSession(BaseModel):
    """User session data model."""
    user_id: str
    email: str
    role: str
    permissions: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "role": self.role,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_id": self.device_id,
            "session_id": self.session_id,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        """Create from dictionary."""
        # Handle datetime strings
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if isinstance(data.get('last_active'), str):
            data['last_active'] = datetime.fromisoformat(data['last_active'].replace('Z', '+00:00'))
        return cls(**data)


class AuthenticationResult(BaseModel):
    """Authentication result model."""
    user_id: str
    email: str
    role: str
    permissions: List[str]
    session_id: str
    token_payload: TokenPayload
    is_authenticated: bool = True
    is_authorized: bool = True
    token_type: str = "access"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return self.role == role
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """Check if user has all specified permissions."""
        return all(perm in self.permissions for perm in permissions)


# ======================
# EXCEPTIONS
# ======================

class AuthMiddlewareError(Exception):
    """Base exception for authentication middleware errors."""
    pass


class InvalidTokenError(AuthMiddlewareError):
    """Invalid or malformed token error."""
    pass


class TokenRevokedError(AuthMiddlewareError):
    """Token has been revoked."""
    pass


class InsufficientPermissionsError(AuthMiddlewareError):
    """User lacks required permissions."""
    pass


# ======================
# TOKEN MANAGER
# ======================

class TokenManager:
    """Manages JWT token creation, validation, and storage."""
    
    def __init__(self):
        self.config = config
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis client for token storage."""
        try:
            redis_config = self.config.get_redis_config()
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
                db=redis_config.db,
                decode_responses=True,
                max_connections=redis_config.max_connections
            )
            self.redis_client.ping()
            logger.info("TokenManager: Redis client initialized")
        except Exception as e:
            logger.warning(f"TokenManager: Redis initialization failed: {e}")
            self.redis_client = None
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: str = "user",
        permissions: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        refresh_token_id: Optional[str] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT access token.
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            permissions: List of user permissions
            expires_delta: Token expiration delta
            refresh_token_id: Associated refresh token ID
            additional_claims: Additional claims to include
            
        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(
                minutes=self.config.get("security.access_token_expire_minutes", 30)
            )
        
        expire = datetime.utcnow() + expires_delta
        
        payload = TokenPayload(
            sub=user_id,
            email=email,
            role=role,
            permissions=permissions or [],
            exp=int(expire.timestamp()),
            refresh_token_id=refresh_token_id
        )
        
        # Add additional claims
        payload_dict = payload.dict()
        if additional_claims:
            payload_dict.update(additional_claims)
        
        # Create token
        token = jwt.encode(
            payload_dict,
            self.config.get("security.secret_key"),
            algorithm=self.config.get("security.algorithm", "HS256")
        )
        
        # Store token in Redis if available
        if self.redis_client:
            try:
                key = f"token:access:{payload.jti}"
                ttl = int(expires_delta.total_seconds())
                self.redis_client.setex(key, ttl, user_id)
                
                # Also store in user's active tokens set
                user_tokens_key = f"user:tokens:{user_id}"
                self.redis_client.sadd(user_tokens_key, payload.jti)
                self.redis_client.expire(user_tokens_key, ttl)
            except Exception as e:
                logger.error(f"Failed to store access token in Redis: {e}")
        
        logger.debug(f"Created access token for user {user_id}")
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        device_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create a refresh token with associated access token.
        
        Args:
            user_id: User ID
            device_id: Device identifier
            
        Returns:
            Tuple of (refresh_token, refresh_token_id)
        """
        refresh_token_id = str(uuid.uuid4())
        expires_delta = timedelta(
            days=self.config.get("security.refresh_token_expire_days", 7)
        )
        expire = datetime.utcnow() + expires_delta
        
        # Create refresh token payload
        payload = {
            "sub": user_id,
            "type": "refresh",
            "jti": refresh_token_id,
            "exp": int(expire.timestamp()),
            "iat": int(time.time()),
            "device_id": device_id
        }
        
        refresh_token = jwt.encode(
            payload,
            self.config.get("security.secret_key"),
            algorithm=self.config.get("security.algorithm", "HS256")
        )
        
        # Store refresh token in Redis
        if self.redis_client:
            try:
                key = f"token:refresh:{refresh_token_id}"
                ttl = int(expires_delta.total_seconds())
                
                # Store refresh token metadata
                metadata = {
                    "user_id": user_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "device_id": device_id,
                    "is_active": True
                }
                
                self.redis_client.hset(key, mapping=metadata)
                self.redis_client.expire(key, ttl)
                
                # Add to user's refresh tokens
                user_refresh_key = f"user:refresh_tokens:{user_id}"
                self.redis_client.sadd(user_refresh_key, refresh_token_id)
                self.redis_client.expire(user_refresh_key, ttl)
                
            except Exception as e:
                logger.error(f"Failed to store refresh token in Redis: {e}")
        
        logger.debug(f"Created refresh token for user {user_id}")
        return refresh_token, refresh_token_id
    
    def validate_token(
        self,
        token: str,
        token_type: str = "access",
        require_active: bool = True
    ) -> TokenPayload:
        """
        Validate a JWT token.
        
        Args:
            token: JWT token string
            token_type: Expected token type
            require_active: Whether to check if token is active
            
        Returns:
            TokenPayload if valid
            
        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token has expired
            TokenRevokedError: If token has been revoked
        """
        try:
            # Decode token
            payload_dict = jwt.decode(
                token,
                self.config.get("security.secret_key"),
                algorithms=[self.config.get("security.algorithm", "HS256")],
                audience="goat-prediction-api",
                issuer="goat-prediction"
            )
            
            # Convert to TokenPayload
            payload = TokenPayload(**payload_dict)
            
            # Check token type
            if payload.token_type != token_type:
                raise InvalidTokenError(f"Expected {token_type} token, got {payload.token_type}")
            
            # Check if token is revoked (blacklisted)
            if require_active and self._is_token_revoked(payload.jti):
                raise TokenRevokedError("Token has been revoked")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}")
        except Exception as e:
            raise InvalidTokenError(f"Token validation failed: {e}")
    
    def refresh_access_token(
        self,
        refresh_token: str,
        device_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Create new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            device_id: Device identifier
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            InvalidTokenError: If refresh token is invalid
            TokenRevokedError: If refresh token is revoked
        """
        try:
            # Validate refresh token
            payload = self.validate_token(refresh_token, token_type="refresh")
            
            # Check if refresh token exists and is active
            if self.redis_client:
                key = f"token:refresh:{payload.jti}"
                metadata = self.redis_client.hgetall(key)
                
                if not metadata or metadata.get("is_active") != "True":
                    raise TokenRevokedError("Refresh token has been revoked")
                
                # Optionally check device ID
                if device_id and metadata.get("device_id") != device_id:
                    logger.warning(f"Device mismatch for refresh token {payload.jti}")
            
            # Get user information (in real app, fetch from database)
            user_id = payload.sub
            
            # Create new tokens
            new_refresh_token, new_refresh_token_id = self.create_refresh_token(
                user_id, device_id
            )
            
            new_access_token = self.create_access_token(
                user_id=user_id,
                email=payload.get("email", ""),
                role=payload.get("role", "user"),
                permissions=payload.get("permissions", []),
                refresh_token_id=new_refresh_token_id
            )
            
            # Revoke old refresh token
            self.revoke_token(payload.jti, token_type="refresh")
            
            logger.info(f"Refreshed tokens for user {user_id}")
            return new_access_token, new_refresh_token
            
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
    def revoke_token(
        self,
        token_id: str,
        token_type: str = "access",
        user_id: Optional[str] = None
    ) -> bool:
        """
        Revoke a token.
        
        Args:
            token_id: Token ID (jti)
            token_type: Type of token (access or refresh)
            user_id: Optional user ID for validation
            
        Returns:
            True if token was revoked
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"token:{token_type}:{token_id}"
            
            # Get token metadata if exists
            if token_type == "refresh":
                metadata = self.redis_client.hgetall(key)
                if metadata and user_id and metadata.get("user_id") != user_id:
                    logger.warning(f"User {user_id} attempted to revoke token belonging to {metadata.get('user_id')}")
                    return False
            
            # Add to blacklist
            blacklist_key = f"token:blacklist:{token_id}"
            ttl = 86400  # 24 hours
            self.redis_client.setex(blacklist_key, ttl, "revoked")
            
            # Remove from active tokens
            self.redis_client.delete(key)
            
            logger.info(f"Revoked {token_type} token: {token_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke token {token_id}: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        Revoke all tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        if not self.redis_client:
            return False
        
        try:
            # Get all user's access tokens
            user_tokens_key = f"user:tokens:{user_id}"
            access_tokens = self.redis_client.smembers(user_tokens_key) or []
            
            # Get all user's refresh tokens
            user_refresh_key = f"user:refresh_tokens:{user_id}"
            refresh_tokens = self.redis_client.smembers(user_refresh_key) or []
            
            # Revoke all tokens
            for token_id in access_tokens:
                self.revoke_token(token_id, "access", user_id)
            
            for token_id in refresh_tokens:
                self.revoke_token(token_id, "refresh", user_id)
            
            # Clean up user token sets
            self.redis_client.delete(user_tokens_key)
            self.redis_client.delete(user_refresh_key)
            
            logger.info(f"Revoked all tokens for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke all tokens for user {user_id}: {e}")
            return False
    
    def _is_token_revoked(self, token_id: str) -> bool:
        """
        Check if a token is revoked.
        
        Args:
            token_id: Token ID (jti)
            
        Returns:
            True if token is revoked
        """
        if not self.redis_client:
            return False
        
        try:
            blacklist_key = f"token:blacklist:{token_id}"
            return self.redis_client.exists(blacklist_key) > 0
        except Exception:
            return False
    
    def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active session information
        """
        if not self.redis_client:
            return []
        
        try:
            sessions = []
            
            # Get refresh tokens (represent sessions)
            user_refresh_key = f"user:refresh_tokens:{user_id}"
            refresh_token_ids = self.redis_client.smembers(user_refresh_key) or []
            
            for token_id in refresh_token_ids:
                key = f"token:refresh:{token_id}"
                metadata = self.redis_client.hgetall(key)
                if metadata and metadata.get("is_active") == "True":
                    sessions.append({
                        "session_id": token_id,
                        "created_at": metadata.get("created_at"),
                        "device_id": metadata.get("device_id"),
                        "last_used": metadata.get("last_used", metadata.get("created_at"))
                    })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions for user {user_id}: {e}")
            return []


# ======================
# AUTHENTICATION MIDDLEWARE
# ======================

class AuthMiddleware(BaseMiddleware):
    """
    Advanced JWT Authentication Middleware.
    
    Features:
    - JWT token validation
    - Role-based access control
    - Permission checking
    - Token refresh support
    - Session management
    - Device tracking
    - Token revocation
    - Rate limiting per user
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.token_manager = TokenManager()
        self.security = HTTPBearer(auto_error=False)
        
        # Configuration
        self.secret_key = self.config.get("secret_key")
        self.algorithm = self.config.get("algorithm", "HS256")
        self.token_location = self.config.get("token_location", "headers")  # headers, cookies, both
        self.cookie_name = self.config.get("cookie_name", "access_token")
        self.header_name = self.config.get("header_name", "Authorization")
        self.header_type = self.config.get("header_type", "Bearer")
        self.exclude_paths = set(self.config.get("exclude_paths", []))
        self.auto_renew = self.config.get("auto_renew", False)
        self.renewal_threshold = self.config.get("renewal_threshold", 300)  # seconds
        
        # Role permissions mapping
        self.role_permissions = {
            "user": [
                "predictions:read",
                "bets:create",
                "profile:read",
                "profile:update"
            ],
            "premium": [
                "predictions:read",
                "predictions:advanced",
                "bets:create",
                "analytics:basic",
                "profile:read",
                "profile:update"
            ],
            "admin": [
                "predictions:read",
                "predictions:write",
                "bets:create",
                "bets:manage",
                "analytics:full",
                "users:read",
                "users:write",
                "system:manage",
                "profile:read",
                "profile:update"
            ],
            "super_admin": [
                "*"  # All permissions
            ]
        }
        
        # Cache for user permissions (to avoid repeated DB calls)
        self.permissions_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        logger.info("AuthMiddleware initialized")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through authentication middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip authentication for excluded paths
        if self._should_skip_auth(request):
            return await call_next(request)
        
        try:
            # Extract token from request
            token = await self._extract_token(request)
            if not token:
                raise AuthenticationError("No authentication token provided")
            
            # Validate token
            payload = self.token_manager.validate_token(token)
            
            # Get user permissions
            permissions = await self._get_user_permissions(payload.sub, payload.role)
            
            # Check token renewal
            if self.auto_renew and self._should_renew_token(payload):
                new_token = await self._renew_token(payload, request)
                if new_token:
                    request.state.new_access_token = new_token
            
            # Create authentication result
            auth_result = AuthenticationResult(
                user_id=payload.sub,
                email=payload.email or "",
                role=payload.role,
                permissions=permissions,
                session_id=payload.jti,
                token_payload=payload
            )
            
            # Store in request state
            request.state.user = auth_result
            request.state.user_id = payload.sub
            request.state.user_role = payload.role
            request.state.user_permissions = permissions
            
            # Update session activity
            await self._update_session_activity(payload.jti, request)
            
            # Process request
            response = await call_next(request)
            
            # Add new token to response if renewed
            if hasattr(request.state, 'new_access_token'):
                self._add_token_to_response(response, request.state.new_access_token)
            
            return response
            
        except (TokenExpiredError, InvalidTokenError, TokenRevokedError) as e:
            logger.warning(f"Authentication failed: {e}")
            return self._create_unauthorized_response(str(e))
        
        except AuthenticationError as e:
            logger.warning(f"Authentication error: {e}")
            return self._create_unauthorized_response(str(e))
        
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            return self._create_unauthorized_response("Internal authentication error")
    
    def _should_skip_auth(self, request: Request) -> bool:
        """
        Check if authentication should be skipped for this request.
        
        Args:
            request: Incoming request
            
        Returns:
            True if authentication should be skipped
        """
        path = request.url.path
        
        # Check exact matches
        if path in self.exclude_paths:
            return True
        
        # Check prefix matches
        for exclude_path in self.exclude_paths:
            if exclude_path.endswith('*') and path.startswith(exclude_path[:-1]):
                return True
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        return False
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract token from request based on configured location.
        
        Args:
            request: Incoming request
            
        Returns:
            Token string or None
        """
        token = None
        
        # Try headers
        if self.token_location in ["headers", "both"]:
            auth_header = request.headers.get(self.header_name)
            if auth_header:
                scheme, token = get_authorization_scheme_param(auth_header)
                if scheme.lower() != self.header_type.lower():
                    token = None
        
        # Try cookies
        if not token and self.token_location in ["cookies", "both"]:
            token = request.cookies.get(self.cookie_name)
        
        return token
    
    async def _get_user_permissions(self, user_id: str, role: str) -> List[str]:
        """
        Get permissions for a user.
        
        Args:
            user_id: User ID
            role: User role
            
        Returns:
            List of permissions
        """
        # Check cache first
        cache_key = f"permissions:{user_id}"
        if cache_key in self.permissions_cache:
            cached = self.permissions_cache[cache_key]
            if time.time() - cached['timestamp'] < self.cache_ttl:
                return cached['permissions']
        
        # Get base permissions from role
        permissions = self.role_permissions.get(role, [])
        
        # In a real application, you would:
        # 1. Fetch user from database
        # 2. Get custom permissions
        # 3. Merge with role permissions
        
        # For now, return role permissions
        result = permissions.copy()
        
        # Cache the result
        self.permissions_cache[cache_key] = {
            'permissions': result,
            'timestamp': time.time()
        }
        
        return result
    
    def _should_renew_token(self, payload: TokenPayload) -> bool:
        """
        Check if token should be renewed.
        
        Args:
            payload: Token payload
            
        Returns:
            True if token should be renewed
        """
        time_to_expiry = payload.exp - time.time()
        return time_to_expiry < self.renewal_threshold
    
    async def _renew_token(self, payload: TokenPayload, request: Request) -> Optional[str]:
        """
        Renew an access token.
        
        Args:
            payload: Current token payload
            request: Request object
            
        Returns:
            New access token or None
        """
        try:
            # Check if we have a refresh token ID
            if not payload.refresh_token_id:
                return None
            
            # Verify refresh token is still valid
            if self.token_manager.redis_client:
                key = f"token:refresh:{payload.refresh_token_id}"
                if not self.token_manager.redis_client.exists(key):
                    return None
            
            # Create new access token
            new_token = self.token_manager.create_access_token(
                user_id=payload.sub,
                email=payload.email or "",
                role=payload.role,
                permissions=payload.permissions,
                refresh_token_id=payload.refresh_token_id
            )
            
            logger.debug(f"Renewed access token for user {payload.sub}")
            return new_token
            
        except Exception as e:
            logger.error(f"Token renewal failed for user {payload.sub}: {e}")
            return None
    
    async def _update_session_activity(self, token_id: str, request: Request) -> None:
        """
        Update session activity timestamp.
        
        Args:
            token_id: Token ID
            request: Request object
        """
        if not self.token_manager.redis_client:
            return
        
        try:
            # Update last active time for the token
            key = f"token:access:{token_id}"
            if self.token_manager.redis_client.exists(key):
                # Store additional session info
                session_info = {
                    "last_active": datetime.utcnow().isoformat(),
                    "last_ip": request.client.host if request.client else None,
                    "last_user_agent": request.headers.get("user-agent")
                }
                
                # Use pipeline for efficiency
                pipe = self.token_manager.redis_client.pipeline()
                for field, value in session_info.items():
                    if value:
                        pipe.hset(key, field, value)
                pipe.execute()
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
    
    def _add_token_to_response(self, response: Response, token: str) -> None:
        """
        Add token to response based on configuration.
        
        Args:
            response: Response object
            token: New access token
        """
        if self.token_location in ["headers", "both"]:
            response.headers[f"X-New-Access-Token"] = token
        
        if self.token_location in ["cookies", "both"]:
            response.set_cookie(
                key=self.cookie_name,
                value=token,
                httponly=True,
                secure=not config.is_development(),
                samesite="strict",
                max_age=self.config.get("security.access_token_expire_minutes", 30) * 60
            )
    
    def _create_unauthorized_response(self, message: str) -> Response:
        """
        Create unauthorized response.
        
        Args:
            message: Error message
            
        Returns:
            Response with 401 status
        """
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


# ======================
# DEPENDENCY INJECTION
# ======================

class AuthDependency:
    """Dependency injection for authentication."""
    
    def __init__(self, required: bool = True, scopes: Optional[List[str]] = None):
        self.required = required
        self.scopes = scopes or []
    
    async def __call__(self, request: Request) -> Optional[AuthenticationResult]:
        """
        Get authenticated user from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            AuthenticationResult or None
            
        Raises:
            HTTPException: If authentication fails
        """
        # Check if user is authenticated
        if not hasattr(request.state, 'user'):
            if self.required:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            return None
        
        auth_result = request.state.user
        
        # Check scopes/permissions
        if self.scopes:
            for scope in self.scopes:
                if not auth_result.has_permission(scope):
                    raise HTTPException(
                        status_code=HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {scope}"
                    )
        
        return auth_result


# Factory function for creating auth dependencies
def requires_auth(
    required: bool = True,
    permissions: Optional[List[str]] = None,
    roles: Optional[List[str]] = None
) -> Callable:
    """
    Create authentication dependency with permission/role checks.
    
    Args:
        required: Whether authentication is required
        permissions: Required permissions
        roles: Required roles
        
    Returns:
        Dependency function
    """
    async def dependency(request: Request) -> Optional[AuthenticationResult]:
        auth = AuthDependency(required=required)
        auth_result = await auth(request)
        
        if not auth_result:
            return None
        
        # Check roles
        if roles and not any(auth_result.has_role(role) for role in roles):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required one of: {roles}"
            )
        
        # Check permissions
        if permissions:
            for permission in permissions:
                if not auth_result.has_permission(permission):
                    raise HTTPException(
                        status_code=HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {permission}"
                    )
        
        return auth_result
    
    return dependency


# Common authentication dependencies
def get_current_user() -> Callable:
    """Get current authenticated user (required)."""
    return requires_auth(required=True)


def get_optional_user() -> Callable:
    """Get current user if authenticated, None otherwise."""
    return requires_auth(required=False)


def require_permission(permission: str) -> Callable:
    """Require specific permission."""
    return requires_auth(permissions=[permission])


def require_role(role: str) -> Callable:
    """Require specific role."""
    return requires_auth(roles=[role])


def require_admin() -> Callable:
    """Require admin role."""
    return requires_auth(roles=["admin", "super_admin"])


# ======================
# PERMISSION CHECKER
# ======================

class PermissionChecker:
    """Utility for checking permissions."""
    
    @staticmethod
    def has_permission(request: Request, permission: str) -> bool:
        """
        Check if current user has specific permission.
        
        Args:
            request: FastAPI request
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        if not hasattr(request.state, 'user_permissions'):
            return False
        
        return permission in request.state.user_permissions
    
    @staticmethod
    def has_any_permission(request: Request, permissions: List[str]) -> bool:
        """
        Check if current user has any of the specified permissions.
        
        Args:
            request: FastAPI request
            permissions: List of permissions
            
        Returns:
            True if user has any permission
        """
        if not hasattr(request.state, 'user_permissions'):
            return False
        
        return any(perm in request.state.user_permissions for perm in permissions)
    
    @staticmethod
    def has_all_permissions(request: Request, permissions: List[str]) -> bool:
        """
        Check if current user has all specified permissions.
        
        Args:
            request: FastAPI request
            permissions: List of permissions
            
        Returns:
            True if user has all permissions
        """
        if not hasattr(request.state, 'user_permissions'):
            return False
        
        return all(perm in request.state.user_permissions for perm in permissions)
    
    @staticmethod
    def get_user_role(request: Request) -> Optional[str]:
        """
        Get current user's role.
        
        Args:
            request: FastAPI request
            
        Returns:
            User role or None
        """
        return getattr(request.state, 'user_role', None)
    
    @staticmethod
    def get_user_id(request: Request) -> Optional[str]:
        """
        Get current user's ID.
        
        Args:
            request: FastAPI request
            
        Returns:
            User ID or None
        """
        return getattr(request.state, 'user_id', None)


# ======================
# DECORATORS
# ======================

def permission_required(permission: str):
    """
    Decorator to require specific permission for endpoint.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise RuntimeError("Request object not found in function arguments")
            
            # Check permission
            if not PermissionChecker.has_permission(request, permission):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def role_required(role: str):
    """
    Decorator to require specific role for endpoint.
    
    Args:
        role: Required role
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                for value in kwargs.values():
                    if isinstance(value, Request):
                        request = value
                        break
            
            if not request:
                raise RuntimeError("Request object not found in function arguments")
            
            # Check role
            user_role = PermissionChecker.get_user_role(request)
            if user_role != role:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ======================
# UTILITY FUNCTIONS
# ======================

def create_token_manager() -> TokenManager:
    """Create a TokenManager instance."""
    return TokenManager()


def get_token_manager() -> TokenManager:
    """Get the global TokenManager instance."""
    return TokenManager()


def create_auth_response(
    user_id: str,
    email: str,
    role: str = "user",
    permissions: Optional[List[str]] = None,
    include_refresh_token: bool = True,
    device_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create authentication response with tokens.
    
    Args:
        user_id: User ID
        email: User email
        role: User role
        permissions: User permissions
        include_refresh_token: Whether to include refresh token
        device_id: Device identifier
        
    Returns:
        Dictionary with authentication response
    """
    token_manager = TokenManager()
    
    # Create tokens
    access_token = token_manager.create_access_token(
        user_id=user_id,
        email=email,
        role=role,
        permissions=permissions
    )
    
    response = {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.get("security.access_token_expire_minutes", 30) * 60,
        "user": {
            "id": user_id,
            "email": email,
            "role": role,
            "permissions": permissions or []
        }
    }
    
    if include_refresh_token:
        refresh_token, refresh_token_id = token_manager.create_refresh_token(
            user_id, device_id
        )
        response["refresh_token"] = refresh_token
        response["refresh_token_expires_in"] = (
            config.get("security.refresh_token_expire_days", 7) * 24 * 60 * 60
        )
    
    return response


def validate_and_decode_token(token: str) -> Dict[str, Any]:
    """
    Validate and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    token_manager = TokenManager()
    
    try:
        payload = token_manager.validate_token(token)
        return payload.dict()
    except (InvalidTokenError, TokenExpiredError, TokenRevokedError) as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


# ======================
# EXPORTS
# ======================

__all__ = [
    # Models
    "TokenPayload",
    "UserSession",
    "AuthenticationResult",
    
    # Middleware
    "AuthMiddleware",
    
    # Token Manager
    "TokenManager",
    "create_token_manager",
    "get_token_manager",
    
    # Dependencies
    "AuthDependency",
    "requires_auth",
    "get_current_user",
    "get_optional_user",
    "require_permission",
    "require_role",
    "require_admin",
    
    # Permission Checker
    "PermissionChecker",
    
    # Decorators
    "permission_required",
    "role_required",
    
    # Utility Functions
    "create_auth_response",
    "validate_and_decode_token",
    
    # Exceptions
    "AuthMiddlewareError",
    "InvalidTokenError",
    "TokenRevokedError",
    "InsufficientPermissionsError",
]


if __name__ == "__main__":
    # Test the authentication middleware
    print("🔐 Authentication Middleware Test")
    print("=" * 50)
    
    # Create test configuration
    test_config = {
        "secret_key": "test-secret-key-1234567890",
        "algorithm": "HS256",
        "access_token_expire_minutes": 1,
        "refresh_token_expire_days": 7,
    }
    
    # Create token manager
    tm = TokenManager()
    
    # Test token creation
    print("\n1. Testing token creation...")
    access_token = tm.create_access_token(
        user_id="test_user_123",
        email="test@example.com",
        role="premium",
        permissions=["predictions:read", "bets:create"]
    )
    print(f"   Access token created: {len(access_token)} chars")
    
    # Test token validation
    print("\n2. Testing token validation...")
    try:
        payload = tm.validate_token(access_token)
        print(f"   Token valid for user: {payload.sub}")
        print(f"   Role: {payload.role}")
        print(f"   Permissions: {payload.permissions}")
    except Exception as e:
        print(f"   Token validation failed: {e}")
    
    # Test token refresh
    print("\n3. Testing token refresh...")
    refresh_token, refresh_id = tm.create_refresh_token("test_user_123", "test_device")
    print(f"   Refresh token created: {len(refresh_token)} chars")
    
    try:
        new_access, new_refresh = tm.refresh_access_token(refresh_token, "test_device")
        print(f"   Tokens refreshed successfully")
        print(f"   New access token: {len(new_access)} chars")
    except Exception as e:
        print(f"   Token refresh failed: {e}")
    
    # Test token revocation
    print("\n4. Testing token revocation...")
    tm.revoke_token(payload.jti, "access", "test_user_123")
    print(f"   Token revoked")
    
    try:
        tm.validate_token(access_token)
        print(f"   ERROR: Token should be revoked!")
    except TokenRevokedError:
        print(f"   ✓ Token correctly identified as revoked")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n✅ All authentication tests completed successfully!")
