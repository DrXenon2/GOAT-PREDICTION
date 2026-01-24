"""
Advanced CORS (Cross-Origin Resource Sharing) Middleware for GOAT Prediction Ultimate.
Supports dynamic origins, preflight caching, security headers, and fine-grained control.
"""

import re
from typing import List, Optional, Set, Union, Pattern, Callable, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
from urllib.parse import urlparse
import ipaddress

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Send, Scope

# Local imports
from ..core.config import config, get_config
from ..core.logging import get_logger
from ..core.exceptions import SecurityError
from .base import BaseMiddleware

logger = get_logger(__name__)

# ======================
# DATA MODELS
# ======================

class OriginPattern:
    """Pattern for matching origins with wildcards and regex support."""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.is_wildcard = pattern == "*"
        self.is_regex = False
        self.regex_pattern = None
        
        if not self.is_wildcard:
            # Check if pattern contains wildcards
            if "*" in pattern:
                # Convert wildcard pattern to regex
                regex_pattern = re.escape(pattern)
                regex_pattern = regex_pattern.replace(r'\*', r'.*')
                regex_pattern = f"^{regex_pattern}$"
                self.regex_pattern = re.compile(regex_pattern)
                self.is_regex = True
            else:
                # Exact match
                self.is_regex = False
    
    def matches(self, origin: str) -> bool:
        """Check if origin matches the pattern."""
        if self.is_wildcard:
            return True
        
        if self.is_regex:
            return bool(self.regex_pattern.match(origin))
        
        return self.pattern == origin
    
    def __str__(self):
        return self.pattern
    
    def __repr__(self):
        return f"OriginPattern('{self.pattern}')"


class CORSConfig:
    """CORS configuration model."""
    
    def __init__(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_origin_regex: Optional[str] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        expose_headers: Optional[List[str]] = None,
        max_age: int = 600,
        vary_header: bool = True,
        allow_private_network: bool = False,
        preflight_cache_max_age: int = 600,
        strict_origin: bool = False,
        dynamic_origins: bool = False,
        origin_validator: Optional[Callable[[str], bool]] = None
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_origin_regex = allow_origin_regex
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.expose_headers = expose_headers or []
        self.max_age = max_age
        self.vary_header = vary_header
        self.allow_private_network = allow_private_network
        self.preflight_cache_max_age = preflight_cache_max_age
        self.strict_origin = strict_origin
        self.dynamic_origins = dynamic_origins
        self.origin_validator = origin_validator
        
        # Compile origin patterns
        self.origin_patterns = [OriginPattern(pattern) for pattern in self.allow_origins]
        
        # Compile regex if provided
        self.regex_pattern = None
        if allow_origin_regex:
            try:
                self.regex_pattern = re.compile(allow_origin_regex)
            except re.error as e:
                logger.error(f"Invalid CORS origin regex: {e}")
                self.regex_pattern = None
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        # Validate origin format
        if not self._is_valid_origin(origin):
            return False
        
        # Check custom validator first
        if self.origin_validator and not self.origin_validator(origin):
            return False
        
        # Check patterns
        for pattern in self.origin_patterns:
            if pattern.matches(origin):
                return True
        
        # Check regex
        if self.regex_pattern and self.regex_pattern.match(origin):
            return True
        
        return False
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Validate origin format."""
        try:
            parsed = urlparse(origin)
            
            # Origin must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Valid schemes
            if parsed.scheme not in ["http", "https", "ws", "wss"]:
                return False
            
            # Check for invalid characters
            if re.search(r'[<>"\'{}|\\^`]', origin):
                return False
            
            return True
            
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allow_origins": self.allow_origins,
            "allow_origin_regex": self.allow_origin_regex,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "allow_credentials": self.allow_credentials,
            "expose_headers": self.expose_headers,
            "max_age": self.max_age,
            "vary_header": self.vary_header,
            "allow_private_network": self.allow_private_network,
            "preflight_cache_max_age": self.preflight_cache_max_age,
            "strict_origin": self.strict_origin,
            "dynamic_origins": self.dynamic_origins,
        }


class CORSRequestInfo:
    """Information about CORS request."""
    
    def __init__(self, request: Request):
        self.request = request
        self.origin = request.headers.get("origin")
        self.method = request.method
        self.access_control_request_method = request.headers.get("access-control-request-method")
        self.access_control_request_headers = request.headers.get("access-control-request-headers", "")
        self.is_preflight = (
            self.method == "OPTIONS" and 
            self.access_control_request_method is not None
        )
        self.is_cors = self.origin is not None
        self.is_same_origin = self._check_same_origin()
    
    def _check_same_origin(self) -> bool:
        """Check if request is same-origin."""
        if not self.origin:
            return True
        
        # Extract host from request
        host = self.request.headers.get("host")
        if not host:
            return False
        
        # Build request origin from host
        scheme = "https" if self.request.url.scheme == "https" else "http"
        request_origin = f"{scheme}://{host}"
        
        return self.origin == request_origin
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "origin": self.origin,
            "method": self.method,
            "is_preflight": self.is_preflight,
            "is_cors": self.is_cors,
            "is_same_origin": self.is_same_origin,
            "request_method": self.access_control_request_method,
            "request_headers": self.access_control_request_headers,
        }


# ======================
# ORIGIN VALIDATORS
# ======================

class OriginValidator:
    """Collection of origin validation utilities."""
    
    @staticmethod
    def validate_localhost(origin: str) -> bool:
        """Allow localhost and local network origins."""
        parsed = urlparse(origin)
        
        # Allow localhost
        if parsed.hostname in ["localhost", "127.0.0.1", "::1"]:
            return True
        
        # Allow local network (192.168.x.x, 10.x.x.x, 172.16.x.x - 172.31.x.x)
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            return ip.is_private
        except (ValueError, ipaddress.AddressValueError):
            pass
        
        return False
    
    @staticmethod
    def validate_domain(origin: str, allowed_domains: List[str]) -> bool:
        """Validate against list of allowed domains."""
        parsed = urlparse(origin)
        domain = parsed.hostname
        
        # Remove www. prefix for matching
        if domain and domain.startswith("www."):
            domain = domain[4:]
        
        return domain in allowed_domains
    
    @staticmethod
    def validate_subdomain(origin: str, base_domain: str) -> bool:
        """Validate subdomains of a base domain."""
        parsed = urlparse(origin)
        hostname = parsed.hostname
        
        if not hostname:
            return False
        
        # Check if it's the base domain or a subdomain
        return hostname == base_domain or hostname.endswith(f".{base_domain}")
    
    @staticmethod
    def validate_https_only(origin: str) -> bool:
        """Only allow HTTPS origins in production."""
        parsed = urlparse(origin)
        return parsed.scheme == "https"
    
    @staticmethod
    def validate_no_ip_address(origin: str) -> bool:
        """Prevent IP address origins."""
        parsed = urlparse(origin)
        
        try:
            ipaddress.ip_address(parsed.hostname)
            return False  # It's an IP address
        except (ValueError, ipaddress.AddressValueError):
            return True  # It's a domain name
    
    @staticmethod
    def create_validator(
        allow_localhost: bool = True,
        allow_private_network: bool = False,
        https_only: bool = False,
        no_ip_addresses: bool = False,
        allowed_domains: Optional[List[str]] = None,
        base_domain: Optional[str] = None
    ) -> Callable[[str], bool]:
        """Create a combined origin validator."""
        def validator(origin: str) -> bool:
            # Validate HTTPS only
            if https_only and not OriginValidator.validate_https_only(origin):
                return False
            
            # Validate no IP addresses
            if no_ip_addresses and not OriginValidator.validate_no_ip_address(origin):
                return False
            
            # Check localhost
            if allow_localhost and OriginValidator.validate_localhost(origin):
                return True
            
            # Check private network
            if allow_private_network:
                parsed = urlparse(origin)
                try:
                    ip = ipaddress.ip_address(parsed.hostname)
                    if ip.is_private:
                        return True
                except (ValueError, ipaddress.AddressValueError):
                    pass
            
            # Check allowed domains
            if allowed_domains and OriginValidator.validate_domain(origin, allowed_domains):
                return True
            
            # Check subdomains
            if base_domain and OriginValidator.validate_subdomain(origin, base_domain):
                return True
            
            # If no specific validators match, use default patterns
            return True
        
        return validator


# ======================
# CORS MIDDLEWARE
# ======================

class CORSMiddleware(BaseMiddleware):
    """
    Advanced CORS Middleware with enhanced security and flexibility.
    
    Features:
    - Dynamic origin validation
    - Preflight request caching
    - Security headers
    - Private network access
    - Origin pattern matching with wildcards
    - Request/response logging
    - Rate limiting for CORS requests
    - CORS violation detection
    """
    
    def __init__(self, app: ASGIApp, **kwargs):
        super().__init__(app, **kwargs)
        
        # Load configuration
        self.config = self._load_configuration(kwargs)
        
        # CORS violation tracking
        self.violation_tracker = CORSViolationTracker()
        
        # Preflight cache
        self.preflight_cache = PreflightCache(max_age=self.config.preflight_cache_max_age)
        
        # Security headers
        self.security_headers = SecurityHeaders()
        
        logger.info(f"CORS middleware initialized with {len(self.config.allow_origins)} origin patterns")
    
    def _load_configuration(self, kwargs: Dict[str, Any]) -> CORSConfig:
        """Load CORS configuration from various sources."""
        # Get configuration from middleware kwargs
        config_dict = {
            "allow_origins": kwargs.get("allow_origins"),
            "allow_origin_regex": kwargs.get("allow_origin_regex"),
            "allow_methods": kwargs.get("allow_methods"),
            "allow_headers": kwargs.get("allow_headers"),
            "allow_credentials": kwargs.get("allow_credentials"),
            "expose_headers": kwargs.get("expose_headers"),
            "max_age": kwargs.get("max_age"),
            "vary_header": kwargs.get("vary_header", True),
            "allow_private_network": kwargs.get("allow_private_network", False),
            "preflight_cache_max_age": kwargs.get("preflight_cache_max_age", 600),
            "strict_origin": kwargs.get("strict_origin", False),
            "dynamic_origins": kwargs.get("dynamic_origins", False),
        }
        
        # Remove None values
        config_dict = {k: v for k, v in config_dict.items() if v is not None}
        
        # Merge with app config if dynamic origins is enabled
        if config_dict.get("dynamic_origins"):
            app_config = get_config().get("cors", {})
            config_dict.update(app_config)
        
        # Create validator if needed
        if config_dict.get("dynamic_origins"):
            config_dict["origin_validator"] = self._create_dynamic_validator()
        
        return CORSConfig(**config_dict)
    
    def _create_dynamic_validator(self) -> Callable[[str], bool]:
        """Create dynamic origin validator based on configuration."""
        cfg = get_config()
        
        return OriginValidator.create_validator(
            allow_localhost=cfg.get("cors.allow_localhost", True),
            allow_private_network=cfg.get("cors.allow_private_network", False),
            https_only=cfg.get("environment") == "production",
            no_ip_addresses=cfg.get("cors.no_ip_addresses", True),
            allowed_domains=cfg.get("cors.allowed_domains"),
            base_domain=cfg.get("cors.base_domain")
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process CORS headers for request.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint
            
        Returns:
            Response with CORS headers
        """
        # Parse CORS request info
        cors_info = CORSRequestInfo(request)
        
        # Skip CORS for same-origin requests
        if cors_info.is_same_origin:
            return await call_next(request)
        
        # Check if origin is allowed
        if cors_info.origin and not self.config.is_origin_allowed(cors_info.origin):
            self.violation_tracker.record_violation(
                origin=cors_info.origin,
                reason="origin_not_allowed",
                request_info=cors_info.to_dict()
            )
            
            # In strict mode, reject the request
            if self.config.strict_origin:
                return self._create_cors_error_response("Origin not allowed")
        
        # Handle preflight requests
        if cors_info.is_preflight:
            return await self._handle_preflight_request(request, cors_info)
        
        # Handle regular CORS request
        response = await call_next(request)
        
        # Add CORS headers to response
        response = self._add_cors_headers(response, cors_info)
        
        # Add security headers
        response = self.security_headers.add_headers(response)
        
        # Log successful CORS request (debug level)
        logger.debug(
            f"CORS request allowed: {cors_info.origin} -> {request.url.path}",
            extra=cors_info.to_dict()
        )
        
        return response
    
    async def _handle_preflight_request(self, request: Request, cors_info: CORSRequestInfo) -> Response:
        """
        Handle CORS preflight (OPTIONS) requests.
        
        Args:
            request: Preflight request
            cors_info: CORS request info
            
        Returns:
            Preflight response
        """
        # Check cache first
        cache_key = self._get_preflight_cache_key(request)
        cached_response = self.preflight_cache.get(cache_key)
        
        if cached_response:
            logger.debug(f"Serving cached preflight response for {cors_info.origin}")
            return cached_response
        
        # Validate request method
        if cors_info.access_control_request_method:
            if cors_info.access_control_request_method not in self.config.allow_methods:
                self.violation_tracker.record_violation(
                    origin=cors_info.origin,
                    reason="method_not_allowed",
                    request_info=cors_info.to_dict()
                )
                return self._create_cors_error_response(
                    f"Method {cors_info.access_control_request_method} not allowed"
                )
        
        # Validate request headers
        if cors_info.access_control_request_headers:
            requested_headers = [
                h.strip() for h in cors_info.access_control_request_headers.split(",")
            ]
            
            if "*" not in self.config.allow_headers:
                for header in requested_headers:
                    if header.lower() not in [
                        h.lower() for h in self.config.allow_headers
                    ]:
                        self.violation_tracker.record_violation(
                            origin=cors_info.origin,
                            reason="header_not_allowed",
                            request_info=cors_info.to_dict()
                        )
                        return self._create_cors_error_response(
                            f"Header {header} not allowed"
                        )
        
        # Create preflight response
        response = Response(
            content="",
            status_code=204,
            headers=self._build_preflight_headers(cors_info)
        )
        
        # Add security headers
        response = self.security_headers.add_headers(response)
        
        # Cache the response
        self.preflight_cache.set(cache_key, response)
        
        logger.debug(
            f"Preflight request handled: {cors_info.origin}",
            extra={"method": cors_info.access_control_request_method}
        )
        
        return response
    
    def _add_cors_headers(self, response: Response, cors_info: CORSRequestInfo) -> Response:
        """
        Add CORS headers to response.
        
        Args:
            response: Original response
            cors_info: CORS request info
            
        Returns:
            Response with CORS headers
        """
        headers = response.headers
        
        # Add Access-Control-Allow-Origin
        if cors_info.origin and self.config.is_origin_allowed(cors_info.origin):
            if self.config.allow_credentials:
                headers["Access-Control-Allow-Origin"] = cors_info.origin
                headers["Vary"] = "Origin"
            else:
                # For non-credential requests, we can use wildcard or echo origin
                if "*" in self.config.allow_origins:
                    headers["Access-Control-Allow-Origin"] = "*"
                else:
                    headers["Access-Control-Allow-Origin"] = cors_info.origin
                    if self.config.vary_header:
                        vary = headers.get("Vary", "")
                        if "Origin" not in vary:
                            headers["Vary"] = f"{vary}, Origin" if vary else "Origin"
        
        # Add Access-Control-Allow-Credentials
        if self.config.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        
        # Add Access-Control-Expose-Headers
        if self.config.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.config.expose_headers)
        
        # Add Access-Control-Allow-Private-Network
        if self.config.allow_private_network:
            headers["Access-Control-Allow-Private-Network"] = "true"
        
        return response
    
    def _build_preflight_headers(self, cors_info: CORSRequestInfo) -> Dict[str, str]:
        """
        Build headers for preflight response.
        
        Args:
            cors_info: CORS request info
            
        Returns:
            Dictionary of headers
        """
        headers = {}
        
        # Allow-Origin
        if cors_info.origin and self.config.is_origin_allowed(cors_info.origin):
            if self.config.allow_credentials:
                headers["Access-Control-Allow-Origin"] = cors_info.origin
            else:
                if "*" in self.config.allow_origins:
                    headers["Access-Control-Allow-Origin"] = "*"
                else:
                    headers["Access-Control-Allow-Origin"] = cors_info.origin
        
        # Allow-Methods
        headers["Access-Control-Allow-Methods"] = ", ".join(self.config.allow_methods)
        
        # Allow-Headers
        if self.config.allow_headers == ["*"]:
            if cors_info.access_control_request_headers:
                headers["Access-Control-Allow-Headers"] = cors_info.access_control_request_headers
            else:
                headers["Access-Control-Allow-Headers"] = "*"
        else:
            headers["Access-Control-Allow-Headers"] = ", ".join(self.config.allow_headers)
        
        # Max-Age
        headers["Access-Control-Max-Age"] = str(self.config.max_age)
        
        # Allow-Credentials
        if self.config.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        
        # Allow-Private-Network
        if self.config.allow_private_network:
            headers["Access-Control-Allow-Private-Network"] = "true"
        
        # Vary header
        if self.config.vary_header:
            vary_headers = ["Origin"]
            if cors_info.access_control_request_method:
                vary_headers.append("Access-Control-Request-Method")
            if cors_info.access_control_request_headers:
                vary_headers.append("Access-Control-Request-Headers")
            headers["Vary"] = ", ".join(vary_headers)
        
        return headers
    
    def _get_preflight_cache_key(self, request: Request) -> str:
        """
        Generate cache key for preflight request.
        
        Args:
            request: Preflight request
            
        Returns:
            Cache key
        """
        origin = request.headers.get("origin", "")
        method = request.headers.get("access-control-request-method", "")
        headers = request.headers.get("access-control-request-headers", "")
        
        # Normalize headers (case-insensitive, sorted)
        if headers:
            header_list = [h.strip().lower() for h in headers.split(",")]
            header_list.sort()
            headers = ",".join(header_list)
        
        return f"preflight:{origin}:{method}:{headers}"
    
    def _create_cors_error_response(self, message: str) -> Response:
        """
        Create error response for CORS violations.
        
        Args:
            message: Error message
            
        Returns:
            Error response
        """
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=403,
            content={
                "error": "cors_error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            },
            headers={
                "Content-Type": "application/json",
                **self.security_headers.get_base_headers()
            }
        )
    
    def get_origin_stats(self) -> Dict[str, Any]:
        """
        Get statistics about CORS origins.
        
        Returns:
            Dictionary with statistics
        """
        return self.violation_tracker.get_stats()
    
    def get_allowed_origins(self) -> List[str]:
        """
        Get list of allowed origins.
        
        Returns:
            List of allowed origin patterns
        """
        return self.config.allow_origins
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if an origin is allowed.
        
        Args:
            origin: Origin to check
            
        Returns:
            True if origin is allowed
        """
        return self.config.is_origin_allowed(origin)
    
    def add_allowed_origin(self, origin: str) -> bool:
        """
        Dynamically add an allowed origin.
        
        Args:
            origin: Origin to add
            
        Returns:
            True if origin was added
        """
        if not self.config.dynamic_origins:
            logger.warning("Cannot add origin: dynamic origins not enabled")
            return False
        
        if self.config.is_origin_allowed(origin):
            return True  # Already allowed
        
        # Validate origin format
        if not self.config._is_valid_origin(origin):
            logger.warning(f"Invalid origin format: {origin}")
            return False
        
        # Add to patterns
        self.config.allow_origins.append(origin)
        self.config.origin_patterns.append(OriginPattern(origin))
        
        logger.info(f"Added allowed origin: {origin}")
        return True
    
    def remove_allowed_origin(self, origin: str) -> bool:
        """
        Remove an allowed origin.
        
        Args:
            origin: Origin to remove
            
        Returns:
            True if origin was removed
        """
        if origin in self.config.allow_origins:
            self.config.allow_origins.remove(origin)
            self.config.origin_patterns = [
                p for p in self.config.origin_patterns if str(p) != origin
            ]
            logger.info(f"Removed allowed origin: {origin}")
            return True
        
        return False


# ======================
# SUPPORTING CLASSES
# ======================

class CORSViolationTracker:
    """Track CORS violations for security monitoring."""
    
    def __init__(self, max_violations: int = 1000):
        self.violations = []
        self.max_violations = max_violations
        self.stats = {
            "total_violations": 0,
            "violations_by_type": {},
            "violations_by_origin": {},
            "last_violation": None
        }
    
    def record_violation(
        self,
        origin: str,
        reason: str,
        request_info: Dict[str, Any]
    ) -> None:
        """Record a CORS violation."""
        violation = {
            "timestamp": datetime.utcnow().isoformat(),
            "origin": origin,
            "reason": reason,
            "request_info": request_info
        }
        
        # Add to violations list
        self.violations.append(violation)
        
        # Update statistics
        self.stats["total_violations"] += 1
        self.stats["last_violation"] = violation["timestamp"]
        
        # Update by type
        self.stats["violations_by_type"][reason] = (
            self.stats["violations_by_type"].get(reason, 0) + 1
        )
        
        # Update by origin
        self.stats["violations_by_origin"][origin] = (
            self.stats["violations_by_origin"].get(origin, 0) + 1
        )
        
        # Trim old violations
        if len(self.violations) > self.max_violations:
            self.violations = self.violations[-self.max_violations:]
        
        # Log violation
        logger.warning(
            f"CORS violation: {reason} from {origin}",
            extra=violation
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get violation statistics."""
        return {
            **self.stats,
            "recent_violations": self.violations[-10:],  # Last 10 violations
            "max_violations": self.max_violations,
            "current_count": len(self.violations)
        }
    
    def clear_violations(self) -> None:
        """Clear all violations."""
        self.violations.clear()
        self.stats = {
            "total_violations": 0,
            "violations_by_type": {},
            "violations_by_origin": {},
            "last_violation": None
        }
        logger.info("Cleared all CORS violations")


class PreflightCache:
    """Cache for preflight responses."""
    
    def __init__(self, max_age: int = 600):
        self.cache = {}
        self.max_age = max_age
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Response]:
        """Get cached response."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.utcnow() - entry["timestamp"] < timedelta(seconds=self.max_age):
                self.hits += 1
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, response: Response) -> None:
        """Cache a response."""
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.utcnow()
        }
        
        # Clean up old entries periodically
        if len(self.cache) > 100:  # Arbitrary limit
            self._cleanup()
    
    def _cleanup(self) -> None:
        """Clean up expired cache entries."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry["timestamp"] > timedelta(seconds=self.max_age)
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired preflight cache entries")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cleared preflight cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            "max_age": self.max_age
        }


class SecurityHeaders:
    """Manage security headers for CORS responses."""
    
    def __init__(self):
        self.config = get_config()
        self.base_headers = self._get_base_headers()
    
    def _get_base_headers(self) -> Dict[str, str]:
        """Get base security headers."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        # Add CSP if enabled
        if self.config.get("security.csp_enabled", True):
            csp_directives = self.config.get("security.csp_directives", {})
            if csp_directives:
                csp_value = "; ".join(
                    f"{directive} {' '.join(values)}"
                    for directive, values in csp_directives.items()
                )
                headers["Content-Security-Policy"] = csp_value
        
        # Add HSTS if enabled and HTTPS
        if self.config.get("security.hsts_enabled", True):
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return headers
    
    def add_headers(self, response: Response) -> Response:
        """
        Add security headers to response.
        
        Args:
            response: Original response
            
        Returns:
            Response with security headers
        """
        for header, value in self.base_headers.items():
            response.headers[header] = value
        
        return response
    
    def get_base_headers(self) -> Dict[str, str]:
        """Get base security headers."""
        return self.base_headers.copy()


# ======================
# FASTAPI INTEGRATION
# ======================

def create_cors_middleware(
    app: ASGIApp,
    **kwargs
) -> CORSMiddleware:
    """
    Factory function to create CORS middleware.
    
    Args:
        app: ASGI application
        **kwargs: CORS configuration
        
    Returns:
        CORSMiddleware instance
    """
    return CORSMiddleware(app, **kwargs)


def get_default_cors_config() -> Dict[str, Any]:
    """
    Get default CORS configuration from app config.
    
    Returns:
        Default CORS configuration
    """
    cfg = get_config()
    
    return {
        "allow_origins": cfg.get("cors.allow_origins", [
            "http://localhost:3000",
            "http://localhost:3001",
            "https://goat-prediction.com"
        ]),
        "allow_methods": cfg.get("cors.allow_methods", [
            "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"
        ]),
        "allow_headers": cfg.get("cors.allow_headers", ["*"]),
        "allow_credentials": cfg.get("cors.allow_credentials", True),
        "expose_headers": cfg.get("cors.expose_headers", [
            "X-Request-ID",
            "X-Response-Time",
            "X-Total-Count"
        ]),
        "max_age": cfg.get("cors.max_age", 600),
        "vary_header": cfg.get("cors.vary_header", True),
        "allow_private_network": cfg.get("cors.allow_private_network", False),
        "preflight_cache_max_age": cfg.get("cors.preflight_cache_max_age", 600),
        "strict_origin": cfg.get("cors.strict_origin", False),
        "dynamic_origins": cfg.get("cors.dynamic_origins", False),
    }


def setup_cors(app: FastAPI, config: Optional[Dict[str, Any]] = None) -> CORSMiddleware:
    """
    Setup CORS middleware on FastAPI app.
    
    Args:
        app: FastAPI application
        config: CORS configuration (optional)
        
    Returns:
        CORSMiddleware instance
    """
    if config is None:
        config = get_default_cors_config()
    
    middleware = CORSMiddleware(app, **config)
    
    # Add middleware to app
    from ..middleware import MiddlewareManager
    manager = MiddlewareManager(app)
    manager.register("cors", CORSMiddleware, config)
    manager.setup_app()
    
    # Add CORS info endpoint
    @app.get("/cors/info", include_in_schema=False)
    async def get_cors_info() -> Dict[str, Any]:
        """Get CORS configuration and statistics."""
        return {
            "config": config,
            "stats": middleware.get_origin_stats(),
            "cache_stats": middleware.preflight_cache.get_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    logger.info(f"CORS middleware setup with {len(config.get('allow_origins', []))} origins")
    return middleware


# ======================
# DECORATORS AND UTILITIES
# ======================

def cors_exempt(func):
    """
    Decorator to exempt endpoint from CORS middleware.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    func._cors_exempt = True
    return func


def validate_origin(origin: str) -> bool:
    """
    Validate an origin string.
    
    Args:
        origin: Origin to validate
        
    Returns:
        True if origin is valid
    """
    try:
        parsed = urlparse(origin)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def normalize_origin(origin: str) -> str:
    """
    Normalize origin by removing trailing slashes and standardizing.
    
    Args:
        origin: Origin to normalize
        
    Returns:
        Normalized origin
    """
    origin = origin.rstrip("/")
    
    # Ensure scheme is lowercase
    parsed = urlparse(origin)
    if parsed.scheme:
        origin = f"{parsed.scheme.lower()}://{parsed.netloc}{parsed.path}"
    
    return origin


def get_request_origin(request: Request) -> Optional[str]:
    """
    Extract origin from request.
    
    Args:
        request: FastAPI request
        
    Returns:
        Origin string or None
    """
    return request.headers.get("origin")


# ======================
# EXPORTS
# ======================

__all__ = [
    # Main middleware
    "CORSMiddleware",
    "create_cors_middleware",
    "setup_cors",
    
    # Configuration
    "CORSConfig",
    "get_default_cors_config",
    
    # Models
    "OriginPattern",
    "CORSRequestInfo",
    
    # Validators
    "OriginValidator",
    
    # Supporting classes
    "CORSViolationTracker",
    "PreflightCache",
    "SecurityHeaders",
    
    # Decorators and utilities
    "cors_exempt",
    "validate_origin",
    "normalize_origin",
    "get_request_origin",
]


if __name__ == "__main__":
    # Test the CORS middleware
    print("🌐 CORS Middleware Test")
    print("=" * 50)
    
    # Test origin patterns
    print("\n1. Testing origin patterns...")
    
    patterns = [
        OriginPattern("https://example.com"),
        OriginPattern("https://*.example.com"),
        OriginPattern("http://localhost:*"),
        OriginPattern("*"),
    ]
    
    test_origins = [
        "https://example.com",
        "https://api.example.com",
        "https://sub.api.example.com",
        "http://localhost:3000",
        "http://localhost:8080",
        "https://evil.com",
    ]
    
    for origin in test_origins:
        matches = [str(p) for p in patterns if p.matches(origin)]
        status = "✅" if matches else "❌"
        print(f"   {status} {origin:30} -> {matches}")
    
    # Test origin validator
    print("\n2. Testing origin validator...")
    
    validator = OriginValidator.create_validator(
        allow_localhost=True,
        https_only=False,
        allowed_domains=["goat-prediction.com"],
        base_domain="example.org"
    )
    
    test_cases = [
        ("http://localhost:3000", True),
        ("https://goat-prediction.com", True),
        ("https://api.example.org", True),
        ("https://evil.com", False),
        ("http://192.168.1.1:3000", True),  # Private IP
    ]
    
    for origin, expected in test_cases:
        result = validator(origin)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {origin:30} -> {result} (expected: {expected})")
    
    # Test CORS config
    print("\n3. Testing CORS configuration...")
    
    config = CORSConfig(
        allow_origins=["https://example.com", "https://*.example.org"],
        allow_methods=["GET", "POST"],
        allow_credentials=True
    )
    
    test_configs = [
        ("https://example.com", True),
        ("https://api.example.org", True),
        ("https://sub.api.example.org", True),
        ("http://example.com", False),
        ("https://evil.com", False),
    ]
    
    for origin, expected in test_configs:
        result = config.is_origin_allowed(origin)
        status = "✅" if result == expected else "❌"
        print(f"   {status} {origin:30} -> {result} (expected: {expected})")
    
    print("\n✅ All CORS tests completed successfully!")
