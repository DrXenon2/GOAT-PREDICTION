"""
GOAT PREDICTION ULTIMATE - Schemas Module
Schémas Pydantic pour validation et sérialisation
"""

from .predictions import (
    PredictionRequest,
    PredictionResponse,
    PredictionDetail,
    PredictionList,
    LivePrediction,
    PredictionCreate,
    PredictionUpdate,
    PredictionFilter,
    BatchPredictionRequest,
    BatchPredictionResponse,
)

from .bets import (
    BetCreate,
    BetResponse,
    BetDetail,
    BetList,
    BetUpdate,
    BetFilter,
    BetStats,
    CashoutRequest,
    CashoutResponse,
    BetPlacement,
)

from .responses import (
    SuccessResponse,
    ErrorResponse,
    ValidationErrorResponse,
    PaginatedResponse,
    MessageResponse,
    DataResponse,
    APIResponse,
    HealthResponse,
    MetricsResponse,
)

from .schemas_manager import (
    SchemaValidator,
    SchemaSerializer,
    validate_schema,
    serialize_model,
    get_schema_validator,
)

__all__ = [
    # Predictions
    "PredictionRequest",
    "PredictionResponse",
    "PredictionDetail",
    "PredictionList",
    "LivePrediction",
    "PredictionCreate",
    "PredictionUpdate",
    "PredictionFilter",
    "BatchPredictionRequest",
    "BatchPredictionResponse",
    
    # Bets
    "BetCreate",
    "BetResponse",
    "BetDetail",
    "BetList",
    "BetUpdate",
    "BetFilter",
    "BetStats",
    "CashoutRequest",
    "CashoutResponse",
    "BetPlacement",
    
    # Responses
    "SuccessResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "PaginatedResponse",
    "MessageResponse",
    "DataResponse",
    "APIResponse",
    "HealthResponse",
    "MetricsResponse",
    
    # Manager
    "SchemaValidator",
    "SchemaSerializer",
    "validate_schema",
    "serialize_model",
    "get_schema_validator",
]

__version__ = "1.0.0"
