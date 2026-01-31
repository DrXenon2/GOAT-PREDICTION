"""
Rate Limiter Middleware for API Gateway
Implements token bucket algorithm for rate limiting
"""

import time
import hashlib
from typing import Optional, Callable, Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..core.exceptions import RateLimitExceededError

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting
    """
    capacity: int
    tokens: float = field(init=False)
    last_update: float = field(init=False)
    
    def __post_init__(self):
        """Initialize bucket"""
        self.tokens = float(self.capacity)
        self.last_update = time.time()
    
    def consume(self, tokens: int = 1, refill_rate: float = 1.0) -> bool:
        """
        Consume tokens from bucket
        
        Args:
            tokens: Number of tokens to consume
            refill_rate: Token refill rate per second
            
        Returns:
            True if tokens available
        """
        now = time.time()
        elapsed = now - self.last_update
        
        # Refill tokens
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * refill_rate)
        )
        self.last_update = now
        
        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_retry_after(self, tokens: int = 1, refill_rate: float = 1.0) -> int:
        """
        Get retry-after time in seconds
        
        Args:
            tokens: Number of tokens needed
            refill_rate: Token refill rate
            
        Returns:
            Seconds to wait
        """
        tokens_needed = tokens - self.tokens
        if tokens_needed <= 0:
            return 0
        
        return int(tokens_needed / refill_rate) + 1


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter middleware using token bucket algorithm
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: Optional[int] = None,
        by_ip: bool = True,
        by_user: bool = True,
        exclude_paths: Optional[list] = None,
        redis_client: Optional[Any] = None,
    ):
        """
        Initialize rate limiter middleware
        
        Args:
            app: FastAPI application
            requests_per_minute: Requests allowed per minute
            burst_size: Maximum burst size
            by_ip: Rate limit by IP address
            by_user: Rate limit by user ID
            exclude_paths: Paths to exclude from rate limiting
            redis_client: Redis client for distributed rate limiting
        """
        super().__init__(app)
        
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.by_ip = by_ip
        self.by_user = by_user
        self.exclude_paths = exclude_paths or ['/health', '/metrics', '/docs', '/redoc']
        self.redis_client = redis_client
        
        # In-memory storage (fallback if no Redis)
        self.buckets: Dict[str, TokenBucket] = {}
        
        # Cleanup old buckets periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        logger.info(
            f"Rate limiter initialized: {requests_per_minute} req/min, "
            f"burst: {self.burst_size}"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiter
        
        Args:
            request: Incoming request
            call_next: Next handler
            
        Returns:
            Response
        """
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_rate_limit_key(request)
        
        # Check rate limit
        allowed, retry_after = await self._check_rate_limit(key)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded for key: {key}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "retry_after": retry_after,
                }
            )
            
            raise RateLimitExceededError(
                limit=self.requests_per_minute,
                period=60,
                retry_after=retry_after
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers['X-RateLimit-Limit'] = str(self.requests_per_minute)
        response.headers['X-RateLimit-Remaining'] = str(
            self._get_remaining_tokens(key)
        )
        response.headers['X-RateLimit-Reset'] = str(
            int(time.time()) + 60
        )
        
        # Cleanup old buckets periodically
        await self._periodic_cleanup()
        
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from rate limiting"""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Generate rate limit key from request
        
        Args:
            request: Request object
            
        Returns:
            Rate limit key
        """
        key_parts = []
        
        # Add IP address
        if self.by_ip:
            ip = self._get_client_ip(request)
            key_parts.append(f"ip:{ip}")
        
        # Add user ID
        if self.by_user and hasattr(request.state, 'user_id'):
            key_parts.append(f"user:{request.state.user_id}")
        
        # If no key parts, use IP as fallback
        if not key_parts:
            ip = self._get_client_ip(request)
            key_parts.append(f"ip:{ip}")
        
        # Create hash of key
        key = ":".join(key_parts)
        return hashlib.sha256(key.encode()).hexdigest()
    
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
    
    async def _check_rate_limit(self, key: str) -> tuple[bool, int]:
        """
        Check rate limit for key
        
        Args:
            key: Rate limit key
            
        Returns:
            Tuple of (allowed, retry_after)
        """
        if self.redis_client:
            return await self._check_rate_limit_redis(key)
        else:
            return self._check_rate_limit_memory(key)
    
    def _check_rate_limit_memory(self, key: str) -> tuple[bool, int]:
        """
        Check rate limit using in-memory storage
        
        Args:
            key: Rate limit key
            
        Returns:
            Tuple of (allowed, retry_after)
        """
        # Get or create bucket
        if key not in self.buckets:
            self.buckets[key] = TokenBucket(capacity=self.burst_size)
        
        bucket = self.buckets[key]
        
        # Try to consume token
        allowed = bucket.consume(tokens=1, refill_rate=self.refill_rate)
        
        if not allowed:
            retry_after = bucket.get_retry_after(tokens=1, refill_rate=self.refill_rate)
            return False, retry_after
        
        return True, 0
    
    async def _check_rate_limit_redis(self, key: str) -> tuple[bool, int]:
        """
        Check rate limit using Redis
        
        Args:
            key: Rate limit key
            
        Returns:
            Tuple of (allowed, retry_after)
        """
        try:
            # Use Redis INCR with expiry for simple rate limiting
            redis_key = f"ratelimit:{key}"
            
            current = await self.redis_client.incr(redis_key)
            
            if current == 1:
                # First request, set expiry
                await self.redis_client.expire(redis_key, 60)
            
            if current > self.requests_per_minute:
                # Rate limit exceeded
                ttl = await self.redis_client.ttl(redis_key)
                return False, max(1, ttl)
            
            return True, 0
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fallback to memory-based rate limiting
            return self._check_rate_limit_memory(key)
    
    def _get_remaining_tokens(self, key: str) -> int:
        """
        Get remaining tokens for key
        
        Args:
            key: Rate limit key
            
        Returns:
            Number of remaining tokens
        """
        if key in self.buckets:
            return int(self.buckets[key].tokens)
        return self.burst_size
    
    async def _periodic_cleanup(self) -> None:
        """Clean up old buckets periodically"""
        now = time.time()
        
        if now - self.last_cleanup > self.cleanup_interval:
            # Remove buckets older than 5 minutes
            cutoff = now - 300
            
            keys_to_remove = [
                key for key, bucket in self.buckets.items()
                if bucket.last_update < cutoff
            ]
            
            for key in keys_to_remove:
                del self.buckets[key]
            
            if keys_to_remove:
                logger.debug(f"Cleaned up {len(keys_to_remove)} old rate limit buckets")
            
            self.last_cleanup = now


# Decorator for rate limiting specific endpoints
def rate_limit(
    requests_per_minute: int = 60,
    burst_size: Optional[int] = None
):
    """
    Decorator for rate limiting specific endpoints
    
    Args:
        requests_per_minute: Requests allowed per minute
        burst_size: Maximum burst size
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            # Simple rate limiting logic
            # This would need to be integrated with the middleware
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Export all
__all__ = [
    'RateLimiterMiddleware',
    'TokenBucket',
    'rate_limit',
]
