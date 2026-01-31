"""
GOAT PREDICTION ULTIMATE - API Gateway Constants
Constantes globales pour l'API Gateway
"""

from typing import List

# ============================================
# API VERSION & ROUTING
# ============================================
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
API_TITLE = "GOAT Prediction Ultimate API"
API_DESCRIPTION = """
🏆 **GOAT Prediction Ultimate API Gateway**

API de prédiction sportive la plus avancée au monde.

## Features:
- 🎯 Prédictions multi-sports (Football, Basketball, Tennis, eSports)
- 📊 Analytics en temps réel
- 💰 Gestion de bankroll et betting
- 🔐 Authentication JWT sécurisée
- 📈 Métriques et monitoring

## Sports supportés:
- ⚽ Football
- 🏀 Basketball
- 🎾 Tennis
- 🎮 eSports
"""

# ============================================
# CORS CONFIGURATION
# ============================================
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8080",
    "https://goat-prediction.com",
    "https://admin.goat-prediction.com",
]

CORS_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

CORS_HEADERS: List[str] = [
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "X-Request-ID",
    "X-Requested-With",
]

# ============================================
# ALLOWED HOSTS
# ============================================
ALLOWED_HOSTS: List[str] = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "goat-prediction.com",
    "api.goat-prediction.com",
    "*.goat-prediction.com",
]

# ============================================
# REQUEST LIMITS
# ============================================
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
REQUEST_TIMEOUT = 30  # seconds
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_REQUESTS = 100  # requests
RATE_LIMIT_PERIOD = 60  # seconds (1 minute)
RATE_LIMIT_BURST = 20  # burst requests

# Rate limits par endpoint
RATE_LIMITS = {
    "auth": {
        "login": {"requests": 5, "period": 60},
        "register": {"requests": 3, "period": 300},
        "forgot_password": {"requests": 3, "period": 600},
    },
    "predictions": {
        "get": {"requests": 100, "period": 60},
        "create": {"requests": 50, "period": 60},
    },
    "analytics": {
        "get": {"requests": 50, "period": 60},
    },
}

# ============================================
# PAGINATION
# ============================================
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MIN_PAGE_SIZE = 1

# ============================================
# CACHING
# ============================================
CACHE_DEFAULT_TTL = 300  # 5 minutes
CACHE_PREDICTIONS_TTL = 60  # 1 minute
CACHE_ANALYTICS_TTL = 600  # 10 minutes
CACHE_STATIC_TTL = 3600  # 1 hour

# ============================================
# TIMEOUTS
# ============================================
DB_QUERY_TIMEOUT = 30  # seconds
EXTERNAL_API_TIMEOUT = 10  # seconds
ML_PREDICTION_TIMEOUT = 5  # seconds
CACHE_TIMEOUT = 1  # second

# ============================================
# RETRY CONFIGURATION
# ============================================
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 2  # exponential backoff
RETRY_STATUSES = [500, 502, 503, 504]

# ============================================
# SPORTS CONSTANTS
# ============================================
SUPPORTED_SPORTS = ["football", "basketball", "tennis", "esports"]
DEFAULT_SPORT = "football"

SPORT_CODES = {
    "football": "FB",
    "basketball": "BB",
    "tennis": "TN",
    "esports": "ES",
}

# ============================================
# MARKETS
# ============================================
FOOTBALL_MARKETS = [
    "match_winner",
    "over_under",
    "both_teams_to_score",
    "exact_score",
    "halftime_fulltime",
    "corners",
    "cards",
]

BASKETBALL_MARKETS = [
    "match_winner",
    "point_spread",
    "total_points",
    "quarter_winner",
]

TENNIS_MARKETS = [
    "match_winner",
    "set_betting",
    "total_games",
    "tiebreak",
]

ESPORTS_MARKETS = [
    "match_winner",
    "map_winner",
    "total_kills",
    "first_blood",
]

# ============================================
# STATUS CODES
# ============================================
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_503_SERVICE_UNAVAILABLE = 503

# ============================================
# ERROR MESSAGES
# ============================================
ERROR_MESSAGES = {
    "UNAUTHORIZED": "Authentication required",
    "FORBIDDEN": "Access forbidden",
    "NOT_FOUND": "Resource not found",
    "VALIDATION_ERROR": "Validation error",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded. Please try again later.",
    "INTERNAL_ERROR": "Internal server error",
    "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
    "INVALID_REQUEST": "Invalid request",
    "MISSING_PARAMETER": "Missing required parameter",
}

# ============================================
# HEADERS
# ============================================
HEADER_REQUEST_ID = "X-Request-ID"
HEADER_API_KEY = "X-API-Key"
HEADER_USER_AGENT = "User-Agent"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_AUTHORIZATION = "Authorization"

# ============================================
# SECURITY
# ============================================
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600 * 24 * 7  # 7 days
JWT_REFRESH_EXPIRATION = 3600 * 24 * 30  # 30 days

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

# ============================================
# LOGGING
# ============================================
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# ============================================
# MONITORING
# ============================================
METRICS_ENABLED = True
METRICS_PORT = 9090
METRICS_PATH = "/metrics"

HEALTH_CHECK_PATH = "/health"
READINESS_CHECK_PATH = "/ready"
LIVENESS_CHECK_PATH = "/live"

# ============================================
# DOCUMENTATION
# ============================================
DOCS_URL = "/docs"
REDOC_URL = "/redoc"
OPENAPI_URL = "/openapi.json"

# ============================================
# FEATURE FLAGS
# ============================================
FEATURE_FLAGS = {
    "ENABLE_BETTING": True,
    "ENABLE_LIVE_PREDICTIONS": True,
    "ENABLE_ADVANCED_ANALYTICS": True,
    "ENABLE_MULTI_SPORT": True,
    "ENABLE_API_DOCS": True,
    "ENABLE_SWAGGER_UI": True,
    "ENABLE_MONITORING": True,
    "ENABLE_RATE_LIMITING": True,
    "ENABLE_CACHING": True,
}

# ============================================
# REGEX PATTERNS
# ============================================
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
UUID_REGEX = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
PHONE_REGEX = r"^\+?[1-9]\d{1,14}$"

# ============================================
# DATE/TIME FORMATS
# ============================================
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

# ============================================
# CURRENCIES
# ============================================
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "BTC", "ETH"]
DEFAULT_CURRENCY = "USD"

# ============================================
# LOCALES
# ============================================
SUPPORTED_LOCALES = ["en", "fr", "es", "de", "it"]
DEFAULT_LOCALE = "fr"

# ============================================
# TIMEZONE
# ============================================
DEFAULT_TIMEZONE = "UTC"
