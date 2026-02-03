"""
GOAT PREDICTION ULTIMATE - Prediction Schemas
Schémas pour les prédictions sportives
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# ENUMS
# ============================================

class PredictionStatus(str, Enum):
    """Statuts de prédiction"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    PROCESSING = "processing"


class ConfidenceLevel(str, Enum):
    """Niveaux de confiance"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class Sport(str, Enum):
    """Sports disponibles"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    RUGBY = "rugby"
    HOCKEY = "hockey"


class Market(str, Enum):
    """Types de marchés"""
    # Football
    MATCH_WINNER = "match_winner"
    OVER_UNDER = "over_under"
    BTTS = "both_teams_to_score"
    EXACT_SCORE = "exact_score"
    CORNERS = "corners"
    CARDS = "cards"
    
    # Basketball
    POINT_SPREAD = "point_spread"
    TOTAL_POINTS = "total_points"
    QUARTER_WINNER = "quarter_winner"
    
    # Tennis
    SET_BETTING = "set_betting"
    TOTAL_GAMES = "total_games"
    
    # Esports
    MAP_WINNER = "map_winner"
    FIRST_BLOOD = "first_blood"


# ============================================
# REQUEST SCHEMAS
# ============================================

class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    sport: Sport = Field(..., description="Sport concerné")
    match_id: str = Field(..., min_length=1, max_length=100, description="ID du match")
    market: Market = Field(..., description="Type de marché")
    
    # Options avancées
    use_user_model: bool = Field(default=False, description="Utiliser le modèle personnalisé")
    confidence_threshold: float = Field(default=60.0, ge=0.0, le=100.0, description="Seuil de confiance minimum")
    include_analysis: bool = Field(default=True, description="Inclure l'analyse détaillée")
    
    class Config:
        schema_extra = {
            "example": {
                "sport": "football",
                "match_id": "match_123456",
                "market": "match_winner",
                "use_user_model": False,
                "confidence_threshold": 70.0,
                "include_analysis": True
            }
        }


class PredictionCreate(BaseModel):
    """Création d'une prédiction (interne)"""
    user_id: Optional[uuid.UUID] = None
    sport: Sport
    league: Optional[str] = None
    match_id: str
    home_team: str = Field(..., min_length=1, max_length=200)
    away_team: str = Field(..., min_length=1, max_length=200)
    match_date: datetime
    
    market: Market
    prediction: str = Field(..., min_length=1, max_length=100)
    confidence: float = Field(..., ge=0.0, le=100.0)
    
    suggested_odds: Optional[float] = Field(None, gt=1.0)
    expected_value: Optional[float] = None
    
    @validator('confidence')
    def validate_confidence(cls, v):
        """Arrondit la confiance à 2 décimales"""
        return round(v, 2)
    
    @validator('suggested_odds')
    def validate_odds(cls, v):
        """Valide les cotes"""
        if v is not None:
            if v < 1.01:
                raise ValueError("Les cotes doivent être >= 1.01")
            if v > 1000:
                raise ValueError("Les cotes doivent être <= 1000")
        return v


class PredictionUpdate(BaseModel):
    """Mise à jour d'une prédiction"""
    status: Optional[PredictionStatus] = None
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "won",
                "actual_result": "home",
                "is_correct": True
            }
        }


class PredictionFilter(BaseModel):
    """Filtres pour recherche de prédictions"""
    sport: Optional[Sport] = None
    status: Optional[PredictionStatus] = None
    confidence_level: Optional[ConfidenceLevel] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    value_bets_only: bool = False
    min_confidence: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    class Config:
        schema_extra = {
            "example": {
                "sport": "football",
                "status": "won",
                "confidence_level": "high",
                "value_bets_only": True,
                "min_confidence": 75.0
            }
        }


class BatchPredictionRequest(BaseModel):
    """Requête de prédictions en batch"""
    requests: List[PredictionRequest] = Field(..., min_items=1, max_items=20)
    
    @validator('requests')
    def validate_batch_size(cls, v):
        """Limite le nombre de prédictions"""
        if len(v) > 20:
            raise ValueError("Maximum 20 prédictions par batch")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "requests": [
                    {
                        "sport": "football",
                        "match_id": "match_1",
                        "market": "match_winner"
                    },
                    {
                        "sport": "basketball",
                        "match_id": "match_2",
                        "market": "point_spread"
                    }
                ]
            }
        }


# ============================================
# RESPONSE SCHEMAS
# ============================================

class TeamInfo(BaseModel):
    """Information sur une équipe"""
    name: str
    logo: Optional[str] = None
    form: Optional[List[str]] = None
    ranking: Optional[int] = None


class MatchInfo(BaseModel):
    """Informations du match"""
    id: str
    sport: Sport
    league: Optional[str] = None
    home_team: TeamInfo
    away_team: TeamInfo
    match_date: datetime
    venue: Optional[str] = None
    status: str = "scheduled"


class PredictionAnalysis(BaseModel):
    """Analyse détaillée de la prédiction"""
    key_factors: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    
    # Stats comparatives
    head_to_head: Optional[Dict[str, Any]] = None
    recent_form: Optional[Dict[str, Any]] = None
    injuries: Optional[List[str]] = None
    
    # Conditions
    weather: Optional[Dict[str, Any]] = None
    referee: Optional[Dict[str, Any]] = None


class OddsComparison(BaseModel):
    """Comparaison des cotes"""
    bookmaker: str
    odds: float
    is_best: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "bookmaker": "Bet365",
                "odds": 2.50,
                "is_best": True
            }
        }


class PredictionResponse(BaseModel):
    """Réponse de prédiction standard"""
    id: uuid.UUID
    match: MatchInfo
    
    market: Market
    prediction: str
    confidence: float = Field(..., ge=0.0, le=100.0)
    confidence_level: ConfidenceLevel
    
    # Cotes et valeur
    suggested_odds: Optional[float] = None
    market_odds: Optional[Dict[str, float]] = None
    value_bet: bool = False
    expected_value: Optional[float] = None
    
    # Status
    status: PredictionStatus = PredictionStatus.PENDING
    
    # Metadata
    model_used: str = "ensemble_v1"
    created_at: datetime
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "match": {
                    "id": "match_123",
                    "sport": "football",
                    "league": "Premier League",
                    "home_team": {"name": "Manchester United"},
                    "away_team": {"name": "Liverpool"},
                    "match_date": "2026-02-15T15:00:00Z"
                },
                "market": "match_winner",
                "prediction": "home",
                "confidence": 78.5,
                "confidence_level": "high",
                "suggested_odds": 2.10,
                "value_bet": True,
                "expected_value": 8.5,
                "status": "pending",
                "model_used": "ensemble_v1",
                "created_at": "2026-02-03T10:00:00Z"
            }
        }


class PredictionDetail(PredictionResponse):
    """Prédiction avec détails complets"""
    analysis: PredictionAnalysis
    odds_comparison: List[OddsComparison] = Field(default_factory=list)
    similar_matches: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Performance du modèle
    model_accuracy: Optional[float] = None
    model_confidence_calibration: Optional[float] = None
    
    class Config:
        orm_mode = True


class LivePrediction(BaseModel):
    """Prédiction en direct"""
    match_id: str
    sport: Sport
    home_team: str
    away_team: str
    
    # État du match
    current_score: str
    minute: int
    period: str = "1st half"
    
    # Prédictions live
    live_predictions: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Changements de probabilité
    probability_changes: List[Dict[str, Any]] = Field(default_factory=list)
    momentum: str = "neutral"
    
    last_updated: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "match_id": "live_match_123",
                "sport": "football",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "current_score": "1-0",
                "minute": 35,
                "period": "1st half",
                "live_predictions": {
                    "match_winner": {
                        "prediction": "home",
                        "confidence": 72.3
                    }
                },
                "momentum": "home",
                "last_updated": "2026-02-03T15:35:00Z"
            }
        }


class PredictionList(BaseModel):
    """Liste paginée de prédictions"""
    predictions: List[PredictionResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    
    @root_validator
    def calculate_total_pages(cls, values):
        """Calcule le nombre total de pages"""
        total = values.get('total', 0)
        page_size = values.get('page_size', 20)
        values['total_pages'] = (total + page_size - 1) // page_size if page_size > 0 else 0
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [],
                "total": 150,
                "page": 1,
                "page_size": 20,
                "total_pages": 8
            }
        }


class BatchPredictionResponse(BaseModel):
    """Réponse batch de prédictions"""
    predictions: List[Union[PredictionResponse, Dict[str, Any]]]
    total: int
    successful: int
    failed: int
    errors: List[Dict[str, str]] = Field(default_factory=list)
    
    @root_validator
    def validate_counts(cls, values):
        """Valide que les compteurs sont cohérents"""
        total = values.get('total', 0)
        successful = values.get('successful', 0)
        failed = values.get('failed', 0)
        
        if successful + failed != total:
            raise ValueError("successful + failed doit égaler total")
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [],
                "total": 5,
                "successful": 4,
                "failed": 1,
                "errors": [
                    {
                        "match_id": "match_5",
                        "error": "Match not found"
                    }
                ]
            }
        }


class ValueBet(BaseModel):
    """Value bet identifié"""
    prediction: PredictionResponse
    edge_percentage: float = Field(..., description="Avantage en pourcentage")
    recommended_stake: Optional[float] = None
    kelly_fraction: Optional[float] = None
    
    class Config:
        schema_extra = {
            "example": {
                "prediction": {},
                "edge_percentage": 12.5,
                "recommended_stake": 25.0,
                "kelly_fraction": 0.125
            }
        }


class ValueBetList(BaseModel):
    """Liste de value bets"""
    value_bets: List[ValueBet]
    total_found: int
    average_edge: float
    total_expected_value: float
    
    filters: Dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "value_bets": [],
                "total_found": 15,
                "average_edge": 8.3,
                "total_expected_value": 124.5,
                "filters": {
                    "min_confidence": 70.0,
                    "min_ev": 5.0
                },
                "generated_at": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# STATISTICS SCHEMAS
# ============================================

class PredictionStats(BaseModel):
    """Statistiques de prédictions"""
    total_predictions: int = 0
    correct_predictions: int = 0
    incorrect_predictions: int = 0
    pending_predictions: int = 0
    void_predictions: int = 0
    
    accuracy: float = Field(0.0, ge=0.0, le=100.0)
    average_confidence: float = Field(0.0, ge=0.0, le=100.0)
    
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_market: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_confidence_level: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    best_sport: Optional[str] = None
    worst_sport: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "total_predictions": 250,
                "correct_predictions": 175,
                "incorrect_predictions": 70,
                "pending_predictions": 5,
                "accuracy": 71.4,
                "average_confidence": 68.5,
                "by_sport": {
                    "football": {
                        "total": 150,
                        "correct": 105,
                        "accuracy": 70.0
                    }
                },
                "best_sport": "tennis"
            }
        }


class ModelPerformance(BaseModel):
    """Performance d'un modèle"""
    model_name: str
    version: str
    
    total_predictions: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    calibration_score: float
    brier_score: float
    log_loss: float
    
    confidence_distribution: Dict[str, int] = Field(default_factory=dict)
    
    last_trained: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "model_name": "ensemble_v1",
                "version": "1.2.3",
                "total_predictions": 10000,
                "accuracy": 72.5,
                "precision": 71.8,
                "recall": 73.2,
                "f1_score": 72.5,
                "calibration_score": 0.95,
                "brier_score": 0.18,
                "log_loss": 0.45,
                "last_trained": "2026-02-01T00:00:00Z"
            }
        }
