"""
Routes Module for API Gateway
Centralized routing configuration for all API versions
"""

from .router import main_router, configure_routes
from .v1.v1_routes import router as v1_router, get_v1_router
from .v2.v2_routes import router as v2_router, get_v2_router

__all__ = [
    'main_router',
    'configure_routes',
    'v1_router',
    'v2_router',
    'get_v1_router',
    'get_v2_router',
]

__version__ = '1.0.0'
