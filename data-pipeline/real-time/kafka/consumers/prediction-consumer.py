"""
Prediction Consumer for GOAT Prediction Ultimate
Consumes predictions from Kafka topics, processes them, and stores in databases.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import aiokafka
import asyncpg
from redis import asyncio as aioredis
from pydantic import BaseModel, ValidationError
import psycopg2
from psycopg2.extras import Json
import numpy as np
from dataclasses import dataclass
from enum import Enum
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/prediction-consumer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    """Configuration for Kafka consumer"""
    KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']
    KAFKA_TOPIC_PREDICTIONS = 'goat-predictions'
    KAFKA_TOPIC_ODDS = 'goat-odds'
    KAFKA_TOPIC_BETS = 'goat-bets'
    KAFKA_GROUP_ID = 'prediction-consumer-group'
    KAFKA_AUTO_OFFSET_RESET = 'earliest'
    KAFKA_ENABLE_AUTO_COMMIT = True
    KAFKA_MAX_POLL_RECORDS = 100
    KAFKA_SESSION_TIMEOUT_MS = 30000
    
    # Database
    POSTGRES_DSN = "postgresql://user:password@timescaledb:5432/goat_prediction"
    REDIS_URL = "redis://redis:6379/0"
    
    # Processing
    BATCH_SIZE = 100
    PROCESSING_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

# Enums
class PredictionStatus(str, Enum):
    """Status of a prediction"""
    PENDING = "pending"
    PROCESSED = "processed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SETTLED = "settled"

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
    EXACT_SCORE = "exact_score"
    BTTS = "btts"
    CORNERS = "corners"
    CARDS = "cards"
    HANDICAP = "handicap"
    TOTAL_POINTS = "total_points"
    PLAYER_PROPS = "player_props"

# Pydantic Models for validation
class TeamInfo(BaseModel):
    """Team information"""
    team_id: str
    name: str
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    country: Optional[str] = None

class MatchInfo(BaseModel):
    """Match information"""
    match_id: str
    sport: SportType
    league: str
    home_team: TeamInfo
    away_team: TeamInfo
    start_time: datetime
    venue: Optional[str] = None
    round: Optional[str] = None
    season: Optional[str] = None

class OddsInfo(BaseModel):
    """Odds information"""
    odds_id: str
    market: MarketType
    bookmaker: str
    home_odds: float
    away_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    handicap_value: Optional[float] = None
    timestamp: datetime
    url: Optional[str] = None

class ModelPrediction(BaseModel):
    """Model prediction output"""
    model_id: str
    model_version: str
    prediction_type: MarketType
    home_probability: float
    away_probability: Optional[float] = None
    draw_probability: Optional[float] = None
    over_probability: Optional[float] = None
    under_probability: Optional[float] = None
    predicted_score: Optional[str] = None
    confidence: float
    features_used: List[str]
    model_metadata: Dict[str, Any]

class PredictionMessage(BaseModel):
    """Complete prediction message from Kafka"""
    prediction_id: str
    match: MatchInfo
    odds: List[OddsInfo]
    predictions: List[ModelPrediction]
    ensemble_prediction: Dict[str, Any]
    calculated_ev: float
    kelly_fraction: float
    recommended_stake: float
    confidence_interval: Dict[str, float]
    timestamp: datetime
    expires_at: datetime
    metadata: Dict[str, Any]

@dataclass
class ProcessedPrediction:
    """Processed prediction for storage"""
    prediction_id: str
    match_id: str
    sport: SportType
    market: MarketType
    home_probability: float
    away_probability: Optional[float]
    draw_probability: Optional[float]
    over_probability: Optional[float]
    under_probability: Optional[float]
    predicted_score: Optional[str]
    confidence: float
    expected_value: float
    kelly_fraction: float
    recommended_stake: float
    confidence_lower: float
    confidence_upper: float
    best_odds: Dict[str, float]
    model_predictions: List[Dict[str, Any]]
    status: PredictionStatus
    created_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]

class PredictionConsumer:
    """Main Kafka consumer for prediction processing"""
    
    def __init__(self, config: Config):
        self.config = config
        self.kafka_consumer = None
        self.pg_pool = None
        self.redis_client = None
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        
    async def initialize(self):
        """Initialize all connections"""
        try:
            # Initialize Kafka consumer
            self.kafka_consumer = aiokafka.AIOKafkaConsumer(
                self.config.KAFKA_TOPIC_PREDICTIONS,
                bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.config.KAFKA_GROUP_ID,
                auto_offset_reset=self.config.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=self.config.KAFKA_ENABLE_AUTO_COMMIT,
                max_poll_records=self.config.KAFKA_MAX_POLL_RECORDS,
                session_timeout_ms=self.config.KAFKA_SESSION_TIMEOUT_MS
            )
            
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config.POSTGRES_DSN,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            
            # Initialize Redis
            self.redis_client = aioredis.from_url(
                self.config.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connections
            await self.test_connections()
            
            logger.info("PredictionConsumer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PredictionConsumer: {e}")
            return False
    
    async def test_connections(self):
        """Test all database connections"""
        # Test Kafka
        await self.kafka_consumer.start()
        await self.kafka_consumer.stop()
        
        # Test PostgreSQL
        async with self.pg_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        
        # Test Redis
        await self.redis_client.ping()
        
        logger.info("All connections tested successfully")
    
    async def consume_predictions(self):
        """Main consumption loop"""
        await self.kafka_consumer.start()
        self.running = True
        
        logger.info(f"Started consuming from topic: {self.config.KAFKA_TOPIC_PREDICTIONS}")
        
        try:
            async for message in self.kafka_consumer:
                if not self.running:
                    break
                    
                try:
                    await self.process_message(message)
                    self.processed_count += 1
                    
                    # Log progress periodically
                    if self.processed_count % 100 == 0:
                        logger.info(f"Processed {self.processed_count} predictions, errors: {self.error_count}")
                        
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            
        finally:
            await self.kafka_consumer.stop()
            logger.info("Kafka consumer stopped")
    
    async def process_message(self, message: aiokafka.ConsumerRecord):
        """Process a single Kafka message"""
        try:
            # Parse JSON message
            raw_data = json.loads(message.value.decode('utf-8'))
            
            # Validate with Pydantic
            prediction_msg = PredictionMessage(**raw_data)
            
            # Process the prediction
            processed_pred = await self.process_prediction(prediction_msg)
            
            # Store in databases
            await self.store_prediction(processed_pred)
            
            # Update cache
            await self.update_cache(processed_pred)
            
            # Publish to WebSocket if needed
            await self.publish_to_websocket(processed_pred)
            
            logger.info(f"Successfully processed prediction: {processed_pred.prediction_id}")
            
        except ValidationError as ve:
            logger.error(f"Validation error: {ve}")
            await self.handle_invalid_message(message, ve)
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await self.handle_processing_error(message, e)
    
    async def process_prediction(self, msg: PredictionMessage) -> ProcessedPrediction:
        """Process and transform prediction message"""
        
        # Determine main market type
        main_market = msg.predictions[0].prediction_type if msg.predictions else MarketType.MATCH_WINNER
        
        # Extract best odds
        best_odds = self.extract_best_odds(msg.odds, main_market)
        
        # Calculate confidence interval
        conf_lower = msg.confidence_interval.get('lower', 0.0)
        conf_upper = msg.confidence_interval.get('upper', 1.0)
        
        # Process model predictions
        model_preds = []
        for pred in msg.predictions:
            model_pred = {
                'model_id': pred.model_id,
                'model_version': pred.model_version,
                'prediction_type': pred.prediction_type,
                'home_probability': pred.home_probability,
                'away_probability': pred.away_probability,
                'draw_probability': pred.draw_probability,
                'over_probability': pred.over_probability,
                'under_probability': pred.under_probability,
                'predicted_score': pred.predicted_score,
                'confidence': pred.confidence,
                'features_used': pred.features_used,
                'metadata': pred.model_metadata
            }
            model_preds.append(model_pred)
        
        # Create processed prediction
        processed = ProcessedPrediction(
            prediction_id=msg.prediction_id,
            match_id=msg.match.match_id,
            sport=msg.match.sport,
            market=main_market,
            home_probability=msg.ensemble_prediction.get('home_probability', 0.0),
            away_probability=msg.ensemble_prediction.get('away_probability'),
            draw_probability=msg.ensemble_prediction.get('draw_probability'),
            over_probability=msg.ensemble_prediction.get('over_probability'),
            under_probability=msg.ensemble_prediction.get('under_probability'),
            predicted_score=msg.ensemble_prediction.get('predicted_score'),
            confidence=msg.ensemble_prediction.get('confidence', 0.5),
            expected_value=msg.calculated_ev,
            kelly_fraction=msg.kelly_fraction,
            recommended_stake=msg.recommended_stake,
            confidence_lower=conf_lower,
            confidence_upper=conf_upper,
            best_odds=best_odds,
            model_predictions=model_preds,
            status=PredictionStatus.PENDING,
            created_at=msg.timestamp,
            expires_at=msg.expires_at,
            metadata=msg.metadata
        )
        
        return processed
    
    def extract_best_odds(self, odds_list: List[OddsInfo], market: MarketType) -> Dict[str, float]:
        """Extract best odds for each outcome"""
        best_odds = {}
        
        if market == MarketType.MATCH_WINNER:
            home_odds = [o.home_odds for o in odds_list if o.market == market]
            away_odds = [o.away_odds for o in odds_list if o.market == market and o.away_odds]
            draw_odds = [o.draw_odds for o in odds_list if o.market == market and o.draw_odds]
            
            if home_odds:
                best_odds['home'] = max(home_odds)
            if away_odds:
                best_odds['away'] = max(away_odds)
            if draw_odds:
                best_odds['draw'] = max(draw_odds)
                
        elif market == MarketType.OVER_UNDER:
            over_odds = [o.over_odds for o in odds_list if o.market == market and o.over_odds]
            under_odds = [o.under_odds for o in odds_list if o.market == market and o.under_odds]
            
            if over_odds:
                best_odds['over'] = max(over_odds)
            if under_odds:
                best_odds['under'] = max(under_odds)
        
        return best_odds
    
    async def store_prediction(self, prediction: ProcessedPrediction):
        """Store prediction in PostgreSQL and TimescaleDB"""
        
        # Store in main predictions table
        await self.store_in_postgres(prediction)
        
        # Store in TimescaleDB hypertable for time-series analysis
        await self.store_in_timescaledb(prediction)
        
        # Store in Redis for fast access
        await self.store_in_redis(prediction)
    
    async def store_in_postgres(self, prediction: ProcessedPrediction):
        """Store in PostgreSQL main table"""
        query = """
        INSERT INTO predictions (
            prediction_id, match_id, sport, market, home_probability, away_probability,
            draw_probability, over_probability, under_probability, predicted_score,
            confidence, expected_value, kelly_fraction, recommended_stake,
            confidence_lower, confidence_upper, best_odds, model_predictions,
            status, created_at, expires_at, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
        ON CONFLICT (prediction_id) DO UPDATE SET
            home_probability = EXCLUDED.home_probability,
            away_probability = EXCLUDED.away_probability,
            draw_probability = EXCLUDED.draw_probability,
            confidence = EXCLUDED.confidence,
            expected_value = EXCLUDED.expected_value,
            kelly_fraction = EXCLUDED.kelly_fraction,
            recommended_stake = EXCLUDED.recommended_stake,
            best_odds = EXCLUDED.best_odds,
            model_predictions = EXCLUDED.model_predictions,
            status = EXCLUDED.status,
            expires_at = EXCLUDED.expires_at,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    query,
                    prediction.prediction_id,
                    prediction.match_id,
                    prediction.sport.value,
                    prediction.market.value,
                    prediction.home_probability,
                    prediction.away_probability,
                    prediction.draw_probability,
                    prediction.over_probability,
                    prediction.under_probability,
                    prediction.predicted_score,
                    prediction.confidence,
                    prediction.expected_value,
                    prediction.kelly_fraction,
                    prediction.recommended_stake,
                    prediction.confidence_lower,
                    prediction.confidence_upper,
                    json.dumps(prediction.best_odds),
                    json.dumps(prediction.model_predictions),
                    prediction.status.value,
                    prediction.created_at,
                    prediction.expires_at,
                    json.dumps(prediction.metadata)
                )
                
        except Exception as e:
            logger.error(f"Error storing in PostgreSQL: {e}")
            raise
    
    async def store_in_timescaledb(self, prediction: ProcessedPrediction):
        """Store in TimescaleDB hypertable for time-series analysis"""
        query = """
        INSERT INTO predictions_ts (
            time, prediction_id, match_id, sport, market, 
            home_probability, expected_value, confidence, kelly_fraction,
            best_odds_home, best_odds_away, best_odds_draw,
            tags
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(
                    query,
                    prediction.created_at,
                    prediction.prediction_id,
                    prediction.match_id,
                    prediction.sport.value,
                    prediction.market.value,
                    prediction.home_probability,
                    prediction.expected_value,
                    prediction.confidence,
                    prediction.kelly_fraction,
                    prediction.best_odds.get('home'),
                    prediction.best_odds.get('away'),
                    prediction.best_odds.get('draw'),
                    json.dumps({
                        'sport': prediction.sport.value,
                        'market': prediction.market.value,
                        'league': prediction.metadata.get('league', ''),
                        'confidence_level': 'high' if prediction.confidence > 0.7 else 'medium' if prediction.confidence > 0.5 else 'low'
                    })
                )
                
        except Exception as e:
            logger.error(f"Error storing in TimescaleDB: {e}")
            # Don't raise, as this is supplementary storage
    
    async def store_in_redis(self, prediction: ProcessedPrediction):
        """Store prediction in Redis for fast access"""
        try:
            # Store full prediction
            prediction_key = f"prediction:{prediction.prediction_id}"
            prediction_data = {
                'prediction_id': prediction.prediction_id,
                'match_id': prediction.match_id,
                'sport': prediction.sport.value,
                'market': prediction.market.value,
                'home_probability': str(prediction.home_probability),
                'expected_value': str(prediction.expected_value),
                'confidence': str(prediction.confidence),
                'kelly_fraction': str(prediction.kelly_fraction),
                'recommended_stake': str(prediction.recommended_stake),
                'best_odds': json.dumps(prediction.best_odds),
                'status': prediction.status.value,
                'expires_at': prediction.expires_at.isoformat(),
                'created_at': prediction.created_at.isoformat()
            }
            
            # Set with expiration (TTL = time until match starts + buffer)
            ttl = int((prediction.expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl > 0:
                await self.redis_client.hset(prediction_key, mapping=prediction_data)
                await self.redis_client.expire(prediction_key, ttl)
            
            # Add to sport-specific sorted set for recent predictions
            sport_zset_key = f"recent_predictions:{prediction.sport.value}"
            await self.redis_client.zadd(
                sport_zset_key,
                {prediction.prediction_id: prediction.created_at.timestamp()}
            )
            
            # Trim sorted set to keep only last 1000 predictions
            await self.redis_client.zremrangebyrank(sport_zset_key, 0, -1001)
            
            # Update match predictions set
            match_key = f"match_predictions:{prediction.match_id}"
            await self.redis_client.sadd(match_key, prediction.prediction_id)
            await self.redis_client.expire(match_key, 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error storing in Redis: {e}")
            # Don't raise, as cache is non-critical
    
    async def update_cache(self, prediction: ProcessedPrediction):
        """Update various cache entries"""
        try:
            # Update sport statistics
            await self.update_sport_stats(prediction.sport)
            
            # Update model performance cache
            for model_pred in prediction.model_predictions:
                await self.update_model_stats(model_pred['model_id'])
                
        except Exception as e:
            logger.warning(f"Error updating cache: {e}")
    
    async def update_sport_stats(self, sport: SportType):
        """Update sport statistics in cache"""
        stats_key = f"stats:sport:{sport.value}"
        
        try:
            # Increment prediction count
            await self.redis_client.hincrby(stats_key, 'prediction_count', 1)
            
            # Update last prediction time
            await self.redis_client.hset(stats_key, 'last_prediction', datetime.now(timezone.utc).isoformat())
            
            # Set expiration (7 days)
            await self.redis_client.expire(stats_key, 604800)
            
        except Exception as e:
            logger.warning(f"Error updating sport stats: {e}")
    
    async def update_model_stats(self, model_id: str):
        """Update model statistics in cache"""
        stats_key = f"stats:model:{model_id}"
        
        try:
            # Increment prediction count
            await self.redis_client.hincrby(stats_key, 'prediction_count', 1)
            
            # Update last used time
            await self.redis_client.hset(stats_key, 'last_used', datetime.now(timezone.utc).isoformat())
            
            # Set expiration (30 days)
            await self.redis_client.expire(stats_key, 2592000)
            
        except Exception as e:
            logger.warning(f"Error updating model stats: {e}")
    
    async def publish_to_websocket(self, prediction: ProcessedPrediction):
        """Publish prediction to WebSocket for real-time updates"""
        try:
            # Create WebSocket message
            ws_message = {
                'type': 'new_prediction',
                'prediction_id': prediction.prediction_id,
                'match_id': prediction.match_id,
                'sport': prediction.sport.value,
                'market': prediction.market.value,
                'home_probability': prediction.home_probability,
                'expected_value': prediction.expected_value,
                'confidence': prediction.confidence,
                'kelly_fraction': prediction.kelly_fraction,
                'recommended_stake': prediction.recommended_stake,
                'best_odds': prediction.best_odds,
                'created_at': prediction.created_at.isoformat(),
                'expires_at': prediction.expires_at.isoformat()
            }
            
            # Publish to Redis Pub/Sub for WebSocket server
            await self.redis_client.publish(
                'predictions:live',
                json.dumps(ws_message)
            )
            
            # Also publish to sport-specific channel
            await self.redis_client.publish(
                f'predictions:{prediction.sport.value}',
                json.dumps(ws_message)
            )
            
        except Exception as e:
            logger.warning(f"Error publishing to WebSocket: {e}")
    
    async def handle_invalid_message(self, message: aiokafka.ConsumerRecord, error: ValidationError):
        """Handle invalid Kafka messages"""
        try:
            # Log invalid message to dead letter queue
            dead_letter_data = {
                'topic': message.topic,
                'partition': message.partition,
                'offset': message.offset,
                'timestamp': message.timestamp,
                'raw_message': message.value.decode('utf-8'),
                'error': str(error),
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store in PostgreSQL for analysis
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO dead_letter_queue (data, error_type, processed_at)
                    VALUES ($1, $2, $3)
                """, json.dumps(dead_letter_data), 'validation_error', datetime.now(timezone.utc))
                
        except Exception as e:
            logger.error(f"Error handling invalid message: {e}")
    
    async def handle_processing_error(self, message: aiokafka.ConsumerRecord, error: Exception):
        """Handle processing errors"""
        try:
            # Log error with message context
            error_data = {
                'topic': message.topic,
                'partition': message.partition,
                'offset': message.offset,
                'error': str(error),
                'message_sample': message.value[:500].decode('utf-8') if message.value else '',
                'processed_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store error in database
            async with self.pg_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO processing_errors (error_data, error_type, retry_count)
                    VALUES ($1, $2, $3)
                """, json.dumps(error_data), type(error).__name__, 0)
                
        except Exception as e:
            logger.error(f"Error handling processing error: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Return health check status"""
        health = {
            'status': 'healthy',
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'running': self.running,
            'connections': {}
        }
        
        # Check Kafka
        try:
            await self.kafka_consumer._client.check_version()
            health['connections']['kafka'] = 'connected'
        except:
            health['connections']['kafka'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        # Check PostgreSQL
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                health['connections']['postgresql'] = 'connected'
        except:
            health['connections']['postgresql'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        # Check Redis
        try:
            await self.redis_client.ping()
            health['connections']['redis'] = 'connected'
        except:
            health['connections']['redis'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        return health
    
    async def stop(self):
        """Stop the consumer gracefully"""
        logger.info("Stopping PredictionConsumer...")
        self.running = False
        
        if self.kafka_consumer:
            await self.kafka_consumer.stop()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("PredictionConsumer stopped")

# Database schema creation (run once)
async def create_schema(pg_pool):
    """Create necessary database tables"""
    
    # Main predictions table
    predictions_table = """
    CREATE TABLE IF NOT EXISTS predictions (
        id BIGSERIAL PRIMARY KEY,
        prediction_id VARCHAR(255) UNIQUE NOT NULL,
        match_id VARCHAR(255) NOT NULL,
        sport VARCHAR(50) NOT NULL,
        market VARCHAR(50) NOT NULL,
        home_probability FLOAT NOT NULL CHECK (home_probability >= 0 AND home_probability <= 1),
        away_probability FLOAT CHECK (away_probability >= 0 AND away_probability <= 1),
        draw_probability FLOAT CHECK (draw_probability >= 0 AND draw_probability <= 1),
        over_probability FLOAT CHECK (over_probability >= 0 AND over_probability <= 1),
        under_probability FLOAT CHECK (under_probability >= 0 AND under_probability <= 1),
        predicted_score VARCHAR(20),
        confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
        expected_value FLOAT NOT NULL,
        kelly_fraction FLOAT NOT NULL,
        recommended_stake FLOAT NOT NULL,
        confidence_lower FLOAT NOT NULL,
        confidence_upper FLOAT NOT NULL,
        best_odds JSONB,
        model_predictions JSONB NOT NULL,
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        metadata JSONB,
        INDEX idx_prediction_id (prediction_id),
        INDEX idx_match_id (match_id),
        INDEX idx_sport (sport),
        INDEX idx_market (market),
        INDEX idx_status (status),
        INDEX idx_created_at (created_at),
        INDEX idx_expires_at (expires_at)
    );
    """
    
    # TimescaleDB hypertable for time-series data
    timescale_table = """
    SELECT create_hypertable('predictions_ts', 'time', if_not_exists => TRUE);
    
    CREATE TABLE IF NOT EXISTS predictions_ts (
        time TIMESTAMP WITH TIME ZONE NOT NULL,
        prediction_id VARCHAR(255) NOT NULL,
        match_id VARCHAR(255) NOT NULL,
        sport VARCHAR(50) NOT NULL,
        market VARCHAR(50) NOT NULL,
        home_probability FLOAT NOT NULL,
        expected_value FLOAT NOT NULL,
        confidence FLOAT NOT NULL,
        kelly_fraction FLOAT NOT NULL,
        best_odds_home FLOAT,
        best_odds_away FLOAT,
        best_odds_draw FLOAT,
        tags JSONB,
        INDEX idx_time (time DESC),
        INDEX idx_prediction_id (prediction_id),
        INDEX idx_match_id (match_id),
        INDEX idx_sport (sport)
    );
    """
    
    # Dead letter queue for invalid messages
    dead_letter_table = """
    CREATE TABLE IF NOT EXISTS dead_letter_queue (
        id BIGSERIAL PRIMARY KEY,
        data JSONB NOT NULL,
        error_type VARCHAR(100) NOT NULL,
        processed_at TIMESTAMP WITH TIME ZONE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Processing errors table
    errors_table = """
    CREATE TABLE IF NOT EXISTS processing_errors (
        id BIGSERIAL PRIMARY KEY,
        error_data JSONB NOT NULL,
        error_type VARCHAR(100) NOT NULL,
        retry_count INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_retry_at TIMESTAMP WITH TIME ZONE
    );
    """
    
    try:
        async with pg_pool.acquire() as conn:
            # Create tables
            await conn.execute(predictions_table)
            await conn.execute(timescale_table)
            await conn.execute(dead_letter_table)
            await conn.execute(errors_table)
            
            # Create hypertable if TimescaleDB extension exists
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
                await conn.execute("""
                    SELECT create_hypertable('predictions_ts', 'time', if_not_exists => TRUE);
                """)
            except Exception as e:
                logger.warning(f"TimescaleDB not available: {e}")
            
            logger.info("Database schema created successfully")
            
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        raise

async def main():
    """Main entry point"""
    logger.info("Starting GOAT Prediction Consumer...")
    
    config = Config()
    consumer = PredictionConsumer(config)
    
    try:
        # Initialize
        if not await consumer.initialize():
            logger.error("Failed to initialize consumer")
            return
        
        # Create database schema
        await create_schema(consumer.pg_pool)
        
        # Start consuming
        await consumer.consume_predictions()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await consumer.stop()
        logger.info("Prediction consumer shutdown complete")

if __name__ == "__main__":
    # Run with asyncio
    asyncio.run(main())
