"""
Route Initialization Module
Handles initialization and configuration of all routes
"""

import logging
from typing import Optional
from fastapi import FastAPI

from .router import configure_routes
from ..core.config import get_core_config

logger = logging.getLogger(__name__)


def init_routes(app: FastAPI, api_prefix: str = "/api") -> None:
    """
    Initialize all routes for the application
    
    Args:
        app: FastAPI application instance
        api_prefix: API prefix (default: /api)
    """
    try:
        logger.info("Initializing routes...")
        
        # Get configuration
        config = get_core_config()
        
        # Configure all routes
        main_router = configure_routes()
        
        # Include main router with prefix
        app.include_router(main_router, prefix=api_prefix)
        
        logger.info(f"Routes initialized successfully with prefix '{api_prefix}'")
        
        # Log registered routes
        _log_routes(app)
        
    except Exception as e:
        logger.error(f"Error initializing routes: {str(e)}")
        raise


def _log_routes(app: FastAPI) -> None:
    """
    Log all registered routes
    
    Args:
        app: FastAPI application
    """
    logger.info("Registered routes:")
    
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(sorted(route.methods))
            routes_info.append(f"  {methods:20} {route.path}")
    
    # Sort and log
    for route_info in sorted(routes_info):
        logger.debug(route_info)
    
    logger.info(f"Total routes registered: {len(routes_info)}")


def get_route_info(app: FastAPI) -> dict:
    """
    Get information about registered routes
    
    Args:
        app: FastAPI application
        
    Returns:
        Dictionary with route information
    """
    routes = []
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods),
                'name': route.name,
                'tags': getattr(route, 'tags', [])
            })
    
    return {
        'total_routes': len(routes),
        'routes': routes
    }


def validate_routes(app: FastAPI) -> bool:
    """
    Validate that all required routes are registered
    
    Args:
        app: FastAPI application
        
    Returns:
        True if all required routes are present
    """
    required_routes = [
        '/api/v1/health',
        '/api/v2/health',
        '/health',
        '/docs',
    ]
    
    registered_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    
    missing_routes = []
    for required_route in required_routes:
        if required_route not in registered_paths:
            missing_routes.append(required_route)
    
    if missing_routes:
        logger.warning(f"Missing required routes: {missing_routes}")
        return False
    
    logger.info("All required routes are registered")
    return True


def setup_route_handlers(app: FastAPI) -> None:
    """
    Setup custom route handlers and middleware
    
    Args:
        app: FastAPI application
    """
    @app.on_event("startup")
    async def startup_routes():
        """Route initialization on startup"""
        logger.info("Routes startup complete")
    
    @app.on_event("shutdown")
    async def shutdown_routes():
        """Route cleanup on shutdown"""
        logger.info("Routes shutdown complete")


# Export all
__all__ = [
    'init_routes',
    'get_route_info',
    'validate_routes',
    'setup_route_handlers',
]
