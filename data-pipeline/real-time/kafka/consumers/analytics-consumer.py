"""
Analytics Consumer for GOAT Prediction Ultimate
Consumes prediction results, bet outcomes, and system metrics for real-time analytics.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
import aiokafka
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
from scipy import stats
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/analytics-consumer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class AnalyticsConfig:
    """Configuration for Analytics consumer"""
    KAFKA_BOOTSTRAP_SERVERS = ['kafka:9092']
    KAFKA_TOPIC_PREDICTIONS = 'goat-predictions'
    KAFKA_TOPIC_BETS = 'goat-bets'
    KAFKA_TOPIC_RESULTS = 'goat-match-results'
    KAFKA_TOPIC_METRICS = 'goat-system-metrics'
    KAFKA_GROUP_ID = 'analytics-consumer-group'
    KAFKA_AUTO_OFFSET_RESET = 'latest'
    KAFKA_ENABLE_AUTO_COMMIT = True
    KAFKA_MAX_POLL_RECORDS = 500
    KAFKA_SESSION_TIMEOUT_MS = 45000
    
    # Database
    POSTGRES_DSN = "postgresql://user:password@timescaledb:5432/goat_analytics"
    REDIS_URL = "redis://redis:6379/1"
    
    # Processing
    BATCH_SIZE = 1000
    PROCESSING_INTERVAL = 5  # seconds
    WINDOW_SIZES = [100, 1000, 10000]  # Rolling window sizes
    AGGREGATION_INTERVALS = ['5m', '15m', '1h', '1d']
    
    # Retention
    CACHE_TTL = 3600  # 1 hour
    ROLLING_WINDOW_DAYS = 30
    
    # Thresholds
    CONFIDENCE_THRESHOLD = 0.6
    EV_THRESHOLD = 0.05
    ANOMALY_THRESHOLD = 3.0  # z-score

# Enums
class BetOutcome(str, Enum):
    """Bet outcome status"""
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"  # Draw or refund
    CANCELLED = "cancelled"
    PENDING = "pending"

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

class MetricType(str, Enum):
    """System metric types"""
    PREDICTION_LATENCY = "prediction_latency"
    MODEL_ACCURACY = "model_accuracy"
    API_RESPONSE_TIME = "api_response_time"
    DATABASE_LATENCY = "database_latency"
    CACHE_HIT_RATE = "cache_hit_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    KAFKA_LAG = "kafka_lag"
    ERROR_RATE = "error_rate"

# Pydantic Models
class PredictionResult(BaseModel):
    """Prediction with actual outcome"""
    prediction_id: str
    match_id: str
    sport: SportType
    market: MarketType
    predicted_outcome: str
    actual_outcome: str
    confidence: float = Field(ge=0.0, le=1.0)
    expected_value: float
    timestamp: datetime
    model_used: str
    features: List[str]
    metadata: Dict[str, Any]

class BetRecord(BaseModel):
    """Bet record with outcome"""
    bet_id: str
    prediction_id: str
    user_id: str
    sport: SportType
    market: MarketType
    stake: float = Field(gt=0.0)
    odds: float = Field(gt=1.0)
    outcome: BetOutcome
    profit_loss: float
    placed_at: datetime
    settled_at: datetime
    metadata: Dict[str, Any]
    
    @validator('profit_loss')
    def validate_profit_loss(cls, v):
        return float(Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class MatchResult(BaseModel):
    """Match final result"""
    match_id: str
    sport: SportType
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    result: str  # home_win, away_win, draw
    match_date: datetime
    competition: str
    metadata: Dict[str, Any]

class SystemMetric(BaseModel):
    """System performance metric"""
    metric_id: str
    metric_type: MetricType
    service: str
    value: float
    unit: str
    timestamp: datetime
    labels: Dict[str, str]
    
    @validator('value')
    def validate_value(cls, v):
        return float(Decimal(str(v)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))

class AggregationWindow:
    """Time-based aggregation window"""
    def __init__(self, interval: str):
        self.interval = interval
        self.data = deque(maxlen=10000)
        self.start_time = datetime.now(timezone.utc)
    
    def add(self, timestamp: datetime, value: float):
        self.data.append((timestamp, value))
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.data:
            return {}
        
        values = [v for _, v in self.data]
        timestamps = [t for t, _ in self.data]
        
        return {
            'count': len(values),
            'mean': float(np.mean(values)),
            'std': float(np.std(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'median': float(np.median(values)),
            'p90': float(np.percentile(values, 90)),
            'p95': float(np.percentile(values, 95)),
            'p99': float(np.percentile(values, 99)),
            'latest_timestamp': max(timestamps),
            'earliest_timestamp': min(timestamps)
        }

@dataclass
class PerformanceMetrics:
    """Performance metrics for analytics"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: Optional[float]
    brier_score: float
    log_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    average_odds: float
    ev_per_bet: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'roc_auc': self.roc_auc,
            'brier_score': self.brier_score,
            'log_loss': self.log_loss,
            'profit_factor': self.profit_factor,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'average_odds': self.average_odds,
            'ev_per_bet': self.ev_per_bet
        }

class AnalyticsConsumer:
    """Main analytics consumer for real-time analytics processing"""
    
    def __init__(self, config: AnalyticsConfig):
        self.config = config
        self.kafka_consumer = None
        self.pg_pool = None
        self.redis_client = None
        self.running = False
        
        # Aggregation state
        self.aggregations = {
            interval: AggregationWindow(interval) 
            for interval in config.AGGREGATION_INTERVALS
        }
        
        # Rolling statistics
        self.rolling_stats = {
            window: defaultdict(lambda: deque(maxlen=window))
            for window in config.WINDOW_SIZES
        }
        
        # Performance trackers
        self.performance_by_sport = defaultdict(lambda: {
            'predictions': [],
            'bets': [],
            'results': []
        })
        
        # Anomaly detection
        self.anomaly_history = deque(maxlen=1000)
        
        # Counters
        self.processed_counts = {
            'predictions': 0,
            'bets': 0,
            'results': 0,
            'metrics': 0
        }
        
        self.error_counts = {
            'validation': 0,
            'processing': 0,
            'storage': 0
        }
        
        logger.info("AnalyticsConsumer initialized")
    
    async def initialize(self):
        """Initialize all connections and state"""
        try:
            # Initialize Kafka consumer for multiple topics
            self.kafka_consumer = aiokafka.AIOKafkaConsumer(
                self.config.KAFKA_TOPIC_PREDICTIONS,
                self.config.KAFKA_TOPIC_BETS,
                self.config.KAFKA_TOPIC_RESULTS,
                self.config.KAFKA_TOPIC_METRICS,
                bootstrap_servers=self.config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.config.KAFKA_GROUP_ID,
                auto_offset_reset=self.config.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=self.config.KAFKA_ENABLE_AUTO_COMMIT,
                max_poll_records=self.config.KAFKA_MAX_POLL_RECORDS,
                session_timeout_ms=self.config.KAFKA_SESSION_TIMEOUT_MS
            )
            
            # Initialize PostgreSQL connection pool for analytics
            self.pg_pool = await asyncpg.create_pool(
                dsn=self.config.POSTGRES_DSN,
                min_size=10,
                max_size=30,
                command_timeout=120,
                max_inactive_connection_lifetime=300
            )
            
            # Initialize Redis for caching analytics results
            self.redis_client = aioredis.from_url(
                self.config.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20
            )
            
            # Initialize analytics database
            await self.initialize_analytics_db()
            
            # Load historical data for baselines
            await self.load_historical_baselines()
            
            logger.info("AnalyticsConsumer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AnalyticsConsumer: {e}")
            return False
    
    async def initialize_analytics_db(self):
        """Create analytics database schema"""
        schema = """
        -- Performance metrics table
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id BIGSERIAL PRIMARY KEY,
            sport VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            time_window VARCHAR(20) NOT NULL,
            accuracy FLOAT,
            precision FLOAT,
            recall FLOAT,
            f1_score FLOAT,
            roc_auc FLOAT,
            brier_score FLOAT,
            log_loss FLOAT,
            profit_factor FLOAT,
            sharpe_ratio FLOAT,
            max_drawdown FLOAT,
            win_rate FLOAT,
            average_odds FLOAT,
            ev_per_bet FLOAT,
            sample_size INTEGER,
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(sport, market, time_window, calculated_at)
        );
        
        -- Rolling statistics
        CREATE TABLE IF NOT EXISTS rolling_statistics (
            id BIGSERIAL PRIMARY KEY,
            stat_type VARCHAR(50) NOT NULL,
            sport VARCHAR(50),
            window_size INTEGER NOT NULL,
            mean_value FLOAT,
            std_dev FLOAT,
            min_value FLOAT,
            max_value FLOAT,
            p25 FLOAT,
            p50 FLOAT,
            p75 FLOAT,
            p90 FLOAT,
            p95 FLOAT,
            count INTEGER,
            start_time TIMESTAMP WITH TIME ZONE,
            end_time TIMESTAMP WITH TIME ZONE,
            calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Bet performance by user
        CREATE TABLE IF NOT EXISTS user_performance (
            user_id VARCHAR(255) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            total_bets INTEGER DEFAULT 0,
            winning_bets INTEGER DEFAULT 0,
            total_stake DECIMAL(15, 2) DEFAULT 0,
            total_payout DECIMAL(15, 2) DEFAULT 0,
            net_profit DECIMAL(15, 2) DEFAULT 0,
            roi DECIMAL(10, 4),
            avg_odds DECIMAL(10, 2),
            best_win DECIMAL(15, 2),
            worst_loss DECIMAL(15, 2),
            last_active TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (user_id, sport)
        );
        
        -- Model performance tracking
        CREATE TABLE IF NOT EXISTS model_performance (
            model_id VARCHAR(255) NOT NULL,
            sport VARCHAR(50) NOT NULL,
            market VARCHAR(50) NOT NULL,
            total_predictions INTEGER DEFAULT 0,
            correct_predictions INTEGER DEFAULT 0,
            total_confidence FLOAT DEFAULT 0,
            avg_confidence FLOAT,
            calibration_error FLOAT,
            brier_score FLOAT,
            last_used TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            PRIMARY KEY (model_id, sport, market)
        );
        
        -- System metrics timeseries
        CREATE TABLE IF NOT EXISTS system_metrics_ts (
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            metric_type VARCHAR(50) NOT NULL,
            service VARCHAR(100) NOT NULL,
            value FLOAT NOT NULL,
            unit VARCHAR(20),
            labels JSONB,
            INDEX idx_time_metric (time, metric_type)
        );
        
        -- Anomaly detection logs
        CREATE TABLE IF NOT EXISTS anomaly_detection (
            id BIGSERIAL PRIMARY KEY,
            anomaly_type VARCHAR(50) NOT NULL,
            detected_value FLOAT,
            expected_range JSONB,
            z_score FLOAT,
            confidence FLOAT,
            description TEXT,
            detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            resolved_at TIMESTAMP WITH TIME ZONE,
            metadata JSONB
        );
        
        -- Create hypertable for timeseries data
        SELECT create_hypertable('system_metrics_ts', 'time', if_not_exists => TRUE);
        
        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_performance_sport_time ON performance_metrics(sport, calculated_at);
        CREATE INDEX IF NOT EXISTS idx_user_performance_user ON user_performance(user_id);
        CREATE INDEX IF NOT EXISTS idx_model_performance_model ON model_performance(model_id);
        CREATE INDEX IF NOT EXISTS idx_anomaly_detected_at ON anomaly_detection(detected_at);
        """
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.execute(schema)
                logger.info("Analytics database schema created")
        except Exception as e:
            logger.error(f"Error creating analytics schema: {e}")
            raise
    
    async def load_historical_baselines(self):
        """Load historical data for baseline calculations"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Load recent performance metrics
                query = """
                SELECT sport, market, 
                       AVG(accuracy) as avg_accuracy,
                       AVG(profit_factor) as avg_profit_factor,
                       STDDEV(accuracy) as std_accuracy
                FROM performance_metrics 
                WHERE calculated_at > NOW() - INTERVAL '7 days'
                GROUP BY sport, market
                """
                
                results = await conn.fetch(query)
                self.baselines = {
                    (row['sport'], row['market']): {
                        'accuracy': row['avg_accuracy'],
                        'profit_factor': row['avg_profit_factor'],
                        'std_accuracy': row['std_accuracy'] or 0.1
                    }
                    for row in results
                }
                
                logger.info(f"Loaded baselines for {len(self.baselines)} sport/market combinations")
                
        except Exception as e:
            logger.warning(f"Could not load historical baselines: {e}")
            self.baselines = {}
    
    async def consume_analytics(self):
        """Main consumption loop for analytics"""
        await self.kafka_consumer.start()
        self.running = True
        
        logger.info("Started analytics consumer")
        
        # Start background aggregation task
        aggregation_task = asyncio.create_task(self.periodic_aggregation())
        
        try:
            async for message in self.kafka_consumer:
                if not self.running:
                    break
                
                try:
                    topic = message.topic
                    await self.route_message(topic, message)
                    
                except Exception as e:
                    logger.error(f"Error processing message from topic {message.topic}: {e}")
                    self.error_counts['processing'] += 1
        
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        
        finally:
            self.running = False
            aggregation_task.cancel()
            await self.kafka_consumer.stop()
            logger.info("Analytics consumer stopped")
    
    async def route_message(self, topic: str, message: aiokafka.ConsumerRecord):
        """Route message to appropriate handler"""
        try:
            data = json.loads(message.value.decode('utf-8'))
            
            if topic == self.config.KAFKA_TOPIC_PREDICTIONS:
                await self.process_prediction(data)
                self.processed_counts['predictions'] += 1
                
            elif topic == self.config.KAFKA_TOPIC_BETS:
                await self.process_bet(data)
                self.processed_counts['bets'] += 1
                
            elif topic == self.config.KAFKA_TOPIC_RESULTS:
                await self.process_match_result(data)
                self.processed_counts['results'] += 1
                
            elif topic == self.config.KAFKA_TOPIC_METRICS:
                await self.process_system_metric(data)
                self.processed_counts['metrics'] += 1
                
        except ValidationError as ve:
            logger.error(f"Validation error for topic {topic}: {ve}")
            self.error_counts['validation'] += 1
            await self.store_invalid_message(topic, message, str(ve))
            
        except Exception as e:
            logger.error(f"Processing error for topic {topic}: {e}")
            self.error_counts['processing'] += 1
    
    async def process_prediction(self, data: Dict[str, Any]):
        """Process prediction result for analytics"""
        try:
            prediction = PredictionResult(**data)
            
            # Store in rolling statistics
            sport = prediction.sport.value
            market = prediction.market.value
            
            # Update rolling windows
            for window_size in self.config.WINDOW_SIZES:
                self.rolling_stats[window_size][f'confidence_{sport}_{market}'].append(
                    prediction.confidence
                )
                self.rolling_stats[window_size][f'ev_{sport}_{market}'].append(
                    prediction.expected_value
                )
            
            # Update sport performance tracker
            self.performance_by_sport[sport]['predictions'].append({
                'prediction_id': prediction.prediction_id,
                'market': market,
                'confidence': prediction.confidence,
                'expected_value': prediction.expected_value,
                'timestamp': prediction.timestamp,
                'model': prediction.model_used
            })
            
            # Check for anomalies
            await self.check_prediction_anomalies(prediction)
            
            # Update model performance
            await self.update_model_performance(prediction)
            
            # Store in cache for real-time dashboards
            await self.cache_prediction_stats(prediction)
            
        except Exception as e:
            logger.error(f"Error processing prediction: {e}")
            raise
    
    async def process_bet(self, data: Dict[str, Any]):
        """Process bet record for analytics"""
        try:
            bet = BetRecord(**data)
            
            # Calculate performance metrics
            sport = bet.sport.value
            market = bet.market.value
            
            # Update user performance
            await self.update_user_performance(bet)
            
            # Update sport performance
            self.performance_by_sport[sport]['bets'].append({
                'bet_id': bet.bet_id,
                'outcome': bet.outcome.value,
                'stake': bet.stake,
                'profit_loss': bet.profit_loss,
                'odds': bet.odds,
                'timestamp': bet.settled_at
            })
            
            # Update rolling statistics
            for window_size in self.config.WINDOW_SIZES:
                self.rolling_stats[window_size][f'profit_{sport}'].append(
                    bet.profit_loss
                )
                self.rolling_stats[window_size][f'roi_{sport}'].append(
                    bet.profit_loss / bet.stake if bet.stake > 0 else 0
                )
            
            # Calculate and cache real-time metrics
            await self.calculate_realtime_metrics(sport, market)
            
            # Update financial dashboards
            await self.update_financial_dashboards(bet)
            
        except Exception as e:
            logger.error(f"Error processing bet: {e}")
            raise
    
    async def process_match_result(self, data: Dict[str, Any]):
        """Process match result for analytics"""
        try:
            result = MatchResult(**data)
            
            sport = result.sport.value
            
            # Update sport performance tracker
            self.performance_by_sport[sport]['results'].append({
                'match_id': result.match_id,
                'home_score': result.home_score,
                'away_score': result.away_score,
                'result': result.result,
                'timestamp': result.match_date
            })
            
            # Update prediction accuracy based on results
            await self.update_prediction_accuracy(result)
            
            # Store for historical analysis
            await self.store_match_result(result)
            
            # Update league/competition statistics
            await self.update_competition_stats(result)
            
        except Exception as e:
            logger.error(f"Error processing match result: {e}")
            raise
    
    async def process_system_metric(self, data: Dict[str, Any]):
        """Process system metric for monitoring"""
        try:
            metric = SystemMetric(**data)
            
            # Store in TimescaleDB
            await self.store_system_metric(metric)
            
            # Update aggregations
            for interval, window in self.aggregations.items():
                window.add(metric.timestamp, metric.value)
            
            # Update rolling statistics
            metric_key = f"{metric.metric_type.value}_{metric.service}"
            for window_size in self.config.WINDOW_SIZES:
                self.rolling_stats[window_size][metric_key].append(metric.value)
            
            # Check for system anomalies
            await self.check_system_anomalies(metric)
            
            # Update Grafana cache
            await self.cache_system_metrics(metric)
            
        except Exception as e:
            logger.error(f"Error processing system metric: {e}")
            raise
    
    async def update_model_performance(self, prediction: PredictionResult):
        """Update model performance statistics"""
        try:
            async with self.pg_pool.acquire() as conn:
                # First, check if we have the actual outcome for this prediction
                query = """
                SELECT actual_outcome 
                FROM prediction_results 
                WHERE prediction_id = $1
                """
                
                result = await conn.fetchval(query, prediction.prediction_id)
                
                if result:
                    # We have the outcome, update model performance
                    is_correct = (prediction.predicted_outcome == result)
                    
                    update_query = """
                    INSERT INTO model_performance 
                    (model_id, sport, market, total_predictions, correct_predictions, 
                     total_confidence, last_used, updated_at)
                    VALUES ($1, $2, $3, 1, $4, $5, $6, NOW())
                    ON CONFLICT (model_id, sport, market) 
                    DO UPDATE SET
                        total_predictions = model_performance.total_predictions + 1,
                        correct_predictions = model_performance.correct_predictions + EXCLUDED.correct_predictions,
                        total_confidence = model_performance.total_confidence + EXCLUDED.total_confidence,
                        avg_confidence = (model_performance.total_confidence + EXCLUDED.total_confidence) / 
                                         (model_performance.total_predictions + 1),
                        last_used = EXCLUDED.last_used,
                        updated_at = NOW()
                    """
                    
                    await conn.execute(
                        update_query,
                        prediction.model_used,
                        prediction.sport.value,
                        prediction.market.value,
                        1 if is_correct else 0,
                        prediction.confidence,
                        prediction.timestamp
                    )
                    
        except Exception as e:
            logger.error(f"Error updating model performance: {e}")
    
    async def update_user_performance(self, bet: BetRecord):
        """Update user performance statistics"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO user_performance 
                (user_id, sport, total_bets, winning_bets, total_stake, 
                 total_payout, net_profit, avg_odds, last_active, updated_at)
                VALUES ($1, $2, 1, $3, $4, $5, $6, $7, $8, NOW())
                ON CONFLICT (user_id, sport) 
                DO UPDATE SET
                    total_bets = user_performance.total_bets + 1,
                    winning_bets = user_performance.winning_bets + EXCLUDED.winning_bets,
                    total_stake = user_performance.total_stake + EXCLUDED.total_stake,
                    total_payout = user_performance.total_payout + EXCLUDED.total_payout,
                    net_profit = user_performance.net_profit + EXCLUDED.net_profit,
                    avg_odds = (user_performance.avg_odds * user_performance.total_bets + EXCLUDED.avg_odds) / 
                               (user_performance.total_bets + 1),
                    roi = (user_performance.net_profit + EXCLUDED.net_profit) / 
                          (user_performance.total_stake + EXCLUDED.total_stake) * 100,
                    best_win = GREATEST(user_performance.best_win, EXCLUDED.net_profit),
                    worst_loss = LEAST(user_performance.worst_loss, EXCLUDED.net_profit),
                    last_active = EXCLUDED.last_active,
                    updated_at = NOW()
                """
                
                is_win = 1 if bet.outcome == BetOutcome.WIN else 0
                payout = bet.stake * bet.odds if bet.outcome == BetOutcome.WIN else 0
                
                await conn.execute(
                    query,
                    bet.user_id,
                    bet.sport.value,
                    is_win,
                    bet.stake,
                    payout,
                    bet.profit_loss,
                    bet.odds,
                    bet.settled_at
                )
                
        except Exception as e:
            logger.error(f"Error updating user performance: {e}")
    
    async def update_prediction_accuracy(self, result: MatchResult):
        """Update prediction accuracy based on match results"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Find predictions for this match
                query = """
                SELECT p.prediction_id, p.predicted_outcome, p.confidence, p.sport, p.market
                FROM predictions p
                WHERE p.match_id = $1 AND p.status = 'pending'
                """
                
                predictions = await conn.fetch(query, result.match_id)
                
                for pred in predictions:
                    # Determine if prediction was correct
                    predicted_correctly = self.evaluate_prediction(
                        pred['predicted_outcome'],
                        result.result,
                        pred['market']
                    )
                    
                    # Update prediction status
                    update_pred = """
                    UPDATE predictions 
                    SET status = 'settled',
                        actual_outcome = $2,
                        accuracy = $3,
                        updated_at = NOW()
                    WHERE prediction_id = $1
                    """
                    
                    await conn.execute(
                        update_pred,
                        pred['prediction_id'],
                        result.result,
                        predicted_correctly
                    )
                    
                    # Update performance metrics
                    await self.recalculate_performance_metrics(
                        pred['sport'],
                        pred['market']
                    )
                    
        except Exception as e:
            logger.error(f"Error updating prediction accuracy: {e}")
    
    def evaluate_prediction(self, predicted: str, actual: str, market: str) -> bool:
        """Evaluate if prediction was correct"""
        if market == MarketType.MATCH_WINNER:
            return predicted == actual
        elif market == MarketType.OVER_UNDER:
            # Parse over/under predictions
            return predicted == actual
        elif market == MarketType.BTTS:
            return predicted == actual
        elif market == MarketType.EXACT_SCORE:
            return predicted == f"{actual['home']}-{actual['away']}"
        return False
    
    async def recalculate_performance_metrics(self, sport: str, market: str):
        """Recalculate performance metrics for sport/market"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Get recent settled predictions
                query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN accuracy = true THEN 1 ELSE 0 END) as correct,
                    AVG(confidence) as avg_confidence,
                    AVG(expected_value) as avg_ev,
                    AVG(kelly_fraction) as avg_kelly
                FROM predictions 
                WHERE sport = $1 
                  AND market = $2 
                  AND status = 'settled'
                  AND created_at > NOW() - INTERVAL '7 days'
                """
                
                stats = await conn.fetchrow(query, sport, market)
                
                if stats and stats['total'] > 0:
                    accuracy = stats['correct'] / stats['total']
                    
                    # Store performance metric
                    perf_query = """
                    INSERT INTO performance_metrics 
                    (sport, market, time_window, accuracy, sample_size, calculated_at)
                    VALUES ($1, $2, '7d', $3, $4, NOW())
                    """
                    
                    await conn.execute(
                        perf_query,
                        sport,
                        market,
                        accuracy,
                        stats['total']
                    )
                    
                    # Update cache
                    await self.redis_client.setex(
                        f"performance:{sport}:{market}:7d",
                        self.config.CACHE_TTL,
                        json.dumps({
                            'accuracy': accuracy,
                            'sample_size': stats['total'],
                            'avg_confidence': stats['avg_confidence'],
                            'avg_ev': stats['avg_ev'],
                            'updated_at': datetime.now(timezone.utc).isoformat()
                        })
                    )
                    
        except Exception as e:
            logger.error(f"Error recalculating performance metrics: {e}")
    
    async def check_prediction_anomalies(self, prediction: PredictionResult):
        """Check for anomalies in predictions"""
        try:
            sport = prediction.sport.value
            market = prediction.market.value
            key = (sport, market)
            
            if key in self.baselines:
                baseline = self.baselines[key]
                z_score = (prediction.confidence - baseline['accuracy']) / baseline['std_accuracy']
                
                if abs(z_score) > self.config.ANOMALY_THRESHOLD:
                    anomaly = {
                        'anomaly_type': 'prediction_confidence',
                        'detected_value': prediction.confidence,
                        'expected_range': {
                            'lower': baseline['accuracy'] - 2 * baseline['std_accuracy'],
                            'upper': baseline['accuracy'] + 2 * baseline['std_accuracy'],
                            'mean': baseline['accuracy']
                        },
                        'z_score': z_score,
                        'confidence': stats.norm.cdf(-abs(z_score)) * 2,  # Two-tailed p-value
                        'description': f"Prediction confidence anomaly for {sport}/{market}",
                        'metadata': {
                            'prediction_id': prediction.prediction_id,
                            'model_used': prediction.model_used,
                            'expected_value': prediction.expected_value,
                            'features_count': len(prediction.features)
                        }
                    }
                    
                    # Store anomaly
                    await self.store_anomaly(anomaly)
                    
                    # Alert if high confidence anomaly
                    if abs(z_score) > 5.0:
                        await self.send_alert(anomaly)
            
        except Exception as e:
            logger.error(f"Error checking prediction anomalies: {e}")
    
    async def check_system_anomalies(self, metric: SystemMetric):
        """Check for anomalies in system metrics"""
        try:
            metric_key = f"{metric.metric_type.value}_{metric.service}"
            
            # Get rolling statistics for this metric
            window_data = self.rolling_stats[self.config.WINDOW_SIZES[0]][metric_key]
            
            if len(window_data) > 10:  # Need enough data for statistics
                values = list(window_data)
                mean = np.mean(values)
                std = np.std(values)
                
                if std > 0:  # Avoid division by zero
                    z_score = (metric.value - mean) / std
                    
                    if abs(z_score) > self.config.ANOMALY_THRESHOLD:
                        anomaly = {
                            'anomaly_type': 'system_metric',
                            'detected_value': metric.value,
                            'expected_range': {
                                'lower': mean - 2 * std,
                                'upper': mean + 2 * std,
                                'mean': mean
                            },
                            'z_score': z_score,
                            'confidence': stats.norm.cdf(-abs(z_score)) * 2,
                            'description': f"System metric anomaly: {metric.metric_type.value} for {metric.service}",
                            'metadata': {
                                'service': metric.service,
                                'unit': metric.unit,
                                'labels': metric.labels,
                                'timestamp': metric.timestamp.isoformat()
                            }
                        }
                        
                        # Store anomaly
                        await self.store_anomaly(anomaly)
                        
                        # Alert for critical metrics
                        if metric.metric_type in [
                            MetricType.ERROR_RATE,
                            MetricType.KAFKA_LAG,
                            MetricType.DATABASE_LATENCY
                        ]:
                            await self.send_alert(anomaly)
            
        except Exception as e:
            logger.error(f"Error checking system anomalies: {e}")
    
    async def store_anomaly(self, anomaly: Dict[str, Any]):
        """Store anomaly in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO anomaly_detection 
                (anomaly_type, detected_value, expected_range, z_score, 
                 confidence, description, metadata, detected_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                """
                
                await conn.execute(
                    query,
                    anomaly['anomaly_type'],
                    anomaly['detected_value'],
                    json.dumps(anomaly['expected_range']),
                    anomaly['z_score'],
                    anomaly['confidence'],
                    anomaly['description'],
                    json.dumps(anomaly['metadata'])
                )
                
                # Cache recent anomalies
                await self.redis_client.lpush(
                    'recent_anomalies',
                    json.dumps(anomaly)
                )
                await self.redis_client.ltrim('recent_anomalies', 0, 99)
                
        except Exception as e:
            logger.error(f"Error storing anomaly: {e}")
    
    async def send_alert(self, anomaly: Dict[str, Any]):
        """Send alert for critical anomaly"""
        alert_message = {
            'type': 'anomaly_alert',
            'severity': 'high' if abs(anomaly['z_score']) > 5.0 else 'medium',
            'anomaly': anomaly,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system': 'analytics_consumer'
        }
        
        try:
            # Publish to Redis for alert system
            await self.redis_client.publish(
                'alerts:system',
                json.dumps(alert_message)
            )
            
            logger.warning(f"Anomaly alert sent: {anomaly['description']}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def calculate_realtime_metrics(self, sport: str, market: str):
        """Calculate real-time performance metrics"""
        try:
            # Get recent predictions and bets
            predictions = self.performance_by_sport[sport]['predictions'][-1000:]
            bets = self.performance_by_sport[sport]['bets'][-1000:]
            
            if not bets:
                return
            
            # Calculate basic metrics
            total_bets = len(bets)
            winning_bets = sum(1 for b in bets if b['outcome'] == 'win')
            win_rate = winning_bets / total_bets if total_bets > 0 else 0
            
            total_stake = sum(b['stake'] for b in bets)
            total_payout = sum(
                b['stake'] * b['odds'] for b in bets if b['outcome'] == 'win'
            )
            net_profit = sum(b['profit_loss'] for b in bets)
            profit_factor = total_payout / total_stake if total_stake > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            returns = [b['profit_loss'] / b['stake'] if b['stake'] > 0 else 0 
                      for b in bets]
            sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
            
            # Calculate max drawdown
            cumulative_returns = np.cumsum([b['profit_loss'] for b in bets])
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
            
            # Prepare metrics
            metrics = PerformanceMetrics(
                accuracy=0,  # Would need prediction results
                precision=0,
                recall=0,
                f1_score=0,
                roc_auc=None,
                brier_score=0,
                log_loss=0,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=abs(max_drawdown),
                win_rate=win_rate,
                average_odds=np.mean([b['odds'] for b in bets]) if bets else 0,
                ev_per_bet=net_profit / total_bets if total_bets > 0 else 0
            )
            
            # Cache metrics
            cache_key = f"realtime_metrics:{sport}:{market}"
            await self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps({
                    'metrics': metrics.to_dict(),
                    'sample_size': total_bets,
                    'calculated_at': datetime.now(timezone.utc).isoformat(),
                    'time_window': 'realtime'
                })
            )
            
            # Publish to WebSocket for real-time dashboard
            ws_message = {
                'type': 'realtime_metrics',
                'sport': sport,
                'market': market,
                'metrics': metrics.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.publish(
                f'dashboard:{sport}',
                json.dumps(ws_message)
            )
            
        except Exception as e:
            logger.error(f"Error calculating realtime metrics: {e}")
    
    async def update_financial_dashboards(self, bet: BetRecord):
        """Update financial dashboards with new bet"""
        try:
            sport = bet.sport.value
            
            # Update Redis counters
            await self.redis_client.hincrbyfloat(
                f"financial:{sport}:daily",
                'total_stake',
                bet.stake
            )
            
            await self.redis_client.hincrbyfloat(
                f"financial:{sport}:daily",
                'net_profit',
                bet.profit_loss
            )
            
            if bet.outcome == BetOutcome.WIN:
                await self.redis_client.hincrby(
                    f"financial:{sport}:daily",
                    'winning_bets',
                    1
                )
            else:
                await self.redis_client.hincrby(
                    f"financial:{sport}:daily",
                    'losing_bets',
                    1
                )
            
            # Update overall statistics
            await self.redis_client.hincrby(
                'financial:overall',
                'total_bets_today',
                1
            )
            
            # Publish update to dashboard
            dashboard_update = {
                'type': 'financial_update',
                'sport': sport,
                'bet_id': bet.bet_id,
                'outcome': bet.outcome.value,
                'profit_loss': bet.profit_loss,
                'stake': bet.stake,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.publish(
                'dashboard:financial',
                json.dumps(dashboard_update)
            )
            
        except Exception as e:
            logger.error(f"Error updating financial dashboards: {e}")
    
    async def cache_prediction_stats(self, prediction: PredictionResult):
        """Cache prediction statistics for fast access"""
        try:
            sport = prediction.sport.value
            market = prediction.market.value
            
            # Update rolling counts
            await self.redis_client.zadd(
                f"predictions:recent:{sport}",
                {prediction.prediction_id: prediction.timestamp.timestamp()}
            )
            
            # Trim to last 1000 predictions
            await self.redis_client.zremrangebyrank(
                f"predictions:recent:{sport}",
                0,
                -1001
            )
            
            # Update model statistics
            model_key = f"model:stats:{prediction.model_used}"
            await self.redis_client.hincrby(
                model_key,
                'total_predictions',
                1
            )
            
            await self.redis_client.hincrbyfloat(
                model_key,
                'total_confidence',
                prediction.confidence
            )
            
            # Set TTL
            await self.redis_client.expire(model_key, 86400)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error caching prediction stats: {e}")
    
    async def cache_system_metrics(self, metric: SystemMetric):
        """Cache system metrics for Grafana dashboards"""
        try:
            metric_key = f"metrics:{metric.metric_type.value}:{metric.service}"
            
            # Store last value
            await self.redis_client.hset(
                metric_key,
                mapping={
                    'value': str(metric.value),
                    'unit': metric.unit,
                    'timestamp': metric.timestamp.isoformat(),
                    'labels': json.dumps(metric.labels)
                }
            )
            
            # Add to timeseries list (last 100 points)
            ts_key = f"metrics:ts:{metric.metric_type.value}:{metric.service}"
            ts_point = {
                'timestamp': metric.timestamp.timestamp(),
                'value': metric.value
            }
            
            await self.redis_client.lpush(
                ts_key,
                json.dumps(ts_point)
            )
            
            # Trim list
            await self.redis_client.ltrim(ts_key, 0, 99)
            
            # Set TTL
            await self.redis_client.expire(metric_key, 300)  # 5 minutes
            await self.redis_client.expire(ts_key, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error caching system metrics: {e}")
    
    async def store_system_metric(self, metric: SystemMetric):
        """Store system metric in TimescaleDB"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO system_metrics_ts 
                (time, metric_type, service, value, unit, labels)
                VALUES ($1, $2, $3, $4, $5, $6)
                """
                
                await conn.execute(
                    query,
                    metric.timestamp,
                    metric.metric_type.value,
                    metric.service,
                    metric.value,
                    metric.unit,
                    json.dumps(metric.labels)
                )
                
        except Exception as e:
            logger.error(f"Error storing system metric: {e}")
    
    async def store_match_result(self, result: MatchResult):
        """Store match result in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO match_results 
                (match_id, sport, home_score, away_score, result, 
                 match_date, competition, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (match_id) 
                DO UPDATE SET
                    home_score = EXCLUDED.home_score,
                    away_score = EXCLUDED.away_score,
                    result = EXCLUDED.result,
                    updated_at = NOW()
                """
                
                await conn.execute(
                    query,
                    result.match_id,
                    result.sport.value,
                    result.home_score,
                    result.away_score,
                    result.result,
                    result.match_date,
                    result.competition,
                    json.dumps(result.metadata)
                )
                
        except Exception as e:
            logger.error(f"Error storing match result: {e}")
    
    async def update_competition_stats(self, result: MatchResult):
        """Update competition/league statistics"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Update competition stats
                update_query = """
                INSERT INTO competition_stats 
                (competition, sport, total_matches, home_wins, away_wins, draws,
                 avg_home_score, avg_away_score, last_updated)
                VALUES ($1, $2, 1, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (competition, sport) 
                DO UPDATE SET
                    total_matches = competition_stats.total_matches + 1,
                    home_wins = competition_stats.home_wins + EXCLUDED.home_wins,
                    away_wins = competition_stats.away_wins + EXCLUDED.away_wins,
                    draws = competition_stats.draws + EXCLUDED.draws,
                    avg_home_score = (competition_stats.avg_home_score * competition_stats.total_matches + EXCLUDED.avg_home_score) / 
                                     (competition_stats.total_matches + 1),
                    avg_away_score = (competition_stats.avg_away_score * competition_stats.total_matches + EXCLUDED.avg_away_score) / 
                                     (competition_stats.total_matches + 1),
                    last_updated = NOW()
                """
                
                home_win = 1 if result.result == 'home_win' else 0
                away_win = 1 if result.result == 'away_win' else 0
                draw = 1 if result.result == 'draw' else 0
                
                await conn.execute(
                    update_query,
                    result.competition,
                    result.sport.value,
                    home_win,
                    away_win,
                    draw,
                    result.home_score,
                    result.away_score
                )
                
        except Exception as e:
            logger.error(f"Error updating competition stats: {e}")
    
    async def periodic_aggregation(self):
        """Periodic aggregation task"""
        while self.running:
            try:
                await asyncio.sleep(self.config.PROCESSING_INTERVAL)
                
                # Calculate and store aggregations
                await self.calculate_aggregations()
                
                # Update performance metrics
                await self.update_all_performance_metrics()
                
                # Clean old data from memory
                await self.cleanup_old_data()
                
                # Log statistics
                if self.processed_counts['predictions'] % 1000 == 0:
                    logger.info(
                        f"Processed: Predictions={self.processed_counts['predictions']}, "
                        f"Bets={self.processed_counts['bets']}, "
                        f"Results={self.processed_counts['results']}, "
                        f"Metrics={self.processed_counts['metrics']}"
                    )
                
            except Exception as e:
                logger.error(f"Error in periodic aggregation: {e}")
    
    async def calculate_aggregations(self):
        """Calculate aggregations from rolling statistics"""
        try:
            for window_size, stats in self.rolling_stats.items():
                for key, values in stats.items():
                    if len(values) > 0:
                        # Calculate statistics
                        values_list = list(values)
                        
                        aggregation = {
                            'stat_type': key,
                            'window_size': window_size,
                            'mean_value': float(np.mean(values_list)),
                            'std_dev': float(np.std(values_list)),
                            'min_value': float(np.min(values_list)),
                            'max_value': float(np.max(values_list)),
                            'p25': float(np.percentile(values_list, 25)),
                            'p50': float(np.percentile(values_list, 50)),
                            'p75': float(np.percentile(values_list, 75)),
                            'p90': float(np.percentile(values_list, 90)),
                            'p95': float(np.percentile(values_list, 95)),
                            'count': len(values_list),
                            'start_time': datetime.now(timezone.utc) - timedelta(seconds=window_size),
                            'end_time': datetime.now(timezone.utc),
                            'calculated_at': datetime.now(timezone.utc)
                        }
                        
                        # Store in database
                        await self.store_aggregation(aggregation)
                        
                        # Cache for fast access
                        await self.cache_aggregation(aggregation)
                        
        except Exception as e:
            logger.error(f"Error calculating aggregations: {e}")
    
    async def store_aggregation(self, aggregation: Dict[str, Any]):
        """Store aggregation in database"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO rolling_statistics 
                (stat_type, window_size, mean_value, std_dev, min_value, max_value,
                 p25, p50, p75, p90, p95, count, start_time, end_time, calculated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                """
                
                await conn.execute(
                    query,
                    aggregation['stat_type'],
                    aggregation['window_size'],
                    aggregation['mean_value'],
                    aggregation['std_dev'],
                    aggregation['min_value'],
                    aggregation['max_value'],
                    aggregation['p25'],
                    aggregation['p50'],
                    aggregation['p75'],
                    aggregation['p90'],
                    aggregation['p95'],
                    aggregation['count'],
                    aggregation['start_time'],
                    aggregation['end_time'],
                    aggregation['calculated_at']
                )
                
        except Exception as e:
            logger.error(f"Error storing aggregation: {e}")
    
    async def cache_aggregation(self, aggregation: Dict[str, Any]):
        """Cache aggregation in Redis"""
        try:
            cache_key = f"aggregation:{aggregation['stat_type']}:{aggregation['window_size']}"
            
            await self.redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(aggregation)
            )
            
        except Exception as e:
            logger.error(f"Error caching aggregation: {e}")
    
    async def update_all_performance_metrics(self):
        """Update performance metrics for all sports and markets"""
        try:
            for sport in self.performance_by_sport.keys():
                # Get unique markets for this sport
                markets = set(
                    p['market'] 
                    for p in self.performance_by_sport[sport]['predictions'][-1000:]
                )
                
                for market in markets:
                    await self.recalculate_performance_metrics(sport, market)
                    
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def cleanup_old_data(self):
        """Cleanup old data from memory structures"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for sport in list(self.performance_by_sport.keys()):
                # Clean old predictions
                self.performance_by_sport[sport]['predictions'] = [
                    p for p in self.performance_by_sport[sport]['predictions']
                    if p['timestamp'] > cutoff_time
                ]
                
                # Clean old bets
                self.performance_by_sport[sport]['bets'] = [
                    b for b in self.performance_by_sport[sport]['bets']
                    if b['timestamp'] > cutoff_time
                ]
                
                # Clean old results
                self.performance_by_sport[sport]['results'] = [
                    r for r in self.performance_by_sport[sport]['results']
                    if r['timestamp'] > cutoff_time
                ]
                
        except Exception as e:
            logger.error(f"Error cleaning old data: {e}")
    
    async def store_invalid_message(self, topic: str, message: aiokafka.ConsumerRecord, error: str):
        """Store invalid message for analysis"""
        try:
            async with self.pg_pool.acquire() as conn:
                query = """
                INSERT INTO invalid_messages 
                (topic, partition, offset, raw_message, error, received_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                """
                
                await conn.execute(
                    query,
                    topic,
                    message.partition,
                    message.offset,
                    message.value.decode('utf-8')[:10000],  # Truncate if too long
                    error
                )
                
        except Exception as e:
            logger.error(f"Error storing invalid message: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Return health check status"""
        health = {
            'status': 'healthy',
            'running': self.running,
            'processed_counts': self.processed_counts,
            'error_counts': self.error_counts,
            'performance_by_sport': {
                sport: {
                    'predictions': len(data['predictions']),
                    'bets': len(data['bets']),
                    'results': len(data['results'])
                }
                for sport, data in self.performance_by_sport.items()
            },
            'connections': {
                'kafka': 'connected' if self.kafka_consumer else 'disconnected',
                'postgresql': 'connected' if self.pg_pool else 'disconnected',
                'redis': 'connected' if self.redis_client else 'disconnected'
            }
        }
        
        # Check connections
        try:
            await self.kafka_consumer._client.check_version()
        except:
            health['connections']['kafka'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        try:
            async with self.pg_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
        except:
            health['connections']['postgresql'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        try:
            await self.redis_client.ping()
        except:
            health['connections']['redis'] = 'disconnected'
            health['status'] = 'unhealthy'
        
        return health
    
    async def stop(self):
        """Stop the consumer gracefully"""
        logger.info("Stopping AnalyticsConsumer...")
        self.running = False
        
        # Wait for processing to complete
        await asyncio.sleep(2)
        
        if self.kafka_consumer:
            await self.kafka_consumer.stop()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("AnalyticsConsumer stopped")

async def main():
    """Main entry point"""
    logger.info("Starting GOAT Analytics Consumer...")
    
    config = AnalyticsConfig()
    consumer = AnalyticsConsumer(config)
    
    try:
        # Initialize
        if not await consumer.initialize():
            logger.error("Failed to initialize analytics consumer")
            return
        
        # Start consuming
        await consumer.consume_analytics()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        await consumer.stop()
        logger.info("Analytics consumer shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
