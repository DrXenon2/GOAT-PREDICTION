"""
GOAT PREDICTION ULTIMATE - Admin Routes Module
Routes d'administration pour la gestion du système
"""

from fastapi import APIRouter
from .admin_routes import router as admin_router
from .users import router as users_router
from .system import router as system_router

# Router principal admin
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={
        401: {"description": "Non autorisé"},
        403: {"description": "Accès interdit - Admin requis"},
        404: {"description": "Ressource non trouvée"},
    }
)

# Inclure les sous-routes
router.include_router(admin_router, tags=["admin-general"])
router.include_router(users_router, prefix="/users", tags=["admin-users"])
router.include_router(system_router, prefix="/system", tags=["admin-system"])

__all__ = ["router"]
