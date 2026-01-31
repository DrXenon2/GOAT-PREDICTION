"""
Core Configuration Module for API Gateway
Central configuration management with environment support
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import lru_cache
import logging

from .exceptions.config_errors import (
    ConfigError,
    ConfigMissingKeyError,
    ConfigValidationError,
    ConfigEnvironmentError
)

logger = logging.getLogger(__name__)


class CoreConfig:
    """
    Core configuration class for API Gateway
    Manages application-wide configuration settings
    """
    
    def __init__(self, environment: Optional[str] = None):
        """
        Initialize core configuration
        
        Args:
            environment: Environment name (development, staging, production, test)
        """
        self.environment = environment or self._detect_environment()
        self._config: Dict[str, Any] = {}
        self._load_configuration()
    
    def _detect_environment(self) -> str:
        """
        Detect current environment from environment variables
        
        Returns:
            Environment name
        """
        env = os.getenv('ENVIRONMENT', os.getenv('ENV', 'development')).lower()
        
        # Normalize environment names
        env_mapping = {
            'dev': 'development',
            'develop': 'development',
            'prod': 'production',
            'stage': 'staging',
            'test': 'testing'
        }
        
        return env_mapping.get(env, env)
    
    def _load_configuration(self) -> None:
        """Load configuration based on environment"""
        logger.info(f"Loading configuration for environment: {self.environment}")
        
        # Base configuration
        self._config = {
            'environment': self.environment,
            'debug': self.environment in ['development', 'testing'],
            'testing': self.environment == 'testing',
        }
        
        # Load environment-specific settings
        self._load_environment_settings()
        
        # Validate required settings
        self._validate_configuration()
    
    def _load_environment_settings(self) -> None:
        """Load environment-specific settings"""
        if self.environment == 'production':
            self._load_production_settings()
        elif self.environment == 'staging':
            self._load_staging_settings()
        elif self.environment == 'testing':
            self._load_testing_settings()
        else:  # development
            self._load_development_settings()
    
    def _load_production_settings(self) -> None:
        """Load production environment settings"""
        self._config.update({
            'api': {
                'host': os.getenv('API_HOST', '0.0.0.0'),
                'port': int(os.getenv('API_PORT', '8000')),
                'workers': int(os.getenv('API_WORKERS', '4')),
                'reload': False,
                'log_level': 'info',
            },
            'database': {
                'pool_size': int(os.getenv('DB_POOL_SIZE', '20')),
                'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '40')),
                'pool_pre_ping': True,
                'pool_recycle': 3600,
                'echo': False,
            },
            'redis': {
                'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '50')),
                'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
                'socket_connect_timeout': int(os.getenv('REDIS_CONNECT_TIMEOUT', '5')),
            },
            'security': {
                'cors_origins': os.getenv('CORS_ORIGINS', '').split(','),
                'rate_limit_enabled': True,
                'rate_limit_requests': int(os.getenv('RATE_LIMIT_REQUESTS', '100')),
                'rate_limit_period': int(os.getenv('RATE_LIMIT_PERIOD', '60')),
            },
            'logging': {
                'level': 'INFO',
                'json_format': True,
                'access_log': True,
            }
        })
    
    def _load_staging_settings(self) -> None:
        """Load staging environment settings"""
        self._config.update({
            'api': {
                'host': os.getenv('API_HOST', '0.0.0.0'),
                'port': int(os.getenv('API_PORT', '8000')),
                'workers': int(os.getenv('API_WORKERS', '2')),
                'reload': False,
                'log_level': 'debug',
            },
            'database': {
                'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
                'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
                'pool_pre_ping': True,
                'pool_recycle': 3600,
                'echo': True,
            },
            'redis': {
                'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '20')),
                'socket_timeout': int(os.getenv('REDIS_SOCKET_TIMEOUT', '5')),
            },
            'security': {
                'cors_origins': ['*'],  # Permissive in staging
                'rate_limit_enabled': True,
                'rate_limit_requests': int(os.getenv('RATE_LIMIT_REQUESTS', '1000')),
                'rate_limit_period': int(os.getenv('RATE_LIMIT_PERIOD', '60')),
            },
            'logging': {
                'level': 'DEBUG',
                'json_format': False,
                'access_log': True,
            }
        })
    
    def _load_development_settings(self) -> None:
        """Load development environment settings"""
        self._config.update({
            'api': {
                'host': os.getenv('API_HOST', '127.0.0.1'),
                'port': int(os.getenv('API_PORT', '8000')),
                'workers': 1,
                'reload': True,
                'log_level': 'debug',
            },
            'database': {
                'pool_size': 5,
                'max_overflow': 10,
                'pool_pre_ping': True,
                'pool_recycle': 3600,
                'echo': True,
            },
            'redis': {
                'max_connections': 10,
                'socket_timeout': 5,
            },
            'security': {
                'cors_origins': ['*'],
                'rate_limit_enabled': False,
                'rate_limit_requests': 1000000,
                'rate_limit_period': 60,
            },
            'logging': {
                'level': 'DEBUG',
                'json_format': False,
                'access_log': True,
            }
        })
    
    def _load_testing_settings(self) -> None:
        """Load testing environment settings"""
        self._config.update({
            'api': {
                'host': '127.0.0.1',
                'port': 8001,
                'workers': 1,
                'reload': False,
                'log_level': 'debug',
            },
            'database': {
                'pool_size': 5,
                'max_overflow': 10,
                'pool_pre_ping': False,
                'echo': False,
            },
            'redis': {
                'max_connections': 10,
                'socket_timeout': 5,
            },
            'security': {
                'cors_origins': ['*'],
                'rate_limit_enabled': False,
                'rate_limit_requests': 1000000,
                'rate_limit_period': 60,
            },
            'logging': {
                'level': 'DEBUG',
                'json_format': False,
                'access_log': False,
            }
        })
    
    def _validate_configuration(self) -> None:
        """Validate required configuration settings"""
        required_keys = ['environment', 'api', 'security', 'logging']
        
        for key in required_keys:
            if key not in self._config:
                raise ConfigMissingKeyError(
                    key,
                    message=f"Required configuration key '{key}' is missing"
                )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports dot notation)
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return self._config.copy()
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == 'development'
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing"""
        return self.environment == 'testing'
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.environment == 'staging'
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return self.get('debug', False)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"CoreConfig(environment='{self.environment}')"


@lru_cache(maxsize=1)
def get_core_config(environment: Optional[str] = None) -> CoreConfig:
    """
    Get singleton core configuration instance
    
    Args:
        environment: Environment name
        
    Returns:
        CoreConfig instance
    """
    return CoreConfig(environment)


# Convenience functions
def get_environment() -> str:
    """Get current environment"""
    return get_core_config().environment


def is_production() -> bool:
    """Check if running in production"""
    return get_core_config().is_production


def is_development() -> bool:
    """Check if running in development"""
    return get_core_config().is_development


def is_testing() -> bool:
    """Check if running in testing"""
    return get_core_config().is_testing


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value"""
    return get_core_config().get(key, default)
