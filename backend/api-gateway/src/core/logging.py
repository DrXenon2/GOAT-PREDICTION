"""
Core Logging Module for API Gateway
Centralized logging configuration and utilities
"""

import os
import sys
import logging
import logging.config
from typing import Optional, Dict, Any
from pathlib import Path
import yaml
from functools import lru_cache
from datetime import datetime
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Bold Red
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with colors
        
        Args:
            record: Log record
            
        Returns:
            Colored log string
        """
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Color the level name
        record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter for adding context"""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process log message with additional context
        
        Args:
            msg: Log message
            kwargs: Additional keyword arguments
            
        Returns:
            Processed message and kwargs
        """
        # Add request ID if available
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        if hasattr(self, 'request_id'):
            kwargs['extra']['request_id'] = self.request_id
        
        return msg, kwargs


class LogManager:
    """Central logging manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize log manager
        
        Args:
            config_path: Path to logging configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self._configured = False
        self._loggers: Dict[str, logging.Logger] = {}
    
    def _get_default_config_path(self) -> str:
        """Get default logging configuration path"""
        possible_paths = [
            'backend/api-gateway/src/config/logging.yaml',
            'src/config/logging.yaml',
            'config/logging.yaml',
            'logging.yaml',
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        return 'config/logging.yaml'
    
    def configure(self, force: bool = False) -> None:
        """
        Configure logging from YAML file
        
        Args:
            force: Force reconfiguration even if already configured
        """
        if self._configured and not force:
            return
        
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Get environment-specific config
                env = os.getenv('ENVIRONMENT', 'development').lower()
                if env in config:
                    env_config = config[env]
                    # Merge with base config
                    base_config = {k: v for k, v in config.items() if k not in ['development', 'production', 'staging', 'testing']}
                    self._deep_merge(base_config, env_config)
                    config = base_config
                
                # Create log directories
                self._create_log_directories(config)
                
                # Apply configuration
                logging.config.dictConfig(config)
                self._configured = True
                
                logger = logging.getLogger(__name__)
                logger.info(f"Logging configured from {self.config_path} for environment: {env}")
            else:
                # Fallback to basic configuration
                self._configure_basic()
                
        except Exception as e:
            print(f"Error configuring logging: {e}", file=sys.stderr)
            self._configure_basic()
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def _create_log_directories(self, config: Dict[str, Any]) -> None:
        """Create log directories from configuration"""
        handlers = config.get('handlers', {})
        
        for handler_config in handlers.values():
            if 'filename' in handler_config:
                log_file = Path(handler_config['filename'])
                log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _configure_basic(self) -> None:
        """Configure basic logging as fallback"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        self._configured = True
        
        logger = logging.getLogger(__name__)
        logger.warning("Using basic logging configuration (config file not found)")
    
    def get_logger(
        self,
        name: str,
        level: Optional[int] = None,
        **context
    ) -> logging.Logger:
        """
        Get or create a logger
        
        Args:
            name: Logger name
            level: Optional log level
            **context: Additional context for logger
            
        Returns:
            Logger instance
        """
        if not self._configured:
            self.configure()
        
        if name not in self._loggers:
            logger = logging.getLogger(name)
            if level:
                logger.setLevel(level)
            self._loggers[name] = logger
        
        logger = self._loggers[name]
        
        # Add context if provided
        if context:
            return LoggerAdapter(logger, context)
        
        return logger
    
    def set_level(self, level: int, logger_name: Optional[str] = None) -> None:
        """
        Set logging level
        
        Args:
            level: Log level (logging.DEBUG, INFO, etc.)
            logger_name: Specific logger name, or None for root logger
        """
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()
        
        logger.setLevel(level)
    
    def add_handler(
        self,
        handler: logging.Handler,
        logger_name: Optional[str] = None
    ) -> None:
        """
        Add handler to logger
        
        Args:
            handler: Logging handler
            logger_name: Logger name, or None for root logger
        """
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()
        
        logger.addHandler(handler)
    
    def remove_handler(
        self,
        handler: logging.Handler,
        logger_name: Optional[str] = None
    ) -> None:
        """
        Remove handler from logger
        
        Args:
            handler: Logging handler
            logger_name: Logger name, or None for root logger
        """
        if logger_name:
            logger = logging.getLogger(logger_name)
        else:
            logger = logging.getLogger()
        
        logger.removeHandler(handler)
    
    def shutdown(self) -> None:
        """Shutdown logging system"""
        logging.shutdown()


# Singleton instance
_log_manager: Optional[LogManager] = None


@lru_cache(maxsize=1)
def get_log_manager(config_path: Optional[str] = None) -> LogManager:
    """
    Get singleton log manager instance
    
    Args:
        config_path: Path to logging configuration
        
    Returns:
        LogManager instance
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(config_path)
        _log_manager.configure()
    return _log_manager


def get_logger(
    name: str,
    level: Optional[int] = None,
    **context
) -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name (usually __name__)
        level: Optional log level
        **context: Additional context
        
    Returns:
        Logger instance
    """
    return get_log_manager().get_logger(name, level, **context)


def configure_logging(config_path: Optional[str] = None, force: bool = False) -> None:
    """
    Configure logging system
    
    Args:
        config_path: Path to logging configuration file
        force: Force reconfiguration
    """
    manager = get_log_manager(config_path)
    manager.configure(force=force)


def set_log_level(level: int, logger_name: Optional[str] = None) -> None:
    """
    Set logging level
    
    Args:
        level: Log level
        logger_name: Logger name, or None for root
    """
    get_log_manager().set_level(level, logger_name)


# Convenience functions for structured logging

def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra
) -> None:
    """
    Log HTTP request
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        **extra: Additional fields
    """
    logger.info(
        f"{method} {path} {status_code} - {duration_ms:.2f}ms",
        extra={
            "extra_fields": {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                **extra
            }
        }
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log error with context
    
    Args:
        logger: Logger instance
        error: Exception
        context: Additional context
    """
    extra_fields = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        extra_fields.update(context)
    
    logger.error(
        f"Error occurred: {str(error)}",
        exc_info=error,
        extra={"extra_fields": extra_fields}
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    **metrics
) -> None:
    """
    Log performance metrics
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        **metrics: Additional metrics
    """
    logger.info(
        f"Performance: {operation} completed in {duration_ms:.2f}ms",
        extra={
            "extra_fields": {
                "operation": operation,
                "duration_ms": duration_ms,
                **metrics
            }
        }
    )


# Export all
__all__ = [
    'LogManager',
    'JSONFormatter',
    'ColoredFormatter',
    'LoggerAdapter',
    'get_log_manager',
    'get_logger',
    'configure_logging',
    'set_log_level',
    'log_request',
    'log_error',
    'log_performance',
]
