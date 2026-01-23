"""
YAML configuration loader for GOAT Prediction API Gateway.
Supports hierarchical configuration with environment-specific overrides.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, ValidationError


class YAMLConfigLoader:
    """YAML configuration loader with environment support."""
    
    def __init__(self, config_dir: str = "config", environment: Optional[str] = None):
        """
        Initialize YAML config loader.
        
        Args:
            config_dir: Directory containing configuration files
            environment: Current environment (development, staging, production)
        """
        self.config_dir = Path(config_dir)
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self, config_file: str = "config.yaml") -> Dict[str, Any]:
        """
        Load configuration from YAML file with environment overrides.
        
        Args:
            config_file: Main configuration file name
        
        Returns:
            Combined configuration dictionary
        """
        cache_key = f"{config_file}:{self.environment}"
        
        # Return cached configuration if available
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        try:
            # Load base configuration
            base_config = self._load_yaml_file(config_file)
            
            # Load environment-specific configuration
            env_config_file = f"config.{self.environment}.yaml"
            env_config = self._load_yaml_file(env_config_file) or {}
            
            # Merge configurations (environment overrides base)
            config = self._deep_merge(base_config, env_config)
            
            # Apply environment variables
            config = self._apply_environment_variables(config)
            
            # Cache the configuration
            self._config_cache[cache_key] = config
            
            return config
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {e}")
    
    def load_section(self, section: str, config_file: str = "config.yaml") -> Dict[str, Any]:
        """
        Load a specific configuration section.
        
        Args:
            section: Configuration section name
            config_file: Main configuration file name
        
        Returns:
            Configuration section dictionary
        """
        config = self.load(config_file)
        return config.get(section, {})
    
    def save(self, config: Dict[str, Any], config_file: str = "config.yaml"):
        """
        Save configuration to YAML file.
        
        Args:
            config: Configuration dictionary
            config_file: Configuration file name
        """
        file_path = self.config_dir / config_file
        
        try:
            with open(file_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise ValueError(f"Failed to save configuration: {e}")
    
    def validate_config(self, schema: BaseModel, config_file: str = "config.yaml") -> bool:
        """
        Validate configuration against a Pydantic schema.
        
        Args:
            schema: Pydantic BaseModel schema
            config_file: Configuration file name
        
        Returns:
            True if configuration is valid
        
        Raises:
            ValidationError: If configuration is invalid
        """
        config = self.load(config_file)
        
        try:
            schema(**config)
            return True
        except ValidationError as e:
            raise e
    
    def get_value(self, key: str, default: Any = None, config_file: str = "config.yaml") -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "database.host")
            default: Default value if key not found
            config_file: Configuration file name
        
        Returns:
            Configuration value
        """
        config = self.load(config_file)
        
        # Split key by dots
        keys = key.split(".")
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_value(self, key: str, value: Any, config_file: str = "config.yaml"):
        """
        Set a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., "database.host")
            value: Value to set
            config_file: Configuration file name
        """
        config = self.load(config_file)
        
        # Split key by dots
        keys = key.split(".")
        current = config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        
        # Save the updated configuration
        self.save(config, config_file)
        
        # Clear cache for this config file
        cache_key = f"{config_file}:{self.environment}"
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
    
    def _load_yaml_file(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load YAML file if it exists."""
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {filename}: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variables to configuration."""
        
        def _process_value(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract environment variable name
                env_var = value[2:-1]
                
                # Split by default value separator
                if ":" in env_var:
                    env_var, default = env_var.split(":", 1)
                else:
                    default = None
                
                # Get value from environment
                env_value = os.getenv(env_var, default)
                
                # Try to parse as JSON if it looks like JSON
                if env_value and env_value.startswith("{") and env_value.endswith("}"):
                    try:
                        return json.loads(env_value)
                    except json.JSONDecodeError:
                        pass
                
                return env_value
            
            elif isinstance(value, dict):
                return {k: _process_value(v) for k, v in value.items()}
            
            elif isinstance(value, list):
                return [_process_value(v) for v in value]
            
            else:
                return value
        
        return _process_value(config)


# Default configuration templates
DEFAULT_CONFIG_TEMPLATES = {
    "development": {
        "app": {
            "name": "GOAT Prediction API Gateway",
            "version": "1.0.0",
            "environment": "development",
            "debug": True,
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 1,
            "reload": True,
        },
        "database": {
            "url": "postgresql+asyncpg://postgres:postgres@localhost:5432/goat_prediction_dev",
            "pool_size": 10,
            "max_overflow": 5,
        },
        "redis": {
            "url": "redis://localhost:6379/0",
            "pool_size": 10,
        },
        "security": {
            "secret_key": "development-secret-key-change-in-production",
            "jwt_secret_key": "development-jwt-secret-key-change-in-production",
        },
    },
    "production": {
        "app": {
            "name": "GOAT Prediction API Gateway",
            "version": "1.0.0",
            "environment": "production",
            "debug": False,
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "workers": 4,
            "reload": False,
        },
        "database": {
            "url": "${DATABASE_URL}",
            "pool_size": 20,
            "max_overflow": 10,
            "ssl_mode": "require",
        },
        "redis": {
            "url": "${REDIS_URL}",
            "pool_size": 20,
            "ssl": True,
        },
        "security": {
            "secret_key": "${SECRET_KEY}",
            "jwt_secret_key": "${JWT_SECRET_KEY}",
        },
    },
}


def create_default_config(environment: str = "development", config_dir: str = "config"):
    """
    Create default configuration files for an environment.
    
    Args:
        environment: Environment name
        config_dir: Configuration directory
    """
    loader = YAMLConfigLoader(config_dir, environment)
    
    # Create base config
    base_config = DEFAULT_CONFIG_TEMPLATES.get("development", {}).copy()
    loader.save(base_config, "config.yaml")
    
    # Create environment-specific config
    if environment in DEFAULT_CONFIG_TEMPLATES:
        env_config = DEFAULT_CONFIG_TEMPLATES[environment]
        loader.save(env_config, f"config.{environment}.yaml")
    
    # Create README
    readme_content = """
    # Configuration Files
    
    This directory contains configuration files for the GOAT Prediction API Gateway.
    
    ## File Structure
    
    - `config.yaml` - Base configuration
    - `config.development.yaml` - Development environment overrides
    - `config.staging.yaml` - Staging environment overrides
    - `config.production.yaml` - Production environment overrides
    - `config.testing.yaml` - Testing environment overrides
    
    ## Configuration Loading Order
    
    1. Load `config.yaml` (base configuration)
    2. Load environment-specific file (e.g., `config.production.yaml`)
    3. Merge configurations (environment overrides base)
    4. Apply environment variables
    
    ## Environment Variables
    
    Configuration values can reference environment variables using `${VAR_NAME}` syntax.
    Default values can be specified using `${VAR_NAME:default_value}`.
    
    Example:
    ```yaml
    database:
      url: ${DATABASE_URL:postgresql://localhost:5432/app}
    ```
    
    ## Security Note
    
    Never commit secrets to version control. Use environment variables for:
    - Database passwords
    - API keys
    - JWT secrets
    - Encryption keys
    """
    
    readme_path = Path(config_dir) / "README.md"
    with open(readme_path, "w") as f:
        f.write(readme_content)


# Singleton configuration loader instance
_config_loader: Optional[YAMLConfigLoader] = None


def get_config_loader() -> YAMLConfigLoader:
    """Get singleton configuration loader instance."""
    global _config_loader
    
    if _config_loader is None:
        environment = os.getenv("ENVIRONMENT", "development")
        config_dir = os.getenv("CONFIG_DIR", "config")
        _config_loader = YAMLConfigLoader(config_dir, environment)
    
    return _config_loader


def get_config() -> Dict[str, Any]:
    """Get current configuration."""
    return get_config_loader().load()


def get_config_value(key: str, default: Any = None) -> Any:
    """Get configuration value using dot notation."""
    return get_config_loader().get_value(key, default)
