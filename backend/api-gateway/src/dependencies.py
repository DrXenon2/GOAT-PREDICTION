"""
Dependency injection for GOAT Prediction API Gateway.
Centralized management of database connections, authentication, and other dependencies.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator, Optional

import aioredis
import structlog
from asyncpg.pool import Pool
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .core.config import settings
from .core.exceptions import AuthenticationError, AuthorizationError
from .models.user import User, UserRole

# Initialize logger
logger = structlog.get_logger(__name__)

# Security scheme for Bearer tokens
security = HTTPBearer(auto_error=False)


# ===========================================
# Database Dependencies
# ===========================================

class Database:
    """Database connection pool manager."""
    
    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._pool: Optional[Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        if self._engine is not None:
            return
        
        try:
            logger.info("creating_database_engine", url=settings.DATABASE_URL)
            
            # Create async engine
            self._engine = create_async_engine(
                str(settings.DATABASE_URL),
                echo=settings.DATABASE_ECHO,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_recycle=settings.DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                future=True,
                connect_args={
                    "server_settings": {
                        "application_name": "goat-api-gateway",
                        "timezone": "UTC",
                    }
                }
            )
            
            # Create session factory
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                autocommit=False,
            )
            
            logger.info("database_engine_created")
            
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Close database connections."""
        if self._engine is None:
            return
        
        try:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("database_connections_closed")
        except Exception as e:
            logger.error("database_disconnect_failed", error=str(e))
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        session: AsyncSession = self._session_factory()
        
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def execute(self, query: str, *args, **kwargs):
        """Execute a raw SQL query."""
        async with self.session() as session:
            result = await session.execute(query, *args, **kwargs)
            return result
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.warning("database_health_check_failed", error=str(e))
            return False


@lru_cache()
def get_database() -> Database:
    """Get cached database instance."""
    return Database()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            # Use db session
    """
    db = get_database()
    
    async with db.session() as session:
        try:
            yield session
        except Exception as e:
            logger.error("database_session_error", error=str(e))
            raise


# ===========================================
# Redis Dependencies
# ===========================================

class RedisClient:
    """Redis connection manager with connection pooling."""
    
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Establish Redis connection."""
        if self._redis is not None:
            return
        
        async with self._lock:
            if self._redis is not None:  # Double-check locking
                return
            
            try:
                logger.info("creating_redis_connection", url=settings.REDIS_URL)
                
                # Parse Redis URL
                redis_url = str(settings.REDIS_URL)
                
                # Create Redis connection pool
                self._redis = aioredis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    max_connections=settings.REDIS_POOL_SIZE,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                
                # Test connection
                await self._redis.ping()
                
                logger.info("redis_connection_established")
                
            except Exception as e:
                logger.error("redis_connection_failed", error=str(e))
                raise
    
    async def close(self):
        """Close Redis connections."""
        if self._redis is None:
            return
        
        async with self._lock:
            if self._redis is None:
                return
            
            try:
                await self._redis.close()
                await self._redis.connection_pool.disconnect()
                self._redis = None
                logger.info("redis_connections_closed")
            except Exception as e:
                logger.error("redis_disconnect_failed", error=str(e))
    
    async def ping(self) -> bool:
        """Ping Redis server."""
        try:
            return await self._redis.ping()
        except Exception as e:
            logger.warning("redis_ping_failed", error=str(e))
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.error("redis_get_failed", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis with optional expiration."""
        try:
            if expire:
                await self._redis.setex(key, expire, value)
            else:
                await self._redis.set(key, value)
            return True
        except Exception as e:
            logger.error("redis_set_failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            return await self._redis.delete(key) > 0
        except Exception as e:
            logger.error("redis_delete_failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.error("redis_exists_failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in Redis."""
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            logger.error("redis_increment_failed", key=key, error=str(e))
            return None
    
    async def get_connection(self) -> aioredis.Redis:
        """Get raw Redis connection for advanced operations."""
        return self._redis
    
    @property
    def client(self) -> aioredis.Redis:
        """Get Redis client."""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis


@lru_cache()
def get_redis() -> RedisClient:
    """Get cached Redis client instance."""
    return RedisClient()


async def get_redis_client() -> RedisClient:
    """
    Dependency for getting Redis client.
    
    Usage:
        @app.get("/cache")
        async def get_cache(redis: RedisClient = Depends(get_redis_client)):
            # Use redis client
    """
    redis = get_redis()
    await redis.connect()
    return redis


# ===========================================
# Authentication & Authorization Dependencies
# ===========================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.
    
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        # Get user from database
        from sqlalchemy import select
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            return None
        
        # Add user to request state for logging
        request.state.user_id = user.id
        request.state.user_email = user.email
        
        return user
        
    except JWTError as e:
        logger.warning("jwt_decode_failed", error=str(e))
        return None
    except Exception as e:
        logger.error("get_current_user_failed", error=str(e))
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """
    Dependency that requires authenticated user.
    
    Raises:
        HTTPException 401 if not authenticated
    """
    if user is None:
        raise AuthenticationError("Authentication required")
    
    return user


async def require_admin(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires admin role.
    
    Raises:
        HTTPException 403 if not admin
    """
    if user.role != UserRole.ADMIN:
        raise AuthorizationError("Admin access required")
    
    return user


async def require_premium(
    user: User = Depends(require_auth),
) -> User:
    """
    Dependency that requires premium subscription.
    
    Raises:
        HTTPException 403 if not premium
    """
    if not user.is_premium:
        raise AuthorizationError("Premium subscription required")
    
    return user


# ===========================================
# Rate Limiting Dependencies
# ===========================================

async def get_client_ip(request: Request) -> str:
    """
    Get client IP address for rate limiting.
    
    Handles proxy headers (X-Forwarded-For, etc.)
    """
    # Try to get IP from X-Forwarded-For header
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in chain
        client_ip = forwarded_for.split(",")[0].strip()
        logger.debug("client_ip_from_forwarded_for", ip=client_ip)
        return client_ip
    
    # Try to get IP from X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        logger.debug("client_ip_from_real_ip", ip=real_ip)
        return real_ip
    
    # Fall back to request client host
    client_ip = request.client.host if request.client else "unknown"
    logger.debug("client_ip_from_request", ip=client_ip)
    
    return client_ip


async def get_user_id_for_rate_limit(
    user: Optional[User] = Depends(get_current_user),
) -> Optional[str]:
    """
    Get user ID for rate limiting.
    Returns None for unauthenticated requests.
    """
    return str(user.id) if user else None


# ===========================================
# Cache Control Dependencies
# ===========================================

class CacheControl:
    """Cache control headers management."""
    
    @staticmethod
    async def no_cache() -> dict:
        """Return headers to prevent caching."""
        return {
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    
    @staticmethod
    async def public_cache(max_age: int = 300) -> dict:
        """Return headers for public caching."""
        return {
            "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=60",
            "Vary": "Accept-Encoding",
        }
    
    @staticmethod
    async def private_cache(max_age: int = 60) -> dict:
        """Return headers for private caching."""
        return {
            "Cache-Control": f"private, max-age={max_age}",
            "Vary": "Accept-Encoding, Authorization",
        }


async def get_cache_control() -> CacheControl:
    """Dependency for cache control headers."""
    return CacheControl()


# ===========================================
# Request Context Dependencies
# ===========================================

async def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.
    
    Usage:
        @app.get("/")
        async def root(request_id: str = Depends(get_request_id)):
            return {"request_id": request_id}
    """
    if hasattr(request.state, "request_id"):
        return request.state.request_id
    
    # Generate a new request ID if not present
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


async def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from headers or generate new.
    
    Usage:
        @app.get("/")
        async def root(correlation_id: str = Depends(get_correlation_id)):
            return {"correlation_id": correlation_id}
    """
    # Try to get from X-Correlation-ID header
    correlation_id = request.headers.get("X-Correlation-ID")
    
    if correlation_id:
        return correlation_id
    
    # Generate a new correlation ID
    import uuid
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    return correlation_id


# ===========================================
# Feature Flag Dependencies
# ===========================================

class FeatureFlags:
    """Feature flag management."""
    
    def __init__(self, redis: RedisClient):
        self.redis = redis
    
    async def is_enabled(self, feature: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature is enabled for a user.
        
        Args:
            feature: Feature name
            user_id: Optional user ID for user-specific flags
        
        Returns:
            True if feature is enabled
        """
        # Check global feature flag
        global_key = f"feature:{feature}:enabled"
        global_enabled = await self.redis.get(global_key)
        
        if global_enabled == "false":
            return False
        
        # Check user-specific feature flag
        if user_id:
            user_key = f"feature:{feature}:user:{user_id}"
            user_enabled = await self.redis.get(user_key)
            
            if user_enabled == "true":
                return True
            elif user_enabled == "false":
                return False
        
        # Default to global setting
        return global_enabled == "true"
    
    async def enable_feature(self, feature: str, user_id: Optional[str] = None):
        """Enable a feature flag."""
        if user_id:
            key = f"feature:{feature}:user:{user_id}"
        else:
            key = f"feature:{feature}:enabled"
        
        await self.redis.set(key, "true")
    
    async def disable_feature(self, feature: str, user_id: Optional[str] = None):
        """Disable a feature flag."""
        if user_id:
            key = f"feature:{feature}:user:{user_id}"
        else:
            key = f"feature:{feature}:enabled"
        
        await self.redis.set(key, "false")


async def get_feature_flags(
    redis: RedisClient = Depends(get_redis_client),
    user: Optional[User] = Depends(get_current_user),
) -> FeatureFlags:
    """
    Dependency for feature flags with user context.
    
    Usage:
        @app.get("/feature")
        async def get_feature(
            feature_flags: FeatureFlags = Depends(get_feature_flags)
        ):
            if await feature_flags.is_enabled("new_ui"):
                # New UI logic
    """
    flags = FeatureFlags(redis)
    
    # Store user ID for user-specific flags
    if user:
        flags.user_id = str(user.id)
    
    return flags


# ===========================================
# External API Clients Dependencies
# ===========================================

class APIClientManager:
    """Manager for external API clients."""
    
    def __init__(self):
        self._clients = {}
        self._lock = asyncio.Lock()
    
    async def get_client(self, service: str):
        """
        Get or create API client for a service.
        
        Args:
            service: Service name (statsbomb, opta, sportradar, etc.)
        
        Returns:
            Configured API client
        """
        async with self._lock:
            if service not in self._clients:
                client = await self._create_client(service)
                self._clients[service] = client
            
            return self._clients[service]
    
    async def _create_client(self, service: str):
        """Create API client for specific service."""
        
        # Common client configuration
        common_config = {
            "timeout": 30.0,
            "limits": {
                "max_connections": 100,
                "max_keepalive_connections": 20,
                "keepalive_expiry": 30.0,
            },
            "transport": {
                "retries": 3,
                "retry_backoff": 0.1,
            },
        }
        
        # Service-specific configuration
        if service == "statsbomb":
            from httpx import AsyncClient
            
            api_key = settings.STATSBOMB_API_KEY
            if not api_key:
                raise ValueError("STATSBOMB_API_KEY not configured")
            
            return AsyncClient(
                base_url="https://data.statsbomb.com/api/v2/",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                **common_config,
            )
        
        elif service == "opta":
            from httpx import AsyncClient
            
            api_key = settings.OPTA_API_KEY
            if not api_key:
                raise ValueError("OPTA_API_KEY not configured")
            
            return AsyncClient(
                base_url="https://api.opta.net/",
                headers={
                    "X-Auth-Token": api_key,
                    "Accept": "application/json",
                },
                **common_config,
            )
        
        elif service == "sportradar":
            from httpx import AsyncClient
            
            api_key = settings.SPORTRADAR_API_KEY
            if not api_key:
                raise ValueError("SPORTRADAR_API_KEY not configured")
            
            return AsyncClient(
                base_url="https://api.sportradar.com/",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                **common_config,
            )
        
        elif service == "betfair":
            from httpx import AsyncClient
            
            api_key = settings.BETFAIR_API_KEY
            if not api_key:
                raise ValueError("BETFAIR_API_KEY not configured")
            
            return AsyncClient(
                base_url="https://api.betfair.com/exchange/",
                headers={
                    "X-Application": api_key,
                    "Accept": "application/json",
                },
                **common_config,
            )
        
        elif service == "weather":
            from httpx import AsyncClient
            
            api_key = settings.OPENWEATHER_API_KEY
            if not api_key:
                raise ValueError("OPENWEATHER_API_KEY not configured")
            
            return AsyncClient(
                base_url="https://api.openweathermap.org/data/2.5/",
                params={"appid": api_key},
                **common_config,
            )
        
        else:
            raise ValueError(f"Unknown service: {service}")
    
    async def close_all(self):
        """Close all API clients."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()


@lru_cache()
def get_api_client_manager() -> APIClientManager:
    """Get cached API client manager."""
    return APIClientManager()


async def get_api_client(
    service: str,
    manager: APIClientManager = Depends(get_api_client_manager),
):
    """
    Dependency for getting external API client.
    
    Usage:
        @app.get("/stats")
        async def get_stats(
            statsbomb_client = Depends(get_api_client, "statsbomb")
        ):
            # Use statsbomb client
    """
    return await manager.get_client(service)


# ===========================================
# Background Task Dependencies
# ===========================================

class TaskManager:
    """Background task manager."""
    
    def __init__(self):
        self._tasks = set()
    
    async def create_task(self, coro):
        """
        Create and track a background task.
        
        Args:
            coro: Coroutine to run
        
        Returns:
            asyncio.Task
        """
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        
        # Add callback to remove task when done
        task.add_done_callback(self._tasks.discard)
        
        return task
    
    async def cancel_all(self):
        """Cancel all background tasks."""
        for task in self._tasks:
            task.cancel()
        
        # Wait for all tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()


async def get_task_manager() -> TaskManager:
    """
    Dependency for background task manager.
    
    Usage:
        @app.post("/process")
        async def process_data(
            task_manager: TaskManager = Depends(get_task_manager)
        ):
            # Start background task
            await task_manager.create_task(process_in_background())
    """
    return TaskManager()


# ===========================================
# Health Check Dependencies
# ===========================================

class HealthChecker:
    """Health check manager for all dependencies."""
    
    def __init__(
        self,
        db: Database = Depends(get_database),
        redis: RedisClient = Depends(get_redis_client),
    ):
        self.db = db
        self.redis = redis
    
    async def check_all(self) -> dict:
        """
        Perform health checks for all dependencies.
        
        Returns:
            Dict with health status for each service
        """
        checks = {}
        
        # Check database
        try:
            db_healthy = await self.db.health_check()
            checks["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "service": "postgresql",
            }
        except Exception as e:
            checks["database"] = {
                "status": "unhealthy",
                "service": "postgresql",
                "error": str(e),
            }
        
        # Check Redis
        try:
            redis_healthy = await self.redis.ping()
            checks["redis"] = {
                "status": "healthy" if redis_healthy else "unhealthy",
                "service": "redis",
            }
        except Exception as e:
            checks["redis"] = {
                "status": "unhealthy",
                "service": "redis",
                "error": str(e),
            }
        
        # Check external APIs (sample check)
        checks["external_apis"] = {
            "status": "healthy",  # Assume healthy by default
            "services": ["statsbomb", "opta", "sportradar"],
        }
        
        # Overall status
        all_healthy = all(
            check["status"] == "healthy"
            for check in checks.values()
            if isinstance(check, dict) and "status" in check
        )
        
        checks["overall"] = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return checks


async def get_health_checker() -> HealthChecker:
    """Dependency for health checking."""
    return HealthChecker()


# ===========================================
# Export Dependencies
# ===========================================

__all__ = [
    # Database
    "Database",
    "get_database",
    "get_db_session",
    
    # Redis
    "RedisClient",
    "get_redis",
    "get_redis_client",
    
    # Authentication
    "get_current_user",
    "require_auth",
    "require_admin",
    "require_premium",
    
    # Rate limiting
    "get_client_ip",
    "get_user_id_for_rate_limit",
    
    # Cache control
    "CacheControl",
    "get_cache_control",
    
    # Request context
    "get_request_id",
    "get_correlation_id",
    
    # Feature flags
    "FeatureFlags",
    "get_feature_flags",
    
    # External APIs
    "APIClientManager",
    "get_api_client_manager",
    "get_api_client",
    
    # Background tasks
    "TaskManager",
    "get_task_manager",
    
    # Health checks
    "HealthChecker",
    "get_health_checker",
]

# Import datetime here to avoid circular imports
from datetime import datetime
