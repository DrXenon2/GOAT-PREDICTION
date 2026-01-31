"""
GOAT PREDICTION ULTIMATE - Environment Configuration
Gestion avancée des variables d'environnement
"""

import os
from typing import Any, Optional, Dict, List, Union
from pathlib import Path
from dotenv import load_dotenv

from ..core.logging import get_logger

logger = get_logger(__name__)


class EnvConfig:
    """Gestionnaire des variables d'environnement"""
    
    def __init__(self, env_file: Optional[str] = None, override: bool = False):
        """
        Initialise le gestionnaire d'environnement
        
        Args:
            env_file: Chemin vers le fichier .env
            override: Si True, écrase les variables existantes
        """
        self.env_file = env_file or self._find_env_file()
        self.override = override
        self._loaded = False
        
        # Charger automatiquement
        self.load()
    
    @staticmethod
    def _find_env_file() -> Optional[Path]:
        """
        Trouve automatiquement le fichier .env
        
        Returns:
            Chemin vers le fichier .env ou None
        """
        # Chercher dans le répertoire courant et parents
        current = Path.cwd()
        
        for _ in range(5):  # Remonter jusqu'à 5 niveaux
            env_path = current / ".env"
            if env_path.exists():
                logger.info(f"Found .env file at: {env_path}")
                return env_path
            
            # Chercher .env.local
            env_local = current / ".env.local"
            if env_local.exists():
                logger.info(f"Found .env.local file at: {env_local}")
                return env_local
            
            current = current.parent
        
        logger.warning("No .env file found")
        return None
    
    def load(self) -> bool:
        """
        Charge les variables d'environnement depuis le fichier
        
        Returns:
            True si chargé avec succès
        """
        if self._loaded:
            logger.debug("Environment already loaded")
            return True
        
        if self.env_file and Path(self.env_file).exists():
            load_dotenv(self.env_file, override=self.override)
            self._loaded = True
            logger.info(f"Environment variables loaded from: {self.env_file}")
            return True
        else:
            logger.warning(f"Environment file not found: {self.env_file}")
            return False
    
    def get(
        self,
        key: str,
        default: Any = None,
        cast: Optional[type] = None,
        required: bool = False
    ) -> Any:
        """
        Récupère une variable d'environnement
        
        Args:
            key: Nom de la variable
            default: Valeur par défaut
            cast: Type de conversion
            required: Si True, lève une exception si absent
        
        Returns:
            Valeur de la variable
        """
        value = os.getenv(key, default)
        
        if required and value is None:
            raise ValueError(f"Required environment variable '{key}' not found")
        
        if value is None:
            return default
        
        # Conversion de type
        if cast:
            try:
                if cast == bool:
                    return self._parse_bool(value)
                elif cast == list:
                    return self._parse_list(value)
                elif cast == dict:
                    return self._parse_dict(value)
                else:
                    return cast(value)
            except (ValueError, TypeError) as e:
                logger.error(f"Error casting {key} to {cast}: {e}")
                return default
        
        return value
    
    @staticmethod
    def _parse_bool(value: Union[str, bool]) -> bool:
        """Parse une valeur booléenne"""
        if isinstance(value, bool):
            return value
        
        value = str(value).lower()
        return value in ('true', '1', 'yes', 'on', 'enabled')
    
    @staticmethod
    def _parse_list(value: Union[str, list]) -> List[str]:
        """Parse une liste depuis une string"""
        if isinstance(value, list):
            return value
        
        # Support de formats: "a,b,c" ou "a;b;c" ou "['a','b','c']"
        value = str(value).strip()
        
        if value.startswith('[') and value.endswith(']'):
            value = value[1:-1]
        
        separator = ',' if ',' in value else ';'
        return [item.strip().strip("'\"") for item in value.split(separator) if item.strip()]
    
    @staticmethod
    def _parse_dict(value: Union[str, dict]) -> Dict[str, Any]:
        """Parse un dictionnaire depuis une string"""
        if isinstance(value, dict):
            return value
        
        import json
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse dict from: {value}")
            return {}
    
    def get_int(self, key: str, default: int = 0, required: bool = False) -> int:
        """Récupère un entier"""
        return self.get(key, default, int, required)
    
    def get_float(self, key: str, default: float = 0.0, required: bool = False) -> float:
        """Récupère un float"""
        return self.get(key, default, float, required)
    
    def get_bool(self, key: str, default: bool = False, required: bool = False) -> bool:
        """Récupère un booléen"""
        return self.get(key, default, bool, required)
    
    def get_list(self, key: str, default: Optional[List] = None, required: bool = False) -> List:
        """Récupère une liste"""
        return self.get(key, default or [], list, required)
    
    def get_dict(self, key: str, default: Optional[Dict] = None, required: bool = False) -> Dict:
        """Récupère un dictionnaire"""
        return self.get(key, default or {}, dict, required)
    
    def set(self, key: str, value: Any) -> None:
        """
        Définit une variable d'environnement
        
        Args:
            key: Nom de la variable
            value: Valeur
        """
        os.environ[key] = str(value)
        logger.debug(f"Environment variable set: {key}")
    
    def has(self, key: str) -> bool:
        """
        Vérifie si une variable existe
        
        Args:
            key: Nom de la variable
        
        Returns:
            True si la variable existe
        """
        return key in os.environ
    
    def get_all(self, prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Récupère toutes les variables d'environnement
        
        Args:
            prefix: Préfixe optionnel pour filtrer
        
        Returns:
            Dictionnaire des variables
        """
        if prefix:
            return {
                key: value
                for key, value in os.environ.items()
                if key.startswith(prefix)
            }
        return dict(os.environ)
    
    def reload(self) -> bool:
        """
        Recharge les variables depuis le fichier
        
        Returns:
            True si rechargé avec succès
        """
        self._loaded = False
        return self.load()
    
    def validate_required(self, *keys: str) -> None:
        """
        Valide que les variables requises sont présentes
        
        Args:
            *keys: Noms des variables requises
        
        Raises:
            ValueError: Si une variable est manquante
        """
        missing = [key for key in keys if not self.has(key)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        logger.info(f"All required environment variables present: {', '.join(keys)}")


# Instance globale
_env_config: Optional[EnvConfig] = None


def get_env_config() -> EnvConfig:
    """Singleton pour EnvConfig"""
    global _env_config
    if _env_config is None:
        _env_config = EnvConfig()
    return _env_config


def load_env_config(env_file: Optional[str] = None, override: bool = False) -> EnvConfig:
    """
    Charge la configuration d'environnement
    
    Args:
        env_file: Chemin vers le fichier .env
        override: Si True, écrase les variables existantes
    
    Returns:
        Instance de EnvConfig
    """
    global _env_config
    _env_config = EnvConfig(env_file, override)
    return _env_config


# Raccourcis pour faciliter l'utilisation
def getenv(key: str, default: Any = None, cast: Optional[type] = None) -> Any:
    """Raccourci pour récupérer une variable d'environnement"""
    return get_env_config().get(key, default, cast)


def setenv(key: str, value: Any) -> None:
    """Raccourci pour définir une variable d'environnement"""
    get_env_config().set(key, value)


def hasenv(key: str) -> bool:
    """Raccourci pour vérifier si une variable existe"""
    return get_env_config().has(key)
