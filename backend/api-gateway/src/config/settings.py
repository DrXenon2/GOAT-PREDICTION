"""
Configuration settings for the application.
"""
from typing import List, Optional
from pydantic import Field, PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "GOAT Prediction API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    secret_key: str = Field(default="your-secret-key-change-in-production", min_length=32)
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    
    # Database
    database_url: PostgresDsn = "postgresql+asyncpg://goat:password@localhost:5432/goat_prediction"
    database_pool_size: int = 20
    database_max_overflow: int = 40
    database_echo: bool = False
    
    # Redis
    redis_url: RedisDsn = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    
    # JWT
    jwt_secret: str = Field(default="your-jwt-secret-key-change-this", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7
    
    # Security
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    rate_limit_per_minute: int = 100
    
    # API Keys
    statsbomb_api_key: Optional[str] = None
    opta_api_key: Optional[str] = None
    sportradar_api_key: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @validator("environment")
    def validate_environment(cls, v):
        if v not in ["development", "testing", "staging", "production"]:
            raise ValueError("Environment must be development, testing, staging, or production")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


# Global settings instance
settings = Settings()
