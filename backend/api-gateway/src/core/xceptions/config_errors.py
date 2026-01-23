"""
Configuration-related exceptions.
"""

from typing import Any, Optional


class ConfigError(Exception):
    """Base exception for configuration errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        self.message = message
        self.config_key = config_key
        super().__init__(self.message)
    
    def __str__(self):
        if self.config_key:
            return f"ConfigError for '{self.config_key}': {self.message}"
        return f"ConfigError: {self.message}"


class ValidationError(ConfigError):
    """Configuration validation error."""
    
    def __init__(self, message: str, config_key: Optional[str] = None,
                 expected: Any = None, actual: Any = None):
        self.expected = expected
        self.actual = actual
        super().__init__(message, config_key)
    
    def __str__(self):
        base_str = super().__str__()
        if self.expected is not None and self.actual is not None:
            return f"{base_str} (expected: {self.expected}, got: {self.actual})"
        return base_str


class ConfigurationNotFoundError(ConfigError):
    """Configuration key not found."""
    pass


class ConfigurationLoadError(ConfigError):
    """Error loading configuration from source."""
    pass


class ConfigurationSaveError(ConfigError):
    """Error saving configuration."""
    pass


class ConfigurationSyncError(ConfigError):
    """Error synchronizing configuration."""
    pass


class ConfigurationSecurityError(ConfigError):
    """Configuration security error."""
    pass
