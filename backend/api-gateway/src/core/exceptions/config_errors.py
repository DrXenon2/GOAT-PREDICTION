"""
Configuration Error Exceptions for API Gateway
Custom exceptions for configuration-related errors
"""

from typing import Optional, Dict, Any


class ConfigError(Exception):
    """Base exception for configuration errors"""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        config_key: Optional[str] = None
    ):
        """
        Initialize configuration error
        
        Args:
            message: Error message
            details: Additional error details
            config_key: Configuration key that caused the error
        """
        self.message = message
        self.details = details or {}
        self.config_key = config_key
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """String representation"""
        if self.config_key:
            return f"ConfigError for '{self.config_key}': {self.message}"
        return f"ConfigError: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "config_key": self.config_key,
            "details": self.details
        }


class ConfigFileNotFoundError(ConfigError):
    """Exception raised when configuration file is not found"""
    
    def __init__(self, file_path: str, message: Optional[str] = None):
        """
        Initialize file not found error
        
        Args:
            file_path: Path to the missing configuration file
            message: Optional custom message
        """
        self.file_path = file_path
        msg = message or f"Configuration file not found: {file_path}"
        super().__init__(msg, details={"file_path": file_path})


class ConfigFileParseError(ConfigError):
    """Exception raised when configuration file cannot be parsed"""
    
    def __init__(
        self,
        file_path: str,
        parse_error: str,
        line_number: Optional[int] = None
    ):
        """
        Initialize parse error
        
        Args:
            file_path: Path to the configuration file
            parse_error: Parse error message
            line_number: Line number where error occurred
        """
        self.file_path = file_path
        self.parse_error = parse_error
        self.line_number = line_number
        
        msg = f"Error parsing configuration file '{file_path}': {parse_error}"
        if line_number:
            msg += f" (line {line_number})"
        
        super().__init__(
            msg,
            details={
                "file_path": file_path,
                "parse_error": parse_error,
                "line_number": line_number
            }
        )


class ConfigValidationError(ConfigError):
    """Exception raised when configuration validation fails"""
    
    def __init__(
        self,
        config_key: str,
        expected_type: Optional[str] = None,
        actual_value: Optional[Any] = None,
        message: Optional[str] = None
    ):
        """
        Initialize validation error
        
        Args:
            config_key: Configuration key that failed validation
            expected_type: Expected type/format
            actual_value: Actual value that failed validation
            message: Optional custom message
        """
        self.expected_type = expected_type
        self.actual_value = actual_value
        
        if message:
            msg = message
        elif expected_type:
            msg = (
                f"Invalid value for '{config_key}': "
                f"expected {expected_type}, got {type(actual_value).__name__}"
            )
        else:
            msg = f"Validation failed for '{config_key}'"
        
        super().__init__(
            msg,
            details={
                "expected_type": expected_type,
                "actual_value": str(actual_value),
                "actual_type": type(actual_value).__name__
            },
            config_key=config_key
        )


class ConfigMissingKeyError(ConfigError):
    """Exception raised when required configuration key is missing"""
    
    def __init__(
        self,
        config_key: str,
        section: Optional[str] = None,
        message: Optional[str] = None
    ):
        """
        Initialize missing key error
        
        Args:
            config_key: Missing configuration key
            section: Configuration section where key is missing
            message: Optional custom message
        """
        self.section = section
        
        if message:
            msg = message
        elif section:
            msg = f"Required configuration key '{config_key}' missing in section '{section}'"
        else:
            msg = f"Required configuration key '{config_key}' is missing"
        
        super().__init__(
            msg,
            details={"section": section},
            config_key=config_key
        )


class ConfigInvalidValueError(ConfigError):
    """Exception raised when configuration value is invalid"""
    
    def __init__(
        self,
        config_key: str,
        value: Any,
        reason: str,
        valid_values: Optional[list] = None
    ):
        """
        Initialize invalid value error
        
        Args:
            config_key: Configuration key with invalid value
            value: Invalid value
            reason: Reason why value is invalid
            valid_values: List of valid values (optional)
        """
        self.value = value
        self.reason = reason
        self.valid_values = valid_values
        
        msg = f"Invalid value '{value}' for '{config_key}': {reason}"
        if valid_values:
            msg += f". Valid values: {', '.join(map(str, valid_values))}"
        
        super().__init__(
            msg,
            details={
                "value": str(value),
                "reason": reason,
                "valid_values": valid_values
            },
            config_key=config_key
        )


class ConfigTypeError(ConfigError):
    """Exception raised when configuration value has wrong type"""
    
    def __init__(
        self,
        config_key: str,
        expected_type: type,
        actual_type: type,
        value: Any
    ):
        """
        Initialize type error
        
        Args:
            config_key: Configuration key
            expected_type: Expected type
            actual_type: Actual type
            value: Actual value
        """
        self.expected_type = expected_type
        self.actual_type = actual_type
        self.value = value
        
        msg = (
            f"Type mismatch for '{config_key}': "
            f"expected {expected_type.__name__}, got {actual_type.__name__}"
        )
        
        super().__init__(
            msg,
            details={
                "expected_type": expected_type.__name__,
                "actual_type": actual_type.__name__,
                "value": str(value)
            },
            config_key=config_key
        )


class ConfigRangeError(ConfigError):
    """Exception raised when configuration value is out of range"""
    
    def __init__(
        self,
        config_key: str,
        value: Any,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None
    ):
        """
        Initialize range error
        
        Args:
            config_key: Configuration key
            value: Out of range value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        
        msg = f"Value '{value}' for '{config_key}' is out of range"
        if min_value is not None and max_value is not None:
            msg += f" (must be between {min_value} and {max_value})"
        elif min_value is not None:
            msg += f" (must be >= {min_value})"
        elif max_value is not None:
            msg += f" (must be <= {max_value})"
        
        super().__init__(
            msg,
            details={
                "value": value,
                "min_value": min_value,
                "max_value": max_value
            },
            config_key=config_key
        )


class ConfigEnvironmentError(ConfigError):
    """Exception raised for environment-specific configuration errors"""
    
    def __init__(
        self,
        environment: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize environment error
        
        Args:
            environment: Environment name (dev, staging, prod, etc.)
            message: Error message
            details: Additional details
        """
        self.environment = environment
        
        msg = f"Configuration error in '{environment}' environment: {message}"
        
        env_details = {"environment": environment}
        if details:
            env_details.update(details)
        
        super().__init__(msg, details=env_details)


class ConfigDependencyError(ConfigError):
    """Exception raised when configuration dependencies are not met"""
    
    def __init__(
        self,
        config_key: str,
        depends_on: str,
        message: Optional[str] = None
    ):
        """
        Initialize dependency error
        
        Args:
            config_key: Configuration key
            depends_on: Key that this configuration depends on
            message: Optional custom message
        """
        self.depends_on = depends_on
        
        msg = message or (
            f"Configuration '{config_key}' depends on '{depends_on}' "
            f"which is not configured"
        )
        
        super().__init__(
            msg,
            details={"depends_on": depends_on},
            config_key=config_key
        )


class ConfigOverrideError(ConfigError):
    """Exception raised when configuration override fails"""
    
    def __init__(
        self,
        config_key: str,
        override_value: Any,
        reason: str
    ):
        """
        Initialize override error
        
        Args:
            config_key: Configuration key being overridden
            override_value: Value attempting to override
            reason: Reason override failed
        """
        self.override_value = override_value
        self.reason = reason
        
        msg = f"Cannot override '{config_key}' with '{override_value}': {reason}"
        
        super().__init__(
            msg,
            details={
                "override_value": str(override_value),
                "reason": reason
            },
            config_key=config_key
        )


class ConfigLoadError(ConfigError):
    """Exception raised when configuration loading fails"""
    
    def __init__(
        self,
        source: str,
        error: Exception,
        message: Optional[str] = None
    ):
        """
        Initialize load error
        
        Args:
            source: Configuration source (file, env, remote, etc.)
            error: Original error
            message: Optional custom message
        """
        self.source = source
        self.original_error = error
        
        msg = message or f"Failed to load configuration from '{source}': {str(error)}"
        
        super().__init__(
            msg,
            details={
                "source": source,
                "original_error": str(error),
                "error_type": type(error).__name__
            }
        )


# Export all exceptions
__all__ = [
    'ConfigError',
    'ConfigFileNotFoundError',
    'ConfigFileParseError',
    'ConfigValidationError',
    'ConfigMissingKeyError',
    'ConfigInvalidValueError',
    'ConfigTypeError',
    'ConfigRangeError',
    'ConfigEnvironmentError',
    'ConfigDependencyError',
    'ConfigOverrideError',
    'ConfigLoadError',
]
