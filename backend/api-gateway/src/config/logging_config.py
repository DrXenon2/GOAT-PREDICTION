"""
GOAT PREDICTION ULTIMATE - Logging Configuration
Configuration avancée du système de logging
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
from datetime import datetime

from .settings import settings


class JSONFormatter(logging.Formatter):
    """Formateur JSON pour logs structurés"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formate un record de log en JSON
        
        Args:
            record: Record de log
        
        Returns:
            String JSON
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }
        
        # Ajouter l'exception si présente
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Ajouter les champs extras
        if hasattr(record, "extra_fields"):
            log_data["extra"] = record.extra_fields
        
        # Ajouter le contexte de requête si disponible
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Formateur avec couleurs pour la console"""
    
    # Codes de couleurs ANSI
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Vert
        'WARNING': '\033[33m',    # Jaune
        'ERROR': '\033[31m',      # Rouge
        'CRITICAL': '\033[35m\033[1m',  # Magenta gras
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formate un record avec des couleurs
        
        Args:
            record: Record de log
        
        Returns:
            String formatée avec couleurs
        """
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET
        
        # Format de base
        log_fmt = (
            f"{color}[%(levelname)s]{reset} "
            f"%(asctime)s - "
            f"%(name)s - "
            f"%(message)s"
        )
        
        # Ajouter le nom de la fonction en mode DEBUG
        if record.levelno == logging.DEBUG:
            log_fmt += f" {color}(%(funcName)s:%(lineno)d){reset}"
        
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


class RequestContextFilter(logging.Filter):
    """Filtre pour ajouter le contexte de requête aux logs"""
    
    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Ajoute le contexte au record
        
        Args:
            record: Record de log
        
        Returns:
            True pour inclure le log
        """
        if self.request_id:
            record.request_id = self.request_id
        
        if self.user_id:
            record.user_id = self.user_id
        
        return True
    
    def set_context(self, request_id: Optional[str] = None, user_id: Optional[str] = None):
        """Définit le contexte"""
        self.request_id = request_id
        self.user_id = user_id


class LoggingConfig:
    """Configuration du système de logging"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.context_filter = RequestContextFilter()
    
    def setup(
        self,
        name: str = "goat_api_gateway",
        level: Optional[str] = None,
        log_file: Optional[Path] = None,
        json_format: bool = False,
        enable_console: bool = True,
    ) -> logging.Logger:
        """
        Configure un logger
        
        Args:
            name: Nom du logger
            level: Niveau de log
            log_file: Fichier de log optionnel
            json_format: Utiliser le format JSON
            enable_console: Activer la sortie console
        
        Returns:
            Logger configuré
        """
        # Éviter la duplication
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        
        # Nettoyer les handlers existants
        logger.handlers.clear()
        
        # Niveau de log
        log_level = level or settings.LOG_LEVEL
        logger.setLevel(getattr(logging, log_level.upper()))
        
        # Ajouter le filtre de contexte
        logger.addFilter(self.context_filter)
        
        # Handler console
        if enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
            
            if json_format or settings.LOG_FORMAT == "json":
                console_handler.setFormatter(JSONFormatter())
            else:
                console_handler.setFormatter(ColoredFormatter())
            
            logger.addHandler(console_handler)
        
        # Handler fichier
        if log_file or settings.LOG_FILE:
            file_path = Path(log_file or settings.LOG_FILE)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Rotation par taille
            file_handler = RotatingFileHandler(
                filename=file_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(JSONFormatter())
            
            logger.addHandler(file_handler)
        
        # Désactiver la propagation pour éviter les doublons
        logger.propagate = False
        
        self.loggers[name] = logger
        return logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Récupère ou crée un logger
        
        Args:
            name: Nom du logger
        
        Returns:
            Logger
        """
        if name not in self.loggers:
            return self.setup(name)
        return self.loggers[name]
    
    def set_request_context(self, request_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Définit le contexte de requête pour tous les logs
        
        Args:
            request_id: ID de la requête
            user_id: ID de l'utilisateur
        """
        self.context_filter.set_context(request_id, user_id)


# Instance globale
_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """Singleton pour LoggingConfig"""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config


def setup_logging(
    name: str = "goat_api_gateway",
    **kwargs
) -> logging.Logger:
    """Configure le logging"""
    return get_logging_config().setup(name, **kwargs)


def get_logger(name: str) -> logging.Logger:
    """Récupère un logger"""
    return get_logging_config().get_logger(name)


def configure_root_logger():
    """Configure le logger racine"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
