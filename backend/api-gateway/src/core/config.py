"""
Core configuration management for GOAT Prediction Ultimate.
Centralized configuration system with validation, caching, and dynamic updates.
"""

import os
import json
import hashlib
import threading
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field, asdict
from functools import lru_cache
import yaml

import redis
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.tools import parse_obj_as

# Local imports
from ..config.settings import settings
from ..core.exceptions.config_errors import ConfigError, ValidationError


class Environment(str, Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigSource(str, Enum):
    """Configuration sources."""
    ENVIRONMENT = "environment"
    DATABASE = "database"
    FILE = "file"
    API = "api"
    DEFAULT = "default"


class ConfigUpdateMode(str, Enum):
    """Configuration update modes."""
    IMMEDIATE = "immediate"
    LAZY = "lazy"
    SCHEDULED = "scheduled"


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource
    last_updated: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    description: Optional[str] = None
    data_type: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    is_sensitive: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        if self.is_sensitive and isinstance(self.value, str):
            data["value"] = "***MASKED***"
        return data
    
    def validate(self) -> bool:
        """Validate configuration value."""
        if not self.validation_rules:
            return True
        
        rules = self.validation_rules
        
        # Type validation
        if "type" in rules:
            expected_type = rules["type"]
            if not isinstance(self.value, eval(expected_type)):
                raise ValidationError(
                    f"Config {self.key}: expected type {expected_type}, got {type(self.value)}"
                )
        
        # Range validation for numbers
        if isinstance(self.value, (int, float)):
            if "min" in rules and self.value < rules["min"]:
                raise ValidationError(
                    f"Config {self.key}: value {self.value} below minimum {rules['min']}"
                )
            if "max" in rules and self.value > rules["max"]:
                raise ValidationError(
                    f"Config {self.key}: value {self.value} above maximum {rules['max']}"
                )
        
        # Length validation for strings
        if isinstance(self.value, str):
            if "min_length" in rules and len(self.value) < rules["min_length"]:
                raise ValidationError(
                    f"Config {self.key}: length {len(self.value)} below minimum {rules['min_length']}"
                )
            if "max_length" in rules and len(self.value) > rules["max_length"]:
                raise ValidationError(
                    f"Config {self.key}: length {len(self.value)} above maximum {rules['max_length']}"
                )
        
        # Enum validation
        if "allowed_values" in rules:
            if self.value not in rules["allowed_values"]:
                raise ValidationError(
                    f"Config {self.key}: value {self.value} not in allowed values {rules['allowed_values']}"
                )
        
        # Regex validation
        if "regex" in rules and isinstance(self.value, str):
            import re
            if not re.match(rules["regex"], self.value):
                raise ValidationError(
                    f"Config {self.key}: value {self.value} doesn't match regex {rules['regex']}"
                )
        
        return True


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    host: str = Field(..., description="Database host")
    port: int = Field(5432, description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Max overflow connections")
    pool_timeout: int = Field(30, description="Connection pool timeout")
    echo: bool = Field(False, description="SQL echo")
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        extra = "forbid"


class RedisConfig(BaseModel):
    """Redis configuration model."""
    host: str = Field("localhost", description="Redis host")
    port: int = Field(6379, description="Redis port")
    password: Optional[str] = Field(None, description="Redis password")
    db: int = Field(0, description="Redis database number")
    max_connections: int = Field(50, description="Max Redis connections")
    decode_responses: bool = Field(True, description="Decode responses")
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"
    
    class Config:
        extra = "forbid"


class APIConfig(BaseModel):
    """API configuration model."""
    base_url: str = Field(..., description="API base URL")
    timeout: int = Field(30, description="Request timeout in seconds")
    retry_attempts: int = Field(3, description="Number of retry attempts")
    retry_delay: int = Field(1, description="Retry delay in seconds")
    rate_limit: int = Field(100, description="Requests per minute")
    api_key: Optional[str] = Field(None, description="API key")
    
    class Config:
        extra = "forbid"


class CacheConfig(BaseModel):
    """Cache configuration model."""
    enabled: bool = Field(True, description="Cache enabled")
    default_ttl: int = Field(300, description="Default TTL in seconds")
    max_size: int = Field(1000, description="Max cache entries")
    cleanup_interval: int = Field(60, description="Cleanup interval in seconds")
    
    # TTLs for different data types
    ttl_predictions: int = Field(60, description="Predictions cache TTL")
    ttl_odds: int = Field(30, description="Odds cache TTL")
    ttl_statistics: int = Field(3600, description="Statistics cache TTL")
    ttl_users: int = Field(300, description="Users cache TTL")
    
    class Config:
        extra = "forbid"


class SecurityConfig(BaseModel):
    """Security configuration model."""
    secret_key: str = Field(..., description="Secret key for encryption")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiry")
    refresh_token_expire_days: int = Field(7, description="Refresh token expiry")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, description="Rate limiting enabled")
    rate_limit_default: str = Field("100/minute", description="Default rate limit")
    rate_limit_premium: str = Field("500/minute", description="Premium rate limit")
    rate_limit_admin: str = Field("1000/minute", description="Admin rate limit")
    
    # CORS
    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # Security headers
    security_headers_enabled: bool = Field(True, description="Security headers enabled")
    hsts_enabled: bool = Field(True, description="HSTS enabled")
    csp_enabled: bool = Field(True, description="Content Security Policy enabled")
    
    class Config:
        extra = "forbid"


class LoggingConfig(BaseModel):
    """Logging configuration model."""
    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file_enabled: bool = Field(True, description="File logging enabled")
    file_path: str = Field("logs/app.log", description="Log file path")
    file_max_size: int = Field(10485760, description="Max log file size (10MB)")
    file_backup_count: int = Field(5, description="Number of backup files")
    
    # External services
    sentry_enabled: bool = Field(False, description="Sentry integration enabled")
    sentry_dsn: Optional[str] = Field(None, description="Sentry DSN")
    logstash_enabled: bool = Field(False, description="Logstash integration enabled")
    logstash_host: Optional[str] = Field(None, description="Logstash host")
    logstash_port: Optional[int] = Field(None, description="Logstash port")
    
    class Config:
        extra = "forbid"


class MonitoringConfig(BaseModel):
    """Monitoring configuration model."""
    prometheus_enabled: bool = Field(True, description="Prometheus enabled")
    prometheus_port: int = Field(9090, description="Prometheus port")
    
    health_check_enabled: bool = Field(True, description="Health checks enabled")
    health_check_interval: int = Field(60, description="Health check interval")
    
    metrics_enabled: bool = Field(True, description="Metrics collection enabled")
    metrics_interval: int = Field(30, description="Metrics collection interval")
    
    # Alerting
    alerting_enabled: bool = Field(False, description="Alerting enabled")
    alert_email: Optional[str] = Field(None, description="Alert email")
    alert_slack_webhook: Optional[str] = Field(None, description="Slack webhook")
    
    class Config:
        extra = "forbid"


class SportsConfig(BaseModel):
    """Sports configuration model."""
    name: str = Field(..., description="Sport name")
    enabled: bool = Field(True, description="Sport enabled")
    markets: List[str] = Field(..., description="Available markets")
    refresh_interval: int = Field(60, description="Data refresh interval")
    api_endpoints: List[str] = Field(..., description="API endpoints")
    
    class Config:
        extra = "forbid"


class SubscriptionPlan(BaseModel):
    """Subscription plan configuration."""
    name: str = Field(..., description="Plan name")
    price: float = Field(..., description="Monthly price")
    currency: str = Field("USD", description="Currency")
    predictions_per_day: int = Field(..., description="Daily prediction limit")
    features: List[str] = Field(..., description="Included features")
    rate_limit: str = Field(..., description="Rate limit")
    
    class Config:
        extra = "forbid"


class FeatureFlag(BaseModel):
    """Feature flag configuration."""
    name: str = Field(..., description="Feature name")
    enabled: bool = Field(False, description="Feature enabled")
    description: str = Field("", description="Feature description")
    rollout_percentage: float = Field(100.0, description="Rollout percentage")
    target_users: Optional[List[str]] = Field(None, description="Target users")
    
    class Config:
        extra = "forbid"


class ConfigManager:
    """
    Centralized configuration manager with caching, validation, and dynamic updates.
    """
    
    def __init__(self, env: Environment = None):
        """
        Initialize configuration manager.
        
        Args:
            env: Environment (defaults to settings.ENVIRONMENT)
        """
        self.env = env or Environment(settings.ENVIRONMENT)
        self._config_cache: Dict[str, ConfigValue] = {}
        self._config_validation_rules: Dict[str, Dict] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._redis_client: Optional[redis.Redis] = None
        self._config_hash: Optional[str] = None
        
        # Load configuration
        self._load_default_config()
        self._load_environment_config()
        self._load_file_config()
        
        # Initialize components
        self._init_validation_rules()
        self._init_redis()
        
        # Start background tasks
        self._start_background_tasks()
    
    def _load_default_config(self) -> None:
        """Load default configuration."""
        default_config = {
            # Database
            "database.host": ConfigValue(
                key="database.host",
                value="localhost",
                source=ConfigSource.DEFAULT,
                description="Database host"
            ),
            "database.port": ConfigValue(
                key="database.port",
                value=5432,
                source=ConfigSource.DEFAULT,
                description="Database port"
            ),
            
            # Redis
            "redis.host": ConfigValue(
                key="redis.host",
                value="localhost",
                source=ConfigSource.DEFAULT,
                description="Redis host"
            ),
            "redis.port": ConfigValue(
                key="redis.port",
                value=6379,
                source=ConfigSource.DEFAULT,
                description="Redis port"
            ),
            
            # API Gateway
            "api_gateway.host": ConfigValue(
                key="api_gateway.host",
                value="0.0.0.0",
                source=ConfigSource.DEFAULT,
                description="API Gateway host"
            ),
            "api_gateway.port": ConfigValue(
                key="api_gateway.port",
                value=8000,
                source=ConfigSource.DEFAULT,
                description="API Gateway port"
            ),
            
            # Security
            "security.rate_limit_enabled": ConfigValue(
                key="security.rate_limit_enabled",
                value=True,
                source=ConfigSource.DEFAULT,
                description="Rate limiting enabled"
            ),
            
            # Logging
            "logging.level": ConfigValue(
                key="logging.level",
                value="INFO",
                source=ConfigSource.DEFAULT,
                description="Logging level"
            ),
        }
        
        with self._lock:
            self._config_cache.update(default_config)
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            # Database
            "POSTGRES_SERVER": "database.host",
            "POSTGRES_PORT": "database.port",
            "POSTGRES_USER": "database.username",
            "POSTGRES_PASSWORD": "database.password",
            "POSTGRES_DB": "database.database",
            
            # Redis
            "REDIS_HOST": "redis.host",
            "REDIS_PORT": "redis.port",
            "REDIS_PASSWORD": "redis.password",
            "REDIS_DB": "redis.db",
            
            # Security
            "SECRET_KEY": "security.secret_key",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "security.access_token_expire_minutes",
            
            # Logging
            "LOG_LEVEL": "logging.level",
            
            # External APIs
            "STATSBOMB_API_KEY": "apis.statsbomb.api_key",
            "OPTA_API_KEY": "apis.opta.api_key",
            "SPORTRADAR_API_KEY": "apis.sportradar.api_key",
            
            # Stripe
            "STRIPE_SECRET_KEY": "payment.stripe.secret_key",
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Try to convert to appropriate type
                converted_value = self._convert_value(value)
                
                config_value = ConfigValue(
                    key=config_key,
                    value=converted_value,
                    source=ConfigSource.ENVIRONMENT,
                    description=f"From environment variable {env_var}"
                )
                
                with self._lock:
                    self._config_cache[config_key] = config_value
    
    def _load_file_config(self) -> None:
        """Load configuration from YAML/JSON files."""
        config_files = [
            Path("config/config.yaml"),
            Path("config/config.json"),
            Path(f"config/config_{self.env.value}.yaml"),
            Path(f"config/config_{self.env.value}.json"),
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    if config_file.suffix == ".yaml":
                        with open(config_file, 'r') as f:
                            config_data = yaml.safe_load(f)
                    else:  # .json
                        with open(config_file, 'r') as f:
                            config_data = json.load(f)
                    
                    self._load_dict_config(config_data, ConfigSource.FILE, str(config_file))
                    print(f"Loaded configuration from {config_file}")
                except Exception as e:
                    print(f"Error loading config from {config_file}: {e}")
    
    def _load_dict_config(self, config_data: Dict, source: ConfigSource, source_name: str) -> None:
        """Load configuration from dictionary."""
        
        def _flatten_dict(d: Dict, parent_key: str = '') -> Dict[str, Any]:
            """Flatten nested dictionary."""
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(_flatten_dict(v, new_key).items())
                else:
                    items.append((new_key, v))
            return dict(items)
        
        flattened = _flatten_dict(config_data)
        
        for key, value in flattened:
            config_value = ConfigValue(
                key=key,
                value=value,
                source=source,
                description=f"From {source_name}"
            )
            
            with self._lock:
                self._config_cache[key] = config_value
    
    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate type.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted value
        """
        # Boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        
        # Integer
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # List
        if value.startswith('[') and value.endswith(']'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Dict
        if value.startswith('{') and value.endswith('}'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # String (default)
        return value
    
    def _init_validation_rules(self) -> None:
        """Initialize validation rules for configuration."""
        self._config_validation_rules = {
            "database.port": {
                "type": "int",
                "min": 1,
                "max": 65535
            },
            "database.pool_size": {
                "type": "int",
                "min": 1,
                "max": 100
            },
            "redis.port": {
                "type": "int",
                "min": 1,
                "max": 65535
            },
            "api_gateway.port": {
                "type": "int",
                "min": 1,
                "max": 65535
            },
            "security.access_token_expire_minutes": {
                "type": "int",
                "min": 1,
                "max": 1440  # 24 hours
            },
            "logging.level": {
                "type": "str",
                "allowed_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            }
        }
    
    def _init_redis(self) -> None:
        """Initialize Redis client for configuration sharing."""
        try:
            if self.env != Environment.TESTING:
                redis_config = self.get_redis_config()
                self._redis_client = redis.Redis(
                    host=redis_config.host,
                    port=redis_config.port,
                    password=redis_config.password,
                    db=redis_config.db,
                    decode_responses=redis_config.decode_responses,
                    max_connections=redis_config.max_connections
                )
                # Test connection
                self._redis_client.ping()
                print("Redis client initialized for configuration sharing")
        except Exception as e:
            print(f"Redis initialization failed: {e}. Continuing without Redis.")
            self._redis_client = None
    
    def _start_background_tasks(self) -> None:
        """Start background configuration tasks."""
        if self.env != Environment.TESTING:
            # Start configuration sync in background
            import threading
            sync_thread = threading.Thread(
                target=self._background_sync,
                daemon=True,
                name="config-sync"
            )
            sync_thread.start()
            
            # Start configuration validation
            validation_thread = threading.Thread(
                target=self._background_validation,
                daemon=True,
                name="config-validation"
            )
            validation_thread.start()
    
    def _background_sync(self) -> None:
        """Background task for configuration synchronization."""
        import time
        
        while True:
            try:
                self._sync_with_redis()
                self._calculate_config_hash()
            except Exception as e:
                print(f"Configuration sync error: {e}")
            
            time.sleep(60)  # Sync every minute
    
    def _background_validation(self) -> None:
        """Background task for configuration validation."""
        import time
        
        while True:
            try:
                self.validate_all()
            except Exception as e:
                print(f"Configuration validation error: {e}")
            
            time.sleep(300)  # Validate every 5 minutes
    
    def _sync_with_redis(self) -> None:
        """Sync configuration with Redis."""
        if not self._redis_client:
            return
        
        try:
            # Get current configuration hash
            current_hash = self._calculate_config_hash()
            
            # Check if configuration changed in Redis
            redis_hash = self._redis_client.get("config:hash")
            
            if redis_hash and redis_hash != current_hash:
                # Configuration changed, load from Redis
                config_data = self._redis_client.get("config:data")
                if config_data:
                    config_dict = json.loads(config_data)
                    self._load_dict_config(config_dict, ConfigSource.DATABASE, "redis")
                    print("Configuration updated from Redis")
            
            # Publish current configuration if changed
            if not redis_hash or redis_hash != current_hash:
                config_data = json.dumps(self.get_all())
                self._redis_client.set("config:data", config_data)
                self._redis_client.set("config:hash", current_hash)
                self._redis_client.publish("config:updates", "updated")
        
        except Exception as e:
            print(f"Redis sync error: {e}")
    
    def _calculate_config_hash(self) -> str:
        """Calculate hash of current configuration."""
        config_dict = {}
        with self._lock:
            for key, config_value in self._config_cache.items():
                config_dict[key] = config_value.value
        
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()
    
    # ======================
    # PUBLIC API
    # ======================
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        with self._lock:
            config_value = self._config_cache.get(key)
        
        if config_value:
            return config_value.value
        
        # Try to get from settings
        try:
            # Convert key to attribute path
            attr_path = key.replace('.', '_')
            if hasattr(settings, attr_path):
                return getattr(settings, attr_path)
        except AttributeError:
            pass
        
        return default
    
    def get_config_value(self, key: str) -> Optional[ConfigValue]:
        """
        Get configuration value with metadata.
        
        Args:
            key: Configuration key
            
        Returns:
            ConfigValue object or None
        """
        with self._lock:
            return self._config_cache.get(key)
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.API,
            description: str = None, validate: bool = True) -> ConfigValue:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            source: Configuration source
            description: Description of the configuration
            validate: Whether to validate the value
            
        Returns:
            Updated ConfigValue object
            
        Raises:
            ValidationError: If validation fails
        """
        # Get existing config value
        existing = self.get_config_value(key)
        
        # Create new config value
        config_value = ConfigValue(
            key=key,
            value=value,
            source=source,
            version=(existing.version + 1) if existing else 1,
            description=description or (existing.description if existing else None),
            validation_rules=self._config_validation_rules.get(key),
            is_sensitive=self._is_sensitive_key(key)
        )
        
        # Validate if requested
        if validate:
            config_value.validate()
        
        # Update cache
        with self._lock:
            self._config_cache[key] = config_value
        
        # Notify callbacks
        self._notify_callbacks(key, config_value)
        
        # Sync with Redis if enabled
        if self._redis_client:
            try:
                self._redis_client.publish(f"config:update:{key}", json.dumps(config_value.to_dict()))
            except Exception:
                pass
        
        return config_value
    
    def get_all(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Args:
            include_sensitive: Whether to include sensitive values
            
        Returns:
            Dictionary of all configuration values
        """
        with self._lock:
            result = {}
            for key, config_value in self._config_cache.items():
                if config_value.is_sensitive and not include_sensitive:
                    result[key] = "***MASKED***"
                else:
                    result[key] = config_value.value
            return result
    
    def get_all_with_metadata(self) -> Dict[str, Dict]:
        """
        Get all configuration values with metadata.
        
        Returns:
            Dictionary of configuration metadata
        """
        with self._lock:
            return {
                key: config_value.to_dict()
                for key, config_value in self._config_cache.items()
            }
    
    def validate_all(self) -> List[str]:
        """
        Validate all configuration values.
        
        Returns:
            List of validation errors
        """
        errors = []
        with self._lock:
            for key, config_value in self._config_cache.items():
                try:
                    config_value.validate()
                except ValidationError as e:
                    errors.append(str(e))
        
        return errors
    
    def register_callback(self, key: str, callback: Callable[[str, ConfigValue], None]) -> None:
        """
        Register callback for configuration changes.
        
        Args:
            key: Configuration key to watch
            callback: Callback function (key, config_value)
        """
        with self._lock:
            if key not in self._callbacks:
                self._callbacks[key] = []
            self._callbacks[key].append(callback)
    
    def _notify_callbacks(self, key: str, config_value: ConfigValue) -> None:
        """Notify registered callbacks of configuration change."""
        callbacks = self._callbacks.get(key, [])
        for callback in callbacks:
            try:
                callback(key, config_value)
            except Exception as e:
                print(f"Callback error for {key}: {e}")
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if configuration key contains sensitive data."""
        sensitive_patterns = [
            "password", "secret", "key", "token", "auth",
            "credential", "private", "salt", "jwt"
        ]
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)
    
    # ======================
    # CONVENIENCE METHODS
    # ======================
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration as Pydantic model."""
        config_dict = {
            "host": self.get("database.host", "localhost"),
            "port": self.get("database.port", 5432),
            "database": self.get("database.database", "goat_prediction"),
            "username": self.get("database.username", "goat_user"),
            "password": self.get("database.password", "goat_password"),
            "pool_size": self.get("database.pool_size", 10),
            "max_overflow": self.get("database.max_overflow", 20),
            "pool_timeout": self.get("database.pool_timeout", 30),
            "echo": self.get("database.echo", False),
        }
        return DatabaseConfig(**config_dict)
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration as Pydantic model."""
        config_dict = {
            "host": self.get("redis.host", "localhost"),
            "port": self.get("redis.port", 6379),
            "password": self.get("redis.password"),
            "db": self.get("redis.db", 0),
            "max_connections": self.get("redis.max_connections", 50),
            "decode_responses": self.get("redis.decode_responses", True),
        }
        return RedisConfig(**config_dict)
    
    def get_cache_config(self) -> CacheConfig:
        """Get cache configuration as Pydantic model."""
        config_dict = {
            "enabled": self.get("cache.enabled", True),
            "default_ttl": self.get("cache.default_ttl", 300),
            "max_size": self.get("cache.max_size", 1000),
            "cleanup_interval": self.get("cache.cleanup_interval", 60),
            "ttl_predictions": self.get("cache.ttl_predictions", 60),
            "ttl_odds": self.get("cache.ttl_odds", 30),
            "ttl_statistics": self.get("cache.ttl_statistics", 3600),
            "ttl_users": self.get("cache.ttl_users", 300),
        }
        return CacheConfig(**config_dict)
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration as Pydantic model."""
        config_dict = {
            "secret_key": self.get("security.secret_key", settings.SECRET_KEY),
            "algorithm": self.get("security.algorithm", "HS256"),
            "access_token_expire_minutes": self.get(
                "security.access_token_expire_minutes",
                settings.ACCESS_TOKEN_EXPIRE_MINUTES
            ),
            "refresh_token_expire_days": self.get(
                "security.refresh_token_expire_days",
                settings.REFRESH_TOKEN_EXPIRE_DAYS
            ),
            "rate_limit_enabled": self.get("security.rate_limit_enabled", True),
            "rate_limit_default": self.get("security.rate_limit_default", "100/minute"),
            "rate_limit_premium": self.get("security.rate_limit_premium", "500/minute"),
            "rate_limit_admin": self.get("security.rate_limit_admin", "1000/minute"),
            "cors_origins": self.get("security.cors_origins", settings.CORS_ORIGINS),
            "security_headers_enabled": self.get("security.security_headers_enabled", True),
            "hsts_enabled": self.get("security.hsts_enabled", True),
            "csp_enabled": self.get("security.csp_enabled", True),
        }
        return SecurityConfig(**config_dict)
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration as Pydantic model."""
        config_dict = {
            "level": self.get("logging.level", settings.LOG_LEVEL),
            "format": self.get("logging.format", settings.LOG_FORMAT),
            "file_enabled": self.get("logging.file_enabled", True),
            "file_path": self.get("logging.file_path", "logs/app.log"),
            "file_max_size": self.get("logging.file_max_size", 10485760),
            "file_backup_count": self.get("logging.file_backup_count", 5),
            "sentry_enabled": self.get("logging.sentry_enabled", False),
            "sentry_dsn": self.get("logging.sentry_dsn"),
            "logstash_enabled": self.get("logging.logstash_enabled", False),
            "logstash_host": self.get("logging.logstash_host"),
            "logstash_port": self.get("logging.logstash_port"),
        }
        return LoggingConfig(**config_dict)
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration as Pydantic model."""
        config_dict = {
            "prometheus_enabled": self.get("monitoring.prometheus_enabled", True),
            "prometheus_port": self.get("monitoring.prometheus_port", 9090),
            "health_check_enabled": self.get("monitoring.health_check_enabled", True),
            "health_check_interval": self.get("monitoring.health_check_interval", 60),
            "metrics_enabled": self.get("monitoring.metrics_enabled", True),
            "metrics_interval": self.get("monitoring.metrics_interval", 30),
            "alerting_enabled": self.get("monitoring.alerting_enabled", False),
            "alert_email": self.get("monitoring.alert_email"),
            "alert_slack_webhook": self.get("monitoring.alert_slack_webhook"),
        }
        return MonitoringConfig(**config_dict)
    
    def get_sports_config(self, sport: str) -> Optional[SportsConfig]:
        """Get sports configuration as Pydantic model."""
        config_key = f"sports.{sport}"
        config_dict = self.get(config_key)
        
        if not config_dict:
            # Try to get from settings
            sport_config = settings.get_sport_config(sport)
            if sport_config:
                return SportsConfig(**sport_config)
            return None
        
        if isinstance(config_dict, dict):
            return SportsConfig(**config_dict)
        
        return None
    
    def get_feature_flag(self, name: str) -> FeatureFlag:
        """Get feature flag configuration."""
        config_key = f"features.{name}"
        config_dict = self.get(config_key, {})
        
        if isinstance(config_dict, dict):
            return FeatureFlag(
                name=name,
                enabled=config_dict.get("enabled", False),
                description=config_dict.get("description", ""),
                rollout_percentage=config_dict.get("rollout_percentage", 100.0),
                target_users=config_dict.get("target_users")
            )
        
        # Try to get from settings
        enabled = settings.get_feature_flag(name)
        return FeatureFlag(
            name=name,
            enabled=enabled,
            description=f"Feature flag for {name}"
        )
    
    def get_subscription_plan(self, plan_name: str) -> Optional[SubscriptionPlan]:
        """Get subscription plan configuration."""
        config_key = f"subscriptions.{plan_name}"
        config_dict = self.get(config_key)
        
        if not config_dict:
            # Try to get from settings
            plan_config = settings.get_subscription_plan(plan_name)
            if plan_config:
                return SubscriptionPlan(**plan_config)
            return None
        
        if isinstance(config_dict, dict):
            return SubscriptionPlan(**config_dict)
        
        return None
    
    def is_feature_enabled(self, name: str, user_id: Optional[str] = None) -> bool:
        """
        Check if a feature is enabled for a user.
        
        Args:
            name: Feature name
            user_id: Optional user ID for targeted rollouts
            
        Returns:
            True if feature is enabled for the user
        """
        feature_flag = self.get_feature_flag(name)
        
        if not feature_flag.enabled:
            return False
        
        # Check rollout percentage
        import random
        if random.random() * 100 > feature_flag.rollout_percentage:
            return False
        
        # Check targeted users
        if feature_flag.target_users and user_id:
            return user_id in feature_flag.target_users
        
        return True
    
    # ======================
    # STATIC METHODS
    # ======================
    
    @staticmethod
    @lru_cache(maxsize=1)
    def get_instance(env: Environment = None) -> 'ConfigManager':
        """
        Get singleton instance of ConfigManager.
        
        Args:
            env: Environment (defaults to settings.ENVIRONMENT)
            
        Returns:
            ConfigManager instance
        """
        return ConfigManager(env)
    
    @staticmethod
    def reload_instance() -> None:
        """Reload the singleton instance."""
        ConfigManager.get_instance.cache_clear()


# Global configuration instance
config = ConfigManager.get_instance()


def get_config() -> ConfigManager:
    """Get global configuration instance."""
    return config


__all__ = [
    "ConfigManager",
    "ConfigValue",
    "ConfigSource",
    "Environment",
    "ConfigUpdateMode",
    "DatabaseConfig",
    "RedisConfig",
    "APIConfig",
    "CacheConfig",
    "SecurityConfig",
    "LoggingConfig",
    "MonitoringConfig",
    "SportsConfig",
    "SubscriptionPlan",
    "FeatureFlag",
    "config",
    "get_config",
]


if __name__ == "__main__":
    # Example usage
    cfg = get_config()
    
    # Get configuration values
    db_host = cfg.get("database.host")
    redis_port = cfg.get("redis.port")
    
    print(f"Database Host: {db_host}")
    print(f"Redis Port: {redis_port}")
    
    # Get Pydantic models
    db_config = cfg.get_database_config()
    print(f"Database URL: {db_config.url}")
    
    # Validate all configurations
    errors = cfg.validate_all()
    if errors:
        print(f"Configuration errors: {errors}")
    else:
        print("All configurations validated successfully!")
    
    # Get all configuration with metadata
    all_config = cfg.get_all_with_metadata()
    print(f"Total configurations: {len(all_config)}")
