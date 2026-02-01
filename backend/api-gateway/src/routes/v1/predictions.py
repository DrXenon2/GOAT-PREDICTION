"""
GOAT PREDICTION ULTIMATE - Predictions Routes
Routes pour les prédictions sportives
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid

from ...models.user import User

router = APIRouter()


# ============================================
# MODELS
# ============================================

class PredictionStatus(str, Enum):
    """Statuts de prédiction"""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"


class ConfidenceLevel(str, Enum):
    """Niveaux de confiance"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    sport: str = Field(..., regex="^(football|basketball|tennis|esports)$")
    match_id: str = Field(..., description="ID du match")
    market: str = Field(..., description="Type de marché")
    
    # Optionnel pour personnalisation
    use_user_model: bool = Field(default=False, description="Utiliser le modèle personnalisé")


class Prediction(BaseModel):
    """Modèle de prédiction"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: Optional[uuid.UUID] = None
    
    # Match info
    sport: str
    league: Optional[str] = None
    match_id: str
    home_team: str
    away_team: str
    match_date: datetime
    
    # Prédiction
    market: str
    prediction: str
    confidence: float = Field(..., ge=0.0, le=100.0)
    confidence_level: ConfidenceLevel
    
    # Cotes
    suggested_odds: Optional[float] = None
    market_odds: Optional[Dict[str, float]] = None
    value_bet: bool = False
    expected_value: Optional[float] = None
    
    # Résultat
    status: PredictionStatus = PredictionStatus.PENDING
    actual_result: Optional[str] = None
    is_correct: Optional[bool] = None
    
    # Metadata
    model_used: str = "ensemble_v1"
    features_used: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
        use_enum_values = True


class PredictionDetail(Prediction):
    """Prédiction détaillée avec explications"""
    # Analyse détaillée
    analysis: Dict[str, Any] = Field(default_factory=dict)
    key_factors: List[str] = Field(default_factory=list)
    risk_assessment: str = "medium"
    
    # Comparaison avec bookmakers
    bookmaker_comparison: Dict[str, Any] = Field(default_factory=dict)
    
    # Historique similaire
    similar_matches: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Stats équipes
    team_stats: Dict[str, Any] = Field(default_factory=dict)


class PredictionList(BaseModel):
    """Liste paginée de prédictions"""
    predictions: List[Prediction]
    total: int
    page: int
    page_size: int
    total_pages: int


class LivePrediction(BaseModel):
    """Prédiction en direct"""
    match_id: str
    sport: str
    home_team: str
    away_team: str
    
    current_score: str
    minute: int
    
    live_predictions: Dict[str, Any] = Field(default_factory=dict)
    probability_changes: List[Dict[str, Any]] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# ROUTES
# ============================================

@router.post("", response_model=Prediction, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    request: PredictionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Prediction:
    """
    🎯 Génère une nouvelle prédiction
    
    **Processus:**
    1. Récupération des données du match
    2. Extraction des features
    3. Prédiction avec modèles ML
    4. Calcul de la confiance
    5. Analyse de la valeur
    
    **Retourne:**
    - Prédiction complète
    - Niveau de confiance
    - Cotes suggérées
    """
    try:
        # Vérifier que le match existe
        match_data = await fetch_match_data(request.match_id, request.sport)
        if not match_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match non trouvé"
            )
        
        # Vérifier que le match n'a pas commencé
        if match_data.get("started"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le match a déjà commencé. Utilisez /predictions/live"
            )
        
        # Générer la prédiction
        prediction_result = await generate_prediction(
            match_data=match_data,
            market=request.market,
            user_id=current_user.id if current_user else None,
            use_user_model=request.use_user_model
        )
        
        # Calculer la confiance
        confidence_level = calculate_confidence_level(prediction_result["confidence"])
        
        # Analyser la valeur
        value_analysis = await analyze_value(
            prediction_result["prediction"],
            prediction_result["probability"],
            match_data.get("odds", {})
        )
        
        # Créer l'objet prédiction
        prediction = Prediction(
            user_id=current_user.id if current_user else None,
            sport=request.sport,
            league=match_data.get("league"),
            match_id=request.match_id,
            home_team=match_data["home_team"],
            away_team=match_data["away_team"],
            match_date=match_data["match_date"],
            market=request.market,
            prediction=prediction_result["prediction"],
            confidence=prediction_result["confidence"],
            confidence_level=confidence_level,
            suggested_odds=value_analysis.get("suggested_odds"),
            market_odds=match_data.get("odds"),
            value_bet=value_analysis.get("is_value", False),
            expected_value=value_analysis.get("expected_value"),
            model_used=prediction_result.get("model_used", "ensemble_v1"),
            features_used=prediction_result.get("features", [])
        )
        
        # Sauvegarder si utilisateur connecté
        if current_user:
            saved_prediction = await save_prediction(prediction)
            return saved_prediction
        
        return prediction
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur génération prédiction: {str(e)}"
        )


@router.get("", response_model=PredictionList)
async def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sport: Optional[str] = None,
    status: Optional[PredictionStatus] = None,
    confidence_level: Optional[ConfidenceLevel] = None,
    current_user: User = Depends(get_current_user)
) -> PredictionList:
    """
    📋 Liste les prédictions de l'utilisateur
    
    **Filtres:**
    - sport: Filtrer par sport
    - status: Statut de la prédiction
    - confidence_level: Niveau de confiance
    """
    try:
        predictions, total = await fetch_user_predictions(
            user_id=current_user.id,
            page=page,
            page_size=page_size,
            sport=sport,
            status=status,
            confidence_level=confidence_level
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return PredictionList(
            predictions=predictions,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération prédictions: {str(e)}"
        )


@router.get("/upcoming")
async def get_upcoming_predictions(
    sport: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    📅 Prédictions pour les matchs à venir (prochaines 24h)
    
    **Retourne:**
    - Prédictions des matchs imminents
    - Triées par value/confiance
    """
    try:
        # Récupérer les matchs des prochaines 24h
        upcoming_matches = await fetch_upcoming_matches(
            sport=sport,
            hours=24
        )
        
        # Générer les prédictions
        predictions = []
        for match in upcoming_matches[:limit]:
            pred = await generate_prediction(
                match_data=match,
                market="match_winner",
                user_id=current_user.id if current_user else None
            )
            predictions.append(pred)
        
        # Trier par value/confiance
        predictions.sort(
            key=lambda x: (x.get("value_bet", False), x.get("confidence", 0)),
            reverse=True
        )
        
        return {
            "predictions": predictions,
            "total": len(predictions),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur prédictions à venir: {str(e)}"
        )


@router.get("/live", response_model=List[LivePrediction])
async def get_live_predictions(
    sport: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> List[LivePrediction]:
    """
    ⚡ Prédictions en direct pour les matchs en cours
    
    **Retourne:**
    - Prédictions live mises à jour en temps réel
    - Probabilités dynamiques
    - Changements de momentum
    """
    try:
        # Récupérer les matchs en cours
        live_matches = await fetch_live_matches(sport=sport)
        
        # Générer prédictions live
        live_predictions = []
        for match in live_matches:
            live_pred = await generate_live_prediction(match)
            live_predictions.append(live_pred)
        
        return live_predictions
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur prédictions live: {str(e)}"
        )


@router.get("/{prediction_id}", response_model=PredictionDetail)
async def get_prediction_details(
    prediction_id: str,
    current_user: User = Depends(get_current_user)
) -> PredictionDetail:
    """
    🔍 Détails complets d'une prédiction
    
    **Inclut:**
    - Analyse détaillée
    - Facteurs clés
    - Comparaison bookmakers
    - Matchs similaires
    - Stats équipes
    """
    try:
        # Récupérer la prédiction
        prediction = await fetch_prediction_by_id(prediction_id, current_user.id)
        
        if not prediction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prédiction non trouvée"
            )
        
        # Enrichir avec détails
        detailed_prediction = await enrich_prediction_details(prediction)
        
        return detailed_prediction
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur récupération détails: {str(e)}"
        )


@router.get("/value-bets/today")
async def get_value_bets_today(
    sport: Optional[str] = None,
    min_confidence: float = Query(60.0, ge=0.0, le=100.0),
    min_ev: float = Query(5.0, ge=0.0),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    💎 Meilleurs value bets du jour
    
    **Filtres:**
    - min_confidence: Confiance minimum (%)
    - min_ev: Expected Value minimum (%)
    
    **Retourne:**
    - Top value bets
    - Triés par EV décroissant
    """
    try:
        # Récupérer tous les matchs du jour
        today_matches = await fetch_today_matches(sport=sport)
        
        # Analyser tous les marchés pour value bets
        value_bets = []
        for match in today_matches:
            match_value_bets = await find_value_bets(
                match=match,
                min_confidence=min_confidence,
                min_ev=min_ev
            )
            value_bets.extend(match_value_bets)
        
        # Trier par EV
        value_bets.sort(key=lambda x: x.get("expected_value", 0), reverse=True)
        
        return {
            "value_bets": value_bets[:20],  # Top 20
            "total_found": len(value_bets),
            "filters": {
                "min_confidence": min_confidence,
                "min_ev": min_ev,
                "sport": sport
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur value bets: {str(e)}"
        )


@router.post("/batch")
async def batch_predictions(
    match_ids: List[str] = Field(..., max_items=20),
    market: str = "match_winner",
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    📦 Génère plusieurs prédictions en batch
    
    **Limite:** Maximum 20 matchs par requête
    """
    try:
        if len(match_ids) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 20 matchs par batch"
            )
        
        predictions = []
        for match_id in match_ids:
            try:
                pred = await generate_prediction_for_match(
                    match_id=match_id,
                    market=market,
                    user_id=current_user.id if current_user else None
                )
                predictions.append(pred)
            except Exception as e:
                predictions.append({
                    "match_id": match_id,
                    "error": str(e)
                })
        
        return {
            "predictions": predictions,
            "total": len(predictions),
            "successful": len([p for p in predictions if "error" not in p]),
            "failed": len([p for p in predictions if "error" in p])
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur batch: {str(e)}"
        )


# ============================================
# HELPER FUNCTIONS
# ============================================

def calculate_confidence_level(confidence: float) -> ConfidenceLevel:
    """Calcule le niveau de confiance"""
    if confidence >= 80:
        return ConfidenceLevel.VERY_HIGH
    elif confidence >= 70:
        return ConfidenceLevel.HIGH
    elif confidence >= 60:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


async def fetch_match_data(match_id: str, sport: str):
    """Récupère les données d'un match"""
    # TODO: Implémenter
    return {
        "match_id": match_id,
        "sport": sport,
        "home_team": "Team A",
        "away_team": "Team B",
        "league": "Premier League",
        "match_date": datetime.utcnow() + timedelta(hours=2),
        "started": False,
        "odds": {}
    }


async def generate_prediction(match_data, market, user_id=None, use_user_model=False):
    """Génère une prédiction ML"""
    # TODO: Appel au ML engine
    return {
        "prediction": "home",
        "confidence": 75.5,
        "probability": 0.755,
        "model_used": "ensemble_v1",
        "features": []
    }


async def analyze_value(prediction, probability, odds):
    """Analyse la valeur d'un pari"""
    # TODO: Calcul EV
    return {
        "suggested_odds": 2.0,
        "is_value": True,
        "expected_value": 10.5
    }


async def save_prediction(prediction):
    """Sauvegarde une prédiction"""
    # TODO: DB
    return prediction


async def fetch_user_predictions(user_id, page, page_size, sport, status, confidence_level):
    """Récupère les prédictions d'un utilisateur"""
    # TODO: DB
    return [], 0


async def fetch_upcoming_matches(sport, hours):
    """Récupère les matchs à venir"""
    # TODO: Data collection
    return []


async def fetch_live_matches(sport):
    """Récupère les matchs en cours"""
    # TODO: Live data
    return []


async def generate_live_prediction(match):
    """Génère une prédiction live"""
    # TODO: Real-time ML
    return LivePrediction(
        match_id=match["id"],
        sport=match["sport"],
        home_team=match["home_team"],
        away_team=match["away_team"],
        current_score="0-0",
        minute=45
    )


async def fetch_prediction_by_id(prediction_id, user_id):
    """Récupère une prédiction par ID"""
    # TODO: DB
    return None


async def enrich_prediction_details(prediction):
    """Enrichit une prédiction avec détails"""
    # TODO: Analytics
    return PredictionDetail(**prediction.dict())


async def fetch_today_matches(sport):
    """Récupère les matchs du jour"""
    # TODO: Data
    return []


async def find_value_bets(match, min_confidence, min_ev):
    """Trouve les value bets"""
    # TODO: Value analysis
    return []


async def generate_prediction_for_match(match_id, market, user_id):
    """Génère prédiction pour un match"""
    # TODO: ML
    return {}
