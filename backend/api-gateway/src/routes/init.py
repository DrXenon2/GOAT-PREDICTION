"""
Route configuration for GOAT Prediction API Gateway.
"""

from fastapi import FastAPI


def setup_routers(app: FastAPI):
    """
    Setup all routers for the application.
    
    Args:
        app: FastAPI application instance
    """
    
    # Import routers
    from .v1 import router as v1_router
    from .v2 import router as v2_router
    from .admin import router as admin_router
    
    # Include routers
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
    app.include_router(v2_router, prefix="/api/v2", tags=["v2"])
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    
    # Health and info routes are defined in app.py
