"""
Advanced Rate Limiting Middleware for GOAT Prediction Ultimate.
Supports multiple algorithms, Redis storage, user/plan-based limits, and dynamic configuration.
"""

import time
import hashlib
import uuid
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import redis
import asyncio
from functools import wraps

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from pydantic import BaseModel, Field, validator

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger
from ..core.exceptions import RateLimitError
from .base import BaseMiddleware
from .auth import get_current_user, PermissionChecker

logger = get_logger(__name__)

# ======================
# DATA MODELS
# ======================

class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    GCRA = "gcra"  # Generic Cell Rate Algorithm


class RateLimitScope(str, Enum):
    """Rate limiting scopes."""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    METHOD = "method"
    PLAN = "plan"
    CUSTOM = "custom"


class RateLimitResult(str, Enum):
    """Rate limiting results."""
    ALLOWED = "allowed"
    DENIED = "denied"
    THROTTLED = "throttled"


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW
    limit: int = 100  # Max requests
    window: int = 60  # Seconds
    burst: int = 10  # Burst capacity for token bucket
    cost: int = 1  # Cost per request
    
    # Advanced settings
    sliding_window_precision: int = 1000  # Milliseconds precision
    token_refill_rate: float = 1.0  # Tokens per second
    leak_rate: float = 1.0  # Leak rate for leaky bucket
    emission_interval: float = 1.0  # Emission interval for GCRA
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RateLimitRule:
    """Rate limiting rule."""
    name: str
    pattern: str  # Regex pattern or path
    config: RateLimitConfig
    scope: RateLimitScope = RateLimitScope.GLOBAL
    priority: int = 1000
    enabled: bool = True
    
    def matches(self, path: str) -> bool:
        """Check if rule matches path."""
        import re
        return bool(re.match(self.pattern, path))


@dataclass
class RateLimitState:
    """Current rate limit state."""
    key: str
    limit: int
    remaining: int
    reset_time: int  # Unix timestamp
    retry_after: Optional[int] = None  # Seconds
    window: int = 60
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW
    
    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_time),
        }
        
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
            headers["X-RateLimit-Retry-After"] = str(self.retry_after)
        
        return headers
    
    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        return self.remaining > 0


@dataclass
class RateLimitRequest:
    """Rate limit request information."""
    key: str
    cost: int = 1
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitResponse:
    """Rate limit response."""
    allowed: bool
    state: RateLimitState
    reason: Optional[str] = None
    wait_time: Optional[float] = None  # Seconds to wait
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "state": asdict(self.state),
            "reason": self.reason,
            "wait_time": self.wait_time,
        }


# ======================
# RATE LIMIT ALGORITHMS
# ======================

class RateLimitAlgorithmBase:
    """Base class for rate limiting algorithms."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis client."""
        try:
            redis_config = config.get_redis_config()
            self.redis_client = redis.Redis(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
                db=redis_config.db,
                decode_responses=False,  # Keep bytes for performance
                max_connections=redis_config.max_connections
            )
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Using in-memory storage.")
            self.redis_client = None
    
    async def check(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check if request is allowed (to be implemented by subclasses)."""
        raise NotImplementedError
    
    def _get_redis_key(self, key: str) -> str:
        """Get Redis key with prefix."""
        return f"ratelimit:{self.config.algorithm}:{key}"
    
    def _calculate_reset_time(self, current_time: float) -> int:
        """Calculate reset time for current window."""
        if self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            return int(math.ceil(current_time / self.config.window) * self.config.window)
        else:
            return int(current_time + self.config.window)


class FixedWindowAlgorithm(RateLimitAlgorithmBase):
    """Fixed window rate limiting algorithm."""
    
    async def check(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check using fixed window algorithm."""
        current_time = time.time()
        window_start = int(current_time // self.config.window)
        key = f"{request.key}:{window_start}"
        redis_key = self._get_redis_key(key)
        
        try:
            if self.redis_client:
                # Use Redis for distributed counting
                pipeline = self.redis_client.pipeline()
                pipeline.incrby(redis_key, request.cost)
                pipeline.expire(redis_key, self.config.window)
                current_count, _ = pipeline.execute()
                current_count = int(current_count)
            else:
                # In-memory fallback (not thread-safe in production)
                if not hasattr(self, '_memory_store'):
                    self._memory_store = {}
                
                if key not in self._memory_store:
                    self._memory_store[key] = {
                        'count': 0,
                        'expire_at': current_time + self.config.window
                    }
                
                # Clean expired entries
                expired_keys = [
                    k for k, v in self._memory_store.items()
                    if v['expire_at'] < current_time
                ]
                for k in expired_keys:
                    del self._memory_store[k]
                
                self._memory_store[key]['count'] += request.cost
                current_count = self._memory_store[key]['count']
            
            remaining = max(0, self.config.limit - current_count)
            reset_time = self._calculate_reset_time(current_time)
            
            state = RateLimitState(
                key=request.key,
                limit=self.config.limit,
                remaining=remaining,
                reset_time=reset_time,
                window=self.config.window,
                algorithm=self.config.algorithm
            )
            
            if current_count > self.config.limit:
                retry_after = reset_time - int(current_time)
                state.retry_after = retry_after
                
                return RateLimitResponse(
                    allowed=False,
                    state=state,
                    reason="Rate limit exceeded",
                    wait_time=retry_after
                )
            
            return RateLimitResponse(
                allowed=True,
                state=state,
                reason=None
            )
            
        except Exception as e:
            logger.error(f"Fixed window algorithm error: {e}")
            # Allow request on error (fail open)
            return self._create_error_response(request.key)
    
    def _create_error_response(self, key: str) -> RateLimitResponse:
        """Create error response (fail open)."""
        return RateLimitResponse(
            allowed=True,
            state=RateLimitState(
                key=key,
                limit=self.config.limit,
                remaining=self.config.limit,
                reset_time=int(time.time() + self.config.window),
                window=self.config.window,
                algorithm=self.config.algorithm
            ),
            reason="Rate limit check failed, request allowed"
        )


class SlidingWindowAlgorithm(RateLimitAlgorithmBase):
    """Sliding window rate limiting algorithm."""
    
    async def check(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check using sliding window algorithm."""
        current_time = time.time()
        window_start = current_time - self.config.window
        
        try:
            if self.redis_client:
                # Use Redis sorted set
                redis_key = self._get_redis_key(request.key)
                
                # Remove old entries
                pipeline = self.redis_client.pipeline()
                pipeline.zremrangebyscore(redis_key, 0, window_start)
                
                # Add current request
                member = f"{current_time}:{uuid.uuid4()}"
                pipeline.zadd(redis_key, {member: current_time})
                
                # Count requests in window
                pipeline.zcount(redis_key, window_start, current_time)
                
                # Set TTL
                pipeline.expire(redis_key, self.config.window)
                
                _, _, current_count, _ = pipeline.execute()
                current_count = int(current_count)
            else:
                # In-memory fallback
                if not hasattr(self, '_memory_store'):
                    self._memory_store = {}
                
                if request.key not in self._memory_store:
                    self._memory_store[request.key] = []
                
                # Remove old entries
                self._memory_store[request.key] = [
                    ts for ts in self._memory_store[request.key]
                    if ts > window_start
                ]
                
                # Add current request
                self._memory_store[request.key].append(current_time)
                current_count = len(self._memory_store[request.key])
            
            remaining = max(0, self.config.limit - current_count)
            reset_time = int(current_time + self.config.window)
            
            state = RateLimitState(
                key=request.key,
                limit=self.config.limit,
                remaining=remaining,
                reset_time=reset_time,
                window=self.config.window,
                algorithm=self.config.algorithm
            )
            
            if current_count > self.config.limit:
                # Find oldest request to calculate wait time
                if self.redis_client:
                    oldest = self.redis_client.zrange(
                        redis_key, 0, 0, withscores=True
                    )
                    if oldest:
                        oldest_time = oldest[0][1]
                        retry_after = int(oldest_time + self.config.window - current_time)
                    else:
                        retry_after = self.config.window
                else:
                    if self._memory_store.get(request.key):
                        oldest_time = min(self._memory_store[request.key])
                        retry_after = int(oldest_time + self.config.window - current_time)
                    else:
                        retry_after = self.config.window
                
                state.retry_after = max(1, retry_after)
                
                return RateLimitResponse(
                    allowed=False,
                    state=state,
                    reason="Rate limit exceeded",
                    wait_time=state.retry_after
                )
            
            return RateLimitResponse(
                allowed=True,
                state=state,
                reason=None
            )
            
        except Exception as e:
            logger.error(f"Sliding window algorithm error: {e}")
            return self._create_error_response(request.key)
    
    def _create_error_response(self, key: str) -> RateLimitResponse:
        """Create error response (fail open)."""
        return RateLimitResponse(
            allowed=True,
            state=RateLimitState(
                key=key,
                limit=self.config.limit,
                remaining=self.config.limit,
                reset_time=int(time.time() + self.config.window),
                window=self.config.window,
                algorithm=self.config.algorithm
            ),
            reason="Rate limit check failed, request allowed"
        )


class TokenBucketAlgorithm(RateLimitAlgorithmBase):
    """Token bucket rate limiting algorithm."""
    
    async def check(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check using token bucket algorithm."""
        current_time = time.time()
        
        try:
            if self.redis_client:
                # Use Redis hash for token bucket state
                redis_key = self._get_redis_key(request.key)
                
                pipeline = self.redis_client.pipeline()
                pipeline.hgetall(redis_key)
                pipeline.expire(redis_key, self.config.window * 2)
                
                bucket_data, _ = pipeline.execute()
                
                if bucket_data:
                    tokens = float(bucket_data.get(b'tokens', self.config.limit))
                    last_update = float(bucket_data.get(b'last_update', current_time))
                else:
                    tokens = self.config.limit
                    last_update = current_time
                
                # Refill tokens
                time_passed = current_time - last_update
                refill_amount = time_passed * self.config.token_refill_rate
                tokens = min(self.config.limit, tokens + refill_amount)
                
                # Check if enough tokens
                if tokens >= request.cost:
                    tokens -= request.cost
                    allowed = True
                else:
                    allowed = False
                
                # Update bucket
                pipeline = self.redis_client.pipeline()
                pipeline.hset(redis_key, 'tokens', tokens)
                pipeline.hset(redis_key, 'last_update', current_time)
                pipeline.expire(redis_key, self.config.window * 2)
                pipeline.execute()
                
            else:
                # In-memory fallback
                if not hasattr(self, '_memory_store'):
                    self._memory_store = {}
                
                if request.key not in self._memory_store:
                    self._memory_store[request.key] = {
                        'tokens': self.config.limit,
                        'last_update': current_time
                    }
                
                bucket = self._memory_store[request.key]
                
                # Refill tokens
                time_passed = current_time - bucket['last_update']
                refill_amount = time_passed * self.config.token_refill_rate
                bucket['tokens'] = min(self.config.limit, bucket['tokens'] + refill_amount)
                bucket['last_update'] = current_time
                
                # Check if enough tokens
                if bucket['tokens'] >= request.cost:
                    bucket['tokens'] -= request.cost
                    allowed = True
                else:
                    allowed = False
            
            remaining = max(0, int(tokens if 'tokens' in locals() else bucket['tokens']))
            reset_time = int(current_time + self.config.window)
            
            state = RateLimitState(
                key=request.key,
                limit=self.config.limit,
                remaining=remaining,
                reset_time=reset_time,
                window=self.config.window,
                algorithm=self.config.algorithm
            )
            
            if not allowed:
                # Calculate wait time
                deficit = request.cost - tokens if 'tokens' in locals() else request.cost - bucket['tokens']
                wait_time = deficit / self.config.token_refill_rate
                state.retry_after = max(1, int(wait_time))
                
                return RateLimitResponse(
                    allowed=False,
                    state=state,
                    reason="Insufficient tokens",
                    wait_time=wait_time
                )
            
            return RateLimitResponse(
                allowed=True,
                state=state,
                reason=None
            )
            
        except Exception as e:
            logger.error(f"Token bucket algorithm error: {e}")
            return self._create_error_response(request.key)
    
    def _create_error_response(self, key: str) -> RateLimitResponse:
        """Create error response (fail open)."""
        return RateLimitResponse(
            allowed=True,
            state=RateLimitState(
                key=key,
                limit=self.config.limit,
                remaining=self.config.limit,
                reset_time=int(time.time() + self.config.window),
                window=self.config.window,
                algorithm=self.config.algorithm
            ),
            reason="Rate limit check failed, request allowed"
        )


class GCRAlgorithm(RateLimitAlgorithmBase):
    """Generic Cell Rate Algorithm (GCRA)."""
    
    async def check(self, request: RateLimitRequest) -> RateLimitResponse:
        """Check using GCRA algorithm."""
        current_time = time.time()
        emission_interval = self.config.emission_interval
        delay_variation_tolerance = self.config.window
        
        try:
            if self.redis_client:
                redis_key = self._get_redis_key(request.key)
                
                # Lua script for atomic GCRA check
                lua_script = """
                local key = KEYS[1]
                local cost = tonumber(ARGV[1])
                local emission_interval = tonumber(ARGV[2])
                local delay_variation_tolerance = tonumber(ARGV[3])
                local current_time = tonumber(ARGV[4])
                local window = tonumber(ARGV[5])
                
                -- Get theoretical arrival time (TAT)
                local tat = redis.call('GET', key)
                if not tat then
                    tat = current_time
                else
                    tat = tonumber(tat)
                end
                
                -- Calculate new TAT
                local new_tat = math.max(tat, current_time) + (cost * emission_interval)
                local allow_at = new_tat - delay_variation_tolerance
                
                if current_time >= allow_at then
                    -- Allow request
                    redis.call('SET', key, new_tat, 'EX', window)
                    return {1, new_tat}
                else
                    -- Deny request
                    return {0, allow_at}
                end
                """
                
                script = self.redis_client.register_script(lua_script)
                result = script(
                    keys=[redis_key],
                    args=[
                        request.cost,
                        emission_interval,
                        delay_variation_tolerance,
                        current_time,
                        self.config.window
                    ]
                )
                
                allowed, next_time = result
                allowed = bool(allowed)
                next_time = float(next_time)
                
            else:
                # In-memory fallback
                if not hasattr(self, '_memory_store'):
                    self._memory_store = {}
                
                if request.key not in self._memory_store:
                    self._memory_store[request.key] = {
                        'tat': current_time,  # Theoretical Arrival Time
                        'expire_at': current_time + self.config.window
                    }
                
                bucket = self._memory_store[request.key]
                
                # Clean expired entries
                if bucket['expire_at'] < current_time:
                    bucket['tat'] = current_time
                    bucket['expire_at'] = current_time + self.config.window
                
                # Calculate new TAT
                new_tat = max(bucket['tat'], current_time) + (request.cost * emission_interval)
                allow_at = new_tat - delay_variation_tolerance
                
                if current_time >= allow_at:
                    allowed = True
                    bucket['tat'] = new_tat
                    bucket['expire_at'] = current_time + self.config.window
                else:
                    allowed = False
                    next_time = allow_at
            
            remaining = self.config.limit  # GCRA doesn't have simple remaining count
            reset_time = int(current_time + self.config.window)
            
            state = RateLimitState(
                key=request.key,
                limit=self.config.limit,
                remaining=remaining,
                reset_time=reset_time,
                window=self.config.window,
                algorithm=self.config.algorithm
            )
            
            if not allowed:
                wait_time = max(0, next_time - current_time)
                state.retry_after = max(1, int(wait_time))
                
                return RateLimitResponse(
                    allowed=False,
                    state=state,
                    reason="Rate limit exceeded (GCRA)",
                    wait_time=wait_time
                )
            
            return RateLimitResponse(
                allowed=True,
                state=state,
                reason=None
            )
            
        except Exception as e:
            logger.error(f"GCRA algorithm error: {e}")
            return self._create_error_response(request.key)
    
    def _create_error_response(self, key: str) -> RateLimitResponse:
        """Create error response (fail open)."""
        return RateLimitResponse(
            allowed=True,
            state=RateLimitState(
                key=key,
                limit=self.config.limit,
                remaining=self.config.limit,
                reset_time=int(time.time() + self.config.window),
                window=self.config.window,
                algorithm=self.config.algorithm
            ),
            reason="Rate limit check failed, request allowed"
        )


# ======================
# RATE LIMIT MANAGER
# ======================

class RateLimitManager:
    """Manage rate limiting rules and algorithms."""
    
    def __init__(self):
        self.rules: List[RateLimitRule] = []
        self.algorithms: Dict[RateLimitAlgorithm, RateLimitAlgorithmBase] = {}
        self.rule_cache: Dict[str, RateLimitRule] = {}
        self.stats = {
            "total_checks": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
            "checks_by_algorithm": {},
            "checks_by_scope": {},
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        self._initialize_algorithms()
    
    def _initialize_default_rules(self) -> None:
        """Initialize default rate limiting rules from config."""
        cfg = get_config()
        
        # Get rate limit config
        rate_limit_config = cfg.get("rate_limiting", {})
        
        # Global default rule
        default_config = RateLimitConfig(
            algorithm=RateLimitAlgorithm(rate_limit_config.get("algorithm", "fixed_window")),
            limit=rate_limit_config.get("default_limit", 100),
            window=rate_limit_config.get("default_window", 60),
        )
        
        self.add_rule(RateLimitRule(
            name="global_default",
            pattern=".*",  # Match all paths
            config=default_config,
            scope=RateLimitScope.GLOBAL,
            priority=1000
        ))
        
        # Plan-based rules
        subscription_plans = cfg.get("subscription_plans", {})
        for plan_name, plan_config in subscription_plans.items():
            if "rate_limit" in plan_config:
                try:
                    limit_str = plan_config["rate_limit"]
                    limit, window = self._parse_rate_limit_string(limit_str)
                    
                    plan_config_obj = RateLimitConfig(
                        algorithm=RateLimitAlgorithm.FIXED_WINDOW,
                        limit=limit,
                        window=window,
                    )
                    
                    self.add_rule(RateLimitRule(
                        name=f"plan_{plan_name}",
                        pattern=".*",
                        config=plan_config_obj,
                        scope=RateLimitScope.PLAN,
                        priority=900,
                        metadata={"plan": plan_name}
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse rate limit for plan {plan_name}: {e}")
        
        logger.info(f"Initialized {len(self.rules)} rate limiting rules")
    
    def _initialize_algorithms(self) -> None:
        """Initialize rate limiting algorithms."""
        self.algorithms = {
            RateLimitAlgorithm.FIXED_WINDOW: FixedWindowAlgorithm(
                RateLimitConfig(algorithm=RateLimitAlgorithm.FIXED_WINDOW)
            ),
            RateLimitAlgorithm.SLIDING_WINDOW: SlidingWindowAlgorithm(
                RateLimitConfig(algorithm=RateLimitAlgorithm.SLIDING_WINDOW)
            ),
            RateLimitAlgorithm.TOKEN_BUCKET: TokenBucketAlgorithm(
                RateLimitConfig(algorithm=RateLimitAlgorithm.TOKEN_BUCKET)
            ),
            RateLimitAlgorithm.GCRA: GCRAlgorithm(
                RateLimitConfig(algorithm=RateLimitAlgorithm.GCRA)
            ),
        }
    
    def _parse_rate_limit_string(self, rate_string: str) -> Tuple[int, int]:
        """Parse rate limit string like '100/minute'."""
        try:
            if "/" not in rate_string:
                return int(rate_string), 60  # Default to per minute
            
            limit_str, period_str = rate_string.split("/")
            limit = int(limit_str.strip())
            
            period_str = period_str.strip().lower()
            
            if period_str in ["second", "sec", "s"]:
                window = 1
            elif period_str in ["minute", "min", "m"]:
                window = 60
            elif period_str in ["hour", "hr", "h"]:
                window = 3600
            elif period_str in ["day", "d"]:
                window = 86400
            else:
                # Try to parse as seconds
                try:
                    window = int(period_str)
                except ValueError:
                    window = 60  # Default to minute
            
            return limit, window
            
        except Exception as e:
            raise ValueError(f"Invalid rate limit string: {rate_string}") from e
    
    def add_rule(self, rule: RateLimitRule) -> None:
        """Add a rate limiting rule."""
        # Remove existing rule with same name
        self.rules = [r for r in self.rules if r.name != rule.name]
        
        # Add new rule
        self.rules.append(rule)
        
        # Sort by priority (lower priority number = higher priority)
        self.rules.sort(key=lambda r: r.priority)
        
        # Clear cache
        self.rule_cache.clear()
        
        logger.debug(f"Added rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rate limiting rule."""
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        
        if len(self.rules) < initial_count:
            self.rule_cache.clear()
            logger.debug(f"Removed rate limiting rule: {rule_name}")
            return True
        
        return False
    
    def get_matching_rule(self, path: str, scope_context: Dict[str, Any]) -> Optional[RateLimitRule]:
        """Get matching rule for path and scope."""
        cache_key = f"{path}:{hash(frozenset(scope_context.items()))}"
        
        if cache_key in self.rule_cache:
            return self.rule_cache[cache_key]
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if not rule.matches(path):
                continue
            
            # Check scope-specific conditions
            if rule.scope == RateLimitScope.PLAN:
                if "user_plan" not in scope_context:
                    continue
            
            # Rule matches
            self.rule_cache[cache_key] = rule
            return rule
        
        return None
    
    async def check_request(
        self,
        request: RateLimitRequest,
        path: str,
        scope_context: Dict[str, Any]
    ) -> RateLimitResponse:
        """Check if request is allowed based on matching rules."""
        self.stats["total_checks"] += 1
        
        # Find matching rule
        rule = self.get_matching_rule(path, scope_context)
        if not rule:
            # No rule matches, allow request
            self.stats["allowed_requests"] += 1
            return RateLimitResponse(
                allowed=True,
                state=RateLimitState(
                    key=request.key,
                    limit=0,  # No limit
                    remaining=0,
                    reset_time=int(time.time() + 3600),
                    window=3600,
                    algorithm=RateLimitAlgorithm.FIXED_WINDOW
                ),
                reason="No rate limiting rule matched"
            )
        
        # Get algorithm instance
        algorithm = self.algorithms.get(rule.config.algorithm)
        if not algorithm:
            logger.error(f"Algorithm not found: {rule.config.algorithm}")
            self.stats["allowed_requests"] += 1
            return RateLimitResponse(
                allowed=True,
                state=RateLimitState(
                    key=request.key,
                    limit=rule.config.limit,
                    remaining=rule.config.limit,
                    reset_time=int(time.time() + rule.config.window),
                    window=rule.config.window,
                    algorithm=rule.config.algorithm
                ),
                reason="Algorithm not available, request allowed"
            )
        
        # Update request cost
        request.cost = rule.config.cost
        
        # Check rate limit
        response = await algorithm.check(request)
        
        # Update statistics
        if response.allowed:
            self.stats["allowed_requests"] += 1
        else:
            self.stats["denied_requests"] += 1
        
        self.stats["checks_by_algorithm"][rule.config.algorithm.value] = (
            self.stats["checks_by_algorithm"].get(rule.config.algorithm.value, 0) + 1
        )
        
        self.stats["checks_by_scope"][rule.scope.value] = (
            self.stats["checks_by_scope"].get(rule.scope.value, 0) + 1
        )
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        total_checks = self.stats["total_checks"]
        
        return {
            **self.stats,
            "denial_rate": (
                self.stats["denied_requests"] / total_checks * 100
                if total_checks > 0 else 0
            ),
            "active_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "rule_cache_size": len(self.rule_cache),
        }
    
    def clear_stats(self) -> None:
        """Clear statistics."""
        self.stats = {
            "total_checks": 0,
            "allowed_requests": 0,
            "denied_requests": 0,
            "checks_by_algorithm": {},
            "checks_by_scope": {},
        }
        logger.info("Cleared rate limiting statistics")


# ======================
# RATE LIMIT MIDDLEWARE
# ======================

class RateLimiterMiddleware(BaseMiddleware):
    """
    Advanced Rate Limiting Middleware.
    
    Features:
    - Multiple algorithms (fixed window, sliding window, token bucket, GCRA)
    - Redis-backed distributed rate limiting
    - User/plan-based limits
    - Dynamic rule configuration
    - Real-time statistics
    - Graceful degradation
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        
        # Configuration
        self.config = self._load_configuration(kwargs)
        self.enabled = self.config.get("enabled", True)
        self.storage = self.config.get("storage", "redis")
        self.exclude_paths = set(self.config.get("exclude_paths", []))
        self.fail_open = self.config.get("fail_open", True)
        self.include_headers = self.config.get("include_headers", True)
        
        # Initialize manager
        self.manager = RateLimitManager()
        
        # Request tracking for abuse detection
        self.abuse_tracker = AbuseTracker()
        
        logger.info("Rate limiter middleware initialized")
    
    def _load_configuration(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Load rate limiting configuration."""
        # Get from middleware kwargs
        config_dict = {
            "enabled": kwargs.get("enabled", True),
            "storage": kwargs.get("storage", "redis"),
            "exclude_paths": kwargs.get("exclude_paths", []),
            "fail_open": kwargs.get("fail_open", True),
            "include_headers": kwargs.get("include_headers", True),
        }
        
        # Merge with app config
        app_config = get_config().get("rate_limiting", {})
        config_dict.update(app_config)
        
        return config_dict
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response
        """
        # Skip rate limiting if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for excluded paths
        if self._should_skip_rate_limit(request):
            return await call_next(request)
        
        # Get rate limit key
        rate_limit_key = await self._get_rate_limit_key(request)
        if not rate_limit_key:
            # Could not determine key, skip rate limiting
            if self.fail_open:
                return await call_next(request)
            else:
                return self._create_error_response(
                    "Unable to determine rate limit key",
                    HTTP_429_TOO_MANY_REQUESTS
                )
        
        # Check for abuse patterns
        abuse_check = self.abuse_tracker.check_request(request, rate_limit_key)
        if not abuse_check["allowed"]:
            logger.warning(
                f"Abuse detected for key {rate_limit_key}: {abuse_check['reason']}"
            )
            return self._create_error_response(
                "Abuse detected",
                HTTP_429_TOO_MANY_REQUESTS,
                retry_after=abuse_check.get("retry_after", 60)
            )
        
        # Prepare rate limit request
        rate_limit_request = RateLimitRequest(
            key=rate_limit_key,
            metadata={
                "path": str(request.url.path),
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Get scope context
        scope_context = await self._get_scope_context(request)
        
        try:
            # Check rate limit
            response = await self.manager.check_request(
                rate_limit_request,
                str(request.url.path),
                scope_context
            )
            
            # Process response
            if response.allowed:
                # Request allowed
                http_response = await call_next(request)
                
                # Add rate limit headers if enabled
                if self.include_headers:
                    for header, value in response.state.to_headers().items():
                        http_response.headers[header] = value
                
                return http_response
            else:
                # Request denied
                logger.warning(
                    f"Rate limit exceeded for key {rate_limit_key}: "
                    f"{response.state.remaining}/{response.state.limit} remaining"
                )
                
                return self._create_rate_limit_response(response)
                
        except Exception as e:
            # Error in rate limiting logic
            logger.error(f"Rate limiting error: {e}")
            
            if self.fail_open:
                # Fail open: allow request
                logger.warning("Rate limiting failed open, allowing request")
                return await call_next(request)
            else:
                # Fail closed: deny request
                return self._create_error_response(
                    "Rate limiting service unavailable",
                    HTTP_429_TOO_MANY_REQUESTS
                )
    
    def _should_skip_rate_limit(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        path = request.url.path
        
        # Check exact matches
        if path in self.exclude_paths:
            return True
        
        # Check prefix matches
        for exclude_path in self.exclude_paths:
            if exclude_path.endswith('*') and path.startswith(exclude_path[:-1]):
                return True
        
        # Skip health checks, metrics, docs
        if path in ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            return True
        
        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        return False
    
    async def _get_rate_limit_key(self, request: Request) -> Optional[str]:
        """Get rate limit key for request."""
        key_parts = []
        
        # Add scope based on configuration
        scope_config = self.config.get("scope", "ip")
        
        if scope_config == "ip":
            # IP-based rate limiting
            client_ip = request.client.host if request.client else "unknown"
            key_parts.append(f"ip:{client_ip}")
            
        elif scope_config == "user":
            # User-based rate limiting
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                key_parts.append(f"user:{user_id}")
            else:
                # Fall back to IP if user not authenticated
                client_ip = request.client.host if request.client else "unknown"
                key_parts.append(f"ip:{client_ip}")
        
        elif scope_config == "endpoint":
            # Endpoint-based rate limiting
            key_parts.append(f"endpoint:{request.url.path}")
        
        elif scope_config == "global":
            # Global rate limiting
            key_parts.append("global")
        
        else:
            # Custom scope
            key_parts.append(f"custom:{scope_config}")
        
        # Add method for method-specific limits
        if self.config.get("include_method", True):
            key_parts.append(f"method:{request.method}")
        
        # Add path for path-specific limits
        if self.config.get("include_path", False):
            key_parts.append(f"path:{request.url.path}")
        
        # Create final key
        if not key_parts:
            return None
        
        # Hash the key for consistent length
        key_string = ":".join(key_parts)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"rl:{key_hash}"
    
    async def _get_scope_context(self, request: Request) -> Dict[str, Any]:
        """Get scope context for rate limiting rules."""
        context = {}
        
        # Add user information
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            context["user_id"] = user_id
        
        # Add user plan (if available)
        user_plan = getattr(request.state, 'user_plan', None)
        if user_plan:
            context["user_plan"] = user_plan
        
        # Add IP address
        client_ip = request.client.host if request.client else None
        if client_ip:
            context["client_ip"] = client_ip
        
        return context
    
    def _create_rate_limit_response(self, rate_limit_response: RateLimitResponse) -> Response:
        """Create HTTP response for rate limited request."""
        from fastapi.responses import JSONResponse
        
        # Calculate retry after
        retry_after = rate_limit_response.state.retry_after or 60
        
        # Create error response
        error_data = {
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded",
            "retry_after": retry_after,
            "limit": rate_limit_response.state.limit,
            "remaining": rate_limit_response.state.remaining,
            "reset_time": rate_limit_response.state.reset_time,
            "error_id": str(uuid.uuid4()),
        }
        
        response = JSONResponse(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            content=error_data,
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(rate_limit_response.state.limit),
                "X-RateLimit-Remaining": str(rate_limit_response.state.remaining),
                "X-RateLimit-Reset": str(rate_limit_response.state.reset_time),
                "X-RateLimit-Retry-After": str(retry_after),
            }
        )
        
        return response
    
    def _create_error_response(self, message: str, status_code: int = 429, retry_after: int = 60) -> Response:
        """Create generic error response."""
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": "rate_limit_error",
                "message": message,
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        return {
            "manager_stats": self.manager.get_stats(),
            "abuse_tracker_stats": self.abuse_tracker.get_stats(),
            "config": {
                "enabled": self.enabled,
                "storage": self.storage,
                "fail_open": self.fail_open,
                "include_headers": self.include_headers,
            },
            "active_rules": [
                {
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "scope": rule.scope.value,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                    "config": rule.config.to_dict(),
                }
                for rule in self.manager.rules
            ],
        }
    
    def clear_stats(self) -> None:
        """Clear rate limiting statistics."""
        self.manager.clear_stats()
        self.abuse_tracker.clear_stats()
        logger.info("Cleared rate limiting statistics")


# ======================
# ABUSE TRACKER
# ======================

class AbuseTracker:
    """Track abusive request patterns."""
    
    def __init__(self):
        self.request_counts: Dict[str, List[float]] = {}
        self.blocked_keys: Dict[str, float] = {}
        
        # Configuration
        self.window_size = 60  # seconds
        self.max_requests_per_window = 100
        self.block_duration = 300  # seconds
        self.suspicious_patterns = [
            r"\.\./",  # Directory traversal
            r"<script>",  # XSS attempts
            r"union.*select",  # SQL injection (simplified)
            r"eval\(",  # Code injection
        ]
        
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "suspicious_requests": 0,
            "blocks_by_reason": {},
        }
    
    def check_request(self, request: Request, key: str) -> Dict[str, Any]:
        """Check request for abuse patterns."""
        self.stats["total_requests"] += 1
        
        # Check if key is blocked
        if key in self.blocked_keys:
            block_until = self.blocked_keys[key]
            if time.time() < block_until:
                self.stats["blocked_requests"] += 1
                return {
                    "allowed": False,
                    "reason": "key_blocked",
                    "retry_after": int(block_until - time.time()),
                }
            else:
                # Block expired
                del self.blocked_keys[key]
        
        # Check request rate
        rate_check = self._check_request_rate(key)
        if not rate_check["allowed"]:
            # Block the key
            block_until = time.time() + self.block_duration
            self.blocked_keys[key] = block_until
            
            self.stats["blocked_requests"] += 1
            self.stats["blocks_by_reason"]["rate_limit"] = (
                self.stats["blocks_by_reason"].get("rate_limit", 0) + 1
            )
            
            return {
                "allowed": False,
                "reason": "rate_too_high",
                "retry_after": self.block_duration,
            }
        
        # Check for suspicious patterns
        pattern_check = self._check_suspicious_patterns(request)
        if not pattern_check["allowed"]:
            self.stats["suspicious_requests"] += 1
            self.stats["blocks_by_reason"][pattern_check["reason"]] = (
                self.stats["blocks_by_reason"].get(pattern_check["reason"], 0) + 1
            )
            
            # Don't block immediately for suspicious patterns, just log
            logger.warning(
                f"Suspicious request pattern detected: {pattern_check['reason']}",
                extra={
                    "key": key,
                    "path": request.url.path,
                    "pattern": pattern_check["pattern"],
                }
            )
        
        return {"allowed": True, "reason": None}
    
    def _check_request_rate(self, key: str) -> Dict[str, Any]:
        """Check request rate for a key."""
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Initialize or clean up request history
        if key not in self.request_counts:
            self.request_counts[key] = []
        
        # Remove old requests
        self.request_counts[key] = [
            ts for ts in self.request_counts[key]
            if ts > window_start
        ]
        
        # Add current request
        self.request_counts[key].append(current_time)
        
        # Check rate
        request_count = len(self.request_counts[key])
        
        if request_count > self.max_requests_per_window:
            return {
                "allowed": False,
                "reason": f"Rate too high: {request_count} requests in {self.window_size}s",
            }
        
        return {"allowed": True}
    
    def _check_suspicious_patterns(self, request: Request) -> Dict[str, Any]:
        """Check for suspicious patterns in request."""
        import re
        
        # Check path
        path = str(request.url.path)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return {
                    "allowed": False,
                    "reason": "suspicious_path",
                    "pattern": pattern,
                }
        
        # Check query parameters
        for param_name, param_value in request.query_params.items():
            param_str = f"{param_name}={param_value}"
            for pattern in self.suspicious_patterns:
                if re.search(pattern, param_str, re.IGNORECASE):
                    return {
                        "allowed": False,
                        "reason": "suspicious_query_param",
                        "pattern": pattern,
                        "param": param_name,
                    }
        
        return {"allowed": True}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get abuse tracker statistics."""
        return {
            **self.stats,
            "currently_blocked": len(self.blocked_keys),
            "tracked_keys": len(self.request_counts),
        }
    
    def clear_stats(self) -> None:
        """Clear abuse tracker statistics."""
        self.request_counts.clear()
        self.blocked_keys.clear()
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "suspicious_requests": 0,
            "blocks_by_reason": {},
        }


# ======================
# RATE LIMIT UTILITIES
# ======================

def setup_rate_limiter(
    app: FastAPI,
    config: Optional[Dict[str, Any]] = None
) -> RateLimiterMiddleware:
    """
    Setup rate limiter middleware on FastAPI app.
    
    Args:
        app: FastAPI application
        config: Rate limiter configuration
        
    Returns:
        RateLimiterMiddleware instance
    """
    if config is None:
        # Get default config
        cfg = get_config()
        config = {
            "enabled": cfg.get("rate_limiting.enabled", True),
            "storage": "redis",
            "exclude_paths": [
                "/health",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
            ],
            "fail_open": True,
            "include_headers": True,
            "scope": "ip",
            "include_method": True,
            "include_path": False,
        }
    
    # Create middleware
    middleware = RateLimiterMiddleware(app, **config)
    
    # Add middleware to app
    from ..middleware import MiddlewareManager
    manager = MiddlewareManager(app)
    manager.register("rate_limiter", RateLimiterMiddleware, config)
    manager.setup_app()
    
    # Add rate limit info endpoint
    @app.get("/rate-limit/info", include_in_schema=False)
    async def get_rate_limit_info() -> Dict[str, Any]:
        """Get rate limiting information and statistics."""
        return {
            "stats": middleware.get_stats(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @app.post("/rate-limit/clear-stats", include_in_schema=False)
    async def clear_rate_limit_stats() -> Dict[str, Any]:
        """Clear rate limiting statistics."""
        middleware.clear_stats()
        return {
            "message": "Rate limiting statistics cleared",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    logger.info("Rate limiter middleware setup complete")
    return middleware


def rate_limit(
    limit: int = 100,
    window: int = 60,
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW,
    scope: RateLimitScope = RateLimitScope.USER,
    cost: int = 1
):
    """
    Decorator for endpoint-specific rate limiting.
    
    Args:
        limit: Maximum requests
        window: Time window in seconds
        algorithm: Rate limiting algorithm
        scope: Rate limiting scope
        cost: Request cost
        
    Returns:
        Decorated function
    """
    def decorator(func):
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
                raise RuntimeError("Request object not found")
            
            # Check if rate limiter is available
            if hasattr(request.app.state, 'rate_limiter'):
                rate_limiter = request.app.state.rate_limiter
                
                # Create rate limit key based on scope
                key_parts = []
                
                if scope == RateLimitScope.USER:
                    user_id = getattr(request.state, 'user_id', None)
                    if user_id:
                        key_parts.append(f"decorator:user:{user_id}")
                    else:
                        key_parts.append(f"decorator:ip:{request.client.host}")
                
                elif scope == RateLimitScope.IP:
                    client_ip = request.client.host if request.client else "unknown"
                    key_parts.append(f"decorator:ip:{client_ip}")
                
                elif scope == RateLimitScope.ENDPOINT:
                    key_parts.append(f"decorator:endpoint:{request.url.path}")
                
                elif scope == RateLimitScope.METHOD:
                    key_parts.append(f"decorator:{request.method}:{request.url.path}")
                
                # Create key
                key_string = ":".join(key_parts)
                key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
                rate_limit_key = f"decorator:{key_hash}"
                
                # Create rate limit config
                rate_config = RateLimitConfig(
                    algorithm=algorithm,
                    limit=limit,
                    window=window,
                    cost=cost
                )
                
                # Create temporary rule
                rule_name = f"decorator_{func.__name__}_{hash(key_string)}"
                rule = RateLimitRule(
                    name=rule_name,
                    pattern=f"^{request.url.path}$",
                    config=rate_config,
                    scope=scope,
                    priority=100  # High priority
                )
                
                # Add rule to manager
                rate_limiter.manager.add_rule(rule)
                
                # Prepare rate limit request
                rate_limit_request = RateLimitRequest(
                    key=rate_limit_key,
                    cost=cost,
                    metadata={
                        "decorator": True,
                        "function": func.__name__,
                        "scope": scope.value,
                    }
                )
                
                # Get scope context
                scope_context = {}
                if scope == RateLimitScope.USER:
                    user_id = getattr(request.state, 'user_id', None)
                    if user_id:
                        scope_context["user_id"] = user_id
                
                # Check rate limit
                response = await rate_limiter.manager.check_request(
                    rate_limit_request,
                    str(request.url.path),
                    scope_context
                )
                
                if not response.allowed:
                    raise HTTPException(
                        status_code=HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "rate_limit_exceeded",
                            "message": "Rate limit exceeded",
                            "retry_after": response.state.retry_after,
                            "limit": response.state.limit,
                            "remaining": response.state.remaining,
                        }
                    )
            
            # Execute the original function
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ======================
# EXPORTS
# ======================

__all__ = [
    # Main middleware
    "RateLimiterMiddleware",
    "setup_rate_limiter",
    
    # Models and enums
    "RateLimitAlgorithm",
    "RateLimitScope",
    "RateLimitResult",
    "RateLimitConfig",
    "RateLimitRule",
    "RateLimitState",
    "RateLimitRequest",
    "RateLimitResponse",
    
    # Algorithms
    "FixedWindowAlgorithm",
    "SlidingWindowAlgorithm",
    "TokenBucketAlgorithm",
    "GCRAlgorithm",
    
    # Manager
    "RateLimitManager",
    
    # Abuse tracking
    "AbuseTracker",
    
    # Decorators
    "rate_limit",
    
    # Utilities
    "create_rate_limit_key",
]


def create_rate_limit_key(scope: str, identifier: str) -> str:
    """
    Create a rate limit key.
    
    Args:
        scope: Rate limit scope (e.g., 'user', 'ip', 'endpoint')
        identifier: Scope identifier (e.g., user_id, ip_address, endpoint_path)
        
    Returns:
        Rate limit key
    """
    key_string = f"{scope}:{identifier}"
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
    return f"rl:{key_hash}"


if __name__ == "__main__":
    # Test the rate limiter middleware
    import asyncio
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    
    print("⚡ Rate Limiter Middleware Test")
    print("=" * 50)
    
    # Create test app
    app = FastAPI()
    
    # Setup rate limiter
    middleware = setup_rate_limiter(app, {
        "enabled": True,
        "scope": "ip",
        "fail_open": True,
    })
    
    # Add test endpoints
    @app.get("/test/unlimited")
    async def test_unlimited():
        return {"message": "Unlimited endpoint"}
    
    @app.get("/test/limited")
    @rate_limit(limit=5, window=10, scope=RateLimitScope.IP)
    async def test_limited():
        return {"message": "Limited endpoint (5 requests per 10 seconds)"}
    
    @app.get("/test/user-limited")
    @rate_limit(limit=3, window=60, scope=RateLimitScope.USER)
    async def test_user_limited(request: Request):
        # Simulate authenticated user
        request.state.user_id = "test_user_123"
        return {"message": "User-limited endpoint"}
    
    # Test with test client
    client = TestClient(app)
    
    print("\n1. Testing unlimited endpoint...")
    for i in range(3):
        response = client.get("/test/unlimited")
        print(f"   Request {i+1}: Status {response.status_code}")
    
    print("\n2. Testing limited endpoint...")
    successes = 0
    failures = 0
    
    for i in range(7):  # Try 7 requests, limit is 5
        response = client.get("/test/limited")
        if response.status_code == 200:
            successes += 1
            print(f"   Request {i+1}: ✅ Allowed")
        else:
            failures += 1
            print(f"   Request {i+1}: ❌ Denied (Status: {response.status_code})")
            print(f"        Headers: {dict(response.headers)}")
    
    print(f"   Summary: {successes} allowed, {failures} denied")
    
    print("\n3. Testing user-limited endpoint...")
    # Simulate authenticated requests
    for i in range(4):  # Try 4 requests, limit is 3
        response = client.get("/test/user-limited")
        if response.status_code == 200:
            print(f"   Request {i+1}: ✅ Allowed")
        else:
            print(f"   Request {i+1}: ❌ Denied (Status: {response.status_code})")
    
    print("\n4. Testing rate limit info endpoint...")
    response = client.get("/rate-limit/info")
    if response.status_code == 200:
        data = response.json()
        stats = data.get("stats", {})
        print(f"   Total checks: {stats.get('manager_stats', {}).get('total_checks', 0)}")
        print(f"   Denied requests: {stats.get('manager_stats', {}).get('denied_requests', 0)}")
    
    print("\n5. Testing abuse detection...")
    # Make many rapid requests to trigger abuse detection
    rapid_requests = []
    for i in range(50):
        response = client.get("/test/unlimited")
        rapid_requests.append(response.status_code)
    
    abuse_count = rapid_requests.count(429)
    print(f"   Rapid requests: 50, Blocked: {abuse_count}")
    
    print("\n6. Testing statistics...")
    stats = middleware.get_stats()
    print(f"   Active rules: {len(stats.get('active_rules', []))}")
    print(f"   Abuse tracker blocked: {stats.get('abuse_tracker_stats', {}).get('blocked_requests', 0)}")
    
    print("\n✅ All rate limiter tests completed successfully!")
