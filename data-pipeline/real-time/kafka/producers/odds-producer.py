"""
Odds Producer for GOAT Prediction Ultimate
Collects odds from multiple bookmakers and publishes to Kafka for real-time processing.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
import aiokafka
import aiohttp
import asyncpg
from redis import asyncio as aioredis
from pydantic import BaseModel, ValidationError, Field, validator
import numpy as np
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from collections import defaultdict, deque
import hashlib
import time
import ssl
import certifi
from bs4 import BeautifulSoup
import re
import signal
import sys
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/odds-producer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class OddsConfig:
    """Configuration for Odds Producer"""
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092', 'kafka2:9092', 'kafka3:9092']
    KAFKA_TOPIC_ODDS = 'goat-odds'
    KAFKA_TOPIC_ALERTS = 'goat-alerts'
    KAFKA_ACKS = 'all'
    KAFKA_COMPRESSION = 'gzip'
    
    # Bookmaker APIs
    BOOKMAKERS = {
        'pinnacle': {
            'api_key': 'PINNACLE_API_KEY',
            'base_url': 'https://api.pinnacle.com/v1',
            'rate_limit': 1.0,  # seconds between requests
            'timeout': 30
        },
        'betfair': {
            'api_key': 'BETFAIR_API_KEY',
            'app_key': 'BETFAIR_APP_KEY',
            'base_url': 'https://api.betfair.com/exchange',
            'rate_limit': 0.5,
            'timeout': 30
        },
        'bet365': {
            'username': 'BET365_USERNAME',
            'password': 'BET365_PASSWORD',
            'base_url': 'https://api.bet365.com/v1',
            'rate_limit': 2.0,
            'timeout': 60
        },
        'williamhill': {
            'api_key': 'WILLIAMHILL_API_KEY',
            'base_url': 'https://api.wh.com/v1',
            'rate_limit': 1.5,
            'timeout': 30
        },
        'unibet': {
            'api_key': 'UNIBET_API_KEY',
            'base_url': 'https://api.unibet.com/v1',
            'rate_limit': 1.0,
            'timeout': 30
        },
        'bwin': {
            'api_key': 'BWIN_API_KEY',
            'base_url': 'https://api.bwin.com/v3',
            'rate_limit': 1.0,
            'timeout': 30
        }
    }
    
    # Database
    POSTGRES_DSN = "postgresql://user:password@timescaledb:5432/goat_odds"
    REDIS_URL = "redis://redis:6379/2"
    
    # Collection settings
    COLLECTION_INTERVAL = 10  # seconds between collection cycles
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5.0
    BATCH_SIZE = 1000
    
    # Odds processing
    MINIMUM_ODDS = 1.01
    MAXIMUM_ODDS = 1000.0
    ODDS_CHANGE_THRESHOLD = 0.1  # 10% change triggers update
    ARBITRAGE_THRESHOLD = 1.02  # 2% arbitrage opportunity
    VOLATILITY_THRESHOLD = 0.15  # 15% volatility threshold
    
    # Sports to monitor
    MONITORED_SPORTS = ['football', 'basketball', 'tennis', 'esports', 'baseball']
    
    # Markets to collect
    MARKETS = {
        'football': ['match_winner', 'over_under', 'btts', 'handicap', 'corners', 'cards'],
        'basketball': ['moneyline', 'spread', 'totals', 'player_points'],
        'tennis': ['match_winner', 'set_handicap', 'total_games'],
        'esports': ['match_winner', 'map_winner', 'total_kills'],
        'baseball': ['moneyline', 'run_line', 'totals']
    }
    
    # Alert thresholds
    ALERT_ODDS_DROP = 0.5  # 50% drop in odds
    ALERT_SUSPICIOUS_MOVEMENT = 0.3  # 30% suspicious movement
    ALERT_VOLUME_SPIKE = 5.0  # 5x volume increase

# Enums
class Bookmaker(str, Enum):
    """Supported bookmakers"""
    PINNACLE = "pinnacle"
    BETFAIR = "betfair"
    BET365 = "bet365"
    WILLIAMHILL = "williamhill"
    UNIBET = "unibet"
    BWIN = "bwin"

class SportType(str, Enum):
    """Supported sports"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    HOCKEY = "hockey"
    RUGBY = "rugby"

class MarketType(str, Enum):
    """Betting market types"""
    MATCH_WINNER = "match_winner"
    OVER_UNDER = "over_under"
    BTTS = "btts"  # Both Teams To Score
    HANDICAP = "handicap"
    CORNERS = "corners"
    CARDS = "cards"
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    TOTALS = "totals"
    PLAYER_POINTS = "player_points"
    SET_HANDICAP = "set_handicap"
    TOTAL_GAMES = "total_games"
    MAP_WINNER = "map_winner"
    TOTAL_KILLS = "total_kills"
    RUN_LINE = "run_line"

class OddsStatus(str, Enum):
    """Odds status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    SETTLED = "settled"

# Pydantic Models
class TeamInfo(BaseModel):
    """Team information"""
    team_id: str
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None
    
    @validator('team_id')
    def validate_team_id(cls, v):
        if not v or len(v) < 2:
            raise ValueError("Team ID must be at least 2 characters")
        return v

class MatchInfo(BaseModel):
    """Match information"""
    match_id: str
    sport: SportType
    league: str
    competition: str
    home_team: TeamInfo
    away_team: TeamInfo
    start_time: datetime
    venue: Optional[str] = None
    round: Optional[str] = None
    season: Optional[str] = None
    status: str = "scheduled"
    
    @validator('match_id')
    def validate_match_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_\-:]+$', v):
            raise ValueError("Invalid match ID format")
        return v

class MarketOdds(BaseModel):
    """Market-specific odds"""
    market: MarketType
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    handicap_value: Optional[float] = None
    over_line: Optional[float] = None
    under_line: Optional[float] = None
    
    @validator('home_odds', 'away_odds', 'draw_odds', 'over_odds', 'under_odds')
    def validate_odds(cls, v):
        if v is not None:
            if v < OddsConfig.MINIMUM_ODDS or v > OddsConfig.MAXIMUM_ODDS:
                raise ValueError(f"Odds must be between {OddsConfig.MINIMUM_ODDS} and {OddsConfig.MAXIMUM_ODDS}")
        return v

class BookmakerOdds(BaseModel):
    """Complete odds from a bookmaker"""
    odds_id: str = Field(default_factory=lambda: f"odds_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}")
    bookmaker: Bookmaker
    match: MatchInfo
    markets: List[MarketOdds]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: OddsStatus = OddsStatus.ACTIVE
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    volume: Optional[float] = None  # Betting volume if available
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity"""
    opportunity_id: str
    match_id: str
    sport: SportType
    market: MarketType
    outcomes: List[Dict[str, Any]]  # List of {bookmaker: str, outcome: str, odds: float}
    arbitrage_percentage: float
    guaranteed_profit: float
    recommended_stakes: Dict[str, float]
    timestamp: datetime
    expires_at: datetime
    confidence: float
    
    @validator('arbitrage_percentage')
    def validate_arbitrage(cls, v):
        if v < 1.0:
            raise ValueError("Arbitrage percentage must be >= 1.0")
        return v

class OddsAlert(BaseModel):
    """Odds alert"""
    alert_id: str
    alert_type: str
    match_id: str
    sport: SportType
    bookmaker: Bookmaker
    market: MarketType
    current_value: float
    previous_value: float
    change_percentage: float
    threshold: float
    timestamp: datetime
    severity: str  # info, warning, critical
    description: str
    metadata: Dict[str, Any]

@dataclass
class BookmakerState:
    """State for each bookmaker"""
    last_request: datetime
    request_count: int = 0
    error_count: int = 0
    last_success: Optional[datetime] = None
    is_active: bool = True
    consecutive_errors: int = 0

class OddsProducer:
    """Main producer for collecting and publishing odds"""
    
    def __init__(self, config: OddsConfig):
        self.config = config
        self.kafka_producer = None
        self.pg_pool = None
        self.redis_client = None
        self.http_session = None
        self.running = False
        self.bookmaker_states = {}
        
        # Rate limiting
        self.rate_limiters = {}
        self.request_times = defaultdict(list)
        
        # Odds cache for change detection
        self.odds_cache = {}  # match_id -> bookmaker -> market -> odds
        
        # Arbitrage detection
        self.arbitrage_cache = {}
        
        # Statistics
        self.stats = {
            'odds_collected': 0,
            'odds_published': 0,
            'alerts_generated': 0,
            'arbitrage_found': 0,
            'errors': 0
        }
        
        # Market movers
        self.market_movers = defaultdict(lambda: deque(maxlen=100))
        
        # Initialize bookmaker states
        for bookmaker in config.BOOKMAKERS:
            self.bookmaker_states[bookmaker] = BookmakerState(
                last_request=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
        
        logger.info("OddsProducer initialized")
    
    async def initialize(self):
        """Initialize all connections"""
        try:
            # Initialize Kafka producer
            self.kafka_producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                acks=self.config.KAFKA_ACKS,
                compression_type=self.config.KAFKA_COMPRESSION,
                max_batch_size=16384,
                linger_ms=100,
                retry_backoff_ms=100,
                security_protocol='SSL' if 'ssl' in self.config.KAFKA_BOOTSTRAP_SERVERS[0] else 'PLAINTEXT'
            )
            await self.kafka_producer.start()
            
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config.POSTGRES_DSN,
                min_size=5,
                max_size=20,
                command_timeout=60,
                max_inactive_connection_lifetime=300
            )
            
            # Initialize Redis
            self.redis_client = aioredis.from_url(
                self.config.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20
            )
            
            # Initialize HTTP session
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=20
            )
            self.http_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=60)
            )
            
            # Initialize database
            await self.initialize_odds_db()
            
            # Load historical odds for change detection
            await self.load_historical_odds()
            
            # Start monitoring tasks
            asyncio.create_task(self.monitor_bookmakers())
            asyncio.create_task(self.periodic_cleanup())
            
            logger.info("OddsProducer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OddsProducer: {e}")
            return False
    
    async def initialize_odds_db(self):
        """Create odds database schema"""
        schema = """
        -- Matches table
        CREATE TABLE IF NOT EXISTS matches (
            match_id VARCHAR(255) PRIMARY KEY,
            sport VARCHAR(50) NOT NULL,
            league VARCHAR(100) NOT NULL,
            competition VARCHAR(100),
            home_team_id VARCHAR(255) NOT NULL,
            home_team_name VARCHAR(255) NOT NULL,
            away_team_id VARCHAR(255) NOT NULL,
            away_team_name VARCHAR(255) NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            venue VARCHAR(255),
            match_round VARCHAR(50),
            season VARCHAR(50),
            status VARCHAR(50) DEFAULT 'scheduled',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_sport (sport),
            INDEX idx_start_time (start_time),
            INDEX idx_league (league)
        );
        
        -- Teams table
        CREATE TABLE IF NOT EXISTS teams (
            team_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            short_name VARCHAR(50),
            country VARCHAR(100),
            sport VARCHAR(50),
            logo_url VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_sport (sport),
            INDEX idx_country (country)
        );
        
        -- Odds table
        CREATE TABLE IF NOT EXISTS odds (
            odds_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) NOT NULL REFERENCES matches(match_id),
            bookmaker VARCHAR(50) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            home_odds DECIMAL(10, 3),
            away_odds DECIMAL(10, 3),
            draw_odds DECIMAL(10, 3),
            over_odds DECIMAL(10, 3),
            under_odds DECIMAL(10, 3),
            handicap_value DECIMAL(10, 2),
            over_line DECIMAL(10, 2),
            under_line DECIMAL(10, 2),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            volume DECIMAL(15, 2),
            url VARCHAR(500),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_match_bookmaker (match_id, bookmaker),
            INDEX idx_sport_market (sport, market),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Odds history for change tracking
        CREATE TABLE IF NOT EXISTS odds_history (
            id BIGSERIAL PRIMARY KEY,
            odds_id VARCHAR(255) REFERENCES odds(odds_id),
            match_id VARCHAR(255) NOT NULL,
            bookmaker VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            odds_type VARCHAR(20) NOT NULL,  -- home, away, draw, over, under
            odds_value DECIMAL(10, 3) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            change_percentage DECIMAL(10, 4),
            volume DECIMAL(15, 2),
            INDEX idx_match_bookmaker_time (match_id, bookmaker, timestamp),
            INDEX idx_odds_type (odds_type)
        );
        
        -- Arbitrage opportunities
        CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
            opportunity_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            outcomes JSONB NOT NULL,
            arbitrage_percentage DECIMAL(10, 4) NOT NULL,
            guaranteed_profit DECIMAL(10, 4) NOT NULL,
            recommended_stakes JSONB NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            confidence DECIMAL(5, 4),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_sport_market (sport, market),
            INDEX idx_timestamp (timestamp),
            INDEX idx_active (is_active)
        );
        
        -- Odds alerts
        CREATE TABLE IF NOT EXISTS odds_alerts (
            alert_id VARCHAR(255) PRIMARY KEY,
            alert_type VARCHAR(50) NOT NULL,
            match_id VARCHAR(255) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            bookmaker VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            current_value DECIMAL(10, 4) NOT NULL,
            previous_value DECIMAL(10, 4) NOT NULL,
            change_percentage DECIMAL(10, 4) NOT NULL,
            threshold DECIMAL(10, 4) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            severity VARCHAR(20) NOT NULL,
            description TEXT NOT NULL,
            metadata JSONB,
            acknowledged BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_alert_type (alert_type),
            INDEX idx_severity (severity),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Market movers
        CREATE TABLE IF NOT EXISTS market_movers (
            id BIGSERIAL PRIMARY KEY,
            match_id VARCHAR(255) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            bookmaker VARCHAR(50) NOT NULL,
            odds_type VARCHAR(20) NOT NULL,
            start_odds DECIMAL(10, 3) NOT NULL,
            end_odds DECIMAL(10, 3) NOT NULL,
            change_percentage DECIMAL(10, 4) NOT NULL,
            timeframe_minutes INTEGER NOT NULL,
            volume_change DECIMAL(10, 4),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            INDEX idx_match_market (match_id, market),
            INDEX idx_change_percentage (change_percentage),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Bookmaker performance
        CREATE TABLE IF NOT EXISTS bookmaker_performance (
            bookmaker VARCHAR(50) PRIMARY KEY,
            total_requests BIGINT DEFAULT 0,
            successful_requests BIGINT DEFAULT 0,
            failed_requests BIGINT DEFAULT 0,
            avg_response_time_ms DECIMAL(10, 2),
            last_success TIMESTAMP WITH TIME ZONE,
            last_failure TIMESTAMP WITH TIME ZONE,
            uptime_percentage DECIMAL(5, 2),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create hypertables for timeseries data
        SELECT create_hypertable('odds_history', 'timestamp', if_not_exists => TRUE);
        SELECT create_hypertable('market_movers', 'timestamp', if_not_exists => TRUE);
        """
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(schema)
                logger.info("Odds database schema created")
        except Exception as e:
            logger.error(f"Error creating odds schema: {e}")
            raise
    
    async def load_historical_odds(self):
        """Load historical odds for change detection"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Load recent odds for change detection
                query = """
                SELECT match_id, bookmaker, market, 
                       home_odds, away_odds, draw_odds,
                       timestamp
                FROM odds 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC
                LIMIT 10000
                """
                
                results = await conn.fetch(query)
                
                for row in results:
                    match_id = row['match_id']
                    bookmaker = row['bookmaker']
                    market = row['market']
                    
                    if match_id not in self.odds_cache:
                        self.odds_cache[match_id] = {}
                    
                    if bookmaker not in self.odds_cache[match_id]:
                        self.odds_cache[match_id][bookmaker] = {}
                    
                    self.odds_cache[match_id][bookmaker][market] = {
                        'home': row['home_odds'],
                        'away': row['away_odds'],
                        'draw': row['draw_odds'],
                        'timestamp': row['timestamp']
                    }
                
                logger.info(f"Loaded {len(results)} historical odds records")
                
        except Exception as e:
            logger.warning(f"Could not load historical odds: {e}")
    
    async def collect_odds(self):
        """Main odds collection loop"""
        logger.info("Starting odds collection")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Collect odds from each bookmaker
                tasks = []
                for bookmaker in self.config.BOOKMAKERS:
                    if self.bookmaker_states[bookmaker].is_active:
                        task = asyncio.create_task(
                            self.collect_bookmaker_odds(bookmaker)
                        )
                        tasks.append(task)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(results):
                        bookmaker = list(self.config.BOOKMAKERS.keys())[i]
                        if isinstance(result, Exception):
                            logger.error(f"Error collecting from {bookmaker}: {result}")
                            await self.update_bookmaker_state(bookmaker, success=False)
                        else:
                            await self.update_bookmaker_state(bookmaker, success=True)
                
                # Calculate collection time
                collection_time = time.time() - start_time
                
                # Sleep until next collection
                sleep_time = max(0, self.config.COLLECTION_INTERVAL - collection_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(self.config.RETRY_DELAY)
    
    async def collect_bookmaker_odds(self, bookmaker: str):
        """Collect odds from a specific bookmaker"""
        try:
            config = self.config.BOOKMAKERS[bookmaker]
            
            # Check rate limit
            await self.check_rate_limit(bookmaker)
            
            # Update request count
            self.bookmaker_states[bookmaker].request_count += 1
            self.bookmaker_states[bookmaker].last_request = datetime.now(timezone.utc)
            
            logger.debug(f"Collecting odds from {bookmaker}")
            
            # Different collection methods per bookmaker
            if bookmaker == 'pinnacle':
                odds_data = await self.collect_pinnacle_odds(config)
            elif bookmaker == 'betfair':
                odds_data = await self.collect_betfair_odds(config)
            elif bookmaker == 'bet365':
                odds_data = await self.collect_bet365_odds(config)
            elif bookmaker == 'williamhill':
                odds_data = await self.collect_williamhill_odds(config)
            else:
                odds_data = await self.collect_generic_odds(bookmaker, config)
            
            if odds_data:
                # Process and publish odds
                await self.process_bookmaker_odds(bookmaker, odds_data)
                
                # Update success state
                self.bookmaker_states[bookmaker].last_success = datetime.now(timezone.utc)
                self.bookmaker_states[bookmaker].consecutive_errors = 0
                
                return len(odds_data)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error collecting from {bookmaker}: {e}")
            raise
    
    async def collect_pinnacle_odds(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect odds from Pinnacle API"""
        try:
            headers = {
                'X-API-Key': config['api_key'],
                'Accept': 'application/json'
            }
            
            # Get sports
            sports_url = f"{config['base_url']}/sports"
            async with self.http_session.get(sports_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Pinnacle sports API returned {response.status}")
                
                sports_data = await response.json()
                
            # Filter for monitored sports
            pinnacle_sport_ids = {
                'football': 29,    # Soccer
                'basketball': 4,   # Basketball
                'tennis': 33,      # Tennis
                'baseball': 3      # Baseball
            }
            
            odds_list = []
            
            for sport_name, sport_id in pinnacle_sport_ids.items():
                if sport_name not in self.config.MONITORED_SPORTS:
                    continue
                
                # Get fixtures for this sport
                fixtures_url = f"{config['base_url']}/fixtures?sportId={sport_id}"
                async with self.http_session.get(fixtures_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Pinnacle fixtures API returned {response.status} for sport {sport_name}")
                        continue
                    
                    fixtures_data = await response.json()
                
                for league in fixtures_data.get('league', []):
                    for event in league.get('events', []):
                        try:
                            odds_data = self.parse_pinnacle_event(event, sport_name, league['id'])
                            if odds_data:
                                odds_list.append(odds_data)
                        except Exception as e:
                            logger.error(f"Error parsing Pinnacle event: {e}")
                            continue
            
            return odds_list
            
        except Exception as e:
            logger.error(f"Error collecting Pinnacle odds: {e}")
            return []
    
    def parse_pinnacle_event(self, event: Dict[str, Any], sport: str, league_id: int) -> Optional[Dict[str, Any]]:
        """Parse Pinnacle event data"""
        try:
            match_id = f"pinnacle_{event['id']}"
            start_time = datetime.fromisoformat(event['starts'].replace('Z', '+00:00'))
            
            # Parse teams
            home_team, away_team = event['home'], event['away']
            
            match_info = {
                'match_id': match_id,
                'sport': sport,
                'league': str(league_id),
                'competition': event.get('league', {}).get('name', 'Unknown'),
                'home_team': {
                    'team_id': f"pinnacle_team_{hashlib.md5(home_team.encode()).hexdigest()[:8]}",
                    'name': home_team
                },
                'away_team': {
                    'team_id': f"pinnacle_team_{hashlib.md5(away_team.encode()).hexdigest()[:8]}",
                    'name': away_team
                },
                'start_time': start_time,
                'status': 'scheduled'
            }
            
            # Parse odds
            markets = []
            
            # Match winner market
            if 'moneyline' in event.get('periods', [{}])[0]:
                moneyline = event['periods'][0]['moneyline']
                markets.append({
                    'market': 'match_winner',
                    'home_odds': moneyline.get('home'),
                    'away_odds': moneyline.get('away'),
                    'draw_odds': moneyline.get('draw')
                })
            
            # Spread market
            if 'spread' in event.get('periods', [{}])[0]:
                spread = event['periods'][0]['spread']
                markets.append({
                    'market': 'handicap',
                    'home_odds': spread.get('home'),
                    'away_odds': spread.get('away'),
                    'handicap_value': spread.get('hdp')
                })
            
            # Totals market
            if 'total' in event.get('periods', [{}])[0]:
                total = event['periods'][0]['total']
                markets.append({
                    'market': 'over_under',
                    'over_odds': total.get('over'),
                    'under_odds': total.get('under'),
                    'over_line': total.get('points'),
                    'under_line': total.get('points')
                })
            
            if not markets:
                return None
            
            return {
                'match': match_info,
                'markets': markets,
                'timestamp': datetime.now(timezone.utc),
                'url': f"https://www.pinnacle.com/en/{sport}/event/{event['id']}"
            }
            
        except Exception as e:
            logger.error(f"Error parsing Pinnacle event: {e}")
            return None
    
    async def collect_betfair_odds(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect odds from Betfair Exchange API"""
        try:
            # First, authenticate
            auth_url = "https://identitysso.betfair.com/api/certlogin"
            auth_data = {
                'username': config.get('username', ''),
                'password': config.get('password', '')
            }
            
            headers = {
                'X-Application': config['app_key'],
                'Accept': 'application/json'
            }
            
            async with self.http_session.post(auth_url, data=auth_data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Betfair auth returned {response.status}")
                
                auth_result = await response.json()
                session_token = auth_result.get('sessionToken')
            
            if not session_token:
                raise Exception("No session token from Betfair")
            
            # Get events for monitored sports
            event_types = {
                'football': 1,
                'basketball': 7522,
                'tennis': 2,
                'baseball': 7511
            }
            
            odds_list = []
            
            for sport_name, event_type_id in event_types.items():
                if sport_name not in self.config.MONITORED_SPORTS:
                    continue
                
                # Get market catalogue
                catalogue_url = f"{config['base_url']}/betting/rest/v1/listMarketCatalogue/"
                catalogue_headers = {
                    'X-Application': config['app_key'],
                    'X-Authentication': session_token,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                catalogue_body = {
                    "filter": {
                        "eventTypeIds": [event_type_id],
                        "marketCountries": ["GB", "US", "AU"],
                        "marketTypeCodes": ["MATCH_ODDS", "OVER_UNDER_25", "CORRECT_SCORE"],
                        "marketStartTime": {
                            "from": datetime.now(timezone.utc).isoformat(),
                            "to": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                        }
                    },
                    "maxResults": 100,
                    "marketProjection": ["EVENT", "MARKET_DESCRIPTION", "RUNNER_DESCRIPTION"]
                }
                
                async with self.http_session.post(
                    catalogue_url, 
                    json=catalogue_body, 
                    headers=catalogue_headers
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Betfair catalogue API returned {response.status}")
                        continue
                    
                    catalogue_data = await response.json()
                
                # Parse markets
                for market in catalogue_data:
                    try:
                        odds_data = self.parse_betfair_market(market, sport_name)
                        if odds_data:
                            odds_list.append(odds_data)
                    except Exception as e:
                        logger.error(f"Error parsing Betfair market: {e}")
                        continue
            
            return odds_list
            
        except Exception as e:
            logger.error(f"Error collecting Betfair odds: {e}")
            return []
    
    def parse_betfair_market(self, market: Dict[str, Any], sport: str) -> Optional[Dict[str, Any]]:
        """Parse Betfair market data"""
        try:
            event = market.get('event', {})
            match_id = f"betfair_{event.get('id')}"
            
            # Parse team names from event name
            event_name = event.get('name', '')
            teams = event_name.split(' v ')
            if len(teams) != 2:
                return None
            
            home_team, away_team = teams[0].strip(), teams[1].strip()
            
            match_info = {
                'match_id': match_id,
                'sport': sport,
                'league': event.get('competition', {}).get('name', 'Unknown'),
                'competition': event.get('competition', {}).get('name', 'Unknown'),
                'home_team': {
                    'team_id': f"betfair_team_{hashlib.md5(home_team.encode()).hexdigest()[:8]}",
                    'name': home_team
                },
                'away_team': {
                    'team_id': f"betfair_team_{hashlib.md5(away_team.encode()).hexdigest()[:8]}",
                    'name': away_team
                },
                'start_time': datetime.fromisoformat(event.get('openDate', '').replace('Z', '+00:00')),
                'venue': event.get('venue', ''),
                'status': 'scheduled'
            }
            
            # Parse runners (outcomes)
            markets = []
            market_type = market.get('marketName', '')
            
            if market_type == 'Match Odds':
                runners = market.get('runners', [])
                home_odds = None
                away_odds = None
                draw_odds = None
                
                for runner in runners:
                    runner_name = runner.get('runnerName', '')
                    # Get latest odds (simplified)
                    odds = 1.0  # Would get from exchange prices
                    
                    if runner_name == home_team:
                        home_odds = odds
                    elif runner_name == away_team:
                        away_odds = odds
                    elif 'draw' in runner_name.lower():
                        draw_odds = odds
                
                markets.append({
                    'market': 'match_winner',
                    'home_odds': home_odds,
                    'away_odds': away_odds,
                    'draw_odds': draw_odds
                })
            
            # Add more market types as needed
            
            if not markets:
                return None
            
            return {
                'match': match_info,
                'markets': markets,
                'timestamp': datetime.now(timezone.utc),
                'volume': market.get('totalMatched', 0),
                'url': f"https://www.betfair.com/exchange/{sport}/{match_id}"
            }
            
        except Exception as e:
            logger.error(f"Error parsing Betfair market: {e}")
            return None
    
    async def collect_bet365_odds(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect odds from Bet365 (using web scraping/API)"""
        # Note: Bet365 API access is restricted. This is a simplified example.
        try:
            odds_list = []
            
            # For each monitored sport
            for sport in self.config.MONITORED_SPORTS:
                if sport not in self.config.MARKETS:
                    continue
                
                # Simulate API call (in reality would use actual Bet365 API)
                # This is a placeholder for actual implementation
                
                # Example: Create mock odds for demonstration
                mock_match = {
                    'match_id': f"bet365_mock_{sport}_{int(time.time())}",
                    'sport': sport,
                    'league': 'Premier League' if sport == 'football' else 'NBA' if sport == 'basketball' else 'ATP',
                    'competition': 'League' if sport == 'football' else 'Championship',
                    'home_team': {
                        'team_id': f"team_home_{sport}",
                        'name': f'Home Team {sport.title()}',
                        'short_name': 'HOM'
                    },
                    'away_team': {
                        'team_id': f"team_away_{sport}",
                        'name': f'Away Team {sport.title()}',
                        'short_name': 'AWY'
                    },
                    'start_time': datetime.now(timezone.utc) + timedelta(hours=2),
                    'status': 'scheduled'
                }
                
                markets = []
                for market_type in self.config.MARKETS[sport][:3]:  # First 3 markets
                    if market_type == 'match_winner':
                        markets.append({
                            'market': market_type,
                            'home_odds': 1.8 + np.random.random() * 0.5,
                            'away_odds': 2.0 + np.random.random() * 0.5,
                            'draw_odds': 3.2 + np.random.random() * 0.3
                        })
                    elif market_type == 'over_under':
                        markets.append({
                            'market': market_type,
                            'over_odds': 1.9 + np.random.random() * 0.3,
                            'under_odds': 1.9 + np.random.random() * 0.3,
                            'over_line': 2.5,
                            'under_line': 2.5
                        })
                
                if markets:
                    odds_list.append({
                        'match': mock_match,
                        'markets': markets,
                        'timestamp': datetime.now(timezone.utc),
                        'url': f"https://www.bet365.com/{sport}/match/{mock_match['match_id']}"
                    })
            
            logger.info(f"Generated {len(odds_list)} mock odds from Bet365")
            return odds_list
            
        except Exception as e:
            logger.error(f"Error collecting Bet365 odds: {e}")
            return []
    
    async def collect_williamhill_odds(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect odds from William Hill API"""
        try:
            headers = {
                'Authorization': f"Bearer {config['api_key']}",
                'Accept': 'application/json'
            }
            
            odds_list = []
            
            for sport in self.config.MONITORED_SPORTS:
                if sport not in self.config.MARKETS:
                    continue
                
                # Get events for sport
                events_url = f"{config['base_url']}/events?sport={sport}"
                async with self.http_session.get(events_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"William Hill events API returned {response.status} for {sport}")
                        continue
                    
                    events_data = await response.json()
                
                for event in events_data.get('events', [])[:50]:  # Limit to 50 events
                    try:
                        odds_data = self.parse_williamhill_event(event, sport)
                        if odds_data:
                            odds_list.append(odds_data)
                    except Exception as e:
                        logger.error(f"Error parsing William Hill event: {e}")
                        continue
            
            return odds_list
            
        except Exception as e:
            logger.error(f"Error collecting William Hill odds: {e}")
            return []
    
    def parse_williamhill_event(self, event: Dict[str, Any], sport: str) -> Optional[Dict[str, Any]]:
        """Parse William Hill event data"""
        try:
            match_id = f"williamhill_{event.get('id')}"
            
            match_info = {
                'match_id': match_id,
                'sport': sport,
                'league': event.get('league', {}).get('name', 'Unknown'),
                'competition': event.get('competition', {}).get('name', 'Unknown'),
                'home_team': {
                    'team_id': f"wh_team_{event.get('homeTeam', {}).get('id', '')}",
                    'name': event.get('homeTeam', {}).get('name', 'Home')
                },
                'away_team': {
                    'team_id': f"wh_team_{event.get('awayTeam', {}).get('id', '')}",
                    'name': event.get('awayTeam', {}).get('name', 'Away')
                },
                'start_time': datetime.fromisoformat(event.get('startTime', '').replace('Z', '+00:00')),
                'status': event.get('status', 'scheduled')
            }
            
            # Parse markets
            markets = []
            for market in event.get('markets', []):
                market_type = market.get('type', '')
                
                if market_type == 'MATCH_ODDS':
                    outcomes = market.get('outcomes', [])
                    home_odds = None
                    away_odds = None
                    draw_odds = None
                    
                    for outcome in outcomes:
                        outcome_type = outcome.get('outcomeType', '')
                        odds = outcome.get('price', {}).get('decimal', 0)
                        
                        if outcome_type == 'HOME':
                            home_odds = odds
                        elif outcome_type == 'AWAY':
                            away_odds = odds
                        elif outcome_type == 'DRAW':
                            draw_odds = odds
                    
                    markets.append({
                        'market': 'match_winner',
                        'home_odds': home_odds,
                        'away_odds': away_odds,
                        'draw_odds': draw_odds
                    })
                elif market_type == 'TOTAL_GOALS':
                    # Over/under market
                    markets.append({
                        'market': 'over_under',
                        'over_odds': market.get('overOdds'),
                        'under_odds': market.get('underOdds'),
                        'over_line': market.get('line'),
                        'under_line': market.get('line')
                    })
            
            if not markets:
                return None
            
            return {
                'match': match_info,
                'markets': markets,
                'timestamp': datetime.now(timezone.utc),
                'url': event.get('url')
            }
            
        except Exception as e:
            logger.error(f"Error parsing William Hill event: {e}")
            return None
    
    async def collect_generic_odds(self, bookmaker: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic odds collection for other bookmakers"""
        # This would be implemented for each specific bookmaker
        # For now, return empty list
        return []
    
    async def process_bookmaker_odds(self, bookmaker: str, odds_data: List[Dict[str, Any]]):
        """Process and publish odds from a bookmaker"""
        try:
            processed_count = 0
            
            for data in odds_data:
                try:
                    # Create BookmakerOdds object
                    bookmaker_odds = BookmakerOdds(
                        bookmaker=Bookmaker(bookmaker),
                        match=MatchInfo(**data['match']),
                        markets=[MarketOdds(**market) for market in data['markets']],
                        timestamp=data['timestamp'],
                        volume=data.get('volume'),
                        url=data.get('url'),
                        metadata=data.get('metadata', {})
                    )
                    
                    # Check for significant changes
                    changes_detected = await self.detect_odds_changes(bookmaker_odds)
                    
                    # Store in database
                    await self.store_odds(bookmaker_odds)
                    
                    # Publish to Kafka
                    await self.publish_odds(bookmaker_odds)
                    
                    # Detect arbitrage opportunities
                    if changes_detected:
                        await self.detect_arbitrage(bookmaker_odds)
                    
                    # Check for alerts
                    await self.check_alerts(bookmaker_odds)
                    
                    processed_count += 1
                    self.stats['odds_collected'] += 1
                    
                except ValidationError as ve:
                    logger.error(f"Validation error for {bookmaker} odds: {ve}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing {bookmaker} odds: {e}")
                    continue
            
            logger.debug(f"Processed {processed_count} odds from {bookmaker}")
            
        except Exception as e:
            logger.error(f"Error in process_bookmaker_odds: {e}")
    
    async def detect_odds_changes(self, odds: BookmakerOdds) -> bool:
        """Detect significant odds changes"""
        try:
            match_id = odds.match.match_id
            bookmaker = odds.bookmaker.value
            
            if match_id not in self.odds_cache:
                self.odds_cache[match_id] = {}
            
            if bookmaker not in self.odds_cache[match_id]:
                self.odds_cache[match_id][bookmaker] = {}
            
            changes_detected = False
            
            for market_odds in odds.markets:
                market = market_odds.market.value
                
                if market not in self.odds_cache[match_id][bookmaker]:
                    self.odds_cache[match_id][bookmaker][market] = {}
                
                current_odds = {
                    'home': market_odds.home_odds,
                    'away': market_odds.away_odds,
                    'draw': market_odds.draw_odds,
                    'over': market_odds.over_odds,
                    'under': market_odds.under_odds,
                    'timestamp': odds.timestamp
                }
                
                previous_odds = self.odds_cache[match_id][bookmaker].get(market, {})
                
                # Check for significant changes
                for odds_type in ['home', 'away', 'draw', 'over', 'under']:
                    current = current_odds.get(odds_type)
                    previous = previous_odds.get(odds_type)
                    
                    if current is not None and previous is not None:
                        change_pct = abs(current - previous) / previous
                        
                        if change_pct > self.config.ODDS_CHANGE_THRESHOLD:
                            changes_detected = True
                            
                            # Record market mover
                            await self.record_market_mover(
                                match_id, odds.match.sport.value, market,
                                bookmaker, odds_type, previous, current,
                                change_pct, odds.timestamp
                            )
                
                # Update cache
                self.odds_cache[match_id][bookmaker][market] = current_odds
            
            return changes_detected
            
        except Exception as e:
            logger.error(f"Error detecting odds changes: {e}")
            return False
    
    async def record_market_mover(self, match_id: str, sport: str, market: str, 
                                 bookmaker: str, odds_type: str, 
                                 start_odds: float, end_odds: float,
                                 change_pct: float, timestamp: datetime):
        """Record significant market movement"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO market_movers 
                (match_id, sport, market, bookmaker, odds_type,
                 start_odds, end_odds, change_percentage, timeframe_minutes,
                 timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 5, $9)
                """
                
                await conn.execute(
                    query,
                    match_id,
                    sport,
                    market,
                    bookmaker,
                    odds_type,
                    start_odds,
                    end_odds,
                    change_pct,
                    timestamp
                )
            
            # Cache recent market movers
            mover_key = f"market_movers:{sport}:{market}"
            mover_data = {
                'match_id': match_id,
                'bookmaker': bookmaker,
                'odds_type': odds_type,
                'change_pct': change_pct,
                'timestamp': timestamp.isoformat()
            }
            
            await self.redis_client.lpush(mover_key, json.dumps(mover_data))
            await self.redis_client.ltrim(mover_key, 0, 49)  # Keep last 50
            
        except Exception as e:
            logger.error(f"Error recording market mover: {e}")
    
    async def store_odds(self, odds: BookmakerOdds):
        """Store odds in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Store match info
                match_query = """
                INSERT INTO matches 
                (match_id, sport, league, competition, home_team_id, home_team_name,
                 away_team_id, away_team_name, start_time, venue, match_round, season, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (match_id) 
                DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = NOW()
                """
                
                await conn.execute(
                    match_query,
                    odds.match.match_id,
                    odds.match.sport.value,
                    odds.match.league,
                    odds.match.competition,
                    odds.match.home_team.team_id,
                    odds.match.home_team.name,
                    odds.match.away_team.team_id,
                    odds.match.away_team.name,
                    odds.match.start_time,
                    odds.match.venue,
                    odds.match.round,
                    odds.match.season,
                    odds.match.status
                )
                
                # Store teams
                teams = [odds.match.home_team, odds.match.away_team]
                for team in teams:
                    team_query = """
                    INSERT INTO teams 
                    (team_id, name, short_name, country, sport)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (team_id) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        short_name = EXCLUDED.short_name,
                        updated_at = NOW()
                    """
                    
                    await conn.execute(
                        team_query,
                        team.team_id,
                        team.name,
                        team.short_name,
                        team.country,
                        odds.match.sport.value
                    )
                
                # Store odds for each market
                for market_odds in odds.markets:
                    odds_query = """
                    INSERT INTO odds 
                    (odds_id, match_id, bookmaker, sport, market,
                     home_odds, away_odds, draw_odds, over_odds, under_odds,
                     handicap_value, over_line, under_line, timestamp, status,
                     volume, url, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                    ON CONFLICT (odds_id) 
                    DO UPDATE SET
                        home_odds = EXCLUDED.home_odds,
                        away_odds = EXCLUDED.away_odds,
                        draw_odds = EXCLUDED.draw_odds,
                        over_odds = EXCLUDED.over_odds,
                        under_odds = EXCLUDED.under_odds,
                        timestamp = EXCLUDED.timestamp,
                        status = EXCLUDED.status,
                        volume = EXCLUDED.volume,
                        updated_at = NOW()
                    """
                    
                    await conn.execute(
                        odds_query,
                        odds.odds_id,
                        odds.match.match_id,
                        odds.bookmaker.value,
                        odds.match.sport.value,
                        market_odds.market.value,
                        market_odds.home_odds,
                        market_odds.away_odds,
                        market_odds.draw_odds,
                        market_odds.over_odds,
                        market_odds.under_odds,
                        market_odds.handicap_value,
                        market_odds.over_line,
                        market_odds.under_line,
                        odds.timestamp,
                        odds.status.value,
                        odds.volume,
                        odds.url,
                        json.dumps(odds.metadata)
                    )
                    
                    # Store in history for change tracking
                    await self.store_odds_history(odds, market_odds)
                
        except Exception as e:
            logger.error(f"Error storing odds: {e}")
            raise
    
    async def store_odds_history(self, odds: BookmakerOdds, market_odds: MarketOdds):
        """Store odds history for change tracking"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Store each odds type separately
                odds_types = [
                    ('home', market_odds.home_odds),
                    ('away', market_odds.away_odds),
                    ('draw', market_odds.draw_odds),
                    ('over', market_odds.over_odds),
                    ('under', market_odds.under_odds)
                ]
                
                for odds_type, value in odds_types:
                    if value is not None:
                        # Get previous value for change calculation
                        prev_query = """
                        SELECT odds_value 
                        FROM odds_history 
                        WHERE match_id = $1 AND bookmaker = $2 AND market = $3 AND odds_type = $4
                        ORDER BY timestamp DESC LIMIT 1
                        """
                        
                        prev_result = await conn.fetchval(
                            prev_query,
                            odds.match.match_id,
                            odds.bookmaker.value,
                            market_odds.market.value,
                            odds_type
                        )
                        
                        change_pct = None
                        if prev_result:
                            change_pct = (value - prev_result) / prev_result
                        
                        # Insert history record
                        history_query = """
                        INSERT INTO odds_history 
                        (odds_id, match_id, bookmaker, market, odds_type,
                         odds_value, timestamp, change_percentage, volume)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """
                        
                        await conn.execute(
                            history_query,
                            odds.odds_id,
                            odds.match.match_id,
                            odds.bookmaker.value,
                            market_odds.market.value,
                            odds_type,
                            value,
                            odds.timestamp,
                            change_pct,
                            odds.volume
                        )
                
        except Exception as e:
            logger.error(f"Error storing odds history: {e}")
    
    async def publish_odds(self, odds: BookmakerOdds):
        """Publish odds to Kafka"""
        try:
            # Convert to dict for JSON serialization
            odds_dict = odds.dict()
            
            # Publish to Kafka
            await self.kafka_producer.send_and_wait(
                self.config.KAFKA_TOPIC_ODDS,
                key=odds.odds_id.encode('utf-8'),
                value=json.dumps(odds_dict, default=str).encode('utf-8'),
                timestamp_ms=int(odds.timestamp.timestamp() * 1000)
            )
            
            self.stats['odds_published'] += 1
            
            # Cache for fast access
            await self.cache_odds(odds)
            
        except Exception as e:
            logger.error(f"Error publishing odds to Kafka: {e}")
            raise
    
    async def cache_odds(self, odds: BookmakerOdds):
        """Cache odds in Redis for fast access"""
        try:
            # Cache match odds
            match_key = f"odds:match:{odds.match.match_id}:{odds.bookmaker.value}"
            odds_data = {
                'odds_id': odds.odds_id,
                'timestamp': odds.timestamp.isoformat(),
                'markets': [
                    {
                        'market': market.market.value,
                        'home_odds': market.home_odds,
                        'away_odds': market.away_odds,
                        'draw_odds': market.draw_odds,
                        'over_odds': market.over_odds,
                        'under_odds': market.under_odds
                    }
                    for market in odds.markets
                ]
            }
            
            await self.redis_client.setex(
                match_key,
                300,  # 5 minutes TTL
                json.dumps(odds_data)
            )
            
            # Add to recent odds sorted set
            await self.redis_client.zadd(
                'recent_odds',
                {odds.odds_id: odds.timestamp.timestamp()}
            )
            
            # Keep only last 1000 odds
            await self.redis_client.zremrangebyrank('recent_odds', 0, -1001)
            
        except Exception as e:
            logger.error(f"Error caching odds: {e}")
    
    async def detect_arbitrage(self, new_odds: BookmakerOdds):
        """Detect arbitrage opportunities"""
        try:
            match_id = new_odds.match.match_id
            sport = new_odds.match.sport.value
            
            # Get all odds for this match from different bookmakers
            all_odds = await self.get_match_odds_from_cache(match_id)
            
            if not all_odds or len(all_odds) < 2:
                return
            
            # Check each market
            for market in self.config.MARKETS.get(sport, []):
                market_odds = {}
                
                # Collect odds for this market from all bookmakers
                for bookmaker, odds_list in all_odds.items():
                    for odds in odds_list:
                        if odds.get('market') == market:
                            market_odds[bookmaker] = odds
                            break
                
                if len(market_odds) < 2:
                    continue
                
                # Find arbitrage for match winner market
                if market == 'match_winner':
                    await self.find_match_winner_arbitrage(
                        match_id, sport, market, market_odds
                    )
                elif market == 'over_under':
                    await self.find_over_under_arbitrage(
                        match_id, sport, market, market_odds
                    )
                
        except Exception as e:
            logger.error(f"Error detecting arbitrage: {e}")
    
    async def find_match_winner_arbitrage(self, match_id: str, sport: str, market: str,
                                         market_odds: Dict[str, Dict[str, Any]]):
        """Find arbitrage opportunities for match winner market"""
        try:
            # Find best odds for each outcome
            best_odds = {
                'home': {'bookmaker': None, 'odds': 0},
                'away': {'bookmaker': None, 'odds': 0},
                'draw': {'bookmaker': None, 'odds': 0}
            }
            
            for bookmaker, odds in market_odds.items():
                if odds.get('home_odds') and odds['home_odds'] > best_odds['home']['odds']:
                    best_odds['home'] = {'bookmaker': bookmaker, 'odds': odds['home_odds']}
                
                if odds.get('away_odds') and odds['away_odds'] > best_odds['away']['odds']:
                    best_odds['away'] = {'bookmaker': bookmaker, 'odds': odds['away_odds']}
                
                if odds.get('draw_odds') and odds['draw_odds'] > best_odds['draw']['odds']:
                    best_odds['draw'] = {'bookmaker': bookmaker, 'odds': odds['draw_odds']}
            
            # Check if we have all three outcomes
            if not all(v['bookmaker'] for v in best_odds.values()):
                return
            
            # Calculate arbitrage percentage
            arbitrage_pct = sum(1.0 / v['odds'] for v in best_odds.values())
            
            if arbitrage_pct < self.config.ARBITRAGE_THRESHOLD:
                # Found arbitrage opportunity
                guaranteed_profit = (1.0 / arbitrage_pct) - 1.0
                
                # Calculate optimal stakes
                total_investment = 1000  # Example: $1000 total
                stakes = {}
                for outcome, data in best_odds.items():
                    stake = (1.0 / data['odds']) / arbitrage_pct * total_investment
                    stakes[data['bookmaker']] = {
                        'outcome': outcome,
                        'stake': stake,
                        'odds': data['odds']
                    }
                
                # Create arbitrage opportunity
                opportunity = ArbitrageOpportunity(
                    opportunity_id=f"arb_{hashlib.md5(f'{match_id}{market}{time.time()}'.encode()).hexdigest()[:16]}",
                    match_id=match_id,
                    sport=SportType(sport),
                    market=MarketType(market),
                    outcomes=[
                        {
                            'bookmaker': data['bookmaker'],
                            'outcome': outcome,
                            'odds': data['odds']
                        }
                        for outcome, data in best_odds.items()
                    ],
                    arbitrage_percentage=arbitrage_pct,
                    guaranteed_profit=guaranteed_profit * 100,  # Percentage
                    recommended_stakes=stakes,
                    timestamp=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                    confidence=1.0 - arbitrage_pct
                )
                
                # Store opportunity
                await self.store_arbitrage_opportunity(opportunity)
                
                # Publish alert
                await self.publish_arbitrage_alert(opportunity)
                
                self.stats['arbitrage_found'] += 1
                
        except Exception as e:
            logger.error(f"Error finding match winner arbitrage: {e}")
    
    async def store_arbitrage_opportunity(self, opportunity: ArbitrageOpportunity):
        """Store arbitrage opportunity in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO arbitrage_opportunities 
                (opportunity_id, match_id, sport, market, outcomes,
                 arbitrage_percentage, guaranteed_profit, recommended_stakes,
                 timestamp, expires_at, confidence)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """
                
                await conn.execute(
                    query,
                    opportunity.opportunity_id,
                    opportunity.match_id,
                    opportunity.sport.value,
                    opportunity.market.value,
                    json.dumps(opportunity.outcomes),
                    opportunity.arbitrage_percentage,
                    opportunity.guaranteed_profit,
                    json.dumps(opportunity.recommended_stakes),
                    opportunity.timestamp,
                    opportunity.expires_at,
                    opportunity.confidence
                )
            
            # Cache opportunity
            await self.redis_client.setex(
                f"arbitrage:{opportunity.opportunity_id}",
                300,  # 5 minutes
                json.dumps(opportunity.dict())
            )
            
        except Exception as e:
            logger.error(f"Error storing arbitrage opportunity: {e}")
    
    async def publish_arbitrage_alert(self, opportunity: ArbitrageOpportunity):
        """Publish arbitrage alert"""
        try:
            alert = OddsAlert(
                alert_id=f"alert_arb_{opportunity.opportunity_id}",
                alert_type='arbitrage_opportunity',
                match_id=opportunity.match_id,
                sport=opportunity.sport,
                bookmaker='multiple',
                market=opportunity.market,
                current_value=opportunity.arbitrage_percentage,
                previous_value=1.0,
                change_percentage=opportunity.arbitrage_percentage - 1.0,
                threshold=self.config.ARBITRAGE_THRESHOLD - 1.0,
                timestamp=datetime.now(timezone.utc),
                severity='info',
                description=f"Arbitrage opportunity found: {opportunity.guaranteed_profit:.2f}% guaranteed profit",
                metadata=opportunity.dict()
            )
            
            await self.publish_alert(alert)
            
        except Exception as e:
            logger.error(f"Error publishing arbitrage alert: {e}")
    
    async def check_alerts(self, odds: BookmakerOdds):
        """Check for alert conditions"""
        try:
            # Check for suspicious odds drops
            await self.check_odds_drop_alerts(odds)
            
            # Check for volatility
            await self.check_volatility_alerts(odds)
            
            # Check for volume spikes
            await self.check_volume_alerts(odds)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def check_odds_drop_alerts(self, odds: BookmakerOdds):
        """Check for significant odds drops"""
        try:
            match_id = odds.match.match_id
            bookmaker = odds.bookmaker.value
            
            for market_odds in odds.markets:
                market = market_odds.market.value
                
                # Get historical odds for this market
                async with self.pg_pool.acquire() as conn:
                    query = """
                    SELECT odds_value, timestamp
                    FROM odds_history
                    WHERE match_id = $1 AND bookmaker = $2 AND market = $3
                    ORDER BY timestamp DESC
                    LIMIT 10
                    """
                    
                    history = await conn.fetch(
                        query,
                        match_id,
                        bookmaker,
                        market
                    )
                
                if len(history) < 5:
                    continue
                
                # Check for significant drop
                current_home = market_odds.home_odds
                if current_home:
                    # Compare with average of last 5 records
                    recent_avg = np.mean([h['odds_value'] for h in history[:5] if h['odds_value']])
                    
                    if recent_avg and current_home:
                        drop_pct = (recent_avg - current_home) / recent_avg
                        
                        if drop_pct > self.config.ALERT_ODDS_DROP:
                            alert = OddsAlert(
                                alert_id=f"alert_drop_{odds.odds_id}",
                                alert_type='odds_drop',
                                match_id=match_id,
                                sport=odds.match.sport,
                                bookmaker=odds.bookmaker,
                                market=MarketType(market),
                                current_value=current_home,
                                previous_value=float(recent_avg),
                                change_percentage=drop_pct,
                                threshold=self.config.ALERT_ODDS_DROP,
                                timestamp=datetime.now(timezone.utc),
                                severity='warning',
                                description=f"Significant odds drop detected: {drop_pct:.1%}",
                                metadata={
                                    'market': market,
                                    'outcome': 'home',
                                    'match': odds.match.dict()
                                }
                            )
                            
                            await self.publish_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking odds drop alerts: {e}")
    
    async def check_volatility_alerts(self, odds: BookmakerOdds):
        """Check for high volatility"""
        try:
            match_id = odds.match.match_id
            bookmaker = odds.bookmaker.value
            
            for market_odds in odds.markets:
                market = market_odds.market.value
                
                # Get recent volatility
                volatility = await self.calculate_volatility(
                    match_id, bookmaker, market
                )
                
                if volatility > self.config.VOLATILITY_THRESHOLD:
                    alert = OddsAlert(
                        alert_id=f"alert_vol_{odds.odds_id}",
                        alert_type='high_volatility',
                        match_id=match_id,
                        sport=odds.match.sport,
                        bookmaker=odds.bookmaker,
                        market=MarketType(market),
                        current_value=volatility,
                        previous_value=volatility / 2,  # Arbitrary
                        change_percentage=volatility,
                        threshold=self.config.VOLATILITY_THRESHOLD,
                        timestamp=datetime.now(timezone.utc),
                        severity='warning',
                        description=f"High volatility detected: {volatility:.1%}",
                        metadata={
                            'market': market,
                            'match': odds.match.dict()
                        }
                    )
                    
                    await self.publish_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking volatility alerts: {e}")
    
    async def calculate_volatility(self, match_id: str, bookmaker: str, market: str) -> float:
        """Calculate volatility for a market"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                SELECT odds_value
                FROM odds_history
                WHERE match_id = $1 AND bookmaker = $2 AND market = $3
                  AND timestamp > NOW() - INTERVAL '1 hour'
                ORDER BY timestamp
                """
                
                results = await conn.fetch(query, match_id, bookmaker, market)
                
                if len(results) < 5:
                    return 0.0
                
                values = [float(r['odds_value']) for r in results]
                returns = np.diff(values) / values[:-1]
                
                if len(returns) == 0:
                    return 0.0
                
                volatility = np.std(returns)
                return float(volatility)
                
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return 0.0
    
    async def check_volume_alerts(self, odds: BookmakerOdds):
        """Check for volume spikes"""
        # Implementation depends on bookmaker volume data
        # This is a placeholder
        pass
    
    async def publish_alert(self, alert: OddsAlert):
        """Publish alert to Kafka"""
        try:
            await self.kafka_producer.send_and_wait(
                self.config.KAFKA_TOPIC_ALERTS,
                key=alert.alert_id.encode('utf-8'),
                value=json.dumps(alert.dict(), default=str).encode('utf-8')
            )
            
            self.stats['alerts_generated'] += 1
            
            # Also store in database
            await self.store_alert(alert)
            
            # Cache for dashboard
            await self.cache_alert(alert)
            
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
    
    async def store_alert(self, alert: OddsAlert):
        """Store alert in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO odds_alerts 
                (alert_id, alert_type, match_id, sport, bookmaker, market,
                 current_value, previous_value, change_percentage, threshold,
                 timestamp, severity, description, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """
                
                await conn.execute(
                    query,
                    alert.alert_id,
                    alert.alert_type,
                    alert.match_id,
                    alert.sport.value,
                    alert.bookmaker.value,
                    alert.market.value,
                    alert.current_value,
                    alert.previous_value,
                    alert.change_percentage,
                    alert.threshold,
                    alert.timestamp,
                    alert.severity,
                    alert.description,
                    json.dumps(alert.metadata)
                )
                
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    async def cache_alert(self, alert: OddsAlert):
        """Cache alert in Redis"""
        try:
            # Cache recent alerts
            alert_key = f"alerts:recent:{alert.severity}"
            alert_data = alert.dict()
            
            await self.redis_client.lpush(alert_key, json.dumps(alert_data))
            await self.redis_client.ltrim(alert_key, 0, 99)  # Keep last 100
            
            # Set TTL
            await self.redis_client.expire(alert_key, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error caching alert: {e}")
    
    async def get_match_odds_from_cache(self, match_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all odds for a match from cache"""
        try:
            # This would query Redis cache for all bookmaker odds for this match
            # For now, return empty dict
            return {}
        except Exception as e:
            logger.error(f"Error getting match odds from cache: {e}")
            return {}
    
    async def check_rate_limit(self, bookmaker: str):
        """Check and enforce rate limits"""
        try:
            rate_limit = self.config.BOOKMAKERS[bookmaker]['rate_limit']
            now = time.time()
            
            if bookmaker not in self.request_times:
                self.request_times[bookmaker] = []
            
            # Remove old request times
            self.request_times[bookmaker] = [
                t for t in self.request_times[bookmaker]
                if now - t < 60  # Keep last minute
            ]
            
            # Check if we need to wait
            if len(self.request_times[bookmaker]) > 0:
                last_request = self.request_times[bookmaker][-1]
                time_since_last = now - last_request
                
                if time_since_last < rate_limit:
                    wait_time = rate_limit - time_since_last
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times[bookmaker].append(time.time())
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
    
    async def update_bookmaker_state(self, bookmaker: str, success: bool):
        """Update bookmaker performance state"""
        try:
            state = self.bookmaker_states[bookmaker]
            
            if success:
                state.consecutive_errors = 0
                state.last_success = datetime.now(timezone.utc)
                state.is_active = True
            else:
                state.error_count += 1
                state.consecutive_errors += 1
                
                # Deactivate if too many consecutive errors
                if state.consecutive_errors > 10:
                    state.is_active = False
                    logger.warning(f"Deactivated {bookmaker} due to {state.consecutive_errors} consecutive errors")
            
            # Update performance in database
            await self.update_bookmaker_performance(bookmaker, success)
            
        except Exception as e:
            logger.error(f"Error updating bookmaker state: {e}")
    
    async def update_bookmaker_performance(self, bookmaker: str, success: bool):
        """Update bookmaker performance in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                if success:
                    query = """
                    INSERT INTO bookmaker_performance 
                    (bookmaker, total_requests, successful_requests, last_success, updated_at)
                    VALUES ($1, 1, 1, NOW(), NOW())
                    ON CONFLICT (bookmaker) 
                    DO UPDATE SET
                        total_requests = bookmaker_performance.total_requests + 1,
                        successful_requests = bookmaker_performance.successful_requests + 1,
                        last_success = NOW(),
                        uptime_percentage = bookmaker_performance.successful_requests::float / 
                                           bookmaker_performance.total_requests * 100,
                        updated_at = NOW()
                    """
                else:
                    query = """
                    INSERT INTO bookmaker_performance 
                    (bookmaker, total_requests, failed_requests, last_failure, updated_at)
                    VALUES ($1, 1, 1, NOW(), NOW())
                    ON CONFLICT (bookmaker) 
                    DO UPDATE SET
                        total_requests = bookmaker_performance.total_requests + 1,
                        failed_requests = bookmaker_performance.failed_requests + 1,
                        last_failure = NOW(),
                        uptime_percentage = bookmaker_performance.successful_requests::float / 
                                           bookmaker_performance.total_requests * 100,
                        updated_at = NOW()
                    """
                
                await conn.execute(query, bookmaker)
                
        except Exception as e:
            logger.error(f"Error updating bookmaker performance: {e}")
    
    async def monitor_bookmakers(self):
        """Monitor bookmaker health and reactivate if needed"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for bookmaker, state in self.bookmaker_states.items():
                    if not state.is_active and state.consecutive_errors > 10:
                        # Try to reactivate after 10 minutes
                        if state.last_success:
                            time_since_last = datetime.now(timezone.utc) - state.last_success
                            if time_since_last.total_seconds() > 600:  # 10 minutes
                                state.is_active = True
                                state.consecutive_errors = 0
                                logger.info(f"Reactivated {bookmaker}")
                
            except Exception as e:
                logger.error(f"Error in bookmaker monitoring: {e}")
    
    async def periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                # Clean old cache entries
                await self.cleanup_old_cache()
                
                # Log statistics
                logger.info(
                    f"Statistics - Collected: {self.stats['odds_collected']}, "
                    f"Published: {self.stats['odds_published']}, "
                    f"Alerts: {self.stats['alerts_generated']}, "
                    f"Arbitrage: {self.stats['arbitrage_found']}, "
                    f"Errors: {self.stats['errors']}"
                )
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def cleanup_old_cache(self):
        """Cleanup old cache entries"""
        try:
            # Clean odds cache older than 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for match_id in list(self.odds_cache.keys()):
                for bookmaker in list(self.odds_cache[match_id].keys()):
                    for market in list(self.odds_cache[match_id][bookmaker].keys()):
                        odds_data = self.odds_cache[match_id][bookmaker][market]
                        if odds_data.get('timestamp', cutoff) < cutoff:
                            del self.odds_cache[match_id][bookmaker][market]
                    
                    if not self.odds_cache[match_id][bookmaker]:
                        del self.odds_cache[match_id][bookmaker]
                
                if not self.odds_cache[match_id]:
                    del self.odds_cache[match_id]
            
            logger.debug("Cleaned old cache entries")
            
        except Exception as e:
            logger.error(f"Error cleaning old cache: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Return health check status"""
        health = {
            'status': 'healthy',
            'running': self.running,
            'statistics': self.stats,
            'bookmakers': {
                bookmaker: {
                    'is_active': state.is_active,
                    'request_count': state.request_count,
                    'error_count': state.error_count,
                    'consecutive_errors': state.consecutive_errors,
                    'last_success': state.last_success.isoformat() if state.last_success else None
                }
                for bookmaker, state in self.bookmaker_states.items()
            },
            'connections': {
                'kafka': 'connected' if self.kafka_producer else 'disconnected',
                'postgresql': 'connected' if self.pg_pool else 'disconnected',
                'redis': 'connected' if self.redis_client else 'disconnected',
                'http': 'connected' if self.http_session else 'disconnected'
            }
        }
        
        # Check Kafka
        try:
            await self.kafka_producer._sender.client.check_version()
        except:
            health['connections']['kafka'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        # Check PostgreSQL
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except:
            health['connections']['postgresql'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        # Check Redis
        try:
            await self.redis_client.ping()
        except:
            health['connections']['redis'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        return health
    
    async def stop(self):
        """Stop the producer gracefully"""
        logger.info("Stopping OddsProducer...")
        self.running = False
        
        # Wait for current operations to complete
        await asyncio.sleep(2)
        
        if self.kafka_producer:
            await self.kafka_producer.stop()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.http_session:
            await self.http_session.close()
        
        logger.info("OddsProducer stopped")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

async def main():
    """Main entry point"""
    logger.info("Starting GOAT Odds Producer...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = OddsConfig()
    producer = OddsProducer(config)
    
    try:
        # Initialize
        if not await producer.initialize():
            logger.error("Failed to initialize odds producer")
            return
        
        # Start collection
        collection_task = asyncio.create_task(producer.collect_odds())
        
        # Wait for collection task
        await collection_task
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await producer.stop()
        logger.info("Odds producer shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
