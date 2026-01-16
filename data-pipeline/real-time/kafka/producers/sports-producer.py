"""
Sports Data Producer for GOAT Prediction Ultimate
Collects real-time sports data from multiple sources and publishes to Kafka.
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
from pydantic import BaseModel, ValidationError, Field, validator, root_validator
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
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP
import csv
import io
import gzip
import brotli

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/sports-producer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class SportsConfig:
    """Configuration for Sports Producer"""
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092', 'kafka2:9092', 'kafka3:9092']
    KAFKA_TOPIC_MATCHES = 'goat-sports-matches'
    KAFKA_TOPIC_EVENTS = 'goat-sports-events'
    KAFKA_TOPIC_STATS = 'goat-sports-stats'
    KAFKA_TOPIC_INJURIES = 'goat-sports-injuries'
    KAFKA_TOPIC_NEWS = 'goat-sports-news'
    KAFKA_ACKS = 'all'
    KAFKA_COMPRESSION = 'gzip'
    
    # Data Sources
    DATA_SOURCES = {
        'statsbomb': {
            'api_key': 'STATSBOMB_API_KEY',
            'base_url': 'https://data.statsbomb.com/api/v4',
            'rate_limit': 0.5,
            'timeout': 30
        },
        'opta': {
            'api_key': 'OPTA_API_KEY',
            'base_url': 'https://api.opta.net/v1',
            'rate_limit': 1.0,
            'timeout': 30
        },
        'sportradar': {
            'api_key': 'SPORTRADAR_API_KEY',
            'base_url': 'https://api.sportradar.com',
            'rate_limit': 0.2,
            'timeout': 60
        },
        'inStat': {
            'api_key': 'INSTAT_API_KEY',
            'base_url': 'https://api.instat.com/v1',
            'rate_limit': 0.3,
            'timeout': 30
        },
        'wyscout': {
            'api_key': 'WYSCOUT_API_KEY',
            'base_url': 'https://apirest.wyscout.com/v2',
            'rate_limit': 0.5,
            'timeout': 30
        },
        'flashscore': {
            'base_url': 'https://www.flashscore.com',
            'rate_limit': 2.0,
            'timeout': 60
        },
        'sofascore': {
            'api_key': 'SOFASCORE_API_KEY',
            'base_url': 'https://api.sofascore.com/api/v1',
            'rate_limit': 1.0,
            'timeout': 30
        }
    }
    
    # Database
    POSTGRES_DSN = "postgresql://user:password@timescaledb:5432/goat_sports"
    REDIS_URL = "redis://redis:6379/3"
    
    # Collection settings
    COLLECTION_INTERVAL = 15  # seconds between collection cycles
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5.0
    BATCH_SIZE = 500
    
    # Sports to monitor
    MONITORED_SPORTS = [
        'football', 'basketball', 'tennis', 'esports',
        'baseball', 'hockey', 'rugby', 'american_football'
    ]
    
    # Leagues to prioritize
    PRIORITY_LEAGUES = {
        'football': [
            'premier_league', 'la_liga', 'bundesliga', 'serie_a', 'ligue_1',
            'champions_league', 'europa_league', 'world_cup', 'euro'
        ],
        'basketball': ['nba', 'euroleague', 'ncaa'],
        'tennis': ['atp', 'wta', 'grand_slam'],
        'esports': ['lol_worlds', 'csgo_majors', 'dota_ti']
    }
    
    # Data collection depth
    COLLECTION_DEPTH = {
        'live': ['scores', 'events', 'stats'],
        'pre_match': ['lineups', 'injuries', 'news', 'weather'],
        'post_match': ['detailed_stats', 'player_ratings', 'highlights']
    }
    
    # Alert thresholds
    ALERT_INJURY = True
    ALERT_LINEUP_CHANGE = True
    ALERT_WEATHER_IMPACT = True
    ALERT_FORM_DROP = 0.3  # 30% drop in form
    
    # Cache settings
    CACHE_TTL = 3600  # 1 hour
    MATCH_CACHE_SIZE = 10000

# Enums
class SportType(str, Enum):
    """Supported sports"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    HOCKEY = "hockey"
    RUGBY = "rugby"
    AMERICAN_FOOTBALL = "american_football"

class MatchStatus(str, Enum):
    """Match status"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"

class EventType(str, Enum):
    """Sports event types"""
    GOAL = "goal"
    CARD = "card"
    SUBSTITUTION = "substitution"
    PENALTY = "penalty"
    CORNER = "corner"
    FOUL = "foul"
    OFFSIDE = "offside"
    SHOT_ON_TARGET = "shot_on_target"
    SHOT_OFF_TARGET = "shot_off_target"
    SAVE = "save"
    FREE_KICK = "free_kick"
    THROW_IN = "throw_in"
    INJURY = "injury"
    VAR_REVIEW = "var_review"

class PlayerPosition(str, Enum):
    """Player positions"""
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"
    POINT_GUARD = "point_guard"
    SHOOTING_GUARD = "shooting_guard"
    SMALL_FORWARD = "small_forward"
    POWER_FORWARD = "power_forward"
    CENTER = "center"
    PITCHER = "pitcher"
    CATCHER = "catcher"
    INFIELDER = "infielder"
    OUTFIELDER = "outfielder"

# Pydantic Models
class Team(BaseModel):
    """Team information"""
    team_id: str
    name: str
    short_name: Optional[str] = None
    country: str
    city: Optional[str] = None
    stadium: Optional[str] = None
    manager: Optional[str] = None
    founded_year: Optional[int] = None
    colors: Optional[List[str]] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    
    @validator('team_id')
    def validate_team_id(cls, v):
        if not v or len(v) < 2:
            raise ValueError("Team ID must be at least 2 characters")
        return v

class Player(BaseModel):
    """Player information"""
    player_id: str
    name: str
    full_name: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    nationality: Optional[str] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    position: Optional[PlayerPosition] = None
    jersey_number: Optional[int] = None
    preferred_foot: Optional[str] = None
    market_value_eur: Optional[float] = None
    contract_until: Optional[datetime] = None
    photo_url: Optional[str] = None
    
    @validator('player_id')
    def validate_player_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError("Invalid player ID format")
        return v

class Competition(BaseModel):
    """Competition/league information"""
    competition_id: str
    name: str
    country: str
    level: Optional[int] = None  # 1 for top division
    type: str = "league"  # league, cup, tournament
    season: str
    start_date: datetime
    end_date: datetime
    logo_url: Optional[str] = None
    website: Optional[str] = None

class Match(BaseModel):
    """Match information"""
    match_id: str
    competition: Competition
    home_team: Team
    away_team: Team
    match_date: datetime
    venue: Optional[str] = None
    referee: Optional[str] = None
    attendance: Optional[int] = None
    status: MatchStatus
    home_score: Optional[int] = 0
    away_score: Optional[int] = 0
    halftime_score: Optional[Tuple[int, int]] = None
    match_week: Optional[int] = None
    round: Optional[str] = None
    group: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('match_id')
    def validate_match_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_\-:]+$', v):
            raise ValueError("Invalid match ID format")
        return v
    
    @root_validator
    def validate_scores(cls, values):
        if values.get('status') == MatchStatus.FINISHED:
            if values.get('home_score') is None or values.get('away_score') is None:
                raise ValueError("Finished matches must have scores")
        return values

class MatchEvent(BaseModel):
    """Match event (goal, card, substitution, etc.)"""
    event_id: str
    match_id: str
    event_type: EventType
    minute: int
    extra_time: Optional[int] = None
    team: str
    player: Optional[str] = None
    related_player: Optional[str] = None
    description: Optional[str] = None
    x_coordinate: Optional[float] = None  # 0-100
    y_coordinate: Optional[float] = None  # 0-100
    outcome: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MatchStatistics(BaseModel):
    """Match statistics"""
    stats_id: str
    match_id: str
    team_id: str
    statistic_type: str
    value: float
    timestamp: datetime
    period: str = "full"  # first_half, second_half, extra_time, full
    
    @validator('value')
    def validate_value(cls, v):
        return float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class PlayerStatistics(BaseModel):
    """Player statistics for a match"""
    player_stats_id: str
    match_id: str
    player_id: str
    team_id: str
    minutes_played: Optional[int] = None
    goals: Optional[int] = 0
    assists: Optional[int] = 0
    shots: Optional[int] = 0
    shots_on_target: Optional[int] = 0
    passes: Optional[int] = 0
    pass_accuracy: Optional[float] = None
    tackles: Optional[int] = 0
    interceptions: Optional[int] = 0
    fouls: Optional[int] = 0
    yellow_cards: Optional[int] = 0
    red_cards: Optional[int] = 0
    saves: Optional[int] = 0  # for goalkeepers
    rating: Optional[float] = None
    timestamp: datetime

class InjuryReport(BaseModel):
    """Player injury report"""
    injury_id: str
    player_id: str
    team_id: str
    injury_type: str
    severity: str  # minor, moderate, major
    expected_return: Optional[datetime] = None
    date_injured: datetime
    date_reported: datetime
    description: Optional[str] = None
    status: str = "injured"  # injured, recovering, fit
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Lineup(BaseModel):
    """Team lineup for a match"""
    lineup_id: str
    match_id: str
    team_id: str
    formation: Optional[str] = None
    players: List[Dict[str, Any]]  # List of players with positions
    substitutes: List[Dict[str, Any]]
    coach: Optional[str] = None
    timestamp: datetime
    is_confirmed: bool = False

class WeatherCondition(BaseModel):
    """Weather conditions for a match"""
    weather_id: str
    match_id: str
    temperature_c: Optional[float] = None
    condition: Optional[str] = None  # sunny, rainy, cloudy, etc.
    humidity_percent: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    precipitation_mm: Optional[float] = None
    timestamp: datetime

class SportsNews(BaseModel):
    """Sports news article"""
    news_id: str
    title: str
    content: str
    source: str
    url: str
    published_date: datetime
    categories: List[str]
    teams: List[str] = []
    players: List[str] = []
    sentiment_score: Optional[float] = None  # -1 to 1
    importance_score: Optional[float] = None  # 0 to 1
    metadata: Dict[str, Any] = Field(default_factory=dict)

@dataclass
class DataSourceState:
    """State for each data source"""
    last_request: datetime
    request_count: int = 0
    error_count: int = 0
    last_success: Optional[datetime] = None
    is_active: bool = True
    consecutive_errors: int = 0
    data_quality: float = 1.0  # 0 to 1

class SportsProducer:
    """Main producer for collecting and publishing sports data"""
    
    def __init__(self, config: SportsConfig):
        self.config = config
        self.kafka_producer = None
        self.pg_pool = None
        self.redis_client = None
        self.http_session = None
        self.running = False
        self.source_states = {}
        
        # Rate limiting
        self.rate_limiters = {}
        self.request_times = defaultdict(list)
        
        # Data cache
        self.match_cache = {}  # match_id -> match data
        self.team_cache = {}   # team_id -> team data
        self.player_cache = {}  # player_id -> player data
        
        # Live matches tracking
        self.live_matches = set()
        self.match_updates = defaultdict(lambda: deque(maxlen=100))
        
        # Statistics
        self.stats = {
            'matches_collected': 0,
            'events_collected': 0,
            'stats_collected': 0,
            'injuries_collected': 0,
            'news_collected': 0,
            'alerts_generated': 0,
            'errors': 0
        }
        
        # Initialize source states
        for source in config.DATA_SOURCES:
            self.source_states[source] = DataSourceState(
                last_request=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
        
        logger.info("SportsProducer initialized")
    
    async def initialize(self):
        """Initialize all connections"""
        try:
            # Initialize Kafka producer
            self.kafka_producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                acks=self.config.KAFKA_ACKS,
                compression_type=self.config.KAFKA_COMPRESSION,
                max_batch_size=32768,
                linger_ms=50,
                retry_backoff_ms=100,
                security_protocol='SSL' if 'ssl' in self.config.KAFKA_BOOTSTRAP_SERVERS[0] else 'PLAINTEXT'
            )
            await self.kafka_producer.start()
            
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config.POSTGRES_DSN,
                min_size=10,
                max_size=30,
                command_timeout=120,
                max_inactive_connection_lifetime=300
            )
            
            # Initialize Redis
            self.redis_client = aioredis.from_url(
                self.config.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=30
            )
            
            # Initialize HTTP session
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=200,
                limit_per_host=50
            )
            self.http_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=90),
                headers={
                    'User-Agent': 'GOAT-Prediction/1.0 (+https://goat-prediction.com)'
                }
            )
            
            # Initialize database
            await self.initialize_sports_db()
            
            # Load cache from database
            await self.load_cache_from_db()
            
            # Start monitoring tasks
            asyncio.create_task(self.monitor_sources())
            asyncio.create_task(self.periodic_cleanup())
            asyncio.create_task(self.update_live_matches())
            
            logger.info("SportsProducer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize SportsProducer: {e}")
            return False
    
    async def initialize_sports_db(self):
        """Create sports database schema"""
        schema = """
        -- Competitions table
        CREATE TABLE IF NOT EXISTS competitions (
            competition_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            country VARCHAR(100) NOT NULL,
            level INTEGER,
            type VARCHAR(50) DEFAULT 'league',
            season VARCHAR(50) NOT NULL,
            start_date TIMESTAMP WITH TIME ZONE NOT NULL,
            end_date TIMESTAMP WITH TIME ZONE NOT NULL,
            logo_url VARCHAR(500),
            website VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_country (country),
            INDEX idx_season (season),
            INDEX idx_type (type)
        );
        
        -- Teams table
        CREATE TABLE IF NOT EXISTS teams (
            team_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            short_name VARCHAR(50),
            country VARCHAR(100) NOT NULL,
            city VARCHAR(100),
            stadium VARCHAR(255),
            manager VARCHAR(255),
            founded_year INTEGER,
            colors JSONB,
            logo_url VARCHAR(500),
            website VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_country (country),
            INDEX idx_city (city)
        );
        
        -- Players table
        CREATE TABLE IF NOT EXISTS players (
            player_id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            date_of_birth TIMESTAMP WITH TIME ZONE,
            nationality VARCHAR(100),
            height_cm INTEGER,
            weight_kg INTEGER,
            position VARCHAR(50),
            jersey_number INTEGER,
            preferred_foot VARCHAR(10),
            market_value_eur DECIMAL(15, 2),
            contract_until TIMESTAMP WITH TIME ZONE,
            photo_url VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_nationality (nationality),
            INDEX idx_position (position),
            INDEX idx_team (team_id)
        );
        
        -- Matches table
        CREATE TABLE IF NOT EXISTS matches (
            match_id VARCHAR(255) PRIMARY KEY,
            competition_id VARCHAR(255) REFERENCES competitions(competition_id),
            home_team_id VARCHAR(255) REFERENCES teams(team_id),
            away_team_id VARCHAR(255) REFERENCES teams(team_id),
            match_date TIMESTAMP WITH TIME ZONE NOT NULL,
            venue VARCHAR(255),
            referee VARCHAR(255),
            attendance INTEGER,
            status VARCHAR(50) NOT NULL,
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            halftime_score VARCHAR(20),
            match_week INTEGER,
            match_round VARCHAR(50),
            match_group VARCHAR(50),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_competition (competition_id),
            INDEX idx_match_date (match_date),
            INDEX idx_status (status),
            INDEX idx_home_team (home_team_id),
            INDEX idx_away_team (away_team_id)
        );
        
        -- Match events table
        CREATE TABLE IF NOT EXISTS match_events (
            event_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) REFERENCES matches(match_id),
            event_type VARCHAR(50) NOT NULL,
            minute INTEGER NOT NULL,
            extra_time INTEGER,
            team_id VARCHAR(255) REFERENCES teams(team_id),
            player_id VARCHAR(255) REFERENCES players(player_id),
            related_player_id VARCHAR(255) REFERENCES players(player_id),
            description TEXT,
            x_coordinate DECIMAL(5, 2),
            y_coordinate DECIMAL(5, 2),
            outcome VARCHAR(50),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            metadata JSONB,
            INDEX idx_match_event (match_id, event_type),
            INDEX idx_timestamp (timestamp),
            INDEX idx_player (player_id)
        );
        
        -- Match statistics table
        CREATE TABLE IF NOT EXISTS match_statistics (
            stats_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) REFERENCES matches(match_id),
            team_id VARCHAR(255) REFERENCES teams(team_id),
            statistic_type VARCHAR(100) NOT NULL,
            value DECIMAL(10, 2) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            period VARCHAR(50) DEFAULT 'full',
            INDEX idx_match_stats (match_id, team_id),
            INDEX idx_stat_type (statistic_type),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Player statistics table
        CREATE TABLE IF NOT EXISTS player_statistics (
            player_stats_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) REFERENCES matches(match_id),
            player_id VARCHAR(255) REFERENCES players(player_id),
            team_id VARCHAR(255) REFERENCES teams(team_id),
            minutes_played INTEGER,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            shots INTEGER DEFAULT 0,
            shots_on_target INTEGER DEFAULT 0,
            passes INTEGER DEFAULT 0,
            pass_accuracy DECIMAL(5, 2),
            tackles INTEGER DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            fouls INTEGER DEFAULT 0,
            yellow_cards INTEGER DEFAULT 0,
            red_cards INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            rating DECIMAL(5, 2),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            INDEX idx_match_player (match_id, player_id),
            INDEX idx_player_stats (player_id, match_date),
            INDEX idx_team_match (team_id, match_id)
        );
        
        -- Injury reports table
        CREATE TABLE IF NOT EXISTS injury_reports (
            injury_id VARCHAR(255) PRIMARY KEY,
            player_id VARCHAR(255) REFERENCES players(player_id),
            team_id VARCHAR(255) REFERENCES teams(team_id),
            injury_type VARCHAR(100) NOT NULL,
            severity VARCHAR(50) NOT NULL,
            expected_return TIMESTAMP WITH TIME ZONE,
            date_injured TIMESTAMP WITH TIME ZONE NOT NULL,
            date_reported TIMESTAMP WITH TIME ZONE NOT NULL,
            description TEXT,
            status VARCHAR(50) DEFAULT 'injured',
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_player_injury (player_id, status),
            INDEX idx_team_injury (team_id, status),
            INDEX idx_severity (severity)
        );
        
        -- Lineups table
        CREATE TABLE IF NOT EXISTS lineups (
            lineup_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) REFERENCES matches(match_id),
            team_id VARCHAR(255) REFERENCES teams(team_id),
            formation VARCHAR(50),
            players JSONB NOT NULL,
            substitutes JSONB NOT NULL,
            coach VARCHAR(255),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            is_confirmed BOOLEAN DEFAULT FALSE,
            INDEX idx_match_lineup (match_id, team_id),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Weather conditions table
        CREATE TABLE IF NOT EXISTS weather_conditions (
            weather_id VARCHAR(255) PRIMARY KEY,
            match_id VARCHAR(255) REFERENCES matches(match_id),
            temperature_c DECIMAL(5, 2),
            condition VARCHAR(50),
            humidity_percent DECIMAL(5, 2),
            wind_speed_kmh DECIMAL(5, 2),
            precipitation_mm DECIMAL(5, 2),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            INDEX idx_match_weather (match_id),
            INDEX idx_timestamp (timestamp)
        );
        
        -- Sports news table
        CREATE TABLE IF NOT EXISTS sports_news (
            news_id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            source VARCHAR(100) NOT NULL,
            url VARCHAR(500) NOT NULL,
            published_date TIMESTAMP WITH TIME ZONE NOT NULL,
            categories JSONB NOT NULL,
            teams JSONB,
            players JSONB,
            sentiment_score DECIMAL(3, 2),
            importance_score DECIMAL(3, 2),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            INDEX idx_published_date (published_date),
            INDEX idx_source (source),
            INDEX idx_sentiment (sentiment_score),
            INDEX idx_importance (importance_score)
        );
        
        -- Data source performance
        CREATE TABLE IF NOT EXISTS data_source_performance (
            source_name VARCHAR(100) PRIMARY KEY,
            total_requests BIGINT DEFAULT 0,
            successful_requests BIGINT DEFAULT 0,
            failed_requests BIGINT DEFAULT 0,
            avg_response_time_ms DECIMAL(10, 2),
            data_quality DECIMAL(3, 2) DEFAULT 1.0,
            last_success TIMESTAMP WITH TIME ZONE,
            last_failure TIMESTAMP WITH TIME ZONE,
            uptime_percentage DECIMAL(5, 2),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Create hypertables for timeseries data
        SELECT create_hypertable('match_events', 'timestamp', if_not_exists => TRUE);
        SELECT create_hypertable('match_statistics', 'timestamp', if_not_exists => TRUE);
        SELECT create_hypertable('player_statistics', 'timestamp', if_not_exists => TRUE);
        """
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(schema)
                logger.info("Sports database schema created")
        except Exception as e:
            logger.error(f"Error creating sports schema: {e}")
            raise
    
    async def load_cache_from_db(self):
        """Load data from database into cache"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Load recent matches
                matches_query = """
                SELECT match_id, competition_id, home_team_id, away_team_id,
                       match_date, status, home_score, away_score
                FROM matches 
                WHERE match_date > NOW() - INTERVAL '7 days'
                ORDER BY match_date DESC
                LIMIT 1000
                """
                
                matches = await conn.fetch(matches_query)
                for match in matches:
                    self.match_cache[match['match_id']] = {
                        'status': match['status'],
                        'home_score': match['home_score'],
                        'away_score': match['away_score'],
                        'last_updated': datetime.now(timezone.utc)
                    }
                
                logger.info(f"Loaded {len(matches)} matches into cache")
                
                # Load teams
                teams_query = """
                SELECT team_id, name, country
                FROM teams 
                LIMIT 5000
                """
                
                teams = await conn.fetch(teams_query)
                for team in teams:
                    self.team_cache[team['team_id']] = {
                        'name': team['name'],
                        'country': team['country']
                    }
                
                logger.info(f"Loaded {len(teams)} teams into cache")
                
        except Exception as e:
            logger.warning(f"Could not load cache from DB: {e}")
    
    async def collect_sports_data(self):
        """Main sports data collection loop"""
        logger.info("Starting sports data collection")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Collect data from each source
                tasks = []
                for source in self.config.DATA_SOURCES:
                    if self.source_states[source].is_active:
                        task = asyncio.create_task(
                            self.collect_from_source(source)
                        )
                        tasks.append(task)
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for i, result in enumerate(results):
                        source = list(self.config.DATA_SOURCES.keys())[i]
                        if isinstance(result, Exception):
                            logger.error(f"Error collecting from {source}: {result}")
                            await self.update_source_state(source, success=False)
                        else:
                            await self.update_source_state(source, success=True)
                
                # Calculate collection time
                collection_time = time.time() - start_time
                
                # Sleep until next collection
                sleep_time = max(0, self.config.COLLECTION_INTERVAL - collection_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(self.config.RETRY_DELAY)
    
    async def collect_from_source(self, source: str):
        """Collect data from a specific source"""
        try:
            config = self.config.DATA_SOURCES[source]
            
            # Check rate limit
            await self.check_rate_limit(source)
            
            # Update request count
            self.source_states[source].request_count += 1
            self.source_states[source].last_request = datetime.now(timezone.utc)
            
            logger.debug(f"Collecting data from {source}")
            
            # Different collection methods per source
            if source == 'statsbomb':
                data = await self.collect_statsbomb_data(config)
            elif source == 'opta':
                data = await self.collect_opta_data(config)
            elif source == 'sportradar':
                data = await self.collect_sportradar_data(config)
            elif source == 'flashscore':
                data = await self.collect_flashscore_data(config)
            elif source == 'sofascore':
                data = await self.collect_sofascore_data(config)
            else:
                data = await self.collect_generic_data(source, config)
            
            if data:
                # Process and publish data
                await self.process_source_data(source, data)
                
                # Update success state
                self.source_states[source].last_success = datetime.now(timezone.utc)
                self.source_states[source].consecutive_errors = 0
                
                return len(data)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error collecting from {source}: {e}")
            raise
    
    async def collect_statsbomb_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from StatsBomb API"""
        try:
            headers = {
                'Authorization': f"Bearer {config['api_key']}",
                'Accept': 'application/json'
            }
            
            all_data = []
            
            # Get competitions
            comps_url = f"{config['base_url']}/competitions"
            async with self.http_session.get(comps_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"StatsBomb competitions API returned {response.status}")
                
                competitions = await response.json()
            
            # Filter for monitored sports (football only for StatsBomb)
            for comp in competitions:
                if comp.get('competition_name', '').lower() in ['premier league', 'la liga', 'bundesliga']:
                    # Get matches for this competition
                    matches_url = f"{config['base_url']}/competitions/{comp['competition_id']}/matches"
                    async with self.http_session.get(matches_url, headers=headers) as response:
                        if response.status != 200:
                            logger.warning(f"StatsBomb matches API returned {response.status}")
                            continue
                        
                        matches = await response.json()
                    
                    for match in matches[:20]:  # Limit to 20 matches per competition
                        try:
                            match_data = self.parse_statsbomb_match(match, comp)
                            if match_data:
                                all_data.append(match_data)
                        except Exception as e:
                            logger.error(f"Error parsing StatsBomb match: {e}")
                            continue
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting StatsBomb data: {e}")
            return []
    
    def parse_statsbomb_match(self, match: Dict[str, Any], competition: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse StatsBomb match data"""
        try:
            match_id = f"statsbomb_{match['match_id']}"
            
            # Parse teams
            home_team = {
                'team_id': f"statsbomb_team_{match['home_team']['home_team_id']}",
                'name': match['home_team']['home_team_name'],
                'country': match.get('country', {}).get('name', 'Unknown')
            }
            
            away_team = {
                'team_id': f"statsbomb_team_{match['away_team']['away_team_id']}",
                'name': match['away_team']['away_team_name'],
                'country': match.get('country', {}).get('name', 'Unknown')
            }
            
            # Parse competition
            comp_info = {
                'competition_id': f"statsbomb_comp_{competition['competition_id']}",
                'name': competition['competition_name'],
                'country': competition.get('country_name', 'Unknown'),
                'season': match.get('season', {}).get('season_name', '2023/24'),
                'start_date': datetime.fromisoformat(match['match_date'].replace('Z', '+00:00')),
                'end_date': datetime.fromisoformat(match['match_date'].replace('Z', '+00:00')) + timedelta(days=365)
            }
            
            # Determine match status
            status = MatchStatus.SCHEDULED
            if match.get('match_status') == 'Available':
                status = MatchStatus.FINISHED
            elif match.get('match_status') == 'Live':
                status = MatchStatus.LIVE
            
            match_data = {
                'match': {
                    'match_id': match_id,
                    'competition': comp_info,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': datetime.fromisoformat(match['match_date'].replace('Z', '+00:00')),
                    'venue': match.get('stadium', {}).get('name'),
                    'referee': match.get('referee', {}).get('name'),
                    'status': status.value,
                    'home_score': match.get('home_score'),
                    'away_score': match.get('away_score'),
                    'metadata': {
                        'data_version': match.get('data_version'),
                        'shot_fidelity_version': match.get('shot_fidelity_version')
                    }
                },
                'source': 'statsbomb',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Add events if available
            if match.get('match_status') == 'Available':
                # In production, would fetch events from separate endpoint
                match_data['events'] = []
                match_data['statistics'] = []
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing StatsBomb match: {e}")
            return None
    
    async def collect_opta_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from Opta API"""
        try:
            headers = {
                'Ocp-Apim-Subscription-Key': config['api_key'],
                'Accept': 'application/json'
            }
            
            all_data = []
            
            # Get fixtures for monitored sports
            for sport in self.config.MONITORED_SPORTS[:3]:  # Limit to first 3 sports
                fixtures_url = f"{config['base_url']}/fixtures?sport={sport}&dateFrom={datetime.now().date()}&dateTo={(datetime.now() + timedelta(days=7)).date()}"
                
                async with self.http_session.get(fixtures_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Opta fixtures API returned {response.status} for {sport}")
                        continue
                    
                    fixtures = await response.json()
                
                for fixture in fixtures.get('fixtures', [])[:50]:
                    try:
                        fixture_data = self.parse_opta_fixture(fixture, sport)
                        if fixture_data:
                            all_data.append(fixture_data)
                    except Exception as e:
                        logger.error(f"Error parsing Opta fixture: {e}")
                        continue
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting Opta data: {e}")
            return []
    
    def parse_opta_fixture(self, fixture: Dict[str, Any], sport: str) -> Optional[Dict[str, Any]]:
        """Parse Opta fixture data"""
        try:
            match_id = f"opta_{fixture['id']}"
            
            # Parse competition
            competition = fixture.get('competition', {})
            comp_info = {
                'competition_id': f"opta_comp_{competition.get('id', 'unknown')}",
                'name': competition.get('name', 'Unknown'),
                'country': competition.get('country', 'Unknown'),
                'season': fixture.get('season', {}).get('name', '2023/24'),
                'start_date': datetime.fromisoformat(fixture['date'].replace('Z', '+00:00')),
                'end_date': datetime.fromisoformat(fixture['date'].replace('Z', '+00:00')) + timedelta(days=365)
            }
            
            # Parse teams
            home_team = {
                'team_id': f"opta_team_{fixture['homeTeam']['id']}",
                'name': fixture['homeTeam']['name'],
                'country': fixture.get('country', 'Unknown')
            }
            
            away_team = {
                'team_id': f"opta_team_{fixture['awayTeam']['id']}",
                'name': fixture['awayTeam']['name'],
                'country': fixture.get('country', 'Unknown')
            }
            
            # Determine match status
            status = MatchStatus.SCHEDULED
            if fixture.get('status') == 'FINISHED':
                status = MatchStatus.FINISHED
            elif fixture.get('status') == 'LIVE':
                status = MatchStatus.LIVE
            elif fixture.get('status') == 'POSTPONED':
                status = MatchStatus.POSTPONED
            
            match_data = {
                'match': {
                    'match_id': match_id,
                    'competition': comp_info,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': datetime.fromisoformat(fixture['date'].replace('Z', '+00:00')),
                    'venue': fixture.get('venue', {}).get('name'),
                    'status': status.value,
                    'home_score': fixture.get('score', {}).get('fullTime', {}).get('home'),
                    'away_score': fixture.get('score', {}).get('fullTime', {}).get('away'),
                    'metadata': {
                        'last_updated': fixture.get('lastUpdated'),
                        'matchday': fixture.get('matchday')
                    }
                },
                'source': 'opta',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Add lineups if available
            if fixture.get('lineups'):
                match_data['lineups'] = self.parse_opta_lineups(fixture['lineups'])
            
            # Add statistics if available
            if fixture.get('statistics'):
                match_data['statistics'] = self.parse_opta_statistics(fixture['statistics'])
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing Opta fixture: {e}")
            return None
    
    def parse_opta_lineups(self, lineups: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Opta lineup data"""
        try:
            parsed = {
                'home': [],
                'away': []
            }
            
            for team_side in ['home', 'away']:
                if lineups.get(team_side):
                    for player in lineups[team_side].get('players', []):
                        player_data = {
                            'player_id': f"opta_player_{player['id']}",
                            'name': player.get('name'),
                            'position': player.get('position'),
                            'jersey_number': player.get('shirtNumber'),
                            'is_captain': player.get('captain', False)
                        }
                        parsed[team_side].append(player_data)
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Opta lineups: {e}")
            return {}
    
    def parse_opta_statistics(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Opta statistics"""
        try:
            parsed = {
                'home': {},
                'away': {}
            }
            
            for team_side in ['home', 'away']:
                if stats.get(team_side):
                    for stat in stats[team_side]:
                        parsed[team_side][stat['type']] = stat['value']
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing Opta statistics: {e}")
            return {}
    
    async def collect_sportradar_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from SportRadar API"""
        try:
            headers = {
                'Authorization': f"Bearer {config['api_key']}",
                'Accept': 'application/json'
            }
            
            all_data = []
            
            # SportRadar has different APIs per sport
            sport_apis = {
                'football': 'soccer',
                'basketball': 'basketball',
                'tennis': 'tennis',
                'baseball': 'baseball'
            }
            
            for sport, api_name in sport_apis.items():
                if sport not in self.config.MONITORED_SPORTS:
                    continue
                
                # Get daily schedule
                schedule_url = f"{config['base_url']}/{api_name}/trial/v4/en/sport_events/scheduled/{datetime.now().date()}/schedule.json"
                
                async with self.http_session.get(schedule_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"SportRadar schedule API returned {response.status} for {sport}")
                        continue
                    
                    schedule = await response.json()
                
                for event in schedule.get('sport_events', [])[:50]:
                    try:
                        event_data = self.parse_sportradar_event(event, sport)
                        if event_data:
                            all_data.append(event_data)
                    except Exception as e:
                        logger.error(f"Error parsing SportRadar event: {e}")
                        continue
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting SportRadar data: {e}")
            return []
    
    def parse_sportradar_event(self, event: Dict[str, Any], sport: str) -> Optional[Dict[str, Any]]:
        """Parse SportRadar event data"""
        try:
            match_id = f"sportradar_{event['id']}"
            
            # Parse competition
            tournament = event.get('tournament', {})
            comp_info = {
                'competition_id': f"sportradar_comp_{tournament.get('id', 'unknown')}",
                'name': tournament.get('name', 'Unknown'),
                'country': tournament.get('category', {}).get('country_code', 'Unknown'),
                'season': event.get('season', {}).get('name', '2023'),
                'start_date': datetime.fromisoformat(event['scheduled'].replace('Z', '+00:00')),
                'end_date': datetime.fromisoformat(event['scheduled'].replace('Z', '+00:00')) + timedelta(days=365)
            }
            
            # Parse teams
            competitors = event.get('competitors', [])
            if len(competitors) >= 2:
                home_team = {
                    'team_id': f"sportradar_team_{competitors[0]['id']}",
                    'name': competitors[0]['name'],
                    'country': competitors[0].get('country', 'Unknown')
                }
                
                away_team = {
                    'team_id': f"sportradar_team_{competitors[1]['id']}",
                    'name': competitors[1]['name'],
                    'country': competitors[1].get('country', 'Unknown')
                }
            else:
                return None
            
            # Determine match status
            status = MatchStatus.SCHEDULED
            if event.get('status') == 'closed':
                status = MatchStatus.FINISHED
            elif event.get('status') == 'live':
                status = MatchStatus.LIVE
            
            match_data = {
                'match': {
                    'match_id': match_id,
                    'competition': comp_info,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': datetime.fromisoformat(event['scheduled'].replace('Z', '+00:00')),
                    'venue': event.get('venue', {}).get('name'),
                    'status': status.value,
                    'home_score': event.get('scores', {}).get('home'),
                    'away_score': event.get('scores', {}).get('away'),
                    'metadata': {
                        'coverage': event.get('coverage'),
                        'stage': event.get('stage')
                    }
                },
                'source': 'sportradar',
                'timestamp': datetime.now(timezone.utc)
            }
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing SportRadar event: {e}")
            return None
    
    async def collect_flashscore_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from FlashScore website"""
        try:
            all_data = []
            
            # FlashScore uses web scraping
            for sport in self.config.MONITORED_SPORTS[:2]:  # Limit to 2 sports due to scraping
                sport_url = f"{config['base_url']}/{sport}/"
                
                async with self.http_session.get(sport_url) as response:
                    if response.status != 200:
                        logger.warning(f"FlashScore returned {response.status} for {sport}")
                        continue
                    
                    html = await response.text()
                
                # Parse HTML for matches
                soup = BeautifulSoup(html, 'html.parser')
                
                # This is a simplified parser - real implementation would be more complex
                match_elements = soup.find_all('div', class_=re.compile(r'match'))
                
                for element in match_elements[:20]:  # Limit to 20 matches
                    try:
                        match_data = self.parse_flashscore_element(element, sport)
                        if match_data:
                            all_data.append(match_data)
                    except Exception as e:
                        logger.error(f"Error parsing FlashScore element: {e}")
                        continue
            
            logger.info(f"Collected {len(all_data)} matches from FlashScore")
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting FlashScore data: {e}")
            return []
    
    def parse_flashscore_element(self, element, sport: str) -> Optional[Dict[str, Any]]:
        """Parse FlashScore HTML element"""
        try:
            # Extract match ID from data attribute
            match_id = element.get('id', f"flashscore_{hashlib.md5(str(element).encode()).hexdigest()[:16]}")
            
            # Extract team names
            team_elements = element.find_all('span', class_=re.compile(r'team'))
            if len(team_elements) < 2:
                return None
            
            home_team_name = team_elements[0].text.strip()
            away_team_name = team_elements[1].text.strip()
            
            # Extract score
            score_element = element.find('span', class_=re.compile(r'score'))
            home_score = None
            away_score = None
            
            if score_element:
                score_text = score_element.text.strip()
                if ':' in score_text:
                    home_score, away_score = map(int, score_text.split(':'))
            
            # Extract time/status
            time_element = element.find('span', class_=re.compile(r'time'))
            status = MatchStatus.SCHEDULED
            match_date = datetime.now(timezone.utc) + timedelta(hours=2)  # Default
            
            if time_element:
                time_text = time_element.text.strip()
                if 'FT' in time_text:
                    status = MatchStatus.FINISHED
                elif "'" in time_text:  # Live minute
                    status = MatchStatus.LIVE
                elif ':' in time_text:  # Scheduled time
                    try:
                        hour, minute = map(int, time_text.split(':'))
                        match_date = datetime.now(timezone.utc).replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                        if match_date < datetime.now(timezone.utc):
                            match_date += timedelta(days=1)
                    except:
                        pass
            
            match_data = {
                'match': {
                    'match_id': match_id,
                    'competition': {
                        'competition_id': f"flashscore_{sport}",
                        'name': sport.title(),
                        'country': 'International',
                        'season': '2023/24',
                        'start_date': match_date,
                        'end_date': match_date + timedelta(days=365)
                    },
                    'home_team': {
                        'team_id': f"flashscore_team_{hashlib.md5(home_team_name.encode()).hexdigest()[:8]}",
                        'name': home_team_name,
                        'country': 'Unknown'
                    },
                    'away_team': {
                        'team_id': f"flashscore_team_{hashlib.md5(away_team_name.encode()).hexdigest()[:8]}",
                        'name': away_team_name,
                        'country': 'Unknown'
                    },
                    'match_date': match_date,
                    'status': status.value,
                    'home_score': home_score,
                    'away_score': away_score,
                    'metadata': {
                        'source': 'flashscore',
                        'scraped_at': datetime.now(timezone.utc).isoformat()
                    }
                },
                'source': 'flashscore',
                'timestamp': datetime.now(timezone.utc)
            }
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing FlashScore element: {e}")
            return None
    
    async def collect_sofascore_data(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect data from SofaScore API"""
        try:
            headers = {
                'Authorization': f"Bearer {config['api_key']}",
                'Accept': 'application/json'
            }
            
            all_data = []
            
            # Get today's events
            today = datetime.now().date()
            events_url = f"{config['base_url']}/sport/{today}/events"
            
            async with self.http_session.get(events_url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"SofaScore events API returned {response.status}")
                
                events = await response.json()
            
            for event in events.get('events', [])[:50]:
                try:
                    event_data = self.parse_sofascore_event(event)
                    if event_data:
                        all_data.append(event_data)
                except Exception as e:
                    logger.error(f"Error parsing SofaScore event: {e}")
                    continue
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error collecting SofaScore data: {e}")
            return []
    
    def parse_sofascore_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse SofaScore event data"""
        try:
            match_id = f"sofascore_{event['id']}"
            
            # Parse tournament
            tournament = event.get('tournament', {})
            comp_info = {
                'competition_id': f"sofascore_comp_{tournament.get('id', 'unknown')}",
                'name': tournament.get('name', 'Unknown'),
                'country': tournament.get('category', {}).get('name', 'Unknown'),
                'season': tournament.get('season', {}).get('name', '2023'),
                'start_date': datetime.fromtimestamp(event['startTimestamp']),
                'end_date': datetime.fromtimestamp(event['startTimestamp']) + timedelta(days=365)
            }
            
            # Parse teams
            home_team = {
                'team_id': f"sofascore_team_{event['homeTeam']['id']}",
                'name': event['homeTeam']['name'],
                'country': event['homeTeam'].get('country', {}).get('name', 'Unknown')
            }
            
            away_team = {
                'team_id': f"sofascore_team_{event['awayTeam']['id']}",
                'name': event['awayTeam']['name'],
                'country': event['awayTeam'].get('country', {}).get('name', 'Unknown')
            }
            
            # Determine match status
            status = MatchStatus.SCHEDULED
            if event.get('status', {}).get('type') == 'finished':
                status = MatchStatus.FINISHED
            elif event.get('status', {}).get('type') == 'inprogress':
                status = MatchStatus.LIVE
            
            match_data = {
                'match': {
                    'match_id': match_id,
                    'competition': comp_info,
                    'home_team': home_team,
                    'away_team': away_team,
                    'match_date': datetime.fromtimestamp(event['startTimestamp']),
                    'venue': event.get('venue', {}).get('name'),
                    'status': status.value,
                    'home_score': event.get('homeScore', {}).get('current'),
                    'away_score': event.get('awayScore', {}).get('current'),
                    'metadata': {
                        'round': event.get('roundInfo', {}).get('round'),
                        'has_lineups': event.get('hasLineups', False)
                    }
                },
                'source': 'sofascore',
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Add statistics if available
            if event.get('statistics'):
                match_data['statistics'] = event['statistics']
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error parsing SofaScore event: {e}")
            return None
    
    async def collect_generic_data(self, source: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic data collection for other sources"""
        # Placeholder for additional data sources
        return []
    
    async def process_source_data(self, source: str, data: List[Dict[str, Any]]):
        """Process and publish data from a source"""
        try:
            processed_count = 0
            
            for item in data:
                try:
                    # Extract match data
                    match_data = item.get('match')
                    if not match_data:
                        continue
                    
                    # Create Match object
                    match_obj = self.create_match_object(match_data)
                    
                    # Check for updates
                    has_updates = await self.check_match_updates(match_obj)
                    
                    # Store in database
                    await self.store_match_data(match_obj, source)
                    
                    # Publish to Kafka
                    await self.publish_match_data(match_obj)
                    
                    # Process additional data
                    if item.get('events'):
                        await self.process_match_events(match_obj.match_id, item['events'])
                    
                    if item.get('statistics'):
                        await self.process_match_statistics(match_obj.match_id, item['statistics'])
                    
                    if item.get('lineups'):
                        await self.process_lineups(match_obj.match_id, item['lineups'])
                    
                    # Generate alerts if needed
                    if has_updates:
                        await self.generate_match_alerts(match_obj, source)
                    
                    processed_count += 1
                    self.stats['matches_collected'] += 1
                    
                except ValidationError as ve:
                    logger.error(f"Validation error for {source} data: {ve}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing {source} data: {e}")
                    continue
            
            logger.debug(f"Processed {processed_count} matches from {source}")
            
        except Exception as e:
            logger.error(f"Error in process_source_data: {e}")
    
    def create_match_object(self, match_data: Dict[str, Any]) -> Match:
        """Create Match object from raw data"""
        try:
            # Create Competition object
            competition = Competition(**match_data['competition'])
            
            # Create Team objects
            home_team = Team(**match_data['home_team'])
            away_team = Team(**match_data['away_team'])
            
            # Create Match object
            match_obj = Match(
                match_id=match_data['match_id'],
                competition=competition,
                home_team=home_team,
                away_team=away_team,
                match_date=match_data['match_date'],
                venue=match_data.get('venue'),
                referee=match_data.get('referee'),
                attendance=match_data.get('attendance'),
                status=MatchStatus(match_data['status']),
                home_score=match_data.get('home_score'),
                away_score=match_data.get('away_score'),
                match_week=match_data.get('match_week'),
                round=match_data.get('round'),
                group=match_data.get('group'),
                metadata=match_data.get('metadata', {})
            )
            
            return match_obj
            
        except Exception as e:
            logger.error(f"Error creating match object: {e}")
            raise
    
    async def check_match_updates(self, match: Match) -> bool:
        """Check if match has significant updates"""
        try:
            match_id = match.match_id
            
            if match_id not in self.match_cache:
                self.match_cache[match_id] = {
                    'status': match.status.value,
                    'home_score': match.home_score,
                    'away_score': match.away_score,
                    'last_updated': datetime.now(timezone.utc)
                }
                return True  # New match
            
            cached = self.match_cache[match_id]
            
            # Check for status change
            if cached['status'] != match.status.value:
                self.match_updates[match_id].append({
                    'type': 'status_change',
                    'old': cached['status'],
                    'new': match.status.value,
                    'timestamp': datetime.now(timezone.utc)
                })
                return True
            
            # Check for score change
            if (cached['home_score'] != match.home_score or 
                cached['away_score'] != match.away_score):
                self.match_updates[match_id].append({
                    'type': 'score_change',
                    'old_score': f"{cached['home_score']}-{cached['away_score']}",
                    'new_score': f"{match.home_score}-{match.away_score}",
                    'timestamp': datetime.now(timezone.utc)
                })
                return True
            
            # Update cache
            self.match_cache[match_id] = {
                'status': match.status.value,
                'home_score': match.home_score,
                'away_score': match.away_score,
                'last_updated': datetime.now(timezone.utc)
            }
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking match updates: {e}")
            return False
    
    async def store_match_data(self, match: Match, source: str):
        """Store match data in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Store competition
                comp_query = """
                INSERT INTO competitions 
                (competition_id, name, country, level, type, season, start_date, end_date, logo_url, website)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (competition_id) 
                DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    season = EXCLUDED.season,
                    updated_at = NOW()
                """
                
                await conn.execute(
                    comp_query,
                    match.competition.competition_id,
                    match.competition.name,
                    match.competition.country,
                    match.competition.level,
                    match.competition.type,
                    match.competition.season,
                    match.competition.start_date,
                    match.competition.end_date,
                    match.competition.logo_url,
                    match.competition.website
                )
                
                # Store teams
                teams = [match.home_team, match.away_team]
                for team in teams:
                    team_query = """
                    INSERT INTO teams 
                    (team_id, name, short_name, country, city, stadium, manager, 
                     founded_year, colors, logo_url, website)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (team_id) 
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        country = EXCLUDED.country,
                        updated_at = NOW()
                    """
                    
                    await conn.execute(
                        team_query,
                        team.team_id,
                        team.name,
                        team.short_name,
                        team.country,
                        team.city,
                        team.stadium,
                        team.manager,
                        team.founded_year,
                        json.dumps(team.colors) if team.colors else None,
                        team.logo_url,
                        team.website
                    )
                
                # Store match
                match_query = """
                INSERT INTO matches 
                (match_id, competition_id, home_team_id, away_team_id, match_date,
                 venue, referee, attendance, status, home_score, away_score,
                 halftime_score, match_week, match_round, match_group, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                ON CONFLICT (match_id) 
                DO UPDATE SET
                    status = EXCLUDED.status,
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    updated_at = NOW()
                """
                
                halftime_score = None
                if match.halftime_score:
                    halftime_score = f"{match.halftime_score[0]}-{match.halftime_score[1]}"
                
                await conn.execute(
                    match_query,
                    match.match_id,
                    match.competition.competition_id,
                    match.home_team.team_id,
                    match.away_team.team_id,
                    match.match_date,
                    match.venue,
                    match.referee,
                    match.attendance,
                    match.status.value,
                    match.home_score,
                    match.away_score,
                    halftime_score,
                    match.match_week,
                    match.round,
                    match.group,
                    json.dumps(match.metadata)
                )
                
        except Exception as e:
            logger.error(f"Error storing match data: {e}")
            raise
    
    async def publish_match_data(self, match: Match):
        """Publish match data to Kafka"""
        try:
            # Convert to dict for JSON serialization
            match_dict = match.dict()
            
            # Publish to matches topic
            await self.kafka_producer.send_and_wait(
                self.config.KAFKA_TOPIC_MATCHES,
                key=match.match_id.encode('utf-8'),
                value=json.dumps(match_dict, default=str).encode('utf-8'),
                timestamp_ms=int(match.match_date.timestamp() * 1000)
            )
            
            # Cache for fast access
            await self.cache_match_data(match)
            
        except Exception as e:
            logger.error(f"Error publishing match data to Kafka: {e}")
            raise
    
    async def cache_match_data(self, match: Match):
        """Cache match data in Redis"""
        try:
            # Cache match info
            match_key = f"match:{match.match_id}"
            match_data = {
                'match_id': match.match_id,
                'home_team': match.home_team.name,
                'away_team': match.away_team.name,
                'status': match.status.value,
                'home_score': match.home_score,
                'away_score': match.away_score,
                'match_date': match.match_date.isoformat(),
                'competition': match.competition.name,
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.setex(
                match_key,
                self.config.CACHE_TTL,
                json.dumps(match_data)
            )
            
            # Add to live matches if status is LIVE
            if match.status == MatchStatus.LIVE:
                await self.redis_client.sadd('live_matches', match.match_id)
                self.live_matches.add(match.match_id)
            else:
                await self.redis_client.srem('live_matches', match.match_id)
                self.live_matches.discard(match.match_id)
            
            # Add to competition sorted set
            comp_key = f"competition:{match.competition.competition_id}:matches"
            await self.redis_client.zadd(
                comp_key,
                {match.match_id: match.match_date.timestamp()}
            )
            
            # Keep only recent matches
            await self.redis_client.zremrangebyscore(
                comp_key,
                '-inf',
                (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
            )
            
        except Exception as e:
            logger.error(f"Error caching match data: {e}")
    
    async def process_match_events(self, match_id: str, events_data: List[Dict[str, Any]]):
        """Process match events"""
        try:
            for event_data in events_data:
                try:
                    event = MatchEvent(**event_data)
                    
                    # Store in database
                    await self.store_match_event(event)
                    
                    # Publish to Kafka
                    await self.publish_match_event(event)
                    
                    self.stats['events_collected'] += 1
                    
                except ValidationError as ve:
                    logger.error(f"Validation error for match event: {ve}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing match event: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in process_match_events: {e}")
    
    async def store_match_event(self, event: MatchEvent):
        """Store match event in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO match_events 
                (event_id, match_id, event_type, minute, extra_time, team_id,
                 player_id, related_player_id, description, x_coordinate,
                 y_coordinate, outcome, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (event_id) 
                DO UPDATE SET
                    outcome = EXCLUDED.outcome,
                    timestamp = EXCLUDED.timestamp
                """
                
                await conn.execute(
                    query,
                    event.event_id,
                    event.match_id,
                    event.event_type.value,
                    event.minute,
                    event.extra_time,
                    event.team,
                    event.player,
                    event.related_player,
                    event.description,
                    event.x_coordinate,
                    event.y_coordinate,
                    event.outcome,
                    event.timestamp,
                    json.dumps(event.metadata)
                )
                
        except Exception as e:
            logger.error(f"Error storing match event: {e}")
    
    async def publish_match_event(self, event: MatchEvent):
        """Publish match event to Kafka"""
        try:
            event_dict = event.dict()
            
            await self.kafka_producer.send_and_wait(
                self.config.KAFKA_TOPIC_EVENTS,
                key=event.event_id.encode('utf-8'),
                value=json.dumps(event_dict, default=str).encode('utf-8')
            )
            
            # Cache recent events
            events_key = f"match:{event.match_id}:events"
            await self.redis_client.lpush(events_key, json.dumps(event_dict))
            await self.redis_client.ltrim(events_key, 0, 49)  # Keep last 50 events
            await self.redis_client.expire(events_key, 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error publishing match event: {e}")
    
    async def process_match_statistics(self, match_id: str, stats_data: Dict[str, Any]):
        """Process match statistics"""
        try:
            for team_side, team_stats in stats_data.items():
                team_id = None
                if team_side == 'home':
                    # Get team_id from match cache
                    pass
                elif team_side == 'away':
                    # Get team_id from match cache
                    pass
                
                if not team_id:
                    continue
                
                for stat_type, value in team_stats.items():
                    try:
                        stats = MatchStatistics(
                            stats_id=f"stats_{match_id}_{team_id}_{stat_type}_{int(time.time())}",
                            match_id=match_id,
                            team_id=team_id,
                            statistic_type=stat_type,
                            value=float(value),
                            timestamp=datetime.now(timezone.utc)
                        )
                        
                        # Store in database
                        await self.store_match_statistics(stats)
                        
                        # Publish to Kafka
                        await self.publish_match_statistics(stats)
                        
                        self.stats['stats_collected'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing statistics: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in process_match_statistics: {e}")
    
    async def store_match_statistics(self, stats: MatchStatistics):
        """Store match statistics in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO match_statistics 
                (stats_id, match_id, team_id, statistic_type, value, timestamp, period)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """
                
                await conn.execute(
                    query,
                    stats.stats_id,
                    stats.match_id,
                    stats.team_id,
                    stats.statistic_type,
                    stats.value,
                    stats.timestamp,
                    stats.period
                )
                
        except Exception as e:
            logger.error(f"Error storing match statistics: {e}")
    
    async def publish_match_statistics(self, stats: MatchStatistics):
        """Publish match statistics to Kafka"""
        try:
            stats_dict = stats.dict()
            
            await self.kafka_producer.send_and_wait(
                self.config.KAFKA_TOPIC_STATS,
                key=stats.stats_id.encode('utf-8'),
                value=json.dumps(stats_dict, default=str).encode('utf-8')
            )
            
        except Exception as e:
            logger.error(f"Error publishing match statistics: {e}")
    
    async def process_lineups(self, match_id: str, lineups_data: Dict[str, Any]):
        """Process team lineups"""
        try:
            for team_side, players in lineups_data.items():
                team_id = None
                # Get team_id from cache or database
                
                if team_id and players:
                    lineup = Lineup(
                        lineup_id=f"lineup_{match_id}_{team_id}_{int(time.time())}",
                        match_id=match_id,
                        team_id=team_id,
                        players=players,
                        substitutes=[],
                        timestamp=datetime.now(timezone.utc),
                        is_confirmed=True
                    )
                    
                    # Store in database
                    await self.store_lineup(lineup)
                    
                    # Cache lineup
                    await self.cache_lineup(lineup)
                    
        except Exception as e:
            logger.error(f"Error processing lineups: {e}")
    
    async def store_lineup(self, lineup: Lineup):
        """Store lineup in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO lineups 
                (lineup_id, match_id, team_id, formation, players, substitutes, coach, timestamp, is_confirmed)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (lineup_id) 
                DO UPDATE SET
                    players = EXCLUDED.players,
                    substitutes = EXCLUDED.substitutes,
                    is_confirmed = EXCLUDED.is_confirmed,
                    timestamp = EXCLUDED.timestamp
                """
                
                await conn.execute(
                    query,
                    lineup.lineup_id,
                    lineup.match_id,
                    lineup.team_id,
                    lineup.formation,
                    json.dumps(lineup.players),
                    json.dumps(lineup.substitutes),
                    lineup.coach,
                    lineup.timestamp,
                    lineup.is_confirmed
                )
                
        except Exception as e:
            logger.error(f"Error storing lineup: {e}")
    
    async def cache_lineup(self, lineup: Lineup):
        """Cache lineup in Redis"""
        try:
            lineup_key = f"match:{lineup.match_id}:lineup:{lineup.team_id}"
            lineup_data = {
                'formation': lineup.formation,
                'players': lineup.players,
                'substitutes': lineup.substitutes,
                'coach': lineup.coach,
                'is_confirmed': lineup.is_confirmed,
                'timestamp': lineup.timestamp.isoformat()
            }
            
            await self.redis_client.setex(
                lineup_key,
                3600,  # 1 hour TTL
                json.dumps(lineup_data)
            )
            
        except Exception as e:
            logger.error(f"Error caching lineup: {e}")
    
    async def generate_match_alerts(self, match: Match, source: str):
        """Generate alerts for significant match updates"""
        try:
            match_id = match.match_id
            
            # Check for status changes
            updates = list(self.match_updates[match_id])
            for update in updates:
                if update['type'] == 'status_change':
                    if update['new'] == MatchStatus.LIVE.value:
                        alert = {
                            'alert_id': f"alert_{match_id}_live_{int(time.time())}",
                            'type': 'match_started',
                            'match_id': match_id,
                            'title': f"Match Started: {match.home_team.name} vs {match.away_team.name}",
                            'message': f"The match has started. Current score: {match.home_score or 0}-{match.away_score or 0}",
                            'severity': 'info',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'metadata': {
                                'competition': match.competition.name,
                                'source': source
                            }
                        }
                        
                        await self.publish_alert(alert)
                    
                    elif update['new'] == MatchStatus.FINISHED.value:
                        alert = {
                            'alert_id': f"alert_{match_id}_finished_{int(time.time())}",
                            'type': 'match_finished',
                            'match_id': match_id,
                            'title': f"Match Finished: {match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}",
                            'message': f"Final score: {match.home_score}-{match.away_score}",
                            'severity': 'info',
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'metadata': {
                                'competition': match.competition.name,
                                'source': source
                            }
                        }
                        
                        await self.publish_alert(alert)
                
                elif update['type'] == 'score_change':
                    alert = {
                        'alert_id': f"alert_{match_id}_score_{int(time.time())}",
                        'type': 'score_update',
                        'match_id': match_id,
                        'title': f"Score Update: {match.home_team.name} vs {match.away_team.name}",
                        'message': f"Score changed from {update['old_score']} to {update['new_score']}",
                        'severity': 'info',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'metadata': {
                            'competition': match.competition.name,
                            'source': source
                        }
                    }
                    
                    await self.publish_alert(alert)
            
            self.stats['alerts_generated'] += len(updates)
            
            # Clear updates for this match
            self.match_updates[match_id].clear()
            
        except Exception as e:
            logger.error(f"Error generating match alerts: {e}")
    
    async def publish_alert(self, alert: Dict[str, Any]):
        """Publish alert to Redis and Kafka"""
        try:
            # Publish to Redis for real-time notifications
            await self.redis_client.publish(
                'sports:alerts',
                json.dumps(alert)
            )
            
            # Store in Redis list for recent alerts
            await self.redis_client.lpush('recent_alerts', json.dumps(alert))
            await self.redis_client.ltrim('recent_alerts', 0, 99)  # Keep last 100
            
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
    
    async def update_live_matches(self):
        """Periodic update of live matches"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Update live matches from cache
                live_match_ids = await self.redis_client.smembers('live_matches')
                
                for match_id in live_match_ids:
                    # Check if match is still live
                    match_key = f"match:{match_id}"
                    match_data = await self.redis_client.get(match_key)
                    
                    if match_data:
                        match_info = json.loads(match_data)
                        if match_info.get('status') != 'live':
                            await self.redis_client.srem('live_matches', match_id)
                            self.live_matches.discard(match_id)
                    else:
                        await self.redis_client.srem('live_matches', match_id)
                        self.live_matches.discard(match_id)
                
                logger.debug(f"Updated live matches: {len(live_match_ids)}")
                
            except Exception as e:
                logger.error(f"Error updating live matches: {e}")
    
    async def check_rate_limit(self, source: str):
        """Check and enforce rate limits"""
        try:
            rate_limit = self.config.DATA_SOURCES[source]['rate_limit']
            now = time.time()
            
            if source not in self.request_times:
                self.request_times[source] = []
            
            # Remove old request times
            self.request_times[source] = [
                t for t in self.request_times[source]
                if now - t < 60  # Keep last minute
            ]
            
            # Check if we need to wait
            if len(self.request_times[source]) > 0:
                last_request = self.request_times[source][-1]
                time_since_last = now - last_request
                
                if time_since_last < rate_limit:
                    wait_time = rate_limit - time_since_last
                    await asyncio.sleep(wait_time)
            
            # Record this request
            self.request_times[source].append(time.time())
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
    
    async def update_source_state(self, source: str, success: bool):
        """Update data source performance state"""
        try:
            state = self.source_states[source]
            
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
                    logger.warning(f"Deactivated {source} due to {state.consecutive_errors} consecutive errors")
            
            # Update performance in database
            await self.update_source_performance(source, success)
            
        except Exception as e:
            logger.error(f"Error updating source state: {e}")
    
    async def update_source_performance(self, source: str, success: bool):
        """Update data source performance in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                if success:
                    query = """
                    INSERT INTO data_source_performance 
                    (source_name, total_requests, successful_requests, last_success, updated_at)
                    VALUES ($1, 1, 1, NOW(), NOW())
                    ON CONFLICT (source_name) 
                    DO UPDATE SET
                        total_requests = data_source_performance.total_requests + 1,
                        successful_requests = data_source_performance.successful_requests + 1,
                        last_success = NOW(),
                        uptime_percentage = data_source_performance.successful_requests::float / 
                                           data_source_performance.total_requests * 100,
                        updated_at = NOW()
                    """
                else:
                    query = """
                    INSERT INTO data_source_performance 
                    (source_name, total_requests, failed_requests, last_failure, updated_at)
                    VALUES ($1, 1, 1, NOW(), NOW())
                    ON CONFLICT (source_name) 
                    DO UPDATE SET
                        total_requests = data_source_performance.total_requests + 1,
                        failed_requests = data_source_performance.failed_requests + 1,
                        last_failure = NOW(),
                        uptime_percentage = data_source_performance.successful_requests::float / 
                                           data_source_performance.total_requests * 100,
                        updated_at = NOW()
                    """
                
                await conn.execute(query, source)
                
        except Exception as e:
            logger.error(f"Error updating source performance: {e}")
    
    async def monitor_sources(self):
        """Monitor data source health and reactivate if needed"""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for source, state in self.source_states.items():
                    if not state.is_active and state.consecutive_errors > 10:
                        # Try to reactivate after 10 minutes
                        if state.last_success:
                            time_since_last = datetime.now(timezone.utc) - state.last_success
                            if time_since_last.total_seconds() > 600:  # 10 minutes
                                state.is_active = True
                                state.consecutive_errors = 0
                                logger.info(f"Reactivated {source}")
                
            except Exception as e:
                logger.error(f"Error in source monitoring: {e}")
    
    async def periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                # Clean old cache entries
                await self.cleanup_old_cache()
                
                # Log statistics
                logger.info(
                    f"Statistics - Matches: {self.stats['matches_collected']}, "
                    f"Events: {self.stats['events_collected']}, "
                    f"Stats: {self.stats['stats_collected']}, "
                    f"Alerts: {self.stats['alerts_generated']}, "
                    f"Errors: {self.stats['errors']}"
                )
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def cleanup_old_cache(self):
        """Cleanup old cache entries"""
        try:
            # Clean match cache older than 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for match_id in list(self.match_cache.keys()):
                cached = self.match_cache[match_id]
                if cached['last_updated'] < cutoff:
                    del self.match_cache[match_id]
            
            logger.debug(f"Cleaned match cache: {len(self.match_cache)} entries remaining")
            
        except Exception as e:
            logger.error(f"Error cleaning old cache: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Return health check status"""
        health = {
            'status': 'healthy',
            'running': self.running,
            'statistics': self.stats,
            'live_matches_count': len(self.live_matches),
            'sources': {
                source: {
                    'is_active': state.is_active,
                    'request_count': state.request_count,
                    'error_count': state.error_count,
                    'consecutive_errors': state.consecutive_errors,
                    'data_quality': state.data_quality,
                    'last_success': state.last_success.isoformat() if state.last_success else None
                }
                for source, state in self.source_states.items()
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
        logger.info("Stopping SportsProducer...")
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
        
        logger.info("SportsProducer stopped")

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)

async def main():
    """Main entry point"""
    logger.info("Starting GOAT Sports Producer...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = SportsConfig()
    producer = SportsProducer(config)
    
    try:
        # Initialize
        if not await producer.initialize():
            logger.error("Failed to initialize sports producer")
            return
        
        # Start collection
        collection_task = asyncio.create_task(producer.collect_sports_data())
        
        # Wait for collection task
        await collection_task
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await producer.stop()
        logger.info("Sports producer shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
