"""
Configuration management for GOAT Prediction API Gateway.
Uses Pydantic settings for type-safe environment variable handling.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, Field, PostgresDsn, RedisDsn, validator


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "GOAT Prediction API Gateway"
    APP_DESCRIPTION: str = "Advanced Sports Prediction Platform - API Gateway"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Server
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")
    WORKERS: int = Field(1, env="WORKERS")
    RELOAD: bool = Field(False, env="RELOAD")
    ROOT_PATH: str = Field("", env="ROOT_PATH")
    
    # Database
    DATABASE_URL: Optional[PostgresDsn] = Field(None, env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    DATABASE_POOL_RECYCLE: int = Field(3600, env="DATABASE_POOL_RECYCLE")
    DATABASE_ECHO: bool = Field(False, env="DATABASE_ECHO")
    
    # Redis
    REDIS_URL: Optional[RedisDsn] = Field(None, env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(20, env="REDIS_POOL_SIZE")
    REDIS_SOCKET_TIMEOUT: int = Field(5, env="REDIS_SOCKET_TIMEOUT")
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # CORS
    CORS_ENABLED: bool = Field(True, env="CORS_ENABLED")
    CORS_ORIGINS: List[str] = Field(["http://localhost:3000"], env="CORS_ORIGINS")
    CORS_ALLOW_CREDENTIALS: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(["*"], env="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: List[str] = Field(["*"], env="CORS_ALLOW_HEADERS")
    CORS_EXPOSE_HEADERS: List[str] = Field([], env="CORS_EXPOSE_HEADERS")
    CORS_MAX_AGE: int = Field(600, env="CORS_MAX_AGE")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_DEFAULT: List[str] = Field(["100/minute"], env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_BYPASS_KEY: Optional[str] = Field(None, env="RATE_LIMIT_BYPASS_KEY")
    
    # Trusted Hosts
    TRUSTED_HOSTS: List[str] = Field([], env="TRUSTED_HOSTS")
    
    # Compression
    GZIP_ENABLED: bool = Field(True, env="GZIP_ENABLED")
    GZIP_MINIMUM_SIZE: int = Field(1000, env="GZIP_MINIMUM_SIZE")
    
    # Timeouts
    REQUEST_TIMEOUT: int = Field(30, env="REQUEST_TIMEOUT")
    MAX_BODY_SIZE: int = Field(10485760, env="MAX_BODY_SIZE")  # 10MB
    
    # Documentation
    DOCS_ENABLED: bool = Field(True, env="DOCS_ENABLED")
    
    # Monitoring & Observability
    METRICS_ENABLED: bool = Field(True, env="METRICS_ENABLED")
    OTEL_ENABLED: bool = Field(True, env="OTEL_ENABLED")
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = Field(None, env="OTEL_EXPORTER_OTLP_ENDPOINT")
    OTEL_EXPORTER_OTLP_INSECURE: bool = Field(False, env="OTEL_EXPORTER_OTLP_INSECURE")
    OTEL_EXCLUDED_URLS: List[str] = Field(["/health", "/metrics", "/ready", "/live"], env="OTEL_EXCLUDED_URLS")
    OTEL_INSTRUMENT_REDIS: bool = Field(True, env="OTEL_INSTRUMENT_REDIS")
    OTEL_INSTRUMENT_SQLALCHEMY: bool = Field(True, env="OTEL_INSTRUMENT_SQLALCHEMY")
    
    # Background Tasks
    BACKGROUND_TASKS_ENABLED: bool = Field(True, env="BACKGROUND_TASKS_ENABLED")
    BACKGROUND_HEALTH_CHECKS: bool = Field(True, env="BACKGROUND_HEALTH_CHECKS")
    BACKGROUND_CACHE_WARMING: bool = Field(True, env="BACKGROUND_CACHE_WARMING")
    BACKGROUND_METRICS_AGGREGATION: bool = Field(True, env="BACKGROUND_METRICS_AGGREGATION")
    
    # Logging
    ACCESS_LOG: bool = Field(True, env="ACCESS_LOG")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    LOG_DATEFMT: str = Field("%Y-%m-%d %H:%M:%S", env="LOG_DATEFMT")
    
    # Build Information
    BUILD_NUMBER: Optional[str] = Field(None, env="BUILD_NUMBER")
    COMMIT_HASH: Optional[str] = Field(None, env="COMMIT_HASH")
    BUILD_DATE: Optional[str] = Field(None, env="BUILD_DATE")
    
    # Contact Information
    CONTACT_EMAIL: str = Field("dev@goat-prediction.com", env="CONTACT_EMAIL")
    CONTACT_WEBSITE: str = Field("https://goat-prediction.com", env="CONTACT_WEBSITE")
    
    # Legal
    TERMS_URL: Optional[str] = Field(None, env="TERMS_URL")
    LICENSE_NAME: str = Field("Proprietary", env="LICENSE_NAME")
    LICENSE_URL: Optional[str] = Field(None, env="LICENSE_URL")
    
    # Uvicorn Settings
    PROXY_HEADERS: bool = Field(True, env="PROXY_HEADERS")
    FORWARDED_ALLOW_IPS: str = Field("*", env="FORWARDED_ALLOW_IPS")
    LIMIT_CONCURRENCY: Optional[int] = Field(None, env="LIMIT_CONCURRENCY")
    BACKLOG: int = Field(2048, env="BACKLOG")
    LIMIT_MAX_REQUESTS: Optional[int] = Field(None, env="LIMIT_MAX_REQUESTS")
    TIMEOUT_KEEP_ALIVE: int = Field(5, env="TIMEOUT_KEEP_ALIVE")
    
    # SSL/TLS
    SSL_KEYFILE: Optional[str] = Field(None, env="SSL_KEYFILE")
    SSL_CERTFILE: Optional[str] = Field(None, env="SSL_CERTFILE")
    SSL_KEYFILE_PASSWORD: Optional[str] = Field(None, env="SSL_KEYFILE_PASSWORD")
    SSL_VERSION: int = Field(2, env="SSL_VERSION")
    SSL_CERT_REQS: int = Field(0, env="SSL_CERT_REQS")
    SSL_CA_CERTS: Optional[str] = Field(None, env="SSL_CA_CERTS")
    SSL_CIPHERS: str = Field("TLSv1", env="SSL_CIPHERS")
    
    # API Keys (External Services)
    STATSBOMB_API_KEY: Optional[str] = Field(None, env="STATSBOMB_API_KEY")
    OPTA_API_KEY: Optional[str] = Field(None, env="OPTA_API_KEY")
    SPORTRADAR_API_KEY: Optional[str] = Field(None, env="SPORTRADAR_API_KEY")
    BETFAIR_API_KEY: Optional[str] = Field(None, env="BETFAIR_API_KEY")
    PINNACLE_API_KEY: Optional[str] = Field(None, env="PINNACLE_API_KEY")
    OPENWEATHER_API_KEY: Optional[str] = Field(None, env="OPENWEATHER_API_KEY")
    TWITTER_API_KEY: Optional[str] = Field(None, env="TWITTER_API_KEY")
    NEWSAPI_API_KEY: Optional[str] = Field(None, env="NEWSAPI_API_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("TRUSTED_HOSTS", pre=True)
    def parse_trusted_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("OTEL_EXCLUDED_URLS", pre=True)
    def parse_otel_excluded_urls(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
