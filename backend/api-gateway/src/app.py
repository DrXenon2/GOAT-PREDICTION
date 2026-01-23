"""
GOAT Prediction API Gateway - Main Application
The core FastAPI application with all configurations, middleware, and routing
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .core.config import settings
from .core.exceptions import (
    APIException,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from .core.logging import setup_logging
from .dependencies import get_database, get_redis
from .middleware import (
    AuditLogMiddleware,
    CacheControlMiddleware,
    DatabaseSessionMiddleware,
    ExceptionHandlerMiddleware,
    MetricsMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
)
from .routes import setup_routers

# Load environment variables
load_dotenv()

# Configure structured logging
setup_logging()
logger = structlog.get_logger(__name__)

# Global state for application lifespan
_app_state: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown events.
    
    This handles:
    - Database connection pool initialization
    - Redis connection setup
    - Monitoring instrumentation
    - Background task startup
    """
    startup_logger = structlog.get_logger(__name__)
    
    try:
        startup_logger.info(
            "application_startup",
            environment=settings.ENVIRONMENT,
            version=settings.APP_VERSION,
            log_level=settings.LOG_LEVEL,
            debug=settings.DEBUG,
        )
        
        # Initialize database connection pool
        if settings.DATABASE_URL:
            startup_logger.info("initializing_database_pool")
            _app_state["database"] = await get_database()
            await _app_state["database"].connect()
            startup_logger.info("database_pool_initialized")
        
        # Initialize Redis connection pool
        if settings.REDIS_URL:
            startup_logger.info("initializing_redis_pool")
            _app_state["redis"] = await get_redis()
            startup_logger.info("redis_pool_initialized")
        
        # Initialize OpenTelemetry if enabled
        if settings.OTEL_ENABLED:
            startup_logger.info("initializing_opentelemetry")
            setup_opentelemetry(app)
            startup_logger.info("opentelemetry_initialized")
        
        # Initialize monitoring if enabled
        if settings.METRICS_ENABLED:
            startup_logger.info("initializing_metrics")
            setup_metrics(app)
            startup_logger.info("metrics_initialized")
        
        # Start background tasks if any
        if settings.BACKGROUND_TASKS_ENABLED:
            startup_logger.info("starting_background_tasks")
            await start_background_tasks()
            startup_logger.info("background_tasks_started")
        
        startup_logger.info("application_startup_complete")
        yield
        
    except Exception as e:
        startup_logger.error(
            "application_startup_failed",
            error=str(e),
            exc_info=True,
        )
        raise
        
    finally:
        shutdown_logger = structlog.get_logger(__name__)
        shutdown_logger.info("application_shutdown_started")
        
        # Shutdown database connection pool
        if "database" in _app_state:
            try:
                shutdown_logger.info("closing_database_pool")
                await _app_state["database"].disconnect()
                shutdown_logger.info("database_pool_closed")
            except Exception as e:
                shutdown_logger.error(
                    "database_pool_shutdown_error",
                    error=str(e),
                )
        
        # Shutdown Redis connection pool
        if "redis" in _app_state:
            try:
                shutdown_logger.info("closing_redis_pool")
                await _app_state["redis"].close()
                shutdown_logger.info("redis_pool_closed")
            except Exception as e:
                shutdown_logger.error(
                    "redis_pool_shutdown_error",
                    error=str(e),
                )
        
        # Cancel background tasks
        if "background_tasks" in _app_state:
            try:
                shutdown_logger.info("cancelling_background_tasks")
                for task in _app_state["background_tasks"]:
                    task.cancel()
                shutdown_logger.info("background_tasks_cancelled")
            except Exception as e:
                shutdown_logger.error(
                    "background_tasks_shutdown_error",
                    error=str(e),
                )
        
        shutdown_logger.info("application_shutdown_complete")


def setup_opentelemetry(app: FastAPI):
    """Configure OpenTelemetry for distributed tracing."""
    
    # Create resource
    resource = Resource(attributes={
        SERVICE_NAME: settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    })
    
    # Set tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Add OTLP exporter if endpoint is configured
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
        )
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls=settings.OTEL_EXCLUDED_URLS,
    )
    
    # Instrument Redis if enabled
    if settings.REDIS_URL and settings.OTEL_INSTRUMENT_REDIS:
        RedisInstrumentor().instrument(tracer_provider=tracer_provider)
    
    # Instrument SQLAlchemy if enabled
    if settings.DATABASE_URL and settings.OTEL_INSTRUMENT_SQLALCHEMY:
        SQLAlchemyInstrumentor().instrument(tracer_provider=tracer_provider)


def setup_metrics(app: FastAPI):
    """Configure Prometheus metrics."""
    
    # Create ASGI app for metrics endpoint
    metrics_app = make_asgi_app()
    
    # Mount metrics endpoint
    app.mount("/metrics", metrics_app)
    
    logger.info("metrics_endpoint_mounted", path="/metrics")


async def start_background_tasks():
    """Start background tasks for the application."""
    
    tasks = []
    
    # Example: Start periodic health check task
    if settings.BACKGROUND_HEALTH_CHECKS:
        from .background_tasks import health_check_task
        task = asyncio.create_task(health_check_task())
        tasks.append(task)
        logger.info("health_check_task_started")
    
    # Example: Start cache warming task
    if settings.BACKGROUND_CACHE_WARMING:
        from .background_tasks import cache_warming_task
        task = asyncio.create_task(cache_warming_task())
        tasks.append(task)
        logger.info("cache_warming_task_started")
    
    # Example: Start metrics aggregation task
    if settings.BACKGROUND_METRICS_AGGREGATION:
        from .background_tasks import metrics_aggregation_task
        task = asyncio.create_task(metrics_aggregation_task())
        tasks.append(task)
        logger.info("metrics_aggregation_task_started")
    
    _app_state["background_tasks"] = tasks


def setup_rate_limiter() -> Limiter:
    """Configure rate limiting."""
    
    # Create rate limiter instance
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=settings.RATE_LIMIT_DEFAULT,
        storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
        storage_options={
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
        },
        strategy="fixed-window",
        headers_enabled=True,
    )
    
    return limiter


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    
    # Initialize application with metadata
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
        debug=settings.DEBUG,
        lifespan=lifespan,
        default_response_class=JSONResponse,
        root_path=settings.ROOT_PATH,
        servers=[
            {"url": "http://localhost:8000", "description": "Local development"},
            {"url": "https://api.goat-prediction.com", "description": "Production API"},
        ] if settings.ENVIRONMENT == "production" else None,
    )
    
    # Setup rate limiter
    if settings.RATE_LIMIT_ENABLED:
        limiter = setup_rate_limiter()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add CORS middleware
    if settings.CORS_ENABLED:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
            max_age=settings.CORS_MAX_AGE,
        )
    
    # Add trusted host middleware
    if settings.TRUSTED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.TRUSTED_HOSTS,
        )
    
    # Add GZip middleware for response compression
    if settings.GZIP_ENABLED:
        app.add_middleware(
            GZipMiddleware,
            minimum_size=settings.GZIP_MINIMUM_SIZE,
        )
    
    # Add custom middlewares
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(DatabaseSessionMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CacheControlMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(AuditLogMiddleware)
    
    # Add timeout middleware if enabled
    if settings.REQUEST_TIMEOUT > 0:
        app.add_middleware(
            TimeoutMiddleware,
            timeout=settings.REQUEST_TIMEOUT,
        )
    
    # Setup all routers
    setup_routers(app)
    
    # Add health check endpoint
    @app.get(
        "/health",
        tags=["health"],
        summary="Health Check",
        description="Check the health status of the API",
        response_description="Health status of the service",
    )
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for monitoring."""
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
        
        # Check database connectivity
        if settings.DATABASE_URL:
            try:
                database = await get_database()
                await database.execute("SELECT 1")
                health_status["database"] = "healthy"
            except Exception as e:
                health_status["database"] = "unhealthy"
                health_status["database_error"] = str(e)
                health_status["status"] = "degraded"
        
        # Check Redis connectivity
        if settings.REDIS_URL:
            try:
                redis = await get_redis()
                await redis.ping()
                health_status["redis"] = "healthy"
            except Exception as e:
                health_status["redis"] = "unhealthy"
                health_status["redis_error"] = str(e)
                health_status["status"] = "degraded"
        
        return health_status
    
    # Add readiness probe
    @app.get(
        "/ready",
        tags=["health"],
        summary="Readiness Probe",
        description="Check if the service is ready to accept traffic",
        response_description="Readiness status of the service",
    )
    async def readiness_probe() -> Dict[str, Any]:
        """Readiness probe for Kubernetes/container orchestration."""
        
        readiness = {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
        }
        
        all_ready = True
        
        # Database readiness check
        if settings.DATABASE_URL:
            try:
                database = await get_database()
                await database.execute("SELECT 1")
                readiness["checks"]["database"] = "ready"
            except Exception as e:
                readiness["checks"]["database"] = "not_ready"
                readiness["checks"]["database_error"] = str(e)
                all_ready = False
        
        # Redis readiness check
        if settings.REDIS_URL:
            try:
                redis = await get_redis()
                await redis.ping()
                readiness["checks"]["redis"] = "ready"
            except Exception as e:
                readiness["checks"]["redis"] = "not_ready"
                readiness["checks"]["redis_error"] = str(e)
                all_ready = False
        
        readiness["status"] = "ready" if all_ready else "not_ready"
        return readiness
    
    # Add liveness probe
    @app.get(
        "/live",
        tags=["health"],
        summary="Liveness Probe",
        description="Check if the service is alive",
        response_description="Liveness status of the service",
    )
    async def liveness_probe() -> Dict[str, Any]:
        """Liveness probe for Kubernetes/container orchestration."""
        
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "service": settings.APP_NAME,
            "uptime": get_uptime(),
        }
    
    # Add root endpoint
    @app.get(
        "/",
        tags=["root"],
        summary="API Root",
        description="Root endpoint with API information",
        response_description="API information and available endpoints",
    )
    async def root() -> Dict[str, Any]:
        """Root endpoint with API information."""
        
        return {
            "name": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "documentation": "/docs" if settings.DOCS_ENABLED else None,
            "health": "/health",
            "ready": "/ready",
            "live": "/live",
            "metrics": "/metrics" if settings.METRICS_ENABLED else None,
            "contact": {
                "email": settings.CONTACT_EMAIL,
                "website": settings.CONTACT_WEBSITE,
            },
            "terms": settings.TERMS_URL,
            "license": {
                "name": settings.LICENSE_NAME,
                "url": settings.LICENSE_URL,
            },
        }
    
    # Add version endpoint
    @app.get(
        "/version",
        tags=["info"],
        summary="API Version",
        description="Get the current API version",
        response_description="API version information",
    )
    async def version() -> Dict[str, Any]:
        """Get API version information."""
        
        return {
            "version": settings.APP_VERSION,
            "build": settings.BUILD_NUMBER,
            "commit": settings.COMMIT_HASH,
            "build_date": settings.BUILD_DATE,
            "python_version": sys.version,
        }
    
    # Add info endpoint
    @app.get(
        "/info",
        tags=["info"],
        summary="API Information",
        description="Get detailed information about the API",
        response_description="Detailed API information",
    )
    async def info() -> Dict[str, Any]:
        """Get detailed API information."""
        
        return {
            "name": settings.APP_NAME,
            "description": settings.APP_DESCRIPTION,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "features": {
                "cors": settings.CORS_ENABLED,
                "rate_limiting": settings.RATE_LIMIT_ENABLED,
                "metrics": settings.METRICS_ENABLED,
                "tracing": settings.OTEL_ENABLED,
                "compression": settings.GZIP_ENABLED,
                "database": bool(settings.DATABASE_URL),
                "cache": bool(settings.REDIS_URL),
                "background_tasks": settings.BACKGROUND_TASKS_ENABLED,
            },
            "limits": {
                "rate_limit": settings.RATE_LIMIT_DEFAULT,
                "request_timeout": settings.REQUEST_TIMEOUT,
                "max_body_size": settings.MAX_BODY_SIZE,
            },
            "endpoints": {
                "health": "/health",
                "ready": "/ready",
                "live": "/live",
                "metrics": "/metrics" if settings.METRICS_ENABLED else None,
                "docs": "/docs" if settings.DOCS_ENABLED else None,
                "redoc": "/redoc" if settings.DOCS_ENABLED else None,
            },
        }
    
    # Add metrics endpoint (if not already mounted)
    if not settings.METRICS_ENABLED:
        @app.get(
            "/metrics",
            tags=["metrics"],
            summary="Metrics",
            description="Prometheus metrics endpoint",
            response_description="Metrics in Prometheus format",
            include_in_schema=False,
        )
        async def metrics():
            """Placeholder metrics endpoint when not enabled."""
            return Response(
                content="# Metrics disabled\n",
                media_type="text/plain",
                status_code=status.HTTP_404_NOT_FOUND,
            )
    
    # Custom 404 handler
    @app.exception_handler(404)
    async def custom_404_handler(request: Request, exc: Exception) -> JSONResponse:
        """Custom 404 handler."""
        
        logger.warning(
            "route_not_found",
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None,
        )
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "not_found",
                "message": f"Route {request.url.path} not found",
                "path": str(request.url.path),
                "method": request.method,
            },
        )
    
    # Custom 405 handler
    @app.exception_handler(405)
    async def custom_405_handler(request: Request, exc: Exception) -> JSONResponse:
        """Custom 405 handler."""
        
        logger.warning(
            "method_not_allowed",
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None,
        )
        
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "error": "method_not_allowed",
                "message": f"Method {request.method} not allowed for {request.url.path}",
                "path": str(request.url.path),
                "method": request.method,
                "allowed_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            },
            headers={"Allow": "GET, POST, PUT, DELETE, PATCH, OPTIONS"},
        )
    
    # Custom 500 handler
    @app.exception_handler(500)
    async def custom_500_handler(request: Request, exc: Exception) -> JSONResponse:
        """Custom 500 handler."""
        
        logger.error(
            "internal_server_error",
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else None,
            error=str(exc),
            exc_info=True,
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An internal server error occurred",
                "request_id": request.state.request_id if hasattr(request.state, "request_id") else None,
            },
        )
    
    logger.info(
        "application_created",
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )
    
    return app


def get_uptime() -> str:
    """Calculate and format application uptime."""
    
    if "start_time" not in _app_state:
        _app_state["start_time"] = datetime.utcnow()
    
    uptime = datetime.utcnow() - _app_state["start_time"]
    
    # Format uptime
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


# Create the application instance
app = create_application()


def main():
    """Main entry point for running the application."""
    
    # Configure uvicorn
    uvicorn_config = {
        "app": "src.app:app",
        "host": settings.HOST,
        "port": settings.PORT,
        "reload": settings.RELOAD,
        "log_level": settings.LOG_LEVEL.lower(),
        "access_log": settings.ACCESS_LOG,
        "workers": settings.WORKERS,
        "proxy_headers": settings.PROXY_HEADERS,
        "forwarded_allow_ips": settings.FORWARDED_ALLOW_IPS,
        "limit_concurrency": settings.LIMIT_CONCURRENCY,
        "backlog": settings.BACKLOG,
        "limit_max_requests": settings.LIMIT_MAX_REQUESTS,
        "timeout_keep_alive": settings.TIMEOUT_KEEP_ALIVE,
        "ssl_keyfile": settings.SSL_KEYFILE,
        "ssl_certfile": settings.SSL_CERTFILE,
        "ssl_keyfile_password": settings.SSL_KEYFILE_PASSWORD,
        "ssl_version": settings.SSL_VERSION,
        "ssl_cert_reqs": settings.SSL_CERT_REQS,
        "ssl_ca_certs": settings.SSL_CA_CERTS,
        "ssl_ciphers": settings.SSL_CIPHERS,
    }
    
    # Remove None values from config
    uvicorn_config = {k: v for k, v in uvicorn_config.items() if v is not None}
    
    logger.info(
        "starting_uvicorn_server",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.RELOAD,
        environment=settings.ENVIRONMENT,
    )
    
    # Run uvicorn
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()
