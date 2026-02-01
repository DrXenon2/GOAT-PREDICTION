"""
V1 Routes Module
Centralized router configuration for API v1
"""

from fastapi import APIRouter
import logging

from .analytics import router as analytics_router
from .bets import router as bets_router
from .predictions import router as predictions_router
from .sports import router as sports_router
from .subscriptions import router as subscriptions_router
from .users import router as users_router
from .webhooks import router as webhooks_router

logger = logging.getLogger(__name__)

# Create main v1 router
router = APIRouter(prefix="/v1")


def configure_v1_routes() -> APIRouter:
    """
    Configure and return v1 router with all sub-routers
    
    Returns:
        Configured APIRouter for v1
    """
    # Include all sub-routers
    router.include_router(users_router)
    router.include_router(predictions_router)
    router.include_router(bets_router)
    router.include_router(sports_router)
    router.include_router(analytics_router)
    router.include_router(subscriptions_router)
    router.include_router(webhooks_router)
    
    logger.info("V1 routes configured successfully")
    
    return router


def get_v1_router() -> APIRouter:
    """
    Get configured v1 router
    
    Returns:
        APIRouter instance
    """
    return configure_v1_routes()


# Health check endpoint for v1
@router.get(
    "/health",
    tags=["Health"],
    summary="V1 API health check",
    description="Check if API v1 is running"
)
async def health_check():
    """
    Health check endpoint for API v1
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "api": "v1"
    }


# Info endpoint for v1
@router.get(
    "/info",
    tags=["Info"],
    summary="V1 API information",
    description="Get API v1 information and available endpoints"
)
async def api_info():
    """
    API information endpoint
    
    Returns:
        API metadata and information
    """
    return {
        "version": "1.0.0",
        "name": "GOAT Prediction API v1",
        "description": "Advanced AI sports prediction platform API",
        "endpoints": {
            "users": "/api/v1/users",
            "predictions": "/api/v1/predictions",
            "bets": "/api/v1/bets",
            "sports": "/api/v1/sports",
            "analytics": "/api/v1/analytics",
            "subscriptions": "/api/v1/subscriptions",
            "webhooks": "/api/v1/webhooks"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


# Export all
__all__ = [
    'router',
    'configure_v1_routes',
    'get_v1_router',
    'analytics_router',
    'bets_router',
    'predictions_router',
    'sports_router',
    'subscriptions_router',
    'users_router',
    'webhooks_router',
]
