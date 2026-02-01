"""
GOAT PREDICTION ULTIMATE - Analytics Routes
Routes pour les analyses et statistiques
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ...models.user import User

router = APIRouter()


# ============================================
# MODELS
# ============================================

class AnalyticsOverview(BaseModel):
    """Vue d'ensemble des analytics"""
    user_id: str
    period: str
    
    # Prédictions
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    
    # Betting
    total_bets: int = 0
    winning_bets: int = 0
    win_rate: float = 0.0
    total_staked: float = 0.0
    total_profit: float = 0.0
    roi: float = 0.0
    
    # Par sport
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Tendances
    trend: str = "stable"  # up, down, stable
    best_performing_sport: Optional[str] = None
    worst_performing_sport: Optional[str] = None


class PredictionAnalytics(BaseModel):
    """Analytics détaillées des prédictions"""
    total_predictions: int = 0
    accuracy: float = 0.0
    
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_market: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_confidence: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    daily_performance: List[Dict[str, Any]] = Field(default_factory=list)
    monthly_performance: List[Dict[str, Any]] = Field(default_factory=list)


class BettingAnalytics(BaseModel):
    """Analytics détaillées du betting"""
    total_bets: int = 0
    winning_bets: int = 0
    losing_bets: int = 0
    pending_bets: int = 0
    
    win_rate: float = 0.0
    total_staked: float = 0.0
    total_returns: float = 0.0
    total_profit: float = 0.0
    roi: float = 0.0
    
    average_stake: float = 0.0
    average_odds: float = 0.0
    
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_market: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    profit_timeline: List[Dict[str, Any]] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """Métriques de performance"""
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0


# ============================================
# ROUTES
# ============================================

@router.get("/overview", response_model=AnalyticsOverview)
async def get_analytics_overview(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    current_user: User = Depends(get_current_user)
) -> AnalyticsOverview:
    """
    📊 Vue d'ensemble des analytics
    
    **Paramètres:**
    - period: Période d'analyse ('7d', '30d', '90d', '1y', 'all')
    
    **Retourne:**
    - Statistiques globales
    - Performance par sport
    - Tendances
    """
    try:
        # Calculer les dates
        end_date = datetime.utcnow()
        start_date = calculate_start_date(period, end_date)
        
        # Récupérer les analytics
        analytics = await fetch_analytics_overview(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date
        )
        
        return analytics
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des analytics: {str(e)}"
        )


@router.get("/predictions", response_model=PredictionAnalytics)
async def get_prediction_analytics(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    sport: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> PredictionAnalytics:
    """
    🎯 Analytics détaillées des prédictions
    
    **Paramètres:**
    - period: Période d'analyse
    - sport: Filtrer par sport (optionnel)
    
    **Retourne:**
    - Précision par sport/marché
    - Performance quotidienne/mensuelle
    - Analyse par niveau de confiance
    """
    try:
        end_date = datetime.utcnow()
        start_date = calculate_start_date(period, end_date)
        
        analytics = await fetch_prediction_analytics(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
            sport=sport
        )
        
        return analytics
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur analytics prédictions: {str(e)}"
        )


@router.get("/betting", response_model=BettingAnalytics)
async def get_betting_analytics(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    sport: Optional[str] = None,
    current_user: User = Depends(get_current_user)
) -> BettingAnalytics:
    """
    💰 Analytics détaillées du betting
    
    **Paramètres:**
    - period: Période d'analyse
    - sport: Filtrer par sport (optionnel)
    
    **Retourne:**
    - Win rate et ROI
    - Profit/perte par sport
    - Timeline des profits
    - Statistiques de stake
    """
    try:
        end_date = datetime.utcnow()
        start_date = calculate_start_date(period, end_date)
        
        analytics = await fetch_betting_analytics(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
            sport=sport
        )
        
        return analytics
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur analytics betting: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    current_user: User = Depends(get_current_user)
) -> PerformanceMetrics:
    """
    📈 Métriques de performance avancées
    
    **Retourne:**
    - Sharpe Ratio
    - Sortino Ratio
    - Max Drawdown
    - Profit Factor
    - Séries de victoires/défaites
    """
    try:
        end_date = datetime.utcnow()
        start_date = calculate_start_date(period, end_date)
        
        metrics = await calculate_performance_metrics(
            user_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date
        )
        
        return metrics
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur métriques performance: {str(e)}"
        )


@router.get("/comparison")
async def compare_performance(
    metric: str = Query(..., regex="^(accuracy|roi|win_rate|profit)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|1y)$"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🔄 Compare la performance avec la moyenne des utilisateurs
    
    **Paramètres:**
    - metric: Métrique à comparer ('accuracy', 'roi', 'win_rate', 'profit')
    - period: Période de comparaison
    
    **Retourne:**
    - Votre performance
    - Moyenne globale
    - Votre percentile
    - Top performers
    """
    try:
        comparison = await fetch_performance_comparison(
            user_id=str(current_user.id),
            metric=metric,
            period=period
        )
        
        return comparison
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur comparaison: {str(e)}"
        )


@router.get("/leaderboard")
async def get_leaderboard(
    metric: str = Query("roi", regex="^(accuracy|roi|win_rate|total_profit)$"),
    period: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    limit: int = Query(10, ge=5, le=100),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    🏆 Classement des meilleurs predicteurs
    
    **Paramètres:**
    - metric: Critère de classement
    - period: Période
    - limit: Nombre de résultats
    
    **Retourne:**
    - Top performers
    - Votre position
    """
    try:
        leaderboard = await fetch_leaderboard(
            metric=metric,
            period=period,
            limit=limit,
            user_id=str(current_user.id)
        )
        
        return leaderboard
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur leaderboard: {str(e)}"
        )


@router.get("/insights")
async def get_insights(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    💡 Insights personnalisés basés sur vos performances
    
    **Retourne:**
    - Recommandations
    - Points forts
    - Points à améliorer
    - Opportunités
    """
    try:
        insights = await generate_user_insights(str(current_user.id))
        
        return {
            "user_id": str(current_user.id),
            "insights": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur insights: {str(e)}"
        )


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_start_date(period: str, end_date: datetime) -> datetime:
    """Calcule la date de début selon la période"""
    period_map = {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
        "all": timedelta(days=3650),  # ~10 ans
    }
    return end_date - period_map.get(period, timedelta(days=30))


async def fetch_analytics_overview(user_id: str, start_date: datetime, end_date: datetime):
    """Récupère la vue d'ensemble des analytics"""
    # TODO: Implémenter
    return AnalyticsOverview(user_id=user_id, period="30d")


async def fetch_prediction_analytics(user_id: str, start_date: datetime, end_date: datetime, sport: Optional[str]):
    """Récupère les analytics de prédictions"""
    # TODO: Implémenter
    return PredictionAnalytics()


async def fetch_betting_analytics(user_id: str, start_date: datetime, end_date: datetime, sport: Optional[str]):
    """Récupère les analytics de betting"""
    # TODO: Implémenter
    return BettingAnalytics()


async def calculate_performance_metrics(user_id: str, start_date: datetime, end_date: datetime):
    """Calcule les métriques de performance"""
    # TODO: Implémenter
    return PerformanceMetrics()


async def fetch_performance_comparison(user_id: str, metric: str, period: str):
    """Compare avec la moyenne"""
    # TODO: Implémenter
    return {}


async def fetch_leaderboard(metric: str, period: str, limit: int, user_id: str):
    """Récupère le classement"""
    # TODO: Implémenter
    return {}


async def generate_user_insights(user_id: str):
    """Génère des insights personnalisés"""
    # TODO: Implémenter ML pour insights
    return []
