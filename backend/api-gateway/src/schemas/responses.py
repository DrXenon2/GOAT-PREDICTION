"""
GOAT PREDICTION ULTIMATE - Response Schemas
Schémas de réponses standardisés pour l'API
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Generic, TypeVar, Union
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# TYPE VARIABLES
# ============================================

T = TypeVar('T')


# ============================================
# ENUMS
# ============================================

class ResponseStatus(str, Enum):
    """Statuts de réponse"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorCode(str, Enum):
    """Codes d'erreur standardisés"""
    # Authentication & Authorization
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    RESOURCE_DELETED = "RESOURCE_DELETED"
    
    # Business Logic
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    MATCH_ALREADY_STARTED = "MATCH_ALREADY_STARTED"
    BET_NOT_ALLOWED = "BET_NOT_ALLOWED"
    PREDICTION_NOT_AVAILABLE = "PREDICTION_NOT_AVAILABLE"
    
    # System
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # External Services
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ML_SERVICE_ERROR = "ML_SERVICE_ERROR"


# ============================================
# BASE RESPONSE SCHEMAS
# ============================================

class BaseResponse(BaseModel):
    """Réponse de base"""
    status: ResponseStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "timestamp": "2026-02-03T10:00:00Z",
                "request_id": "req_123456"
            }
        }


class MessageResponse(BaseResponse):
    """Réponse avec message simple"""
    message: str = Field(..., min_length=1, max_length=500)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Opération réussie",
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


class SuccessResponse(BaseResponse):
    """Réponse de succès générique"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    message: str = "Opération réussie"
    data: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Opération réussie",
                "data": {
                    "id": "123",
                    "created": True
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


class DataResponse(BaseResponse, Generic[T]):
    """Réponse avec données typées"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: T
    meta: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {},
                "meta": {
                    "version": "1.0.0",
                    "cached": False
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# ERROR RESPONSE SCHEMAS
# ============================================

class ErrorDetail(BaseModel):
    """Détail d'une erreur"""
    code: ErrorCode
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Le champ 'email' est invalide",
                "field": "email",
                "details": {
                    "pattern": "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$"
                }
            }
        }


class ErrorResponse(BaseResponse):
    """Réponse d'erreur"""
    status: ResponseStatus = ResponseStatus.ERROR
    error: ErrorDetail
    
    # Debug info (seulement en dev)
    debug: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Ressource non trouvée"
                },
                "timestamp": "2026-02-03T10:00:00Z",
                "request_id": "req_123456"
            }
        }


class ValidationErrorDetail(BaseModel):
    """Détail d'erreur de validation"""
    field: str
    message: str
    type: str
    value: Optional[Any] = None
    
    class Config:
        schema_extra = {
            "example": {
                "field": "email",
                "message": "Format d'email invalide",
                "type": "value_error.email",
                "value": "invalid-email"
            }
        }


class ValidationErrorResponse(BaseResponse):
    """Réponse d'erreur de validation"""
    status: ResponseStatus = ResponseStatus.ERROR
    message: str = "Erreur de validation"
    errors: List[ValidationErrorDetail]
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Erreur de validation",
                "errors": [
                    {
                        "field": "email",
                        "message": "Format d'email invalide",
                        "type": "value_error.email"
                    }
                ],
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# PAGINATION RESPONSE SCHEMAS
# ============================================

class PaginationMeta(BaseModel):
    """Métadonnées de pagination"""
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    
    has_previous: bool = False
    has_next: bool = False
    
    previous_page: Optional[int] = None
    next_page: Optional[int] = None
    
    @validator('total_pages', always=True)
    def calculate_total_pages(cls, v, values):
        """Calcule le nombre total de pages"""
        if 'total_items' in values and 'page_size' in values:
            page_size = values['page_size']
            total_items = values['total_items']
            return (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return v
    
    @validator('has_previous', always=True)
    def check_has_previous(cls, v, values):
        """Vérifie s'il y a une page précédente"""
        if 'page' in values:
            return values['page'] > 1
        return v
    
    @validator('has_next', always=True)
    def check_has_next(cls, v, values):
        """Vérifie s'il y a une page suivante"""
        if 'page' in values and 'total_pages' in values:
            return values['page'] < values['total_pages']
        return v
    
    @validator('previous_page', always=True)
    def set_previous_page(cls, v, values):
        """Définit le numéro de page précédente"""
        if values.get('has_previous'):
            return values['page'] - 1
        return None
    
    @validator('next_page', always=True)
    def set_next_page(cls, v, values):
        """Définit le numéro de page suivante"""
        if values.get('has_next'):
            return values['page'] + 1
        return None
    
    class Config:
        schema_extra = {
            "example": {
                "page": 2,
                "page_size": 20,
                "total_items": 150,
                "total_pages": 8,
                "has_previous": True,
                "has_next": True,
                "previous_page": 1,
                "next_page": 3
            }
        }


class PaginatedResponse(BaseResponse, Generic[T]):
    """Réponse paginée générique"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    data: List[T]
    pagination: PaginationMeta
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": [],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 150,
                    "total_pages": 8,
                    "has_previous": False,
                    "has_next": True,
                    "next_page": 2
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# SYSTEM RESPONSE SCHEMAS
# ============================================

class HealthStatus(str, Enum):
    """Statuts de santé"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Santé d'un service"""
    name: str
    status: HealthStatus
    latency: Optional[float] = Field(None, description="Latence en ms")
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "database",
                "status": "healthy",
                "latency": 15.3,
                "message": "Connected",
                "details": {
                    "connections": 5,
                    "max_connections": 100
                }
            }
        }


class HealthResponse(BaseModel):
    """Réponse de health check"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    
    services: List[ServiceHealth] = Field(default_factory=list)
    
    uptime: float = Field(..., description="Uptime en secondes")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-03T10:00:00Z",
                "version": "1.0.0",
                "services": [
                    {
                        "name": "database",
                        "status": "healthy",
                        "latency": 15.3
                    },
                    {
                        "name": "redis",
                        "status": "healthy",
                        "latency": 2.1
                    }
                ],
                "uptime": 86400.5
            }
        }


class MetricsResponse(BaseModel):
    """Réponse de métriques"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # API Metrics
    requests_total: int = 0
    requests_per_second: float = 0.0
    average_response_time: float = 0.0
    error_rate: float = 0.0
    
    # System Metrics
    cpu_usage: float = Field(0.0, ge=0.0, le=100.0)
    memory_usage: float = Field(0.0, ge=0.0, le=100.0)
    disk_usage: float = Field(0.0, ge=0.0, le=100.0)
    
    # Database Metrics
    db_connections: int = 0
    db_queries_per_second: float = 0.0
    
    # Cache Metrics
    cache_hit_rate: float = Field(0.0, ge=0.0, le=100.0)
    cache_size: int = 0
    
    # Active Users
    active_users: int = 0
    online_users: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "timestamp": "2026-02-03T10:00:00Z",
                "requests_total": 125000,
                "requests_per_second": 45.3,
                "average_response_time": 125.5,
                "error_rate": 0.5,
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "disk_usage": 35.1,
                "db_connections": 15,
                "db_queries_per_second": 120.5,
                "cache_hit_rate": 85.5,
                "cache_size": 1024000,
                "active_users": 250,
                "online_users": 85
            }
        }


# ============================================
# API RESPONSE SCHEMAS
# ============================================

class APIResponse(BaseModel):
    """Réponse API standardisée"""
    success: bool
    status_code: int
    message: Optional[str] = None
    data: Optional[Any] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "status_code": 200,
                "message": "Opération réussie",
                "data": {},
                "meta": {
                    "request_id": "req_123456",
                    "version": "1.0.0"
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


class BatchResponse(BaseModel):
    """Réponse pour opérations batch"""
    total: int = Field(..., ge=0)
    successful: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    
    results: List[Union[SuccessResponse, ErrorResponse]]
    errors: List[ErrorDetail] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('failed', always=True)
    def calculate_failed(cls, v, values):
        """Calcule le nombre d'échecs"""
        if 'total' in values and 'successful' in values:
            return values['total'] - values['successful']
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "total": 10,
                "successful": 8,
                "failed": 2,
                "results": [],
                "errors": [
                    {
                        "code": "NOT_FOUND",
                        "message": "Item not found"
                    }
                ],
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# FILE RESPONSE SCHEMAS
# ============================================

class FileUploadResponse(BaseResponse):
    """Réponse d'upload de fichier"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    file_id: str
    filename: str
    size: int = Field(..., ge=0, description="Taille en bytes")
    content_type: str
    url: str
    
    thumbnail_url: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "file_id": "file_123456",
                "filename": "avatar.jpg",
                "size": 245760,
                "content_type": "image/jpeg",
                "url": "https://cdn.example.com/avatars/user_123/avatar.jpg",
                "thumbnail_url": "https://cdn.example.com/avatars/user_123/avatar_thumb.jpg",
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


class ExportResponse(BaseResponse):
    """Réponse d'export de données"""
    status: ResponseStatus = ResponseStatus.SUCCESS
    export_id: str
    format: str = Field(..., regex="^(csv|json|xlsx|pdf)$")
    
    download_url: str
    expires_at: datetime
    
    size: Optional[int] = None
    record_count: Optional[int] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "export_id": "export_123456",
                "format": "csv",
                "download_url": "https://api.example.com/exports/export_123456/download",
                "expires_at": "2026-02-04T10:00:00Z",
                "size": 1024000,
                "record_count": 500,
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# WEBHOOK RESPONSE SCHEMAS
# ============================================

class WebhookEvent(BaseModel):
    """Événement webhook"""
    id: str
    type: str
    timestamp: datetime
    data: Dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "id": "evt_123456",
                "type": "prediction.completed",
                "timestamp": "2026-02-03T10:00:00Z",
                "data": {
                    "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "won"
                }
            }
        }


class WebhookResponse(BaseModel):
    """Réponse webhook"""
    received: bool = True
    event_id: str
    processed: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "received": True,
                "event_id": "evt_123456",
                "processed": False,
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# RATE LIMIT RESPONSE SCHEMAS
# ============================================

class RateLimitInfo(BaseModel):
    """Informations de rate limiting"""
    limit: int = Field(..., ge=0, description="Limite de requêtes")
    remaining: int = Field(..., ge=0, description="Requêtes restantes")
    reset: datetime = Field(..., description="Date de réinitialisation")
    
    retry_after: Optional[int] = Field(None, ge=0, description="Secondes avant retry")
    
    class Config:
        schema_extra = {
            "example": {
                "limit": 100,
                "remaining": 75,
                "reset": "2026-02-03T11:00:00Z",
                "retry_after": None
            }
        }


class RateLimitExceededResponse(ErrorResponse):
    """Réponse de dépassement de rate limit"""
    error: ErrorDetail = Field(
        default=ErrorDetail(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Limite de requêtes dépassée"
        )
    )
    rate_limit: RateLimitInfo
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Limite de requêtes dépassée. Réessayez dans 60 secondes."
                },
                "rate_limit": {
                    "limit": 100,
                    "remaining": 0,
                    "reset": "2026-02-03T11:00:00Z",
                    "retry_after": 60
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# CACHE RESPONSE SCHEMAS
# ============================================

class CacheInfo(BaseModel):
    """Informations de cache"""
    cached: bool = False
    cache_key: Optional[str] = None
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    ttl: Optional[int] = Field(None, ge=0, description="TTL en secondes")
    
    class Config:
        schema_extra = {
            "example": {
                "cached": True,
                "cache_key": "predictions:user_123:page_1",
                "cached_at": "2026-02-03T10:00:00Z",
                "expires_at": "2026-02-03T10:05:00Z",
                "ttl": 300
            }
        }


class CachedDataResponse(DataResponse[T]):
    """Réponse avec données en cache"""
    cache: CacheInfo = Field(default_factory=CacheInfo)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {},
                "cache": {
                    "cached": True,
                    "ttl": 300
                },
                "timestamp": "2026-02-03T10:00:00Z"
            }
        }
