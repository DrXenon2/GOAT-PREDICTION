"""
Main Router Module for API Gateway
Central router configuration and route aggregation
"""

import os
from typing import Optional
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
import logging
from datetime import datetime

from .v1.v1_routes import get_v1_router
from .v2.v2_routes import get_v2_router
from ..core.config import get_core_config

logger = logging.getLogger(__name__)

# Create main router
main_router = APIRouter()


def configure_routes() -> APIRouter:
    """
    Configure and return main router with all API versions
    
    Returns:
        Configured main APIRouter
    """
    # Include v1 routes
    v1_router = get_v1_router()
    main_router.include_router(v1_router)
    logger.info("V1 routes included in main router")
    
    # Include v2 routes
    v2_router = get_v2_router()
    main_router.include_router(v2_router)
    logger.info("V2 routes included in main router")
    
    return main_router


# Root endpoint
@main_router.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="API Gateway root endpoint"
)
async def root():
    """
    Root endpoint
    
    Returns API information and available versions
    """
    config = get_core_config()
    
    return {
        "name": "GOAT Prediction API Gateway",
        "description": "Advanced AI Sports Prediction Platform",
        "version": "1.0.0",
        "environment": config.environment,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "api_versions": {
            "v1": {
                "status": "stable",
                "base_url": "/api/v1",
                "documentation": "/docs#/",
                "features": [
                    "Basic predictions",
                    "User management",
                    "Betting tracking",
                    "Analytics",
                    "Subscriptions"
                ]
            },
            "v2": {
                "status": "stable",
                "base_url": "/api/v2",
                "documentation": "/docs#/",
                "features": [
                    "Enhanced AI predictions",
                    "Real-time updates (WebSocket)",
                    "Advanced analytics",
                    "Multi-sport analysis",
                    "Personalized insights",
                    "Arbitrage detection",
                    "Portfolio optimization"
                ]
            }
        },
        "links": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "status": "/status"
        }
    }


# Health check endpoint (global)
@main_router.get(
    "/health",
    tags=["Health"],
    summary="Global health check",
    description="Check overall API health"
)
async def health_check():
    """
    Global health check endpoint
    
    Returns:
        Health status of the API
    """
    config = get_core_config()
    
    # TODO: Add actual health checks (database, redis, external services)
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": config.environment,
        "version": "1.0.0",
        "components": {
            "api_gateway": {
                "status": "healthy",
                "uptime_seconds": 0  # TODO: Calculate actual uptime
            },
            "database": {
                "status": "healthy",
                "response_time_ms": 0  # TODO: Actual DB ping
            },
            "redis": {
                "status": "healthy",
                "response_time_ms": 0  # TODO: Actual Redis ping
            },
            "ml_service": {
                "status": "healthy",
                "response_time_ms": 0  # TODO: Actual ML service ping
            }
        }
    }
    
    # Check if all components are healthy
    all_healthy = all(
        component["status"] == "healthy" 
        for component in health_status["components"].values()
    )
    
    if all_healthy:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status
        )
    else:
        health_status["status"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )


# Readiness check endpoint
@main_router.get(
    "/ready",
    tags=["Health"],
    summary="Readiness check",
    description="Check if API is ready to serve requests"
)
async def readiness_check():
    """
    Readiness probe endpoint for Kubernetes
    
    Returns:
        Readiness status
    """
    # TODO: Check if all dependencies are ready
    ready = True
    
    if ready:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Liveness check endpoint
@main_router.get(
    "/live",
    tags=["Health"],
    summary="Liveness check",
    description="Check if API is alive"
)
async def liveness_check():
    """
    Liveness probe endpoint for Kubernetes
    
    Returns:
        Liveness status
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Status endpoint
@main_router.get(
    "/status",
    tags=["Status"],
    summary="Detailed status",
    description="Get detailed API status and metrics"
)
async def get_status():
    """
    Get detailed API status
    
    Returns:
        Detailed status information
    """
    config = get_core_config()
    
    return {
        "api": {
            "name": "GOAT Prediction API Gateway",
            "version": "1.0.0",
            "environment": config.environment,
            "status": "operational",
            "uptime": "N/A"  # TODO: Calculate actual uptime
        },
        "system": {
            "timestamp": datetime.utcnow().isoformat(),
            "timezone": "UTC"
        },
        "features": {
            "v1_api": True,
            "v2_api": True,
            "websocket": True,
            "real_time": True,
            "ml_predictions": True,
            "analytics": True
        },
        "metrics": {
            "total_requests": 0,  # TODO: Actual metrics
            "requests_per_second": 0,
            "average_response_time_ms": 0,
            "error_rate": 0
        },
        "dependencies": {
            "database": "connected",
            "redis": "connected",
            "ml_service": "connected"
        }
    }


# Version info endpoint
@main_router.get(
    "/version",
    tags=["Info"],
    summary="Version information",
    description="Get API version information"
)
async def get_version():
    """
    Get API version information
    
    Returns:
        Version details
    """
    return {
        "api_version": "1.0.0",
        "v1_version": "1.0.0",
        "v2_version": "2.0.0",
        "build_date": "2026-01-15",
        "commit": "N/A",  # TODO: Get from environment
        "environment": get_core_config().environment
    }


# Redirect /api to /api/
@main_router.get(
    "/api",
    include_in_schema=False
)
async def redirect_api():
    """Redirect /api to root"""
    return RedirectResponse(url="/api/")


# API documentation redirect
@main_router.get(
    "/api/",
    tags=["Info"],
    summary="API information",
    description="Get API information and available endpoints"
)
async def api_info():
    """
    API information endpoint
    
    Returns:
        Available API versions and documentation links
    """
    return {
        "message": "GOAT Prediction API Gateway",
        "versions": {
            "v1": "/api/v1/info",
            "v2": "/api/v2/info"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "health_checks": {
            "health": "/health",
            "ready": "/ready",
            "live": "/live",
            "status": "/status"
        }
    }


# Ping endpoint
@main_router.get(
    "/ping",
    tags=["Health"],
    summary="Ping endpoint",
    description="Simple ping to check if API is responsive"
)
async def ping():
    """
    Simple ping endpoint
    
    Returns:
        Pong response
    """
    return {"message": "pong", "timestamp": datetime.utcnow().isoformat()}


# Metrics endpoint (for monitoring)
@main_router.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Prometheus metrics",
    description="Metrics endpoint for Prometheus monitoring",
    include_in_schema=False
)
async def metrics():
    """
    Prometheus-compatible metrics endpoint
    
    Returns:
        Metrics in Prometheus format
    """
    # TODO: Implement actual Prometheus metrics
    metrics_text = """
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total{method="GET",endpoint="/api/v1/predictions"} 1234
api_requests_total{method="POST",endpoint="/api/v1/predictions"} 567

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{le="0.1"} 1000
api_request_duration_seconds_bucket{le="0.5"} 1500
api_request_duration_seconds_bucket{le="1.0"} 1800
api_request_duration_seconds_bucket{le="+Inf"} 2000

# HELP api_errors_total Total number of API errors
# TYPE api_errors_total counter
api_errors_total{code="400"} 10
api_errors_total{code="500"} 2
"""
    
    return Response(
        content=metrics_text,
        media_type="text/plain"
    )


# Favicon endpoint (to avoid 404s)
@main_router.get(
    "/favicon.ico",
    include_in_schema=False
)
async def favicon():
    """Return empty response for favicon requests"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Robots.txt endpoint
@main_router.get(
    "/robots.txt",
    include_in_schema=False
)
async def robots():
    """
    Robots.txt for search engines
    
    Returns:
        Robots.txt content
    """
    robots_content = """
User-agent: *
Disallow: /api/
Disallow: /admin/
Allow: /docs
Allow: /redoc
"""
    return Response(
        content=robots_content.strip(),
        media_type="text/plain"
    )


# Request ID middleware helper endpoint
@main_router.get(
    "/request-info",
    tags=["Debug"],
    summary="Request information",
    description="Get information about current request (debug only)",
    include_in_schema=False
)
async def request_info(request: Request):
    """
    Get current request information (for debugging)
    
    Returns:
        Request details
    """
    config = get_core_config()
    
    # Only available in development
    if not config.is_development:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "Only available in development mode"}
        )
    
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client": {
            "host": request.client.host if request.client else None,
            "port": request.client.port if request.client else None
        },
        "path_params": request.path_params,
        "query_params": dict(request.query_params),
        "state": {
            key: str(value) 
            for key, value in request.state.__dict__.items()
        } if hasattr(request, 'state') else {}
    }


# Export all
__all__ = [
    'main_router',
    'configure_routes',
]
