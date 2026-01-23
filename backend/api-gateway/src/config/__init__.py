"""
Constants for GOAT Prediction API Gateway configuration.
"""

from enum import Enum
from typing import Dict, List, Tuple


# Environment Choices
ENVIRONMENT_CHOICES = ["development", "testing", "staging", "production"]

# Log Level Choices
LOG_LEVEL_CHOICES = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# User Roles
USER_ROLES = {
    "USER": "user",
    "PREMIUM": "premium", 
    "ADMIN": "admin",
    "SYSTEM": "system",
}

# Default CORS Origins
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

# Default Rate Limits
DEFAULT_RATE_LIMITS = [
    "100/minute",      # 100 requests per minute per IP
    "1000/hour",       # 1000 requests per hour per IP
    "10000/day",       # 10000 requests per day per IP
    "50/minute",       # 50 requests per minute per user
    "500/hour",        # 500 requests per hour per user
    "5000/day",        # 5000 requests per day per user
]

# Sports Configuration
SPORTS_CONFIG = {
    "football": {
        "name": "Football",
        "markets": [
            "match_winner",
            "over_under",
            "both_teams_to_score", 
            "correct_score",
            "half_time",
            "corners",
            "cards",
            "player_goals",
        ],
        "leagues": [
            "premier_league",
            "la_liga", 
            "serie_a",
            "bundesliga",
            "ligue_1",
            "champions_league",
            "europa_league",
            "world_cup",
            "euro",
        ],
        "data_sources": ["statsbomb", "opta", "sportradar"],
        "prediction_models": ["transformer", "gnn", "ensemble"],
    },
    "basketball": {
        "name": "Basketball",
        "markets": [
            "moneyline",
            "point_spread", 
            "total_points",
            "quarter_betting",
            "player_points",
            "player_assists",
            "player_rebounds",
        ],
        "leagues": ["nba", "euroleague", "fiba"],
        "data_sources": ["nba_api", "euroleague_api"],
        "prediction_models": ["gradient_boosting", "neural_network"],
    },
    "tennis": {
        "name": "Tennis",
        "markets": [
            "match_winner",
            "set_betting",
            "total_games",
            "games_spread",
            "tiebreak",
        ],
        "leagues": ["atp", "wta", "grand_slam"],
        "data_sources": ["atp_api", "wta_api"],
        "prediction_models": ["elo", "markov_chain", "mlp"],
    },
    "esports": {
        "name": "Esports",
        "markets": [
            "match_winner",
            "map_winner",
            "handicap",
            "total_kills",
            "first_blood",
        ],
        "leagues": ["lol", "dota2", "csgo", "valorant"],
        "data_sources": ["riot_api", "steam_api"],
        "prediction_models": ["lstm", "attention"],
    },
    "baseball": {
        "name": "Baseball",
        "markets": ["moneyline", "run_line", "total_runs"],
        "leagues": ["mlb"],
        "data_sources": ["mlb_api"],
        "prediction_models": ["poisson", "ensemble"],
    },
    "hockey": {
        "name": "Hockey",
        "markets": ["moneyline", "puck_line", "total_goals"],
        "leagues": ["nhl"],
        "data_sources": ["nhl_api"],
        "prediction_models": ["poisson", "ensemble"],
    },
    "rugby": {
        "name": "Rugby",
        "markets": ["match_winner", "handicap", "total_points"],
        "leagues": ["premiership", "super_rugby", "six_nations"],
        "data_sources": ["rugby_api"],
        "prediction_models": ["ensemble"],
    },
}

# Market Types
MARKET_TYPES = {
    "match_winner": "Match Winner",
    "over_under": "Over/Under",
    "both_teams_to_score": "Both Teams to Score",
    "correct_score": "Correct Score",
    "moneyline": "Moneyline",
    "point_spread": "Point Spread",
    "total_points": "Total Points",
    "set_betting": "Set Betting",
    "total_games": "Total Games",
    "handicap": "Handicap",
    "total_kills": "Total Kills",
    "first_blood": "First Blood",
}

# Betting Odds Formats
ODDS_FORMATS = {
    "decimal": "Decimal (European)",
    "fractional": "Fractional (British)",
    "american": "American (Moneyline)",
    "probability": "Probability (%)",
}

# Currencies
CURRENCIES = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "GBP": "British Pound",
    "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar",
    "JPY": "Japanese Yen",
}

# Timezones
TIMEZONES = [
    "UTC",
    "Europe/London",
    "Europe/Paris",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Australia/Sydney",
    "Asia/Tokyo",
    "Asia/Dubai",
]

# Languages
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
}

# API Response Formats
RESPONSE_FORMATS = ["json", "xml", "yaml", "csv"]

# Cache Keys
CACHE_KEYS = {
    "user": "user:{user_id}",
    "predictions": "predictions:{sport}:{league}:{date}",
    "odds": "odds:{bookmaker}:{match_id}",
    "config": "config:{key}",
    "rate_limit": "rate_limit:{identifier}:{window}",
    "session": "session:{session_id}",
}

# HTTP Status Codes
HTTP_STATUS_CODES = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}

# Error Codes
ERROR_CODES = {
    "validation_error": "Validation Error",
    "authentication_error": "Authentication Error",
    "authorization_error": "Authorization Error",
    "not_found": "Not Found",
    "rate_limit_exceeded": "Rate Limit Exceeded",
    "database_error": "Database Error",
    "external_service_error": "External Service Error",
    "timeout_error": "Timeout Error",
    "internal_server_error": "Internal Server Error",
}

# JWT Token Types
JWT_TOKEN_TYPES = {
    "access": "access",
    "refresh": "refresh",
    "api": "api",
    "password_reset": "password_reset",
    "email_verification": "email_verification",
}

# Background Task Names
BACKGROUND_TASKS = {
    "health_check": "health_check",
    "cache_warming": "cache_warming",
    "metrics_aggregation": "metrics_aggregation",
    "data_sync": "data_sync",
    "model_training": "model_training",
    "prediction_generation": "prediction_generation",
    "notification_sending": "notification_sending",
    "report_generation": "report_generation",
}

# Monitoring Metrics
MONITORING_METRICS = {
    "request_count": "request_count",
    "error_count": "error_count",
    "response_time": "response_time",
    "active_users": "active_users",
    "cache_hit_rate": "cache_hit_rate",
    "database_queries": "database_queries",
    "redis_operations": "redis_operations",
    "external_api_calls": "external_api_calls",
}

# Feature Flags
FEATURE_FLAGS = {
    "new_ui": "new_ui",
    "advanced_analytics": "advanced_analytics",
    "live_betting": "live_betting",
    "multi_sport": "multi_sport",
    "predictions_v2": "predictions_v2",
    "social_features": "social_features",
    "mobile_app": "mobile_app",
    "api_v2": "api_v2",
}
