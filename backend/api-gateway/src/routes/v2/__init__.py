"""
Routes V2 Module
Enhanced API endpoints with advanced features
"""

from .v2_routes import router, configure_v2_routes, get_v2_router
from .predictions import router as predictions_router
from .insights import router as insights_router
from .realtime import router as realtime_router
from .advanced import router as advanced_router

__all__ = [
    'router',
    'configure_v2_routes',
    'get_v2_router',
    'predictions_router',
    'insights_router',
    'realtime_router',
    'advanced_router',
]

__version__ = '2.0.0'
