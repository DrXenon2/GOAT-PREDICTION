"""
GOAT PREDICTION ULTIMATE - API Gateway Settings
Configuration principale avec Pydantic BaseSettings
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator, AnyHttpUrl
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration principale de l'API Gateway"""
    
    # ============================================
    # APPLICATION
    # ============================================
    APP_NAME: str = Field(default="GOAT Prediction API Gateway", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # ============================================
    # API CONFIGURATION
    # ============================================
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=4, env="API_WORKERS")
    API_RELOAD: bool = Field(default=True, env="HOT_RELOAD")
    
    API_PREFIX: str = "/api/v1"
    API_TITLE: str = "GOAT Prediction Ultimate API"
    API_DESCRIPTION: str = "API de prédiction sportive la plus avancée au monde"
    
    # ============================================
    # CORS
    # ============================================
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:8080",
        ],
        env="CORS_ORIGINS"
    )
    CORS_CREDENTIALS: bool = Field(default=True, env="CORS_CREDENTIALS")
    CORS_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        env="CORS_METHODS"
    )
    CORS_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization", "X-API-Key"],
        env="CORS_ALLOWED_HEADERS"
    )
    
    # ============================================
    # DATABASE
    # ============================================
    POSTGRES_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_USER: str = Field(default="goat_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(default="goat_password", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="goat_prediction", env="POSTGRES_DB")
    POSTGRES_POOL_SIZE: int = Field(default=10, env="POSTGRES_POOL_SIZE")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # ============================================
    # REDIS
    # ============================================
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: str = Field(default="goat_redis_pass", env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_CACHE_TTL: int = Field(default=3600, env="REDIS_CACHE_TTL")
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ============================================
    # JWT AUTHENTICATION
    # ============================================
    JWT_SECRET: str = Field(
        default="dev_jwt_super_secret_key_change_in_production",
        env="JWT_SECRET"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRES_IN: str = Field(default="7d", env="JWT_EXPIRES_IN")
    JWT_REFRESH_EXPIRES_IN: str = Field(default="30d", env="JWT_REFRESH_EXPIRES_IN")
    
    # ============================================
    # RATE LIMITING
    # ============================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_WINDOW_MS: int = Field(default=900000, env="RATE_LIMIT_WINDOW_MS")
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=100, env="RATE_LIMIT_MAX_REQUESTS")
    
    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # ============================================
    # MONITORING
    # ============================================
    SENTRY_ENABLED: bool = Field(default=False, env="SENTRY_ENABLED")
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(default=9090, env="PROMETHEUS_PORT")
    
    # ============================================
    # EXTERNAL SERVICES
    # ============================================
    ML_API_URL: str = Field(default="http://localhost:8001", env="ML_API_URL")
    ML_API_TIMEOUT: int = Field(default=30, env="ML_PREDICTION_TIMEOUT")
    
    # ============================================
    # FEATURE FLAGS
    # ============================================
    ENABLE_BETTING: bool = Field(default=True, env="ENABLE_BETTING")
    ENABLE_LIVE_PREDICTIONS: bool = Field(default=True, env="ENABLE_LIVE_PREDICTIONS")
    ENABLE_ADVANCED_ANALYTICS: bool = Field(default=True, env="ENABLE_ADVANCED_ANALYTICS")
    ENABLE_API_DOCS: bool = Field(default=True, env="ENABLE_API_DOCS")
    ENABLE_SWAGGER_UI: bool = Field(default=True, env="ENABLE_SWAGGER_UI")
    
    # ============================================
    # VALIDATORS
    # ============================================
    @validator("CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS", pre=True)
    def parse_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    @validator("APP_ENV")
    def validate_env(cls, v):
        allowed_envs = ["development", "staging", "production", "test"]
        if v not in allowed_envs:
            raise ValueError(f"APP_ENV must be one of {allowed_envs}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed_levels:
            raise ValueError(f"LOG_LEVEL must be one of {allowed_levels}")
        return v
    
    # ============================================
    # METHODS
    # ============================================
    def is_development(self) -> bool:
        return self.APP_ENV == "development"
    
    def is_production(self) -> bool:
        return self.APP_ENV == "production"
    
    def is_testing(self) -> bool:
        return self.APP_ENV == "test"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Singleton pour les settings avec cache"""
    return Settings()


# Instance globale
settings = get_settings()
