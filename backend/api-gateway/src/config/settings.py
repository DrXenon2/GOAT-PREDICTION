"""
Configuration settings for GOAT Prediction Ultimate API Gateway.
Environment-based settings with validation and type safety.
"""

import os
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseSettings, Field, PostgresDsn, RedisDsn, validator
from pydantic.networks import AnyHttpUrl
from datetime import timedelta

class Settings(BaseSettings):
    """
    Application settings using Pydantic BaseSettings.
    Environment variables will be loaded automatically.
    """
    
    # ======================
    # APPLICATION CONFIG
    # ======================
    APP_NAME: str = "GOAT Prediction Ultimate API Gateway"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Advanced Sports Prediction & Betting Intelligence Platform"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    PROJECT_NAME: str = "goat-prediction-ultimate"
    
    # Environment
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT tokens and cryptographic operations"
    )
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://goat-prediction.com",
        "https://www.goat-prediction.com",
        "https://admin.goat-prediction.com",
        "https://api.goat-prediction.com",
    ]
    
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # ======================
    # DATABASE CONFIG
    # ======================
    POSTGRES_SERVER: str = Field("localhost", env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field("goat_user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("goat_password", env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field("goat_prediction", env="POSTGRES_DB")
    POSTGRES_PORT: str = Field("5432", env="POSTGRES_PORT")
    
    # Database URLs
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
    
    # Redis
    REDIS_HOST: str = Field("localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(0, env="REDIS_DB")
    
    REDIS_URL: Optional[RedisDsn] = None
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        password = values.get("REDIS_PASSWORD")
        auth_part = f":{password}@" if password else ""
        return f"redis://{auth_part}{values.get('REDIS_HOST')}:{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
    
    # ======================
    # AUTHENTICATION & JWT
    # ======================
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    JWT_ACCESS_TOKEN_EXPIRE: timedelta = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRE: timedelta = timedelta(days=7)
    
    # OAuth2
    GOOGLE_CLIENT_ID: Optional[str] = Field(None, env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(None, env="GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = Field(
        "http://localhost:8000/api/v1/auth/google/callback",
        env="GOOGLE_REDIRECT_URI"
    )
    
    # ======================
    # RATE LIMITING
    # ======================
    RATE_LIMIT_ENABLED: bool = Field(True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_DEFAULT: str = Field("100/minute", env="RATE_LIMIT_DEFAULT")
    RATE_LIMIT_PREMIUM: str = Field("500/minute", env="RATE_LIMIT_PREMIUM")
    RATE_LIMIT_ADMIN: str = Field("1000/minute", env="RATE_LIMIT_ADMIN")
    
    # ======================
    # CACHE CONFIG
    # ======================
    CACHE_ENABLED: bool = Field(True, env="CACHE_ENABLED")
    CACHE_DEFAULT_TTL: int = Field(300, env="CACHE_DEFAULT_TTL")  # 5 minutes
    CACHE_PREDICTIONS_TTL: int = Field(60, env="CACHE_PREDICTIONS_TTL")  # 1 minute
    CACHE_ODDS_TTL: int = Field(30, env="CACHE_ODDS_TTL")  # 30 seconds
    CACHE_STATS_TTL: int = Field(3600, env="CACHE_STATS_TTL")  # 1 hour
    
    # ======================
    # MICROSERVICES
    # ======================
    # Prediction Engine
    PREDICTION_ENGINE_URL: str = Field(
        "http://prediction-engine:8001",
        env="PREDICTION_ENGINE_URL"
    )
    PREDICTION_ENGINE_TIMEOUT: int = Field(30, env="PREDICTION_ENGINE_TIMEOUT")
    
    # User Service
    USER_SERVICE_URL: str = Field(
        "http://user-service:8002",
        env="USER_SERVICE_URL"
    )
    
    # Auth Service
    AUTH_SERVICE_URL: str = Field(
        "http://auth-service:8003",
        env="AUTH_SERVICE_URL"
    )
    
    # Notification Service
    NOTIFICATION_SERVICE_URL: str = Field(
        "http://notification-service:8004",
        env="NOTIFICATION_SERVICE_URL"
    )
    
    # Subscription Service
    SUBSCRIPTION_SERVICE_URL: str = Field(
        "http://subscription-service:8005",
        env="SUBSCRIPTION_SERVICE_URL"
    )
    
    # ======================
    # EXTERNAL APIS
    # ======================
    # StatsBomb API
    STATSBOMB_API_KEY: Optional[str] = Field(None, env="STATSBOMB_API_KEY")
    STATSBOMB_BASE_URL: str = Field(
        "https://api.statsbomb.com",
        env="STATSBOMB_BASE_URL"
    )
    
    # Opta API
    OPTA_API_KEY: Optional[str] = Field(None, env="OPTA_API_KEY")
    OPTA_BASE_URL: str = Field(
        "https://api.opta.net",
        env="OPTA_BASE_URL"
    )
    
    # SportRadar API
    SPORTRADAR_API_KEY: Optional[str] = Field(None, env="SPORTRADAR_API_KEY")
    SPORTRADAR_BASE_URL: str = Field(
        "https://api.sportradar.com",
        env="SPORTRADAR_BASE_URL"
    )
    
    # Betting APIs
    BETFAIR_API_KEY: Optional[str] = Field(None, env="BETFAIR_API_KEY")
    BETFAIR_USERNAME: Optional[str] = Field(None, env="BETFAIR_USERNAME")
    BETFAIR_PASSWORD: Optional[str] = Field(None, env="BETFAIR_PASSWORD")
    BETFAIR_APP_KEY: Optional[str] = Field(None, env="BETFAIR_APP_KEY")
    
    PINNACLE_API_KEY: Optional[str] = Field(None, env="PINNACLE_API_KEY")
    BET365_API_KEY: Optional[str] = Field(None, env="BET365_API_KEY")
    
    # ======================
    # WEBHOOKS
    # ======================
    WEBHOOK_SECRET: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="WEBHOOK_SECRET"
    )
    WEBHOOK_TIMEOUT: int = Field(10, env="WEBHOOK_TIMEOUT")
    WEBHOOK_MAX_RETRIES: int = Field(3, env="WEBHOOK_MAX_RETRIES")
    
    # ======================
    # MONITORING & LOGGING
    # ======================
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Prometheus
    PROMETHEUS_ENABLED: bool = Field(True, env="PROMETHEUS_ENABLED")
    PROMETHEUS_PORT: int = Field(9090, env="PROMETHEUS_PORT")
    
    # Sentry
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    SENTRY_ENVIRONMENT: str = Field("development", env="SENTRY_ENVIRONMENT")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(1.0, env="SENTRY_TRACES_SAMPLE_RATE")
    
    # ======================
    # PERFORMANCE
    # ======================
    MAX_WORKERS: int = Field(4, env="MAX_WORKERS")
    REQUEST_TIMEOUT: int = Field(30, env="REQUEST_TIMEOUT")
    KEEPALIVE_TIMEOUT: int = Field(5, env="KEEPALIVE_TIMEOUT")
    
    # Gzip compression
    GZIP_MIN_SIZE: int = Field(1000, env="GZIP_MIN_SIZE")  # 1KB
    GZIP_COMPRESSION_LEVEL: int = Field(6, env="GZIP_COMPRESSION_LEVEL")
    
    # ======================
    # SECURITY
    # ======================
    # HTTPS enforcement
    HTTPS_REDIRECT: bool = Field(False, env="HTTPS_REDIRECT")
    
    # Security headers
    SECURITY_HEADERS_ENABLED: bool = Field(True, env="SECURITY_HEADERS_ENABLED")
    CSP_DIRECTIVES: Dict[str, List[str]] = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https:"],
        "connect-src": ["'self'", "https://api.goat-prediction.com"],
    }
    
    # Rate limiting for security
    SECURITY_RATE_LIMIT: str = Field("10/minute", env="SECURITY_RATE_LIMIT")
    BRUTE_FORCE_PROTECTION: bool = Field(True, env="BRUTE_FORCE_PROTECTION")
    BRUTE_FORCE_LOCKOUT_MINUTES: int = Field(15, env="BRUTE_FORCE_LOCKOUT_MINUTES")
    BRUTE_FORCE_MAX_ATTEMPTS: int = Field(5, env="BRUTE_FORCE_MAX_ATTEMPTS")
    
    # ======================
    # BUSINESS LOGIC
    # ======================
    # Subscription plans
    SUBSCRIPTION_PLANS: Dict[str, Dict[str, Any]] = {
        "free": {
            "name": "Free",
            "price": 0,
            "currency": "USD",
            "predictions_per_day": 10,
            "sports": ["football"],
            "features": ["basic_predictions", "daily_summary"],
            "rate_limit": "10/minute",
        },
        "premium": {
            "name": "Premium",
            "price": 29.99,
            "currency": "USD",
            "predictions_per_day": 100,
            "sports": ["football", "basketball", "tennis"],
            "features": ["all_predictions", "real_time_updates", "advanced_analytics"],
            "rate_limit": "100/minute",
        },
        "pro": {
            "name": "Professional",
            "price": 99.99,
            "currency": "USD",
            "predictions_per_day": 1000,
            "sports": ["all"],
            "features": ["all_predictions", "real_time_updates", "advanced_analytics", 
                        "api_access", "custom_models", "priority_support"],
            "rate_limit": "500/minute",
        },
        "enterprise": {
            "name": "Enterprise",
            "price": 499.99,
            "currency": "USD",
            "predictions_per_day": 10000,
            "sports": ["all"],
            "features": ["all_predictions", "real_time_updates", "advanced_analytics",
                        "api_access", "custom_models", "priority_support", 
                        "dedicated_instance", "sla_agreement"],
            "rate_limit": "1000/minute",
        }
    }
    
    # Sports configuration
    SPORTS_CONFIG: Dict[str, Dict[str, Any]] = {
        "football": {
            "name": "Football",
            "api_endpoints": ["/api/v1/sports/football"],
            "markets": ["match_winner", "over_under", "both_teams_to_score", "exact_score"],
            "refresh_interval": 60,  # seconds
            "enabled": True,
        },
        "basketball": {
            "name": "Basketball",
            "api_endpoints": ["/api/v1/sports/basketball"],
            "markets": ["moneyline", "point_spread", "total_points"],
            "refresh_interval": 30,
            "enabled": True,
        },
        "tennis": {
            "name": "Tennis",
            "api_endpoints": ["/api/v1/sports/tennis"],
            "markets": ["match_winner", "set_betting", "total_games"],
            "refresh_interval": 45,
            "enabled": True,
        },
        "esports": {
            "name": "Esports",
            "api_endpoints": ["/api/v1/sports/esports"],
            "markets": ["match_winner", "map_winner", "total_kills"],
            "refresh_interval": 30,
            "enabled": True,
        }
    }
    
    # ======================
    # FILE UPLOADS
    # ======================
    UPLOAD_DIR: str = Field("/app/uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(10 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".json", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg"]
    
    # ======================
    # EMAIL CONFIG
    # ======================
    SMTP_HOST: str = Field("smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    EMAILS_ENABLED: bool = Field(False, env="EMAILS_ENABLED")
    
    EMAIL_FROM_NAME: str = Field("GOAT Prediction", env="EMAIL_FROM_NAME")
    EMAIL_FROM_EMAIL: str = Field("noreply@goat-prediction.com", env="EMAIL_FROM_EMAIL")
    
    # ======================
    # PAYMENT PROCESSING
    # ======================
    STRIPE_SECRET_KEY: Optional[str] = Field(None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(None, env="STRIPE_WEBHOOK_SECRET")
    
    # ======================
    # FEATURE FLAGS
    # ======================
    FEATURE_FLAGS: Dict[str, bool] = {
        "enable_live_predictions": True,
        "enable_betting_simulator": True,
        "enable_advanced_analytics": True,
        "enable_multi_sport": True,
        "enable_real_time_updates": True,
        "enable_api_rate_limiting": True,
        "enable_cache_warming": False,
        "enable_ai_explanations": True,
        "enable_sentiment_analysis": True,
        "enable_weather_integration": True,
    }
    
    # ======================
    # VALIDATION METHODS
    # ======================
    def is_development(self) -> bool:
        """Check if environment is development."""
        return self.ENVIRONMENT.lower() in ["dev", "development", "local"]
    
    def is_production(self) -> bool:
        """Check if environment is production."""
        return self.ENVIRONMENT.lower() in ["prod", "production", "live"]
    
    def is_testing(self) -> bool:
        """Check if environment is testing."""
        return self.ENVIRONMENT.lower() in ["test", "testing", "ci"]
    
    def get_database_url(self) -> str:
        """Get database URL as string."""
        return str(self.SQLALCHEMY_DATABASE_URI)
    
    def get_redis_url(self) -> str:
        """Get Redis URL as string."""
        return str(self.REDIS_URL)
    
    def get_rate_limit(self, plan: str = "free") -> str:
        """Get rate limit based on subscription plan."""
        plan_limits = {
            "free": self.RATE_LIMIT_DEFAULT,
            "premium": self.RATE_LIMIT_PREMIUM,
            "pro": self.RATE_LIMIT_PREMIUM,
            "enterprise": self.RATE_LIMIT_ADMIN,
        }
        return plan_limits.get(plan, self.RATE_LIMIT_DEFAULT)
    
    def get_subscription_plan(self, plan_name: str) -> Optional[Dict[str, Any]]:
        """Get subscription plan details by name."""
        return self.SUBSCRIPTION_PLANS.get(plan_name)
    
    def get_sport_config(self, sport: str) -> Optional[Dict[str, Any]]:
        """Get sport configuration."""
        return self.SPORTS_CONFIG.get(sport)
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get feature flag value."""
        return self.FEATURE_FLAGS.get(flag_name, False)
    
    # ======================
    # PYDANTIC CONFIG
    # ======================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True
        
        # Example .env file
        env_file_example = """
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=goat_user
POSTGRES_PASSWORD=goat_password
POSTGRES_DB=goat_prediction
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# External APIs
STATSBOMB_API_KEY=your-statsbomb-key
OPTA_API_KEY=your-opta-key
SPORTRADAR_API_KEY=your-sportradar-key

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
"""


# Global settings instance
settings = Settings()

# Export settings
__all__ = ["settings"]
