"""
Application settings configuration using Pydantic Settings.
"""

import os
from typing import List, Optional
from pydantic import AnyHttpUrl, Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    
    # ====================
    # APPLICATION SETTINGS
    # ====================
    APP_NAME: str = "GOAT Prediction Ultimate"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "The most advanced sports prediction AI in the world"
    
    # Environment
    ENVIRONMENT: str = Field("development", regex="^(development|testing|staging|production)$")
    DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-this-in-production",
        min_length=32,
        description="Secret key for cryptographic operations"
    )
    
    # ====================
    # SERVER SETTINGS
    # ====================
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False
    
    # URLs
    API_URL: AnyHttpUrl = "http://localhost:8000"
    FRONTEND_URL: AnyHttpUrl = "http://localhost:3000"
    PUBLIC_URL: AnyHttpUrl = "http://localhost:8000"
    
    # ====================
    # DATABASE SETTINGS
    # ====================
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://goat:password@localhost:5432/goat_prediction"
    DATABASE_POOL_SIZE: int = Field(20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(40, ge=0, le=200)
    DATABASE_ECHO: bool = False
    DATABASE_ECHO_POOL: bool = False
    DATABASE_POOL_RECYCLE: int = 3600  # seconds
    DATABASE_POOL_PRE_PING: bool = True
    
    # ====================
    # REDIS SETTINGS
    # ====================
    REDIS_URL: RedisDsn = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = Field(50, ge=1, le=1000)
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_RETRY_ON_TIMEOUT: bool = True
    
    # ====================
    # JWT SETTINGS
    # ====================
    JWT_SECRET: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        min_length=32
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1, le=1440)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1, le=90)
    JWT_TOKEN_PREFIX: str = "Bearer"
    
    # ====================
    # SECURITY SETTINGS
    # ====================
    CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.lower() == "all":
                return ["*"]
            return [origin.strip() for origin in v.split(",")]
        return v
    
    RATE_LIMIT_PER_MINUTE: int = Field(100, ge=1, le=10000)
    RATE_LIMIT_PER_HOUR: int = Field(1000, ge=1, le=100000)
    
    # Password security
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 100
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # ====================
    # API KEYS (Sports Data)
    # ====================
    STATSBOMB_API_KEY: Optional[str] = None
    OPTA_API_KEY: Optional[str] = None
    SPORTRADAR_API_KEY: Optional[str] = None
    BETFAIR_API_KEY: Optional[str] = None
    PINNACLE_API_KEY: Optional[str] = None
    BET365_API_KEY: Optional[str] = None
    WILLIAM_HILL_API_KEY: Optional[str] = None
    
    # ====================
    # LOGGING SETTINGS
    # ====================
    LOG_LEVEL: str = Field("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # ====================
    # MONITORING SETTINGS
    # ====================
    ENABLE_METRICS: bool = True
    METRICS_PATH: str = "/metrics"
    ENABLE_TRACING: bool = False
    ENABLE_PROFILING: bool = False
    
    # ====================
    # CACHE SETTINGS
    # ====================
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_PREDICTION_TTL: int = 1800  # 30 minutes
    CACHE_ODDS_TTL: int = 60  # 1 minute
    CACHE_USER_TTL: int = 3600  # 1 hour
    
    # ====================
    # EMAIL SETTINGS
    # ====================
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "noreply@goat-prediction.com"
    EMAIL_FROM_NAME: str = "GOAT Prediction"
    
    # ====================
    # PAYMENT SETTINGS
    # ====================
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLIC_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # ====================
    # FILE STORAGE
    # ====================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".csv"]
    
    # ====================
    # FEATURE FLAGS
    # ====================
    ENABLE_REGISTRATION: bool = True
    ENABLE_EMAIL_VERIFICATION: bool = False
    ENABLE_TWO_FACTOR_AUTH: bool = False
    ENABLE_SOCIAL_LOGIN: bool = False
    ENABLE_API_DOCS: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_MAINTENANCE_MODE: bool = False
    
    # ====================
    # PERFORMANCE
    # ====================
    REQUEST_TIMEOUT: int = 30
    RESPONSE_COMPRESSION: bool = True
    GZIP_LEVEL: int = 6
    
    # ====================
    # BUSINESS SETTINGS
    # ====================
    DEFAULT_CURRENCY: str = "USD"
    DEFAULT_LANGUAGE: str = "en"
    DEFAULT_TIMEZONE: str = "UTC"
    SUPPORTED_LANGUAGES: List[str] = ["en", "fr", "es", "de", "it"]
    SUPPORTED_CURRENCIES: List[str] = ["USD", "EUR", "GBP", "CAD", "AUD"]
    
    # Subscription pricing (in cents)
    SUBSCRIPTION_PRICES: dict = {
        "free": 0,
        "basic": 999,  # $9.99
        "pro": 2999,   # $29.99
        "enterprise": 9999,  # $99.99
    }
    
    # Betting limits
    MIN_BET_AMOUNT: float = 1.0
    MAX_BET_AMOUNT: float = 10000.0
    DAILY_BET_LIMIT: float = 50000.0
    
    # ====================
    # VALIDATORS
    # ====================
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if "postgresql" not in str(v):
            raise ValueError("Database URL must be a PostgreSQL connection string")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        if "redis" not in str(v):
            raise ValueError("Redis URL must be a Redis connection string")
        return v
    
    @validator("ENVIRONMENT")
    def set_debug_from_environment(cls, v, values):
        if v == "development":
            values["DEBUG"] = True
            values["RELOAD"] = True
        elif v == "production":
            values["DEBUG"] = False
            values["RELOAD"] = False
        return v
    
    @validator("UPLOAD_DIR")
    def create_upload_dir(cls, v):
        os.makedirs(v, exist_ok=True)
        return v
    
    # ====================
    # CONFIG
    # ====================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"
        
        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            # Priority: env_settings > file_secret_settings > init_settings
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


# Global settings instance
settings = Settings()
