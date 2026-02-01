"""
GOAT PREDICTION ULTIMATE - V1 API Routes
Routes principales de l'API v1
"""

from fastapi import APIRouter
from .predictions import router as predictions_router
from .bets import router as bets_router
from .analytics import router as analytics_router
from .sports import router as sports_router
from .subscriptions import router as subscriptions_router
from .users import router as users_router
from .webhooks import router as webhooks_router

# Router principal v1
router = APIRouter(
    prefix="/v1",
    responses={
        401: {"description": "Non autorisé"},
        404: {"description": "Ressource non trouvée"},
        422: {"description": "Erreur de validation"},
        500: {"description": "Erreur serveur"},
    }
)

# Inclure tous les sous-routers
router.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
router.include_router(bets_router, prefix="/bets", tags=["bets"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
router.include_router(sports_router, prefix="/sports", tags=["sports"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])

__all__ = ["router"]
