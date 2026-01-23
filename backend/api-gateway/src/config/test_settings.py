"""
Test settings for API Gateway.
"""

import os
from typing import Dict, Any
from .settings import Settings


class TestSettings(Settings):
    """Test environment settings."""
    
    # Override settings for tests
    ENVIRONMENT: str = "testing"
    DEBUG: bool = True
    
    # Use test database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "test_user"
    POSTGRES_PASSWORD: str = "test_password"
    POSTGRES_DB: str = "goat_prediction_test"
    POSTGRES_PORT: str = "5432"
    
    # Use test Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    
    # Disable external API calls in tests
    STATSBOMB_API_KEY: str = "test_key"
    OPTA_API_KEY: str = "test_key"
    SPORTRADAR_API_KEY: str = "test_key"
    
    # Disable emails in tests
    EMAILS_ENABLED: bool = False
    
    # Disable rate limiting in tests
    RATE_LIMIT_ENABLED: bool = False
    
    # Disable cache in tests
    CACHE_ENABLED: bool = False
    
    # Disable security features in tests
    SECURITY_HEADERS_ENABLED: bool = False
    BRUTE_FORCE_PROTECTION: bool = False
    
    # Faster token expiration for tests
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    
    # Feature flags for testing
    FEATURE_FLAGS: Dict[str, bool] = {
        "enable_live_predictions": True,
        "enable_betting_simulator": False,
        "enable_advanced_analytics": True,
        "enable_multi_sport": True,
        "enable_real_time_updates": False,
        "enable_api_rate_limiting": False,
        "enable_cache_warming": False,
        "enable_ai_explanations": True,
        "enable_sentiment_analysis": False,
        "enable_weather_integration": False,
    }
    
    class Config:
        env_file = ".env.test"
        env_file_encoding = "utf-8"


# Test settings instance
test_settings = TestSettings()
