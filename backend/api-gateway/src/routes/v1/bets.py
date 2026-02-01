"""
GOAT PREDICTION ULTIMATE - Bets Routes
Routes pour la gestion des paris
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid

from ...models.user import User

router = APIRouter()


# ============================================
# MODELS
# ============================================

class BetStatus(str, Enum):
    """Statuts de paris"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    CASHED_OUT = "cashed_out"


class BetType(str, Enum):
    """Types de paris"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    SYSTEM = "system"


class BetCreate(BaseModel):
    """Création d'un pari"""
    prediction_id: uuid.UUID = Field(..., description="ID de la prédiction")
    stake: float = Field(..., ge=0.01, description="Montant misé")
    odds: float = Field(..., ge=1.01, description="Cote")
    market: str = Field(..., description="Type de marché")
    selection: str = Field(..., description="Sélection")
    
    # Optionnel pour paris multiples
    legs: Optional[List[Dict[str, Any]]] = None
    
    @validator('stake')
    def validate_stake(cls, v):
        if v < 1.0:
            raise ValueError("Le stake minimum est 1.0")
        if v > 10000.0:
            raise ValueError("Le stake maximum est 10000.0")
        return v


class Bet(BaseModel):
    """Modèle de pari"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    
    prediction_id: uuid.UUID
    bet_type: BetType
    
    stake: float
    odds: float
    potential_return: float
    
    market: str
    selection: str
    
    status: BetStatus = BetStatus.PENDING
    
    # Résultat
    result: Optional[str] = None
    actual_return: Optional[float] = None
    profit: Optional[float] = None
    
    # Metadata
    sport: str
    league: Optional[str] = None
    match_id: Optional[str] = None
    
    # Timestamps
    placed_at: datetime = Field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None
    
    # Cash out
    cashout_available: bool = False
    cashout_value: Optional[float] = None
    
    class Config:
        orm_mode = True
        use_enum_values = True


class BetUpdate(BaseModel):
    """Mise à jour d'un pari"""
    status: Optional[BetStatus] = None
    result: Optional[str] = None
    actual_return: Optional[float] = None


class BetList(BaseModel):
    """Liste paginée de paris"""
    bets: List[Bet]
    total: int
    page: int
    page_size: int
    total_pages: int


class BetStats(BaseModel):
    """Statistiques de paris"""
    total_bets: int = 0
    pending_bets: int = 0
    won_bets: int = 0
    lost_bets: int = 0
    
    total_staked: float = 0.0
    total_returns: float = 0.0
    total_profit: float = 0.0
    
    win_rate: float = 0.0
    roi: float = 0.0
    average_odds: float = 0.0


# ============================================
# ROUTES
# ============================================

@router.post("", response_model=Bet, status_code=status.HTTP_201_CREATED)
async def place_bet(
    bet_create: BetCreate,
    current_user: User = Depends(get_current_user)
) -> Bet:
    """
    💰 Place un nouveau pari
    
    **Validation:**
    - Vérification du solde
    - Validation de la cote
    - Vérification que le match n'a pas commencé
    
    **Retourne:**
    - Détails du pari placé
    """
    try:
        # Vérifier le solde utilisateur
        user_balance = await get_user_balance(current_user.id)
        if user_balance < bet_create.stake:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solde insuffisant"
            )
        
        # Vérifier que la prédiction existe
        prediction = await get_prediction(bet_create.prediction_id)
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prédiction non trouvée"
            )
        
        # Vérifier que le match n'a pas commencé
        if prediction.get("match_started"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le match a déjà commencé"
            )
        
        # Calculer le retour potentiel
        potential_return = bet_create.stake * bet_create.odds
        
        # Créer le pari
        bet = Bet(
            user_id=current_user.id,
            prediction_id=bet_create.prediction_id,
            bet_type=BetType.SINGLE,
            stake=bet_create.stake,
            odds=bet_create.odds,
            potential_return=potential_return,
            market=bet_create.market,
            selection=bet_create.selection,
            sport=prediction.get("sport", "football")
        )
        
        # Sauvegarder en DB
        saved_bet = await save_bet(bet)
        
        # Déduire du solde
        await deduct_balance(current_user.id, bet_create.stake)
        
        return saved_bet
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du placement du pari: {str(e)}"
        )


@router.get("", response_model=BetList)
async def list_bets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[BetStatus] = None,
    sport: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> BetList:
    """
    📋 Liste les paris de l'utilisateur
    
    **Filtres:**
    - status: Statut du pari
    - sport: Sport
    
    **Pagination:**
    - page: Numéro de page
    - page_size: Taille de page
    """
    try:
        bets, total = await fetch_user_bets(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            status=status,
            sport=sport
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return BetList(
            bets=bets,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération paris: {str(e)}"
        )


@router.get("/stats", response_model=BetStats)
async def get_bet_statistics(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    current_user: User = Depends(get_current_user)
) -> BetStats:
    """
    📊 Statistiques des paris
    
    **Retourne:**
    - Win rate
    - ROI
    - Profit total
    - Cotes moyennes
    """
    try:
        stats = await calculate_bet_stats(
            user_id=current_user.id,
            period=period
        )
        
        return stats
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur stats: {str(e)}"
        )


@router.get("/{bet_id}", response_model=Bet)
async def get_bet_details(
    bet_id: str,
    current_user: User = Depends(get_current_user)
) -> Bet:
    """
    🔍 Détails d'un pari spécifique
    """
    try:
        bet = await fetch_bet_by_id(bet_id, current_user.id)
        
        if not bet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pari non trouvé"
            )
        
        return bet
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération pari: {str(e)}"
        )


@router.post("/{bet_id}/cashout")
async def cashout_bet(
    bet_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    💵 Cash out d'un pari en cours
    
    **Conditions:**
    - Le pari doit être en cours (PENDING)
    - Le cash out doit être disponible
    
    **Retourne:**
    - Montant du cash out
    - Nouveau solde
    """
    try:
        bet = await fetch_bet_by_id(bet_id, current_user.id)
        
        if not bet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pari non trouvé"
            )
        
        if bet.status != BetStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le pari n'est plus en cours"
            )
        
        if not bet.cashout_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cash out non disponible pour ce pari"
            )
        
        # Effectuer le cash out
        cashout_amount = bet.cashout_value or 0.0
        await process_cashout(bet_id, cashout_amount, current_user.id)
        
        return {
            "message": "Cash out effectué avec succès",
            "bet_id": bet_id,
            "cashout_amount": cashout_amount,
            "profit": cashout_amount - bet.stake,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur cash out: {str(e)}"
        )


@router.delete("/{bet_id}")
async def cancel_bet(
    bet_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    ❌ Annule un pari (seulement si pas encore commencé)
    """
    try:
        bet = await fetch_bet_by_id(bet_id, current_user.id)
        
        if not bet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pari non trouvé"
            )
        
        if bet.status != BetStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'annuler un pari terminé"
            )
        
        # Vérifier que le match n'a pas commencé
        prediction = await get_prediction(bet.prediction_id)
        if prediction.get("match_started"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le match a déjà commencé"
            )
        
        # Annuler et rembourser
        await cancel_bet_and_refund(bet_id, current_user.id)
        
        return {
            "message": "Pari annulé avec succès",
            "bet_id": bet_id,
            "refunded_amount": bet.stake,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur annulation: {str(e)}"
        )


# Helper functions (à implémenter)
async def get_user_balance(user_id):
    return 1000.0

async def get_prediction(prediction_id):
    return {"sport": "football", "match_started": False}

async def save_bet(bet):
    return bet

async def deduct_balance(user_id, amount):
    pass

async def fetch_user_bets(user_id, page, page_size, status, sport):
    return [], 0

async def calculate_bet_stats(user_id, period):
    return BetStats()

async def fetch_bet_by_id(bet_id, user_id):
    return None

async def process_cashout(bet_id, amount, user_id):
    pass

async def cancel_bet_and_refund(bet_id, user_id):
    pass
