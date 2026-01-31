"""
Test Settings Configuration for API Gateway
Provides configuration overrides and settings specifically for testing environment
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class TestDatabaseSettings:
    """Test database configuration"""
    
    # Use SQLite in-memory for tests by default
    driver: str = "sqlite"
    host: str = ":memory:"
    port: int = 0
    database: str = "test_db"
    username: str = "test_user"
    password: str = "test_password"
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    
    # Alternative: Use PostgreSQL test database
    use_postgres: bool = False
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "goat_prediction_test"
    postgres_username: str = "postgres"
    postgres_password: str = "postgres"
    
    @property
    def connection_string(self) -> str:
        """Get database connection string for tests"""
        if self.use_postgres:
            return (
                f"postgresql://{self.postgres_username}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
        return f"sqlite:///{self.host}"
    
    @property
    def async_connection_string(self) -> str:
        """Get async database connection string for tests"""
        if self.use_postgres:
            return (
                f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
            )
        return f"sqlite+aiosqlite:///{self.host}"


@dataclass
class TestRedisSettings:
    """Test Redis configuration"""
    
    host: str = "localhost"
    port: int = 6379
    database: int = 15  # Use DB 15 for tests
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    max_connections: int = 10
    
    # Use fakeredis for tests
    use_fake_redis: bool = True
    
    @property
    def connection_url(self) -> str:
        """Get Redis connection URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.database}"


@dataclass
class TestAPISettings:
    """Test API configuration"""
    
    host: str = "127.0.0.1"
    port: int = 8001  # Different port for tests
    debug: bool = True
    testing: bool = True
    reload: bool = False
    workers: int = 1
    
    # CORS settings for tests
    allow_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    allow_credentials: bool = True
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting (disabled for tests)
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 1000000  # Very high limit
    rate_limit_period: int = 60


@dataclass
class TestAuthSettings:
    """Test authentication configuration"""
    
    secret_key: str = "test-secret-key-do-not-use-in-production-12345"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Test users
    test_user_email: str = "test@goat-prediction.com"
    test_user_password: str = "TestPassword123!"
    test_admin_email: str = "admin@goat-prediction.com"
    test_admin_password: str = "AdminPassword123!"
    
    # Disable password hashing for faster tests
    skip_password_hashing: bool = True
    
    # JWT settings
    jwt_issuer: str = "goat-prediction-test"
    jwt_audience: str = "goat-prediction-api-test"


@dataclass
class TestLoggingSettings:
    """Test logging configuration"""
    
    level: str = "DEBUG"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Disable file logging in tests
    enable_file_logging: bool = False
    
    # Suppress noisy loggers
    suppress_loggers: List[str] = field(default_factory=lambda: [
        "urllib3",
        "httpx",
        "asyncio",
        "sqlalchemy.engine"
    ])


@dataclass
class TestCacheSettings:
    """Test cache configuration"""
    
    enabled: bool = False  # Disable caching in tests by default
    backend: str = "memory"
    ttl: int = 60
    max_size: int = 100


@dataclass
class TestExternalAPISettings:
    """Test external API configuration"""
    
    # Use mock APIs for tests
    use_mocks: bool = True
    
    # Test API keys (fake)
    statsbomb_api_key: str = "test-statsbomb-key"
    opta_api_key: str = "test-opta-key"
    sportradar_api_key: str = "test-sportradar-key"
    
    # Timeouts
    request_timeout: int = 5
    max_retries: int = 1


@dataclass
class TestFileStorageSettings:
    """Test file storage configuration"""
    
    # Use temporary directory for tests
    base_path: str = field(default_factory=lambda: tempfile.mkdtemp(prefix="goat_test_"))
    upload_path: str = field(default_factory=lambda: os.path.join(tempfile.gettempdir(), "uploads"))
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = field(default_factory=lambda: [".jpg", ".png", ".pdf", ".csv"])


@dataclass
class TestMLSettings:
    """Test ML/AI configuration"""
    
    # Use lightweight models for tests
    model_path: str = field(default_factory=lambda: tempfile.mkdtemp(prefix="goat_models_"))
    use_gpu: bool = False
    batch_size: int = 8
    
    # Mock predictions
    use_mock_predictions: bool = True
    mock_prediction_accuracy: float = 0.75


class TestSettings:
    """Main test settings class"""
    
    def __init__(self):
        """Initialize test settings"""
        self.environment: str = "test"
        self.app_name: str = "GOAT Prediction API - Test"
        self.version: str = "1.0.0-test"
        
        # Component settings
        self.database = TestDatabaseSettings()
        self.redis = TestRedisSettings()
        self.api = TestAPISettings()
        self.auth = TestAuthSettings()
        self.logging = TestLoggingSettings()
        self.cache = TestCacheSettings()
        self.external_apis = TestExternalAPISettings()
        self.file_storage = TestFileStorageSettings()
        self.ml = TestMLSettings()
        
        # Test-specific settings
        self.cleanup_after_tests: bool = True
        self.parallel_tests: bool = False
        self.test_data_path: str = "tests/fixtures"
        
        # Override with environment variables if present
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """Load settings from environment variables"""
        # Database
        if os.getenv("TEST_USE_POSTGRES"):
            self.database.use_postgres = os.getenv("TEST_USE_POSTGRES").lower() == "true"
        
        if os.getenv("TEST_POSTGRES_HOST"):
            self.database.postgres_host = os.getenv("TEST_POSTGRES_HOST")
        
        if os.getenv("TEST_POSTGRES_DATABASE"):
            self.database.postgres_database = os.getenv("TEST_POSTGRES_DATABASE")
        
        # Redis
        if os.getenv("TEST_USE_FAKE_REDIS"):
            self.redis.use_fake_redis = os.getenv("TEST_USE_FAKE_REDIS").lower() == "true"
        
        if os.getenv("TEST_REDIS_HOST"):
            self.redis.host = os.getenv("TEST_REDIS_HOST")
        
        # API
        if os.getenv("TEST_API_PORT"):
            self.api.port = int(os.getenv("TEST_API_PORT"))
        
        # Logging
        if os.getenv("TEST_LOG_LEVEL"):
            self.logging.level = os.getenv("TEST_LOG_LEVEL")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            "environment": self.environment,
            "app_name": self.app_name,
            "version": self.version,
            "database": self.database.__dict__,
            "redis": self.redis.__dict__,
            "api": self.api.__dict__,
            "auth": self.auth.__dict__,
            "logging": self.logging.__dict__,
            "cache": self.cache.__dict__,
            "external_apis": self.external_apis.__dict__,
            "file_storage": self.file_storage.__dict__,
            "ml": self.ml.__dict__,
        }
    
    def cleanup(self) -> None:
        """Cleanup test resources"""
        if self.cleanup_after_tests:
            # Clean up temporary directories
            import shutil
            
            try:
                if Path(self.file_storage.base_path).exists():
                    shutil.rmtree(self.file_storage.base_path)
                    logger.debug(f"Cleaned up test storage: {self.file_storage.base_path}")
            except Exception as e:
                logger.warning(f"Error cleaning up test storage: {e}")
            
            try:
                if Path(self.ml.model_path).exists():
                    shutil.rmtree(self.ml.model_path)
                    logger.debug(f"Cleaned up test models: {self.ml.model_path}")
            except Exception as e:
                logger.warning(f"Error cleaning up test models: {e}")
    
    def reset(self) -> None:
        """Reset settings to default values"""
        self.__init__()
    
    def override(self, **kwargs) -> None:
        """Override specific settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"Unknown setting: {key}")
    
    def get_database_url(self, async_mode: bool = False) -> str:
        """Get database URL for tests"""
        if async_mode:
            return self.database.async_connection_string
        return self.database.connection_string
    
    def get_redis_url(self) -> str:
        """Get Redis URL for tests"""
        return self.redis.connection_url
    
    def __repr__(self) -> str:
        """String representation"""
        return f"TestSettings(environment='{self.environment}', app_name='{self.app_name}')"


# Singleton instance
_test_settings: Optional[TestSettings] = None


def get_test_settings() -> TestSettings:
    """
    Get singleton test settings instance
    
    Returns:
        TestSettings instance
    """
    global _test_settings
    if _test_settings is None:
        _test_settings = TestSettings()
    return _test_settings


def reset_test_settings() -> None:
    """Reset test settings singleton"""
    global _test_settings
    _test_settings = None


# Pytest fixtures helper
def get_test_config() -> Dict[str, Any]:
    """
    Get test configuration as dictionary (useful for pytest fixtures)
    
    Returns:
        Test configuration dictionary
    """
    return get_test_settings().to_dict()


# Test database URL helpers
def get_test_database_url(async_mode: bool = False) -> str:
    """
    Get test database URL
    
    Args:
        async_mode: Whether to return async-compatible URL
        
    Returns:
        Database connection URL
    """
    return get_test_settings().get_database_url(async_mode)


def get_test_redis_url() -> str:
    """
    Get test Redis URL
    
    Returns:
        Redis connection URL
    """
    return get_test_settings().get_redis_url()


# Context managers for temporary settings
class TemporaryTestSettings:
    """Context manager for temporary test settings override"""
    
    def __init__(self, **overrides):
        """
        Initialize temporary settings
        
        Args:
            **overrides: Settings to override
        """
        self.overrides = overrides
        self.original_settings = {}
    
    def __enter__(self):
        """Enter context"""
        settings = get_test_settings()
        
        # Save original values
        for key, value in self.overrides.items():
            if hasattr(settings, key):
                self.original_settings[key] = getattr(settings, key)
                setattr(settings, key, value)
        
        return settings
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore original settings"""
        settings = get_test_settings()
        
        # Restore original values
        for key, value in self.original_settings.items():
            setattr(settings, key, value)


# Test fixtures data
TEST_USERS = [
    {
        "email": "test@goat-prediction.com",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "role": "user",
        "is_active": True,
    },
    {
        "email": "admin@goat-prediction.com",
        "password": "AdminPassword123!",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
    },
    {
        "email": "premium@goat-prediction.com",
        "password": "PremiumPassword123!",
        "first_name": "Premium",
        "last_name": "User",
        "role": "premium",
        "is_active": True,
    },
]


TEST_PREDICTIONS = [
    {
        "match_id": "test-match-001",
        "sport": "football",
        "league": "Premier League",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "prediction": "home_win",
        "confidence": 0.75,
        "odds": 2.10,
    },
    {
        "match_id": "test-match-002",
        "sport": "basketball",
        "league": "NBA",
        "home_team": "Lakers",
        "away_team": "Warriors",
        "prediction": "away_win",
        "confidence": 0.68,
        "odds": 1.85,
    },
]


TEST_API_KEYS = {
    "statsbomb": "test-statsbomb-api-key-12345",
    "opta": "test-opta-api-key-67890",
    "sportradar": "test-sportradar-api-key-abcde",
}


# Export all
__all__ = [
    'TestSettings',
    'TestDatabaseSettings',
    'TestRedisSettings',
    'TestAPISettings',
    'TestAuthSettings',
    'TestLoggingSettings',
    'TestCacheSettings',
    'TestExternalAPISettings',
    'TestFileStorageSettings',
    'TestMLSettings',
    'get_test_settings',
    'reset_test_settings',
    'get_test_config',
    'get_test_database_url',
    'get_test_redis_url',
    'TemporaryTestSettings',
    'TEST_USERS',
    'TEST_PREDICTIONS',
    'TEST_API_KEYS',
]
