"""
GOAT PREDICTION ULTIMATE - Bet Schemas
Schémas pour les paris sportifs
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ============================================
# ENUMS
# ============================================

class BetStatus(str, Enum):
    """Statuts de paris"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    CASHED_OUT = "cashed_out"
    PARTIALLY_CASHED_OUT = "partially_cashed_out"


class BetType(str, Enum):
    """Types de paris"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    ACCUMULATOR = "accumulator"
    SYSTEM = "system"


# ============================================
# REQUEST SCHEMAS
# ============================================

class BetCreate(BaseModel):
    """Création d'un pari"""
    prediction_id: uuid.UUID = Field(..., description="ID de la prédiction associée")
    
    stake: float = Field(..., gt=0, description="Montant misé")
    odds: float = Field(..., gt=1.0, description="Cote du pari")
    
    market: str = Field(..., min_length=1, max_length=100)
    selection: str = Field(..., min_length=1, max_length=200)
    
    # Pour paris multiples
    bet_type: BetType = BetType.SINGLE
    legs: Optional[List[Dict[str, Any]]] = None
    
    # Options
    each_way: bool = Field(default=False, description="Pari each-way")
    banker: bool = Field(default=False, description="Pari banker (système)")
    
    @validator('stake')
    def validate_stake(cls, v):
        """Valide le montant du stake"""
        if v < 1.0:
            raise ValueError("Le stake minimum est 1.0")
        if v > 10000.0:
            raise ValueError("Le stake maximum est 10000.0")
        return round(v, 2)
    
    @validator('odds')
    def validate_odds(cls, v):
        """Valide les cotes"""
        if v < 1.01:
            raise ValueError("Les cotes minimales sont 1.01")
        if v > 1000.0:
            raise ValueError("Les cotes maximales sont 1000.0")
        return round(v, 2)
    
    @root_validator
    def validate_multiple_bet(cls, values):
        """Valide les paris multiples"""
        bet_type = values.get('bet_type')
        legs = values.get('legs')
        
        if bet_type in [BetType.MULTIPLE, BetType.ACCUMULATOR, BetType.SYSTEM]:
            if not legs or len(legs) < 2:
                raise ValueError("Un pari multiple nécessite au moins 2 sélections")
            if len(legs) > 20:
                raise ValueError("Maximum 20 sélections par pari multiple")
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "prediction_id": "550e8400-e29b-41d4-a716-446655440000",
                "stake": 25.0,
                "odds": 2.50,
                "market": "match_winner",
                "selection": "home",
                "bet_type": "single"
            }
        }


class BetUpdate(BaseModel):
    """Mise à jour d'un pari"""
    status: Optional[BetStatus] = None
    result: Optional[str] = None
    actual_return: Optional[float] = None
    settled_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "status": "won",
                "result": "home",
                "actual_return": 62.50,
                "settled_at": "2026-02-03T17:00:00Z"
            }
        }


class BetFilter(BaseModel):
    """Filtres pour recherche de paris"""
    status: Optional[BetStatus] = None
    bet_type: Optional[BetType] = None
    sport: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_stake: Optional[float] = Field(None, gt=0)
    max_stake: Optional[float] = Field(None, gt=0)
    min_odds: Optional[float] = Field(None, gt=1.0)
    max_odds: Optional[float] = Field(None, gt=1.0)
    
    @root_validator
    def validate_ranges(cls, values):
        """Valide les plages de valeurs"""
        min_stake = values.get('min_stake')
        max_stake = values.get('max_stake')
        
        if min_stake and max_stake and min_stake > max_stake:
            raise ValueError("min_stake ne peut pas être supérieur à max_stake")
        
        min_odds = values.get('min_odds')
        max_odds = values.get('max_odds')
        
        if min_odds and max_odds and min_odds > max_odds:
            raise ValueError("min_odds ne peut pas être supérieur à max_odds")
        
        return values


class CashoutRequest(BaseModel):
    """Requête de cashout"""
    bet_id: uuid.UUID = Field(..., description="ID du pari à cashout")
    partial: bool = Field(default=False, description="Cashout partiel")
    partial_amount: Optional[float] = Field(None, gt=0, description="Montant du cashout partiel")
    
    @root_validator
    def validate_partial(cls, values):
        """Valide le cashout partiel"""
        partial = values.get('partial')
        partial_amount = values.get('partial_amount')
        
        if partial and not partial_amount:
            raise ValueError("partial_amount requis pour cashout partiel")
        
        if not partial and partial_amount:
            raise ValueError("partial doit être True si partial_amount est fourni")
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "bet_id": "550e8400-e29b-41d4-a716-446655440000",
                "partial": False
            }
        }


class BetPlacement(BaseModel):
    """Placement de pari (réponse immédiate)"""
    bet_id: uuid.UUID
    status: str = "pending_confirmation"
    stake: float
    potential_return: float
    reference: str
    
    class Config:
        schema_extra = {
            "example": {
                "bet_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending_confirmation",
                "stake": 25.0,
                "potential_return": 62.50,
                "reference": "BET-2026-000001"
            }
        }


# ============================================
# RESPONSE SCHEMAS
# ============================================

class BetLeg(BaseModel):
    """Jambe d'un pari multiple"""
    match_id: str
    home_team: str
    away_team: str
    market: str
    selection: str
    odds: float
    status: Optional[str] = None
    result: Optional[str] = None


class BetResponse(BaseModel):
    """Réponse de pari standard"""
    id: uuid.UUID
    user_id: uuid.UUID
    
    prediction_id: uuid.UUID
    bet_type: BetType
    
    stake: float
    odds: float
    potential_return: float
    
    market: str
    selection: str
    
    status: BetStatus
    
    # Résultat
    result: Optional[str] = None
    actual_return: Optional[float] = None
    profit: Optional[float] = None
    
    # Metadata
    sport: str
    league: Optional[str] = None
    match_id: Optional[str] = None
    reference: Optional[str] = None
    
    # Timestamps
    placed_at: datetime
    settled_at: Optional[datetime] = None
    
    # Cashout
    cashout_available: bool = False
    cashout_value: Optional[float] = None
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "660e8400-e29b-41d4-a716-446655440000",
                "prediction_id": "770e8400-e29b-41d4-a716-446655440000",
                "bet_type": "single",
                "stake": 25.0,
                "odds": 2.50,
                "potential_return": 62.50,
                "market": "match_winner",
                "selection": "home",
                "status": "pending",
                "sport": "football",
                "reference": "BET-2026-000001",
                "placed_at": "2026-02-03T10:00:00Z",
                "cashout_available": True,
                "cashout_value": 45.50
            }
        }


class BetDetail(BetResponse):
    """Pari avec détails complets"""
    # Détails du match
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    match_date: Optional[datetime] = None
    
    # Pour paris multiples
    legs: Optional[List[BetLeg]] = None
    total_odds: Optional[float] = None
    
    # Analyse
    expected_value: Optional[float] = None
    value_percentage: Optional[float] = None
    
    # Prédiction associée
    prediction_confidence: Optional[float] = None
    
    # Cashout historique
    cashout_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        orm_mode = True


class BetList(BaseModel):
    """Liste paginée de paris"""
    bets: List[BetResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    
    # Statistiques de la page
    total_staked: float = 0.0
    total_returns: float = 0.0
    total_profit: float = 0.0
    
    @root_validator
    def calculate_totals(cls, values):
        """Calcule les totaux"""
        bets = values.get('bets', [])
        page_size = values.get('page_size', 20)
        total = values.get('total', 0)
        
        # Calculer total_pages
        values['total_pages'] = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        # Calculer les sommes
        total_staked = sum(bet.stake for bet in bets)
        total_returns = sum(bet.actual_return or 0 for bet in bets)
        
        values['total_staked'] = round(total_staked, 2)
        values['total_returns'] = round(total_returns, 2)
        values['total_profit'] = round(total_returns - total_staked, 2)
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "bets": [],
                "total": 125,
                "page": 1,
                "page_size": 20,
                "total_pages": 7,
                "total_staked": 500.0,
                "total_returns": 625.0,
                "total_profit": 125.0
            }
        }


class CashoutResponse(BaseModel):
    """Réponse de cashout"""
    bet_id: uuid.UUID
    cashout_amount: float
    original_stake: float
    potential_return: float
    profit: float
    partial: bool
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "bet_id": "550e8400-e29b-41d4-a716-446655440000",
                "cashout_amount": 45.50,
                "original_stake": 25.0,
                "potential_return": 62.50,
                "profit": 20.50,
                "partial": False,
                "timestamp": "2026-02-03T15:30:00Z"
            }
        }


# ============================================
# STATISTICS SCHEMAS
# ============================================

class BetStats(BaseModel):
    """Statistiques de paris"""
    total_bets: int = 0
    pending_bets: int = 0
    won_bets: int = 0
    lost_bets: int = 0
    void_bets: int = 0
    cashed_out_bets: int = 0
    
    total_staked: float = 0.0
    total_returns: float = 0.0
    total_profit: float = 0.0
    
    win_rate: float = Field(0.0, ge=0.0, le=100.0)
    roi: float = 0.0
    average_odds: float = 0.0
    average_stake: float = 0.0
    
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0
    current_streak: int = 0
    
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_market: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_bet_type: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    profit_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        schema_extra = {
            "example": {
                "total_bets": 200,
                "pending_bets": 5,
                "won_bets": 115,
                "lost_bets": 75,
                "total_staked": 5000.0,
                "total_returns": 6250.0,
                "total_profit": 1250.0,
                "win_rate": 60.5,
                "roi": 25.0,
                "average_odds": 2.15,
                "average_stake": 25.0,
                "biggest_win": 500.0,
                "biggest_loss": 100.0,
                "longest_winning_streak": 8,
                "longest_losing_streak": 4,
                "current_streak": 3
            }
        }


class RiskMetrics(BaseModel):
    """Métriques de risque"""
    value_at_risk_95: float = Field(..., description="VaR à 95%")
    expected_shortfall: float = Field(..., description="Expected Shortfall (CVaR)")
    max_drawdown: float = Field(..., description="Drawdown maximum")
    sharpe_ratio: float = Field(..., description="Ratio de Sharpe")
    sortino_ratio: float = Field(..., description="Ratio de Sortino")
    
    volatility: float = Field(..., description="Volatilité")
    kelly_criterion: float = Field(..., description="Critère de Kelly")
    
    risk_level: str = Field(..., regex="^(low|medium|high|very_high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "value_at_risk_95": 150.0,
                "expected_shortfall": 200.0,
                "max_drawdown": 25.5,
                "sharpe_ratio": 1.85,
                "sortino_ratio": 2.10,
                "volatility": 15.3,
                "kelly_criterion": 0.05,
                "risk_level": "medium"
            }
        }


class BankrollManagement(BaseModel):
    """Gestion du bankroll"""
    current_bankroll: float
    starting_bankroll: float
    profit_loss: float
    profit_loss_percentage: float
    
    recommended_stake: float
    max_stake_per_bet: float
    max_daily_loss: float
    
    bets_today: int
    profit_today: float
    remaining_budget_today: float
    
    class Config:
        schema_extra = {
            "example": {
                "current_bankroll": 11250.0,
                "starting_bankroll": 10000.0,
                "profit_loss": 1250.0,
                "profit_loss_percentage": 12.5,
                "recommended_stake": 22.50,
                "max_stake_per_bet": 225.0,
                "max_daily_loss": 500.0,
                "bets_today": 3,
                "profit_today": 75.0,
                "remaining_budget_today": 425.0
            }
        }
