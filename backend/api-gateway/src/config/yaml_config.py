"""
YAML Configuration Handler for API Gateway
Manages loading, parsing, and validation of YAML configuration files
"""

import os
import yaml
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
from functools import lru_cache
from datetime import datetime

logger = logging.getLogger(__name__)


class YAMLConfigError(Exception):
    """Custom exception for YAML configuration errors"""
    pass


class YAMLConfig:
    """
    YAML Configuration Manager
    Handles loading and parsing YAML configuration files with validation
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize YAML configuration manager
        
        Args:
            config_path: Path to the main YAML configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config_cache: Dict[str, Any] = {}
        self._last_loaded: Optional[datetime] = None
        self._validate_config_path()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration path"""
        default_paths = [
            os.getenv('CONFIG_PATH'),
            './config/config.yaml',
            './config.yaml',
            '/etc/goat-prediction/config.yaml',
        ]
        
        for path in default_paths:
            if path and Path(path).exists():
                return path
        
        # Return first non-None path as fallback
        return next((p for p in default_paths if p), './config/config.yaml')
    
    def _validate_config_path(self) -> None:
        """Validate that configuration path exists and is readable"""
        path = Path(self.config_path)
        if not path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            return
        
        if not path.is_file():
            raise YAMLConfigError(f"Configuration path is not a file: {self.config_path}")
        
        if not os.access(self.config_path, os.R_OK):
            raise YAMLConfigError(f"Configuration file is not readable: {self.config_path}")
    
    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load YAML configuration from file
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary containing configuration data
        """
        if not force_reload and self._config_cache:
            logger.debug("Using cached configuration")
            return self._config_cache
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                config = {}
            
            self._config_cache = config
            self._last_loaded = datetime.now()
            logger.info(f"Successfully loaded configuration from {self.config_path}")
            
            return config
            
        except yaml.YAMLError as e:
            raise YAMLConfigError(f"Error parsing YAML file: {e}")
        except Exception as e:
            raise YAMLConfigError(f"Error loading configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key (supports nested keys with dot notation)
        
        Args:
            key: Configuration key (use dots for nested keys, e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = self.load()
        
        # Handle nested keys
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name
            
        Returns:
            Dictionary containing section data
        """
        config = self.load()
        return config.get(section, {})
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value (only in memory, not persisted)
        
        Args:
            key: Configuration key
            value: Value to set
        """
        config = self.load()
        
        # Handle nested keys
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        self._config_cache = config
        logger.debug(f"Set configuration key '{key}' to '{value}'")
    
    def merge(self, other_config: Dict[str, Any]) -> None:
        """
        Merge another configuration dictionary into current config
        
        Args:
            other_config: Dictionary to merge
        """
        config = self.load()
        self._deep_merge(config, other_config)
        self._config_cache = config
        logger.debug("Merged external configuration")
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """
        Deep merge two dictionaries
        
        Args:
            base: Base dictionary
            update: Dictionary to merge into base
            
        Returns:
            Merged dictionary
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def load_multiple(self, paths: List[str]) -> Dict[str, Any]:
        """
        Load and merge multiple YAML configuration files
        
        Args:
            paths: List of file paths to load
            
        Returns:
            Merged configuration dictionary
        """
        merged_config = {}
        
        for path in paths:
            if not Path(path).exists():
                logger.warning(f"Configuration file not found: {path}")
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    self._deep_merge(merged_config, config)
                    logger.info(f"Loaded configuration from {path}")
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
        
        return merged_config
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate configuration against a schema
        
        Args:
            schema: Schema dictionary defining required keys and types
            
        Returns:
            True if valid, raises YAMLConfigError if invalid
        """
        config = self.load()
        return self._validate_dict(config, schema, "root")
    
    def _validate_dict(self, config: Dict, schema: Dict, path: str) -> bool:
        """
        Recursively validate dictionary against schema
        
        Args:
            config: Configuration dictionary to validate
            schema: Schema dictionary
            path: Current path in config (for error messages)
            
        Returns:
            True if valid
        """
        for key, expected_type in schema.items():
            if key not in config:
                raise YAMLConfigError(f"Missing required key: {path}.{key}")
            
            value = config[key]
            
            if isinstance(expected_type, dict):
                if not isinstance(value, dict):
                    raise YAMLConfigError(
                        f"Expected dict at {path}.{key}, got {type(value).__name__}"
                    )
                self._validate_dict(value, expected_type, f"{path}.{key}")
            elif isinstance(expected_type, type):
                if not isinstance(value, expected_type):
                    raise YAMLConfigError(
                        f"Expected {expected_type.__name__} at {path}.{key}, "
                        f"got {type(value).__name__}"
                    )
        
        return True
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file
        
        Args:
            path: File path to save to (uses current config_path if not provided)
        """
        save_path = path or self.config_path
        config = self.load()
        
        try:
            # Create directory if it doesn't exist
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    config,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )
            
            logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            raise YAMLConfigError(f"Error saving configuration: {e}")
    
    def reload(self) -> Dict[str, Any]:
        """
        Force reload configuration from file
        
        Returns:
            Reloaded configuration dictionary
        """
        return self.load(force_reload=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary
        
        Returns:
            Configuration dictionary
        """
        return self.load().copy()
    
    def clear_cache(self) -> None:
        """Clear configuration cache"""
        self._config_cache = {}
        self._last_loaded = None
        logger.debug("Configuration cache cleared")
    
    def get_all_keys(self, prefix: str = "") -> List[str]:
        """
        Get all configuration keys as flat list
        
        Args:
            prefix: Prefix to filter keys
            
        Returns:
            List of configuration keys
        """
        config = self.load()
        return self._flatten_keys(config, prefix)
    
    def _flatten_keys(self, d: Dict, prefix: str = "") -> List[str]:
        """
        Flatten nested dictionary keys
        
        Args:
            d: Dictionary to flatten
            prefix: Current prefix
            
        Returns:
            List of flattened keys
        """
        keys = []
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.append(full_key)
            
            if isinstance(value, dict):
                keys.extend(self._flatten_keys(value, full_key))
        
        return keys
    
    def has_key(self, key: str) -> bool:
        """
        Check if configuration key exists
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists
        """
        config = self.load()
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False
        
        return True
    
    def delete_key(self, key: str) -> bool:
        """
        Delete configuration key
        
        Args:
            key: Configuration key to delete
            
        Returns:
            True if deleted, False if key didn't exist
        """
        config = self.load()
        keys = key.split('.')
        
        # Navigate to parent
        current = config
        for k in keys[:-1]:
            if k not in current:
                return False
            current = current[k]
        
        # Delete final key
        if keys[-1] in current:
            del current[keys[-1]]
            self._config_cache = config
            logger.debug(f"Deleted configuration key: {key}")
            return True
        
        return False
    
    @property
    def last_loaded(self) -> Optional[datetime]:
        """Get timestamp of last configuration load"""
        return self._last_loaded
    
    @property
    def config_file_exists(self) -> bool:
        """Check if configuration file exists"""
        return Path(self.config_path).exists()
    
    def __repr__(self) -> str:
        """String representation"""
        return f"YAMLConfig(path='{self.config_path}', loaded={self._last_loaded})"
    
    def __str__(self) -> str:
        """String conversion"""
        return self.__repr__()


@lru_cache(maxsize=1)
def get_yaml_config(config_path: Optional[str] = None) -> YAMLConfig:
    """
    Get singleton instance of YAMLConfig
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        YAMLConfig instance
    """
    return YAMLConfig(config_path)


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML file and return its contents
    
    Args:
        file_path: Path to YAML file
        
    Returns:
        Dictionary containing YAML data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}")
        return {}


def save_yaml_file(data: Dict[str, Any], file_path: str) -> bool:
    """
    Save dictionary to YAML file
    
    Args:
        data: Dictionary to save
        file_path: Path to save file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                data,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        return True
    except Exception as e:
        logger.error(f"Error saving YAML file {file_path}: {e}")
        return False
