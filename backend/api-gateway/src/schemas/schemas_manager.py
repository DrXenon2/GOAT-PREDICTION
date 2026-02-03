"""
GOAT PREDICTION ULTIMATE - Schema Manager
Gestionnaire centralisé pour validation et sérialisation des schémas
"""

from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Dict, Any, List, Optional, Callable
from functools import wraps, lru_cache
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


# ============================================
# SCHEMA VALIDATOR
# ============================================

class SchemaValidator:
    """Validateur de schémas Pydantic"""
    
    def __init__(self):
        self._validators: Dict[str, Type[BaseModel]] = {}
        self._custom_validators: Dict[str, Callable] = {}
    
    def register(self, name: str, schema: Type[BaseModel]) -> None:
        """
        Enregistre un schéma
        
        Args:
            name: Nom du schéma
            schema: Classe Pydantic
        """
        self._validators[name] = schema
        logger.info(f"Schéma enregistré: {name}")
    
    def register_custom(self, name: str, validator: Callable) -> None:
        """
        Enregistre un validateur personnalisé
        
        Args:
            name: Nom du validateur
            validator: Fonction de validation
        """
        self._custom_validators[name] = validator
        logger.info(f"Validateur personnalisé enregistré: {name}")
    
    def validate(self, schema_name: str, data: Dict[str, Any]) -> BaseModel:
        """
        Valide des données contre un schéma
        
        Args:
            schema_name: Nom du schéma
            data: Données à valider
            
        Returns:
            Instance du modèle validée
            
        Raises:
            ValueError: Si le schéma n'existe pas
            ValidationError: Si les données sont invalides
        """
        if schema_name not in self._validators:
            raise ValueError(f"Schéma non trouvé: {schema_name}")
        
        schema = self._validators[schema_name]
        
        try:
            validated = schema(**data)
            logger.debug(f"Validation réussie: {schema_name}")
            return validated
        except ValidationError as e:
            logger.error(f"Erreur de validation {schema_name}: {e}")
            raise
    
    def validate_custom(self, validator_name: str, data: Any) -> Any:
        """
        Valide avec un validateur personnalisé
        
        Args:
            validator_name: Nom du validateur
            data: Données à valider
            
        Returns:
            Données validées
        """
        if validator_name not in self._custom_validators:
            raise ValueError(f"Validateur non trouvé: {validator_name}")
        
        validator = self._custom_validators[validator_name]
        return validator(data)
    
    def validate_many(
        self, 
        schema_name: str, 
        data_list: List[Dict[str, Any]]
    ) -> List[BaseModel]:
        """
        Valide plusieurs instances
        
        Args:
            schema_name: Nom du schéma
            data_list: Liste de données
            
        Returns:
            Liste d'instances validées
        """
        return [self.validate(schema_name, data) for data in data_list]
    
    def get_schema(self, name: str) -> Optional[Type[BaseModel]]:
        """Récupère un schéma par son nom"""
        return self._validators.get(name)
    
    def list_schemas(self) -> List[str]:
        """Liste tous les schémas enregistrés"""
        return list(self._validators.keys())


# ============================================
# SCHEMA SERIALIZER
# ============================================

class SchemaSerializer:
    """Sérialiseur de schémas Pydantic"""
    
    @staticmethod
    def to_dict(
        model: BaseModel, 
        exclude_none: bool = True,
        exclude_unset: bool = False,
        by_alias: bool = False
    ) -> Dict[str, Any]:
        """
        Convertit un modèle en dictionnaire
        
        Args:
            model: Instance du modèle
            exclude_none: Exclure les valeurs None
            exclude_unset: Exclure les valeurs non définies
            by_alias: Utiliser les alias
            
        Returns:
            Dictionnaire
        """
        return model.dict(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=by_alias
        )
    
    @staticmethod
    def to_json(
        model: BaseModel,
        exclude_none: bool = True,
        exclude_unset: bool = False,
        by_alias: bool = False,
        indent: Optional[int] = None
    ) -> str:
        """
        Convertit un modèle en JSON
        
        Args:
            model: Instance du modèle
            exclude_none: Exclure les valeurs None
            exclude_unset: Exclure les valeurs non définies
            by_alias: Utiliser les alias
            indent: Indentation JSON
            
        Returns:
            String JSON
        """
        return model.json(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            indent=indent
        )
    
    @staticmethod
    def from_dict(
        schema: Type[T],
        data: Dict[str, Any]
    ) -> T:
        """
        Crée une instance depuis un dictionnaire
        
        Args:
            schema: Classe du schéma
            data: Données
            
        Returns:
            Instance du modèle
        """
        return schema(**data)
    
    @staticmethod
    def from_json(
        schema: Type[T],
        json_str: str
    ) -> T:
        """
        Crée une instance depuis JSON
        
        Args:
            schema: Classe du schéma
            json_str: String JSON
            
        Returns:
            Instance du modèle
        """
        return schema.parse_raw(json_str)
    
    @staticmethod
    def to_dict_many(
        models: List[BaseModel],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Convertit plusieurs modèles en dictionnaires"""
        return [
            SchemaSerializer.to_dict(model, **kwargs)
            for model in models
        ]
    
    @staticmethod
    def from_dict_many(
        schema: Type[T],
        data_list: List[Dict[str, Any]]
    ) -> List[T]:
        """Crée plusieurs instances depuis des dictionnaires"""
        return [
            SchemaSerializer.from_dict(schema, data)
            for data in data_list
        ]


# ============================================
# SCHEMA TRANSFORMER
# ============================================

class SchemaTransformer:
    """Transformateur de schémas"""
    
    @staticmethod
    def transform(
        source: BaseModel,
        target_schema: Type[T],
        mapping: Optional[Dict[str, str]] = None
    ) -> T:
        """
        Transforme un schéma en un autre
        
        Args:
            source: Modèle source
            target_schema: Schéma cible
            mapping: Mapping de champs (source -> target)
            
        Returns:
            Instance du schéma cible
        """
        source_dict = source.dict()
        
        if mapping:
            target_dict = {}
            for source_field, target_field in mapping.items():
                if source_field in source_dict:
                    target_dict[target_field] = source_dict[source_field]
        else:
            target_dict = source_dict
        
        return target_schema(**target_dict)
    
    @staticmethod
    def merge(
        *models: BaseModel,
        priority: str = "last"
    ) -> Dict[str, Any]:
        """
        Fusionne plusieurs modèles
        
        Args:
            models: Modèles à fusionner
            priority: Priorité en cas de conflit ('first' ou 'last')
            
        Returns:
            Dictionnaire fusionné
        """
        merged = {}
        
        model_list = models if priority == "last" else reversed(models)
        
        for model in model_list:
            merged.update(model.dict(exclude_none=True))
        
        return merged
    
    @staticmethod
    def extract_fields(
        model: BaseModel,
        fields: List[str]
    ) -> Dict[str, Any]:
        """
        Extrait certains champs d'un modèle
        
        Args:
            model: Modèle source
            fields: Liste de champs à extraire
            
        Returns:
            Dictionnaire avec les champs extraits
        """
        model_dict = model.dict()
        return {
            field: model_dict[field]
            for field in fields
            if field in model_dict
        }


# ============================================
# DECORATORS
# ============================================

def validate_schema(schema: Type[BaseModel]):
    """
    Décorateur pour valider les arguments de fonction
    
    Usage:
        @validate_schema(UserCreate)
        def create_user(user_data: dict):
            # user_data sera validé automatiquement
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Valider le premier argument dict
            for arg in args:
                if isinstance(arg, dict):
                    validated = schema(**arg)
                    args = tuple(
                        validated if isinstance(a, dict) else a
                        for a in args
                    )
                    break
            
            # Valider les kwargs
            if kwargs:
                for key, value in kwargs.items():
                    if isinstance(value, dict):
                        kwargs[key] = schema(**value)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def serialize_model(
    exclude_none: bool = True,
    exclude_unset: bool = False,
    by_alias: bool = False
):
    """
    Décorateur pour sérialiser automatiquement le retour
    
    Usage:
        @serialize_model()
        def get_user() -> User:
            return User(...)
            # Retournera un dict au lieu de User
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if isinstance(result, BaseModel):
                return SchemaSerializer.to_dict(
                    result,
                    exclude_none=exclude_none,
                    exclude_unset=exclude_unset,
                    by_alias=by_alias
                )
            elif isinstance(result, list) and result and isinstance(result[0], BaseModel):
                return SchemaSerializer.to_dict_many(
                    result,
                    exclude_none=exclude_none,
                    exclude_unset=exclude_unset,
                    by_alias=by_alias
                )
            
            return result
        return wrapper
    return decorator


# ============================================
# SINGLETON INSTANCE
# ============================================

@lru_cache(maxsize=1)
def get_schema_validator() -> SchemaValidator:
    """Récupère l'instance singleton du validateur"""
    return SchemaValidator()


@lru_cache(maxsize=1)
def get_schema_serializer() -> SchemaSerializer:
    """Récupère l'instance singleton du sérialiseur"""
    return SchemaSerializer()


@lru_cache(maxsize=1)
def get_schema_transformer() -> SchemaTransformer:
    """Récupère l'instance singleton du transformateur"""
    return SchemaTransformer()


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def validate_data(schema: Type[T], data: Dict[str, Any]) -> T:
    """
    Fonction utilitaire pour valider des données
    
    Args:
        schema: Schéma Pydantic
        data: Données à valider
        
    Returns:
        Instance validée
    """
    return schema(**data)


def serialize_to_dict(model: BaseModel, **kwargs) -> Dict[str, Any]:
    """Fonction utilitaire pour sérialiser en dict"""
    serializer = get_schema_serializer()
    return serializer.to_dict(model, **kwargs)


def serialize_to_json(model: BaseModel, **kwargs) -> str:
    """Fonction utilitaire pour sérialiser en JSON"""
    serializer = get_schema_serializer()
    return serializer.to_json(model, **kwargs)


# ============================================
# AUTO-REGISTRATION
# ============================================

def auto_register_schemas():
    """
    Enregistre automatiquement tous les schémas disponibles
    
    À appeler au démarrage de l'application
    """
    validator = get_schema_validator()
    
    # Import des schémas
    from . import predictions, bets, responses
    
    # Enregistrer les schémas de prédictions
    for name in dir(predictions):
        obj = getattr(predictions, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            validator.register(f"predictions.{name}", obj)
    
    # Enregistrer les schémas de paris
    for name in dir(bets):
        obj = getattr(bets, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            validator.register(f"bets.{name}", obj)
    
    # Enregistrer les schémas de réponses
    for name in dir(responses):
        obj = getattr(responses, name)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            validator.register(f"responses.{name}", obj)
    
    logger.info(f"Auto-registration: {len(validator.list_schemas())} schémas enregistrés")


# ============================================
# SCHEMA VALIDATION UTILITIES
# ============================================

class ValidationHelper:
    """Utilitaires pour la validation"""
    
    @staticmethod
    def format_validation_errors(error: ValidationError) -> List[Dict[str, Any]]:
        """
        Formate les erreurs de validation Pydantic
        
        Args:
            error: ValidationError de Pydantic
            
        Returns:
            Liste d'erreurs formatées
        """
        formatted_errors = []
        
        for err in error.errors():
            formatted_errors.append({
                "field": ".".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
                "value": err.get("ctx", {}).get("given", None)
            })
        
        return formatted_errors
    
    @staticmethod
    def create_validation_error_response(error: ValidationError) -> Dict[str, Any]:
        """
        Crée une réponse d'erreur de validation
        
        Args:
            error: ValidationError de Pydantic
            
        Returns:
            Dictionnaire de réponse
        """
        from .responses import ValidationErrorResponse, ValidationErrorDetail
        
        errors = [
            ValidationErrorDetail(**err)
            for err in ValidationHelper.format_validation_errors(error)
        ]
        
        response = ValidationErrorResponse(errors=errors)
        
        return serialize_to_dict(response)


# ============================================
# EXPORTS
# ============================================

__all__ = [
    "SchemaValidator",
    "SchemaSerializer",
    "SchemaTransformer",
    "validate_schema",
    "serialize_model",
    "get_schema_validator",
    "get_schema_serializer",
    "get_schema_transformer",
    "validate_data",
    "serialize_to_dict",
    "serialize_to_json",
    "auto_register_schemas",
    "ValidationHelper",
]
