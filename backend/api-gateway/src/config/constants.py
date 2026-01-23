"""
Constants for GOAT Prediction API Gateway.
Centralized location for all application constants, enums, and static configuration.
"""

from enum import Enum, IntEnum
from typing import Dict, List, Tuple, Any


# ===========================================
# Environment & Deployment Constants
# ===========================================

class Environment(str, Enum):
    """Application environment constants."""
    
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    LOCAL = "local"
    DOCKER = "docker"
    CI = "ci"


ENVIRONMENT_CHOICES = [env.value for env in Environment]

# Environment-specific settings
ENVIRONMENT_CONFIG = {
    Environment.DEVELOPMENT: {
        "debug": True,
        "reload": True,
        "workers": 1,
        "log_level": "DEBUG",
        "cors_origins": ["http://localhost:3000", "http://localhost:8080"],
    },
    Environment.TESTING: {
        "debug": False,
        "reload": False,
        "workers": 1,
        "log_level": "INFO",
        "cors_origins": ["http://localhost:3000"],
    },
    Environment.STAGING: {
        "debug": False,
        "reload": False,
        "workers": 4,
        "log_level": "INFO",
        "cors_origins": ["https://staging.goat-prediction.com"],
    },
    Environment.PRODUCTION: {
        "debug": False,
        "reload": False,
        "workers": 8,
        "log_level": "WARNING",
        "cors_origins": ["https://goat-prediction.com"],
    },
}


# ===========================================
# Logging Constants
# ===========================================

class LogLevel(str, Enum):
    """Logging level constants."""
    
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


LOG_LEVEL_CHOICES = [level.value for level in LogLevel]

# Log format constants
LOG_FORMATS = {
    "json": "json",
    "text": "text",
    "console": "console",
    "gunicorn": "gunicorn",
}

# Log field names
LOG_FIELDS = {
    "timestamp": "timestamp",
    "level": "level",
    "logger": "logger",
    "message": "message",
    "event": "event",
    "request_id": "request_id",
    "correlation_id": "correlation_id",
    "user_id": "user_id",
    "ip_address": "ip_address",
    "user_agent": "user_agent",
    "method": "method",
    "path": "path",
    "status_code": "status_code",
    "response_time": "response_time",
    "error": "error",
    "stack_trace": "stack_trace",
}


# ===========================================
# User & Authentication Constants
# ===========================================

class UserRole(str, Enum):
    """User role constants."""
    
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SYSTEM = "system"
    BOT = "bot"
    MODERATOR = "moderator"
    ANALYST = "analyst"
    TRADER = "trader"


USER_ROLES = [role.value for role in UserRole]

# User role hierarchy (higher = more permissions)
ROLE_HIERARCHY = {
    UserRole.USER: 0,
    UserRole.PREMIUM: 1,
    UserRole.ANALYST: 2,
    UserRole.TRADER: 3,
    UserRole.MODERATOR: 4,
    UserRole.ADMIN: 5,
    UserRole.SYSTEM: 6,
}

# User status
class UserStatus(str, Enum):
    """User account status."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"


# Subscription tiers
class SubscriptionTier(str, Enum):
    """Subscription tier constants."""
    
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


# Permission constants
class Permission(str, Enum):
    """Permission constants."""
    
    # User permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    
    # Prediction permissions
    PREDICTION_READ = "prediction:read"
    PREDICTION_WRITE = "prediction:write"
    PREDICTION_DELETE = "prediction:delete"
    
    # Betting permissions
    BETTING_READ = "betting:read"
    BETTING_WRITE = "betting:write"
    BETTING_DELETE = "betting:delete"
    
    # Admin permissions
    ADMIN_READ = "admin:read"
    ADMIN_WRITE = "admin:write"
    ADMIN_DELETE = "admin:delete"
    
    # System permissions
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_DELETE = "system:delete"


# Role to permission mapping
ROLE_PERMISSIONS = {
    UserRole.USER: [
        Permission.USER_READ,
        Permission.PREDICTION_READ,
        Permission.BETTING_READ,
    ],
    UserRole.PREMIUM: [
        Permission.USER_READ,
        Permission.PREDICTION_READ,
        Permission.PREDICTION_WRITE,
        Permission.BETTING_READ,
        Permission.BETTING_WRITE,
    ],
    UserRole.ANALYST: [
        Permission.USER_READ,
        Permission.PREDICTION_READ,
        Permission.PREDICTION_WRITE,
        Permission.BETTING_READ,
    ],
    UserRole.TRADER: [
        Permission.USER_READ,
        Permission.PREDICTION_READ,
        Permission.BETTING_READ,
        Permission.BETTING_WRITE,
    ],
    UserRole.MODERATOR: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.PREDICTION_READ,
        Permission.PREDICTION_WRITE,
        Permission.BETTING_READ,
        Permission.BETTING_WRITE,
    ],
    UserRole.ADMIN: [
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.PREDICTION_READ,
        Permission.PREDICTION_WRITE,
        Permission.PREDICTION_DELETE,
        Permission.BETTING_READ,
        Permission.BETTING_WRITE,
        Permission.BETTING_DELETE,
        Permission.ADMIN_READ,
        Permission.ADMIN_WRITE,
    ],
    UserRole.SYSTEM: [
        Permission.SYSTEM_READ,
        Permission.SYSTEM_WRITE,
        Permission.SYSTEM_DELETE,
    ],
}


# ===========================================
# Sports & Markets Constants
# ===========================================

class Sport(str, Enum):
    """Sports supported by the platform."""
    
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    HOCKEY = "hockey"
    RUGBY = "rugby"
    CRICKET = "cricket"
    GOLF = "golf"
    BOXING = "boxing"
    MMA = "mma"
    FORMULA1 = "formula1"


SPORTS = [sport.value for sport in Sport]

# Sport display names
SPORT_DISPLAY_NAMES = {
    Sport.FOOTBALL: "Football",
    Sport.BASKETBALL: "Basketball",
    Sport.TENNIS: "Tennis",
    Sport.ESPORTS: "Esports",
    Sport.BASEBALL: "Baseball",
    Sport.HOCKEY: "Ice Hockey",
    Sport.RUGBY: "Rugby",
    Sport.CRICKET: "Cricket",
    Sport.GOLF: "Golf",
    Sport.BOXING: "Boxing",
    Sport.MMA: "Mixed Martial Arts",
    Sport.FORMULA1: "Formula 1",
}

# Sport categories
class SportCategory(str, Enum):
    """Sport categories."""
    
    TEAM_SPORTS = "team_sports"
    INDIVIDUAL_SPORTS = "individual_sports"
    MOTOR_SPORTS = "motor_sports"
    ESPORTS = "esports"


SPORT_CATEGORIES = {
    Sport.FOOTBALL: SportCategory.TEAM_SPORTS,
    Sport.BASKETBALL: SportCategory.TEAM_SPORTS,
    Sport.BASEBALL: SportCategory.TEAM_SPORTS,
    Sport.HOCKEY: SportCategory.TEAM_SPORTS,
    Sport.RUGBY: SportCategory.TEAM_SPORTS,
    Sport.CRICKET: SportCategory.TEAM_SPORTS,
    Sport.TENNIS: SportCategory.INDIVIDUAL_SPORTS,
    Sport.GOLF: SportCategory.INDIVIDUAL_SPORTS,
    Sport.BOXING: SportCategory.INDIVIDUAL_SPORTS,
    Sport.MMA: SportCategory.INDIVIDUAL_SPORTS,
    Sport.ESPORTS: SportCategory.ESPORTS,
    Sport.FORMULA1: SportCategory.MOTOR_SPORTS,
}

# Market types
class MarketType(str, Enum):
    """Betting market types."""
    
    # Common markets
    MATCH_WINNER = "match_winner"
    OVER_UNDER = "over_under"
    HANDICAP = "handicap"
    BOTH_TEAMS_TO_SCORE = "both_teams_to_score"
    CORRECT_SCORE = "correct_score"
    
    # Football specific
    HALF_TIME = "half_time"
    FULL_TIME = "full_time"
    DOUBLE_CHANCE = "double_chance"
    DRAW_NO_BET = "draw_no_bet"
    CORNERS = "corners"
    CARDS = "cards"
    PLAYER_GOALS = "player_goals"
    PENALTIES = "penalties"
    
    # Basketball specific
    POINT_SPREAD = "point_spread"
    TOTAL_POINTS = "total_points"
    QUARTER_BETTING = "quarter_betting"
    PLAYER_POINTS = "player_points"
    PLAYER_ASSISTS = "player_assists"
    PLAYER_REBOUNDS = "player_rebounds"
    
    # Tennis specific
    SET_BETTING = "set_betting"
    TOTAL_GAMES = "total_games"
    GAMES_SPREAD = "games_spread"
    TIEBREAK = "tiebreak"
    SET_SCORE = "set_score"
    
    # Esports specific
    MAP_WINNER = "map_winner"
    TOTAL_KILLS = "total_kills"
    FIRST_BLOOD = "first_blood"
    TOTAL_ROUNDS = "total_rounds"
    PLAYER_KILLS = "player_kills"
    
    # Special markets
    ACCUMULATOR = "accumulator"
    SYSTEM = "system"
    LIVE_BETTING = "live_betting"
    FUTURES = "futures"
    PROPS = "props"


# Market categories
MARKET_CATEGORIES = {
    "main": [MarketType.MATCH_WINNER, MarketType.OVER_UNDER, MarketType.HANDICAP],
    "goals": [MarketType.BOTH_TEAMS_TO_SCORE, MarketType.CORRECT_SCORE, MarketType.PLAYER_GOALS],
    "specials": [MarketType.CORNERS, MarketType.CARDS, MarketType.PENALTIES],
    "player": [MarketType.PLAYER_GOALS, MarketType.PLAYER_POINTS, MarketType.PLAYER_ASSISTS],
    "live": [MarketType.LIVE_BETTING],
    "futures": [MarketType.FUTURES],
}

# Sport to market mapping
SPORT_MARKETS = {
    Sport.FOOTBALL: [
        MarketType.MATCH_WINNER,
        MarketType.OVER_UNDER,
        MarketType.HANDICAP,
        MarketType.BOTH_TEAMS_TO_SCORE,
        MarketType.CORRECT_SCORE,
        MarketType.HALF_TIME,
        MarketType.DOUBLE_CHANCE,
        MarketType.DRAW_NO_BET,
        MarketType.CORNERS,
        MarketType.CARDS,
        MarketType.PLAYER_GOALS,
        MarketType.PENALTIES,
    ],
    Sport.BASKETBALL: [
        MarketType.MATCH_WINNER,
        MarketType.POINT_SPREAD,
        MarketType.TOTAL_POINTS,
        MarketType.HANDICAP,
        MarketType.QUARTER_BETTING,
        MarketType.PLAYER_POINTS,
        MarketType.PLAYER_ASSISTS,
        MarketType.PLAYER_REBOUNDS,
    ],
    Sport.TENNIS: [
        MarketType.MATCH_WINNER,
        MarketType.SET_BETTING,
        MarketType.TOTAL_GAMES,
        MarketType.GAMES_SPREAD,
        MarketType.HANDICAP,
        MarketType.TIEBREAK,
        MarketType.SET_SCORE,
    ],
    Sport.ESPORTS: [
        MarketType.MATCH_WINNER,
        MarketType.MAP_WINNER,
        MarketType.HANDICAP,
        MarketType.TOTAL_KILLS,
        MarketType.FIRST_BLOOD,
        MarketType.TOTAL_ROUNDS,
        MarketType.PLAYER_KILLS,
    ],
}


# ===========================================
# Betting & Odds Constants
# ===========================================

class OddsFormat(str, Enum):
    """Odds format constants."""
    
    DECIMAL = "decimal"
    FRACTIONAL = "fractional"
    AMERICAN = "american"
    PROBABILITY = "probability"
    HONGKONG = "hongkong"
    INDONESIAN = "indonesian"
    MALAY = "malay"


ODDS_FORMATS = [fmt.value for fmt in OddsFormat]

# Odds format display names
ODDS_FORMAT_DISPLAY = {
    OddsFormat.DECIMAL: "Decimal",
    OddsFormat.FRACTIONAL: "Fractional",
    OddsFormat.AMERICAN: "American",
    OddsFormat.PROBABILITY: "Probability",
    OddsFormat.HONGKONG: "Hong Kong",
    OddsFormat.INDONESIAN: "Indonesian",
    OddsFormat.MALAY: "Malay",
}

# Bet types
class BetType(str, Enum):
    """Bet type constants."""
    
    SINGLE = "single"
    MULTIPLE = "multiple"
    SYSTEM = "system"
    ACCUMULATOR = "accumulator"
    PATENT = "patent"
    YANKEE = "yankee"
    LUCKY15 = "lucky15"
    LUCKY31 = "lucky31"
    LUCKY63 = "lucky63"
    HEINZ = "heinz"
    SUPER_HEINZ = "super_heinz"
    GOLIATH = "goliath"


# Bet status
class BetStatus(str, Enum):
    """Bet status constants."""
    
    PENDING = "pending"
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CASHED_OUT = "cashed_out"
    VOID = "void"
    SETTLED = "settled"
    CANCELLED = "cancelled"


# Bet settlement status
class SettlementStatus(str, Enum):
    """Bet settlement status."""
    
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    HALF_WON = "half_won"
    HALF_LOST = "half_lost"
    VOID = "void"
    DRAW = "draw"


# Minimum and maximum odds
MIN_ODDS = 1.01
MAX_ODDS = 1000.0

# Minimum and maximum stake
MIN_STAKE = 0.10  # $0.10
MAX_STAKE = 10000.0  # $10,000

# Commission rates
COMMISSION_RATES = {
    "standard": 0.05,  # 5% commission
    "premium": 0.03,   # 3% commission
    "vip": 0.01,       # 1% commission
}

# Kelly criterion fractions
KELLY_FRACTIONS = {
    "full": 1.0,
    "half": 0.5,
    "quarter": 0.25,
    "eighth": 0.125,
    "safe": 0.1,
}


# ===========================================
# Prediction Constants
# ===========================================

class PredictionStatus(str, Enum):
    """Prediction status constants."""
    
    PENDING = "pending"
    ACTIVE = "active"
    WINNING = "winning"
    LOSING = "losing"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    SETTLED = "settled"
    EXPIRED = "expired"


class PredictionSource(str, Enum):
    """Prediction source constants."""
    
    AI_MODEL = "ai_model"
    EXPERT = "expert"
    COMMUNITY = "community"
    HYBRID = "hybrid"
    MANUAL = "manual"


class PredictionConfidence(str, Enum):
    """Prediction confidence levels."""
    
    VERY_LOW = "very_low"    # 0-20%
    LOW = "low"             # 20-40%
    MEDIUM = "medium"       # 40-60%
    HIGH = "high"           # 60-80%
    VERY_HIGH = "very_high" # 80-100%


# Confidence level to percentage mapping
CONFIDENCE_PERCENTAGES = {
    PredictionConfidence.VERY_LOW: (0.0, 0.2),
    PredictionConfidence.LOW: (0.2, 0.4),
    PredictionConfidence.MEDIUM: (0.4, 0.6),
    PredictionConfidence.HIGH: (0.6, 0.8),
    PredictionConfidence.VERY_HIGH: (0.8, 1.0),
}

# Model types
class ModelType(str, Enum):
    """Machine learning model types."""
    
    TRANSFORMER = "transformer"
    GNN = "gnn"
    LSTM = "lstm"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    ENSEMBLE = "ensemble"
    NEURAL_NETWORK = "neural_network"
    BAYESIAN = "bayesian"
    MARKOV = "markov"
    ELO = "elo"
    TRUESKILL = "trueskill"


# Feature sets
FEATURE_SETS = {
    "basic": ["form", "h2h", "home_advantage"],
    "advanced": ["xG", "possession", "shots", "passing", "defense"],
    "expert": ["player_fitness", "weather", "referee", "motivation"],
    "quantitative": ["market_movement", "volume", "sentiment"],
}


# ===========================================
# API & HTTP Constants
# ===========================================

class HTTPMethod(str, Enum):
    """HTTP method constants."""
    
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"
    HEAD = "HEAD"


HTTP_METHODS = [method.value for method in HTTPMethod]

# HTTP status codes
class HTTPStatus(IntEnum):
    """HTTP status code constants."""
    
    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    
    # 4xx Client Errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 5xx Server Errors
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504


# API error codes
class ErrorCode(str, Enum):
    """API error code constants."""
    
    # General errors
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    CONFLICT_ERROR = "conflict_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    
    # Business logic errors
    INSUFFICIENT_FUNDS = "insufficient_funds"
    BET_LIMIT_EXCEEDED = "bet_limit_exceeded"
    MARKET_CLOSED = "market_closed"
    ODDS_CHANGED = "odds_changed"
    STAKE_TOO_LOW = "stake_too_low"
    STAKE_TOO_HIGH = "stake_too_high"
    
    # System errors
    DATABASE_ERROR = "database_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    TIMEOUT_ERROR = "timeout_error"
    INTERNAL_SERVER_ERROR = "internal_server_error"
    
    # Prediction errors
    PREDICTION_EXPIRED = "prediction_expired"
    MODEL_ERROR = "model_error"
    FEATURE_ERROR = "feature_error"
    CONFIDENCE_TOO_LOW = "confidence_too_low"


# Rate limiting tiers
RATE_LIMIT_TIERS = {
    "free": {
        "requests_per_minute": 60,
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
    },
    "basic": {
        "requests_per_minute": 120,
        "requests_per_hour": 5000,
        "requests_per_day": 50000,
    },
    "premium": {
        "requests_per_minute": 300,
        "requests_per_hour": 20000,
        "requests_per_day": 200000,
    },
    "enterprise": {
        "requests_per_minute": 1000,
        "requests_per_hour": 100000,
        "requests_per_day": 1000000,
    },
}


# ===========================================
# Cache & Redis Constants
# ===========================================

# Cache key patterns
CACHE_KEY_PATTERNS = {
    # User cache
    "user": "user:{user_id}",
    "user_session": "session:{session_id}",
    "user_tokens": "tokens:{user_id}",
    
    # Prediction cache
    "prediction": "prediction:{prediction_id}",
    "predictions_by_sport": "predictions:sport:{sport}:{date}",
    "predictions_by_match": "predictions:match:{match_id}",
    
    # Odds cache
    "odds": "odds:{bookmaker}:{match_id}:{market}",
    "odds_history": "odds:history:{match_id}:{market}",
    
    # Match cache
    "match": "match:{match_id}",
    "matches_by_league": "matches:league:{league_id}:{date}",
    "live_matches": "matches:live:{sport}",
    
    # Statistics cache
    "stats": "stats:{sport}:{league}:{season}",
    "player_stats": "stats:player:{player_id}:{season}",
    "team_stats": "stats:team:{team_id}:{season}",
    
    # Model cache
    "model": "model:{model_type}:{sport}:{version}",
    "model_predictions": "model:predictions:{model_id}:{timestamp}",
    
    # Configuration cache
    "config": "config:{key}",
    "feature_flags": "features:{feature}",
    
    # Rate limiting
    "rate_limit": "ratelimit:{identifier}:{window}",
}

# Cache TTLs in seconds
CACHE_TTLS = {
    "user": 3600,           # 1 hour
    "session": 86400,       # 24 hours
    "prediction": 300,      # 5 minutes
    "odds": 30,            # 30 seconds
    "match": 600,          # 10 minutes
    "stats": 3600,         # 1 hour
    "model": 86400,        # 24 hours
    "config": 300,         # 5 minutes
    "rate_limit": 60,      # 1 minute
}

# Redis connection pool settings
REDIS_POOL_SETTINGS = {
    "max_connections": 50,
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "retry_on_timeout": True,
    "health_check_interval": 30,
}


# ===========================================
# Database & ORM Constants
# ===========================================

# Database connection pool settings
DATABASE_POOL_SETTINGS = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
    "pool_timeout": 30,
    "echo": False,
}

# Database query timeouts (seconds)
QUERY_TIMEOUTS = {
    "fast": 5,
    "normal": 30,
    "slow": 120,
    "very_slow": 300,
}

# Batch sizes for database operations
BATCH_SIZES = {
    "insert": 1000,
    "update": 500,
    "delete": 1000,
    "select": 10000,
}


# ===========================================
# Time & Date Constants
# ===========================================

# Timezone constants
DEFAULT_TIMEZONE = "UTC"

# Supported timezones
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
    "Asia/Hong_Kong",
    "Asia/Singapore",
]

# Date formats
DATE_FORMATS = {
    "iso": "%Y-%m-%dT%H:%M:%SZ",
    "simple": "%Y-%m-%d %H:%M:%S",
    "date_only": "%Y-%m-%d",
    "time_only": "%H:%M:%S",
    "human": "%B %d, %Y at %I:%M %p",
}

# Time intervals in seconds
TIME_INTERVALS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,  # 30 days
    "year": 31536000,  # 365 days
}


# ===========================================
# Currency & Financial Constants
# ===========================================

class Currency(str, Enum):
    """Currency constants."""
    
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    JPY = "JPY"  # Japanese Yen
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan
    INR = "INR"  # Indian Rupee
    BRL = "BRL"  # Brazilian Real
    RUB = "RUB"  # Russian Ruble
    MXN = "MXN"  # Mexican Peso
    ZAR = "ZAR"  # South African Rand
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar


CURRENCIES = [currency.value for currency in Currency]

# Currency symbols
CURRENCY_SYMBOLS = {
    Currency.USD: "$",
    Currency.EUR: "€",
    Currency.GBP: "£",
    Currency.JPY: "¥",
    Currency.CNY: "¥",
    Currency.INR: "₹",
    Currency.BRL: "R$",
    Currency.RUB: "₽",
}

# Currency exchange rate cache TTL (seconds)
EXCHANGE_RATE_TTL = 3600  # 1 hour

# Minimum deposit/withdrawal amounts by currency
MIN_AMOUNTS = {
    Currency.USD: 10.0,
    Currency.EUR: 10.0,
    Currency.GBP: 10.0,
    Currency.CAD: 10.0,
    Currency.AUD: 10.0,
    Currency.JPY: 1000.0,
}


# ===========================================
# Feature Flags & A/B Testing
# ===========================================

class FeatureFlag(str, Enum):
    """Feature flag constants."""
    
    # UI/UX Features
    NEW_UI = "new_ui"
    DARK_MODE = "dark_mode"
    ADVANCED_CHARTS = "advanced_charts"
    REAL_TIME_UPDATES = "real_time_updates"
    
    # Prediction Features
    AI_PREDICTIONS = "ai_predictions"
    LIVE_PREDICTIONS = "live_predictions"
    MULTI_MODEL_ENSEMBLE = "multi_model_ensemble"
    QUANTUM_PREDICTIONS = "quantum_predictions"
    
    # Betting Features
    LIVE_BETTING = "live_betting"
    CASH_OUT = "cash_out"
    BET_BUILDER = "bet_builder"
    AUTO_BETTING = "auto_betting"
    
    # Social Features
    SOCIAL_FEED = "social_feed"
    USER_PROFILES = "user_profiles"
    LEADERBOARDS = "leaderboards"
    COMMUNITY_PREDICTIONS = "community_predictions"
    
    # Advanced Features
    API_V2 = "api_v2"
    WEBHOOKS = "webhooks"
    CUSTOM_ALERTS = "custom_alerts"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    
    # Experimental Features
    BLOCKCHAIN_BETTING = "blockchain_betting"
    NFT_INTEGRATION = "nft_integration"
    METAVERSE_INTEGRATION = "metaverse_integration"


# Feature flag rollout percentages
FEATURE_ROLLOUTS = {
    FeatureFlag.NEW_UI: 0.1,  # 10% rollout
    FeatureFlag.AI_PREDICTIONS: 1.0,  # 100% rollout
    FeatureFlag.LIVE_BETTING: 0.5,  # 50% rollout
}


# ===========================================
# External API Constants
# ===========================================

class ExternalAPI(str, Enum):
    """External API constants."""
    
    # Sports Data APIs
    STATSBOMB = "statsbomb"
    OPTA = "opta"
    SPORTRADAR = "sportradar"
    SPORTSDATAIO = "sportsdataio"
    THEODDSAPI = "theoddsapi"
    
    # Betting APIs
    BETFAIR = "betfair"
    PINNACLE = "pinnacle"
    BET365 = "bet365"
    WILLIAMHILL = "williamhill"
    
    # News & Social APIs
    NEWSAPI = "newsapi"
    TWITTER = "twitter"
    REDDIT = "reddit"
    
    # Weather APIs
    OPENWEATHER = "openweather"
    WEATHERAPI = "weatherapi"
    ACCUWEATHER = "accuweather"
    
    # Financial APIs
    EXCHANGERATEAPI = "exchangerateapi"
    COINMARKETCAP = "coinmarketcap"
    
    # AI/ML APIs
    OPENAI = "openai"
    GOOGLE_AI = "google_ai"
    HUGGINGFACE = "huggingface"


# API rate limits (requests per minute)
API_RATE_LIMITS = {
    ExternalAPI.STATSBOMB: 60,
    ExternalAPI.OPTA: 30,
    ExternalAPI.SPORTRADAR: 120,
    ExternalAPI.BETFAIR: 600,
    ExternalAPI.PINNACLE: 300,
    ExternalAPI.NEWSAPI: 100,
    ExternalAPI.TWITTER: 900,
    ExternalAPI.OPENWEATHER: 60,
    ExternalAPI.OPENAI: 60,
}

# API timeout in seconds
API_TIMEOUTS = {
    "fast": 10,
    "normal": 30,
    "slow": 60,
    "very_slow": 120,
}

# API retry configuration
API_RETRY_CONFIG = {
    "max_retries": 3,
    "backoff_factor": 0.5,
    "status_forcelist": [408, 429, 500, 502, 503, 504],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
}


# ===========================================
# Monitoring & Metrics Constants
# ===========================================

# Metrics names
METRIC_NAMES = {
    # Request metrics
    "request_count": "http_requests_total",
    "request_duration": "http_request_duration_seconds",
    "request_size": "http_request_size_bytes",
    "response_size": "http_response_size_bytes",
    
    # Error metrics
    "error_count": "http_errors_total",
    "error_rate": "http_error_rate",
    
    # Business metrics
    "user_count": "users_total",
    "active_users": "users_active",
    "prediction_count": "predictions_total",
    "bet_count": "bets_total",
    "revenue": "revenue_total",
    
    # System metrics
    "cpu_usage": "cpu_usage_percent",
    "memory_usage": "memory_usage_bytes",
    "disk_usage": "disk_usage_bytes",
    "database_connections": "database_connections_total",
    "redis_connections": "redis_connections_total",
}

# Alert thresholds
ALERT_THRESHOLDS = {
    "error_rate": 0.05,  # 5% error rate
    "response_time_p95": 2.0,  # 2 seconds P95
    "cpu_usage": 0.8,  # 80% CPU usage
    "memory_usage": 0.9,  # 90% memory usage
    "database_connections": 0.8,  # 80% of pool
}

# Health check intervals (seconds)
HEALTH_CHECK_INTERVALS = {
    "fast": 30,
    "normal": 60,
    "slow": 300,
}


# ===========================================
# Export All Constants
# ===========================================

__all__ = [
    # Environment
    "Environment",
    "ENVIRONMENT_CHOICES",
    "ENVIRONMENT_CONFIG",
    
    # Logging
    "LogLevel",
    "LOG_LEVEL_CHOICES",
    "LOG_FORMATS",
    "LOG_FIELDS",
    
    # User & Authentication
    "UserRole",
    "USER_ROLES",
    "ROLE_HIERARCHY",
    "UserStatus",
    "SubscriptionTier",
    "Permission",
    "ROLE_PERMISSIONS",
    
    # Sports & Markets
    "Sport",
    "SPORTS",
    "SPORT_DISPLAY_NAMES",
    "SportCategory",
    "SPORT_CATEGORIES",
    "MarketType",
    "MARKET_CATEGORIES",
    "SPORT_MARKETS",
    
    # Betting & Odds
    "OddsFormat",
    "ODDS_FORMATS",
    "ODDS_FORMAT_DISPLAY",
    "BetType",
    "BetStatus",
    "SettlementStatus",
    "MIN_ODDS",
    "MAX_ODDS",
    "MIN_STAKE",
    "MAX_STAKE",
    "COMMISSION_RATES",
    "KELLY_FRACTIONS",
    
    # Predictions
    "PredictionStatus",
    "PredictionSource",
    "PredictionConfidence",
    "CONFIDENCE_PERCENTAGES",
    "ModelType",
    "FEATURE_SETS",
    
    # API & HTTP
    "HTTPMethod",
    "HTTP_METHODS",
    "HTTPStatus",
    "ErrorCode",
    "RATE_LIMIT_TIERS",
    
    # Cache & Redis
    "CACHE_KEY_PATTERNS",
    "CACHE_TTLS",
    "REDIS_POOL_SETTINGS",
    
    # Database
    "DATABASE_POOL_SETTINGS",
    "QUERY_TIMEOUTS",
    "BATCH_SIZES",
    
    # Time & Date
    "DEFAULT_TIMEZONE",
    "TIMEZONES",
    "DATE_FORMATS",
    "TIME_INTERVALS",
    
    # Currency & Financial
    "Currency",
    "CURRENCIES",
    "CURRENCY_SYMBOLS",
    "EXCHANGE_RATE_TTL",
    "MIN_AMOUNTS",
    
    # Feature Flags
    "FeatureFlag",
    "FEATURE_ROLLOUTS",
    
    # External APIs
    "ExternalAPI",
    "API_RATE_LIMITS",
    "API_TIMEOUTS",
    "API_RETRY_CONFIG",
    
    # Monitoring
    "METRIC_NAMES",
    "ALERT_THRESHOLDS",
    "HEALTH_CHECK_INTERVALS",
]
