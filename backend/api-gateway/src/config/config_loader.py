"""
GOAT PREDICTION ULTIMATE - Configuration Loader
Chargement dynamique de configurations depuis YAML/JSON
"""

import yaml
import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import lru_cache

from .settings import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Gestionnaire de chargement de configurations"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialise le loader de configuration
        
        Args:
            config_dir: Répertoire des fichiers de configuration
        """
        self.config_dir = config_dir or Path(__file__).parent.parent.parent / "config"
        self.cache: Dict[str, Any] = {}
        
        logger.info(f"ConfigLoader initialized with directory: {self.config_dir}")
    
    def load_yaml(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Charge un fichier YAML
        
        Args:
            filename: Nom du fichier (avec ou sans extension)
            use_cache: Utiliser le cache si disponible
        
        Returns:
            Dictionnaire de configuration
        """
        # Ajouter extension si manquante
        if not filename.endswith(('.yaml', '.yml')):
            filename = f"{filename}.yaml"
        
        # Vérifier le cache
        cache_key = f"yaml:{filename}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Loading {filename} from cache")
            return self.cache[cache_key]
        
        # Charger le fichier
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            logger.error(f"Config file not found: {file_path}")
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Successfully loaded YAML config: {filename}")
            
            # Mettre en cache
            if use_cache:
                self.cache[cache_key] = config
            
            return config
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filename}: {e}")
            raise ValueError(f"Invalid YAML in {filename}: {e}")
        except Exception as e:
            logger.error(f"Error loading YAML file {filename}: {e}")
            raise
    
    def load_json(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Charge un fichier JSON
        
        Args:
            filename: Nom du fichier (avec ou sans extension)
            use_cache: Utiliser le cache si disponible
        
        Returns:
            Dictionnaire de configuration
        """
        # Ajouter extension si manquante
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        # Vérifier le cache
        cache_key = f"json:{filename}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Loading {filename} from cache")
            return self.cache[cache_key]
        
        # Charger le fichier
        file_path = self.config_dir / filename
        
        if not file_path.exists():
            logger.error(f"Config file not found: {file_path}")
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Successfully loaded JSON config: {filename}")
            
            # Mettre en cache
            if use_cache:
                self.cache[cache_key] = config
            
            return config
        
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {filename}: {e}")
            raise ValueError(f"Invalid JSON in {filename}: {e}")
        except Exception as e:
            logger.error(f"Error loading JSON file {filename}: {e}")
            raise
    
    def load(self, filename: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Charge un fichier de configuration (auto-détection du format)
        
        Args:
            filename: Nom du fichier
            use_cache: Utiliser le cache si disponible
        
        Returns:
            Dictionnaire de configuration
        """
        if filename.endswith('.json'):
            return self.load_json(filename, use_cache)
        elif filename.endswith(('.yaml', '.yml')):
            return self.load_yaml(filename, use_cache)
        else:
            # Essayer YAML par défaut
            try:
                return self.load_yaml(filename, use_cache)
            except FileNotFoundError:
                return self.load_json(filename, use_cache)
    
    def get(self, filename: str, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur spécifique d'un fichier de config
        
        Args:
            filename: Nom du fichier
            key: Clé à récupérer (support de notation pointée: "section.subsection.key")
            default: Valeur par défaut si la clé n'existe pas
        
        Returns:
            Valeur de configuration
        """
        config = self.load(filename)
        
        # Support de la notation pointée
        keys = key.split('.')
        value = config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                logger.warning(f"Key '{key}' not found in {filename}, returning default")
                return default
        
        return value
    
    def clear_cache(self, filename: Optional[str] = None):
        """
        Vide le cache
        
        Args:
            filename: Nom du fichier spécifique (ou None pour tout vider)
        """
        if filename:
            # Vider le cache pour un fichier spécifique
            keys_to_remove = [k for k in self.cache.keys() if filename in k]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Cache cleared for {filename}")
        else:
            # Vider tout le cache
            self.cache.clear()
            logger.info("All cache cleared")
    
    def reload(self, filename: str) -> Dict[str, Any]:
        """
        Recharge un fichier de configuration (ignore le cache)
        
        Args:
            filename: Nom du fichier
        
        Returns:
            Dictionnaire de configuration rechargé
        """
        self.clear_cache(filename)
        return self.load(filename, use_cache=False)
    
    def merge_configs(self, *filenames: str) -> Dict[str, Any]:
        """
        Fusionne plusieurs fichiers de configuration
        
        Args:
            *filenames: Noms des fichiers à fusionner
        
        Returns:
            Dictionnaire fusionné
        """
        merged = {}
        
        for filename in filenames:
            config = self.load(filename)
            merged = self._deep_merge(merged, config)
        
        logger.info(f"Merged {len(filenames)} config files")
        return merged
    
    @staticmethod
    def _deep_merge(dict1: Dict, dict2: Dict) -> Dict:
        """
        Fusionne profondément deux dictionnaires
        
        Args:
            dict1: Premier dictionnaire
            dict2: Second dictionnaire (prioritaire)
        
        Returns:
            Dictionnaire fusionné
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result


# Instance globale
@lru_cache()
def get_config_loader() -> ConfigLoader:
    """Singleton du ConfigLoader"""
    return ConfigLoader()


# Raccourcis pour faciliter l'utilisation
def load_config(filename: str, use_cache: bool = True) -> Dict[str, Any]:
    """Charge une configuration"""
    return get_config_loader().load(filename, use_cache)


def get_config_value(filename: str, key: str, default: Any = None) -> Any:
    """Récupère une valeur de configuration"""
    return get_config_loader().get(filename, key, default)


def reload_config(filename: str) -> Dict[str, Any]:
    """Recharge une configuration"""
    return get_config_loader().reload(filename)
