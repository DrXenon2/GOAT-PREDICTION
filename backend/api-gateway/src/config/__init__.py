"""
GOAT PREDICTION ULTIMATE - API Gateway Configuration Module
Module de configuration centralisée pour l'API Gateway
Expose toutes les configurations, settings et loaders
"""

from .settings import Settings, get_settings, settings
from .config_loader import ConfigLoader, load_config
from .env_config import EnvConfig, load_env_config
from .logging_config import (
    LoggingConfig,
    setup_logging,
    get_logger,
    configure_root_logger,
)
from .constants import (
    API_VERSION,
    API_PREFIX,
    CORS_ORIGINS,
    ALLOWED_HOSTS,
    MAX_REQUEST_SIZE,
    REQUEST_TIMEOUT,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_PERIOD,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "settings",
    
    # Config Loader
    "ConfigLoader",
    "load_config",
    
    # Environment Config
    "EnvConfig",
    "load_env_config",
    
    # Logging Config
    "LoggingConfig",
    "setup_logging",
    "get_logger",
    "configure_root_logger",
    
    # Constants
    "API_VERSION",
    "API_PREFIX",
    "CORS_ORIGINS",
    "ALLOWED_HOSTS",
    "MAX_REQUEST_SIZE",
    "REQUEST_TIMEOUT",
    "RATE_LIMIT_REQUESTS",
    "RATE_LIMIT_PERIOD",
]

# Version du module
__version__ = "1.0.0"

# Metadata
__author__ = "GOAT Prediction Team"
__email__ = "dev@goat-prediction.com"
__status__ = "Production"
