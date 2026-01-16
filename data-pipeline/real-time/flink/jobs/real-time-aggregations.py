#!/usr/bin/env python3
"""
Real-time Aggregations Job for Goat Prediction
Apache Flink Streaming Job for Real-time Sports Prediction Aggregations
Processing Pipeline: Kafka -> Flink -> TimescaleDB/Redis
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict, field
from decimal import Decimal
import math

from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.connectors.kafka import (
    KafkaSource, 
    KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
    KafkaSink
)
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.common import WatermarkStrategy, Duration, Time
from pyflink.common.typeinfo import Types
from pyflink.datastream.window import (
    TumblingEventTimeWindows,
    SlidingEventTimeWindows,
    GlobalWindows,
    TimeWindow,
    CountWindow
)
from pyflink.datastream.functions import (
    ProcessWindowFunction,
    KeyedProcessFunction,
    MapFunction,
    FilterFunction,
    AggregateFunction,
    ProcessAllWindowFunction,
    WindowFunction
)
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream.state import (
    ValueStateDescriptor,
    ListStateDescriptor,
    MapStateDescriptor,
    ReducingStateDescriptor,
    StateTtlConfig
)
from pyflink.datastream.connectors.jdbc import (
    JdbcSink,
    JdbcConnectionOptions,
    JdbcExecutionOptions
)

# Third-party imports
import numpy as np
import pandas as pd
from scipy import stats
import redis
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import confluent_kafka
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configuration
@dataclass
class FlinkConfig:
    """Flink job configuration"""
    # Kafka Configuration
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_predictions_topic: str = "predictions-raw"
    kafka_odds_topic: str = "odds-raw"
    kafka_betting_events_topic: str = "betting-events-raw"
    kafka_aggregated_topic: str = "predictions-aggregated"
    kafka_anomalies_topic: str = "anomalies-detected"
    
    # Database Configuration
    timescaledb_host: str = "timescaledb:5432"
    timescaledb_database: str = "goat_prediction"
    timescaledb_user: str = "prediction_service"
    timescaledb_password: str = os.getenv("TIMESCALEDB_PASSWORD", "")
    
    redis_host: str = "redis:6379"
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = 0
    
    # Processing Configuration
    window_size_minutes: int = 5  # Aggregation window size
    sliding_window_minutes: int = 1  # Sliding window step
    watermark_delay_seconds: int = 30  # Watermark delay for late data
    checkpoint_interval_ms: int = 30000  # Checkpoint interval
    parallelism: int = 8  # Number of parallel instances
    
    # Aggregation Configuration
    min_predictions_per_window: int = 10
    confidence_threshold: float = 0.7
    value_bet_threshold: float = 0.05
    
    # Alert Configuration
    anomaly_z_score_threshold: float = 3.0
    confidence_drop_threshold: float = 0.2
    volume_spike_threshold: float = 2.0
    
    # Monitoring
    prometheus_port: int = 9091
    metrics_prefix: str = "flink_aggregations_"

# Prometheus Metrics
class AggregationMetrics:
    """Metrics for tracking aggregation performance"""
    
    def __init__(self, prefix: str = "flink_aggregations_"):
        self.prefix = prefix
        
        # Counters
        self.predictions_processed = Counter(
            f'{prefix}predictions_processed_total',
            'Total predictions processed'
        )
        self.aggregations_completed = Counter(
            f'{prefix}aggregations_completed_total',
            'Total aggregations completed'
        )
        self.value_bets_detected = Counter(
            f'{prefix}value_bets_detected_total',
            'Total value bets detected'
        )
        self.anomalies_detected = Counter(
            f'{prefix}anomalies_detected_total',
            'Total anomalies detected'
        )
        self.errors = Counter(
            f'{prefix}errors_total',
            'Total processing errors'
        )
        
        # Gauges
        self.processing_lag = Gauge(
            f'{prefix}processing_lag_seconds',
            'Current processing lag in seconds'
        )
        self.window_size = Gauge(
            f'{prefix}window_size',
            'Current aggregation window size'
        )
        self.active_windows = Gauge(
            f'{prefix}active_windows',
            'Number of active aggregation windows'
        )
        
        # Histograms
        self.processing_time = Histogram(
            f'{prefix}processing_time_seconds',
            'Time spent processing predictions',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        self.window_processing_time = Histogram(
            f'{prefix}window_processing_time_seconds',
            'Time spent processing windows',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        self.prediction_latency = Histogram(
            f'{prefix}prediction_latency_seconds',
            'Prediction processing latency',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )

# Data Models
@dataclass
class PredictionEvent:
    """Prediction event from Kafka"""
    prediction_id: str
    prediction_time: int  # Unix timestamp in milliseconds
    match_id: str
    sport_id: int
    league_id: int
    market_type: str
    model_id: str
    probability: float
    confidence: float
    odds: float
    fair_odds: float
    expected_value: float
    bookmaker_id: int
    bookmaker_name: str
    odds_timestamp: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    match_start_time: int
    kelly_fraction: Optional[float] = None
    risk_score: Optional[float] = None
    is_value_bet: Optional[bool] = None
    feature_importance: Optional[Dict] = None
    shap_values: Optional[Dict] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    is_test_prediction: bool = False
    is_live_bet: bool = False
    metadata: Optional[Dict] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PredictionEvent':
        """Create PredictionEvent from dictionary"""
        return cls(**data)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

@dataclass
class OddsEvent:
    """Odds event from Kafka"""
    event_id: str
    timestamp: int
    match_id: str
    bookmaker_id: int
    market_type: str
    selection_type: str
    odds: float
    odds_decimal: float
    odds_american: Optional[int] = None
    odds_fractional: Optional[str] = None
    probability: Optional[float] = None
    fair_probability: Optional[float] = None
    market_depth: Optional[float] = None
    volume: Optional[float] = None
    is_live: bool = False
    metadata: Optional[Dict] = None

@dataclass
class AggregatedPrediction:
    """Aggregated prediction metrics for a window"""
    window_start: int
    window_end: int
    sport_id: int
    league_id: int
    market_type: str
    model_id: Optional[str] = None
    
    # Count metrics
    prediction_count: int = 0
    unique_matches: int = 0
    unique_models: int = 0
    active_users: int = 0
    
    # Confidence metrics
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0
    confidence_stddev: float = 0.0
    confidence_p25: float = 0.0
    confidence_median: float = 0.0
    confidence_p75: float = 0.0
    
    # Confidence distribution
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    very_low_confidence_count: int = 0
    
    # Expected Value metrics
    avg_expected_value: float = 0.0
    min_expected_value: float = 0.0
    max_expected_value: float = 0.0
    high_value_predictions: int = 0
    medium_value_predictions: int = 0
    negative_value_predictions: int = 0
    
    # Kelly metrics
    avg_kelly_fraction: float = 0.0
    min_kelly_fraction: float = 0.0
    max_kelly_fraction: float = 0.0
    aggressive_bets: int = 0
    moderate_bets: int = 0
    conservative_bets: int = 0
    no_bet_recommendations: int = 0
    
    # Odds metrics
    avg_odds: float = 0.0
    min_odds: float = 0.0
    max_odds: float = 0.0
    avg_fair_odds: float = 0.0
    avg_value_gap: float = 0.0
    high_value_opportunities: int = 0
    
    # Stake metrics
    avg_stake: float = 0.0
    total_stake_volume: float = 0.0
    stake_p95: float = 0.0
    stake_p99: float = 0.0
    
    # Outcome metrics (if available)
    win_count: int = 0
    loss_count: int = 0
    push_count: int = 0
    pending_count: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_win_return: float = 0.0
    
    # Accuracy metrics
    avg_prediction_accuracy: float = 0.0
    accurate_predictions: int = 0
    
    # Timing metrics
    avg_hours_before_match: float = 0.0
    min_hours_before_match: float = 0.0
    max_hours_before_match: float = 0.0
    
    # Performance metrics
    win_rate: Optional[float] = None
    roi_percentage: Optional[float] = None
    sharpe_ratio_approx: Optional[float] = None
    
    # Hit rates
    hit_rate_high_confidence: Optional[float] = None
    hit_rate_medium_plus_confidence: Optional[float] = None
    
    # Value metrics
    avg_probability: float = 0.0
    value_bets_identified: int = 0
    
    # Risk metrics
    avg_risk_score: float = 0.0
    high_risk_predictions: int = 0
    
    # Model metrics
    model_versions_used: int = 0
    
    # Temporal analysis
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    month_of_year: Optional[int] = None
    
    # Statistical significance
    is_statistically_significant: bool = False
    standard_error: float = 0.0
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 0.0
    
    # Anomaly detection
    z_score: Optional[float] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None
    
    # Processing metadata
    processed_at: int = field(default_factory=lambda: int(datetime.utcnow().timestamp() * 1000))
    processing_latency_ms: int = 0
    aggregation_version: str = "1.0.0"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AggregatedPrediction':
        """Create from dictionary"""
        return cls(**data)

# Custom Timestamp Assigner
class PredictionTimestampAssigner(TimestampAssigner):
    """Assign timestamps for prediction events"""
    
    def extract_timestamp(self, value: PredictionEvent, record_timestamp: int) -> int:
        """Extract timestamp from prediction event"""
        return value.prediction_time

# Custom Serializers
class PredictionEventDeserializer(JsonRowDeserializationSchema):
    """Deserialize PredictionEvent from JSON"""
    
    def __init__(self):
        super().__init__(
            type_info=Types.ROW([
                ("prediction_id", Types.STRING()),
                ("prediction_time", Types.BIG_INT()),
                ("match_id", Types.STRING()),
                ("sport_id", Types.INT()),
                ("league_id", Types.INT()),
                ("market_type", Types.STRING()),
                ("model_id", Types.STRING()),
                ("probability", Types.DOUBLE()),
                ("confidence", Types.DOUBLE()),
                ("odds", Types.DOUBLE()),
                ("fair_odds", Types.DOUBLE()),
                ("expected_value", Types.DOUBLE()),
                ("bookmaker_id", Types.INT()),
                ("bookmaker_name", Types.STRING()),
                ("odds_timestamp", Types.BIG_INT()),
                ("home_team_id", Types.INT()),
                ("away_team_id", Types.INT()),
                ("home_team_name", Types.STRING()),
                ("away_team_name", Types.STRING()),
                ("match_start_time", Types.BIG_INT()),
                ("kelly_fraction", Types.DOUBLE()),
                ("risk_score", Types.DOUBLE()),
                ("is_value_bet", Types.BOOLEAN()),
                ("feature_importance", Types.MAP(Types.STRING(), Types.DOUBLE())),
                ("shap_values", Types.MAP(Types.STRING(), Types.DOUBLE())),
                ("user_id", Types.STRING()),
                ("session_id", Types.STRING()),
                ("is_test_prediction", Types.BOOLEAN()),
                ("is_live_bet", Types.BOOLEAN()),
                ("metadata", Types.MAP(Types.STRING(), Types.STRING()))
            ])
        )

class AggregatedPredictionSerializer:
    """Serialize AggregatedPrediction to JSON"""
    
    def serialize(self, aggregated: AggregatedPrediction) -> bytes:
        """Serialize to JSON bytes"""
        return json.dumps(aggregated.to_dict()).encode('utf-8')

# Aggregation Functions
class PredictionAggregator(AggregateFunction):
    """Aggregate predictions within a window"""
    
    def create_accumulator(self) -> Dict:
        """Create initial accumulator"""
        return {
            'predictions': [],
            'confidences': [],
            'expected_values': [],
            'odds_list': [],
            'fair_odds_list': [],
            'kelly_fractions': [],
            'stakes': [],
            'match_ids': set(),
            'model_ids': set(),
            'user_ids': set(),
            'window_metrics': {
                'total_stake': 0.0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'win_count': 0,
                'loss_count': 0,
                'push_count': 0,
                'pending_count': 0,
                'high_confidence_count': 0,
                'medium_confidence_count': 0,
                'low_confidence_count': 0,
                'very_low_confidence_count': 0,
                'high_value_predictions': 0,
                'medium_value_predictions': 0,
                'negative_value_predictions': 0,
                'aggressive_bets': 0,
                'moderate_bets': 0,
                'conservative_bets': 0,
                'no_bet_recommendations': 0,
                'high_value_opportunities': 0,
                'accurate_predictions': 0,
                'high_risk_predictions': 0,
                'value_bets_identified': 0,
                'hours_before_match': []
            }
        }
    
    def add(self, accumulator: Dict, value: PredictionEvent) -> Dict:
        """Add prediction to accumulator"""
        accumulator['predictions'].append(value)
        accumulator['confidences'].append(value.confidence)
        accumulator['expected_values'].append(value.expected_value)
        accumulator['odds_list'].append(value.odds)
        accumulator['fair_odds_list'].append(value.fair_odds)
        
        if value.kelly_fraction is not None:
            accumulator['kelly_fractions'].append(value.kelly_fraction)
        
        # Track unique values
        accumulator['match_ids'].add(value.match_id)
        accumulator['model_ids'].add(value.model_id)
        if value.user_id:
            accumulator['user_ids'].add(value.user_id)
        
        # Update metrics
        metrics = accumulator['window_metrics']
        
        # Confidence distribution
        if value.confidence >= 0.8:
            metrics['high_confidence_count'] += 1
        elif value.confidence >= 0.6:
            metrics['medium_confidence_count'] += 1
        elif value.confidence >= 0.4:
            metrics['low_confidence_count'] += 1
        else:
            metrics['very_low_confidence_count'] += 1
        
        # Expected value distribution
        if value.expected_value > 0.05:
            metrics['high_value_predictions'] += 1
        elif value.expected_value > 0:
            metrics['medium_value_predictions'] += 1
        else:
            metrics['negative_value_predictions'] += 1
        
        # Kelly fraction distribution
        if value.kelly_fraction is not None:
            if value.kelly_fraction > 0.1:
                metrics['aggressive_bets'] += 1
            elif value.kelly_fraction > 0.05:
                metrics['moderate_bets'] += 1
            elif value.kelly_fraction > 0:
                metrics['conservative_bets'] += 1
            else:
                metrics['no_bet_recommendations'] += 1
        
        # Value opportunities
        if value.odds > value.fair_odds * 1.1:
            metrics['high_value_opportunities'] += 1
        
        # Risk assessment
        if value.risk_score is not None and value.risk_score > 0.7:
            metrics['high_risk_predictions'] += 1
        
        # Value bets
        if value.is_value_bet:
            metrics['value_bets_identified'] += 1
        
        # Timing
        hours_before = (value.match_start_time - value.prediction_time) / (1000 * 60 * 60)
        metrics['hours_before_match'].append(hours_before)
        
        return accumulator
    
    def get_result(self, accumulator: Dict) -> Dict:
        """Get aggregation result"""
        predictions = accumulator['predictions']
        if not predictions:
            return None
        
        # Get first prediction for metadata
        first_pred = predictions[0]
        
        # Calculate statistics
        confidences = accumulator['confidences']
        expected_values = accumulator['expected_values']
        odds_list = accumulator['odds_list']
        fair_odds_list = accumulator['fair_odds_list']
        kelly_fractions = accumulator['kelly_fractions']
        hours_before_match = accumulator['window_metrics']['hours_before_match']
        
        # Basic statistics
        import numpy as np
        conf_array = np.array(confidences)
        ev_array = np.array(expected_values)
        odds_array = np.array(odds_list)
        fair_odds_array = np.array(fair_odds_list)
        
        # Calculate percentiles
        conf_p25 = np.percentile(conf_array, 25) if len(conf_array) > 0 else 0.0
        conf_median = np.percentile(conf_array, 50) if len(conf_array) > 0 else 0.0
        conf_p75 = np.percentile(conf_array, 75) if len(conf_array) > 0 else 0.0
        
        kelly_avg = np.mean(kelly_fractions) if kelly_fractions else 0.0
        kelly_min = np.min(kelly_fractions) if kelly_fractions else 0.0
        kelly_max = np.max(kelly_fractions) if kelly_fractions else 0.0
        
        hours_avg = np.mean(hours_before_match) if hours_before_match else 0.0
        hours_min = np.min(hours_before_match) if hours_before_match else 0.0
        hours_max = np.max(hours_before_match) if hours_before_match else 0.0
        
        # Value gap
        value_gaps = odds_array - fair_odds_array
        avg_value_gap = np.mean(value_gaps) if len(value_gaps) > 0 else 0.0
        
        # Calculate win rate if outcomes available
        win_rate = None
        roi_percentage = None
        sharpe_ratio = None
        hit_rate_high = None
        hit_rate_medium = None
        
        metrics = accumulator['window_metrics']
        
        # Prepare result
        result = {
            'predictions': predictions,
            'confidences': confidences,
            'expected_values': expected_values,
            'kelly_fractions': kelly_fractions,
            'metrics': metrics,
            'stats': {
                'avg_confidence': float(np.mean(conf_array)),
                'min_confidence': float(np.min(conf_array)),
                'max_confidence': float(np.max(conf_array)),
                'confidence_stddev': float(np.std(conf_array)) if len(conf_array) > 1 else 0.0,
                'confidence_p25': float(conf_p25),
                'confidence_median': float(conf_median),
                'confidence_p75': float(conf_p75),
                'avg_expected_value': float(np.mean(ev_array)),
                'min_expected_value': float(np.min(ev_array)),
                'max_expected_value': float(np.max(ev_array)),
                'avg_odds': float(np.mean(odds_array)),
                'min_odds': float(np.min(odds_array)),
                'max_odds': float(np.max(odds_array)),
                'avg_fair_odds': float(np.mean(fair_odds_array)),
                'avg_value_gap': float(avg_value_gap),
                'avg_kelly_fraction': float(kelly_avg),
                'min_kelly_fraction': float(kelly_min),
                'max_kelly_fraction': float(kelly_max),
                'avg_hours_before_match': float(hours_avg),
                'min_hours_before_match': float(hours_min),
                'max_hours_before_match': float(hours_max),
                'unique_matches': len(accumulator['match_ids']),
                'unique_models': len(accumulator['model_ids']),
                'active_users': len(accumulator['user_ids']),
                'prediction_count': len(predictions),
                'win_rate': win_rate,
                'roi_percentage': roi_percentage,
                'sharpe_ratio': sharpe_ratio,
                'hit_rate_high_confidence': hit_rate_high,
                'hit_rate_medium_plus_confidence': hit_rate_medium
            },
            'metadata': {
                'sport_id': first_pred.sport_id,
                'league_id': first_pred.league_id,
                'market_type': first_pred.market_type,
                'model_id': first_pred.model_id,
                'hour_of_day': datetime.fromtimestamp(first_pred.prediction_time / 1000).hour,
                'day_of_week': datetime.fromtimestamp(first_pred.prediction_time / 1000).weekday(),
                'month_of_year': datetime.fromtimestamp(first_pred.prediction_time / 1000).month
            }
        }
        
        return result
    
    def merge(self, accumulator: Dict, accumulator1: Dict) -> Dict:
        """Merge two accumulators"""
        # Merge predictions
        accumulator['predictions'].extend(accumulator1['predictions'])
        accumulator['confidences'].extend(accumulator1['confidences'])
        accumulator['expected_values'].extend(accumulator1['expected_values'])
        accumulator['odds_list'].extend(accumulator1['odds_list'])
        accumulator['fair_odds_list'].extend(accumulator1['fair_odds_list'])
        accumulator['kelly_fractions'].extend(accumulator1['kelly_fractions'])
        
        # Merge unique sets
        accumulator['match_ids'].update(accumulator1['match_ids'])
        accumulator['model_ids'].update(accumulator1['model_ids'])
        accumulator['user_ids'].update(accumulator1['user_ids'])
        
        # Merge metrics
        for key in accumulator['window_metrics']:
            if key == 'hours_before_match':
                accumulator['window_metrics'][key].extend(accumulator1['window_metrics'][key])
            else:
                accumulator['window_metrics'][key] += accumulator1['window_metrics'][key]
        
        return accumulator

class WindowAggregationFunction(ProcessWindowFunction):
    """Process window and create aggregated prediction"""
    
    def __init__(self, config: FlinkConfig, metrics: AggregationMetrics):
        self.config = config
        self.metrics = metrics
    
    def process(self, key: Tuple, context: ProcessWindowFunction.Context, 
                elements: Iterable[Dict]) -> Iterable[AggregatedPrediction]:
        """Process window elements"""
        start_time = datetime.utcnow()
        
        try:
            # Get window info
            window = context.window()
            window_start = int(window.start)
            window_end = int(window.end)
            
            # Get aggregation result
            aggregation_result = list(elements)[0]  # Should have one element from aggregator
            if not aggregation_result:
                return
            
            predictions = aggregation_result['predictions']
            stats = aggregation_result['stats']
            metrics = aggregation_result['metrics']
            metadata = aggregation_result['metadata']
            
            # Skip if not enough predictions
            if len(predictions) < self.config.min_predictions_per_window:
                return
            
            # Create aggregated prediction
            aggregated = AggregatedPrediction(
                window_start=window_start,
                window_end=window_end,
                sport_id=metadata['sport_id'],
                league_id=metadata['league_id'],
                market_type=metadata['market_type'],
                model_id=metadata['model_id'],
                
                # Count metrics
                prediction_count=stats['prediction_count'],
                unique_matches=stats['unique_matches'],
                unique_models=stats['unique_models'],
                active_users=stats['active_users'],
                
                # Confidence metrics
                avg_confidence=stats['avg_confidence'],
                min_confidence=stats['min_confidence'],
                max_confidence=stats['max_confidence'],
                confidence_stddev=stats['confidence_stddev'],
                confidence_p25=stats['confidence_p25'],
                confidence_median=stats['confidence_median'],
                confidence_p75=stats['confidence_p75'],
                
                # Confidence distribution
                high_confidence_count=metrics['high_confidence_count'],
                medium_confidence_count=metrics['medium_confidence_count'],
                low_confidence_count=metrics['low_confidence_count'],
                very_low_confidence_count=metrics['very_low_confidence_count'],
                
                # Expected Value metrics
                avg_expected_value=stats['avg_expected_value'],
                min_expected_value=stats['min_expected_value'],
                max_expected_value=stats['max_expected_value'],
                high_value_predictions=metrics['high_value_predictions'],
                medium_value_predictions=metrics['medium_value_predictions'],
                negative_value_predictions=metrics['negative_value_predictions'],
                
                # Kelly metrics
                avg_kelly_fraction=stats['avg_kelly_fraction'],
                min_kelly_fraction=stats['min_kelly_fraction'],
                max_kelly_fraction=stats['max_kelly_fraction'],
                aggressive_bets=metrics['aggressive_bets'],
                moderate_bets=metrics['moderate_bets'],
                conservative_bets=metrics['conservative_bets'],
                no_bet_recommendations=metrics['no_bet_recommendations'],
                
                # Odds metrics
                avg_odds=stats['avg_odds'],
                min_odds=stats['min_odds'],
                max_odds=stats['max_odds'],
                avg_fair_odds=stats['avg_fair_odds'],
                avg_value_gap=stats['avg_value_gap'],
                high_value_opportunities=metrics['high_value_opportunities'],
                
                # Timing metrics
                avg_hours_before_match=stats['avg_hours_before_match'],
                min_hours_before_match=stats['min_hours_before_match'],
                max_hours_before_match=stats['max_hours_before_match'],
                
                # Performance metrics
                win_rate=stats['win_rate'],
                roi_percentage=stats['roi_percentage'],
                sharpe_ratio_approx=stats['sharpe_ratio'],
                
                # Hit rates
                hit_rate_high_confidence=stats['hit_rate_high_confidence'],
                hit_rate_medium_plus_confidence=stats['hit_rate_medium_plus_confidence'],
                
                # Temporal analysis
                hour_of_day=metadata['hour_of_day'],
                day_of_week=metadata['day_of_week'],
                month_of_year=metadata['month_of_year']
            )
            
            # Calculate statistical significance
            self._calculate_statistical_significance(aggregated, predictions)
            
            # Detect anomalies
            self._detect_anomalies(aggregated, context)
            
            # Update metrics
            self.metrics.aggregations_completed.inc()
            self.metrics.value_bets_detected.inc(aggregated.value_bets_identified)
            if aggregated.is_anomaly:
                self.metrics.anomalies_detected.inc()
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            aggregated.processing_latency_ms = int(processing_time * 1000)
            
            self.metrics.window_processing_time.observe(processing_time)
            
            yield aggregated
            
        except Exception as e:
            self.metrics.errors.inc()
            logging.error(f"Error processing window: {e}")
            raise
    
    def _calculate_statistical_significance(self, aggregated: AggregatedPrediction, 
                                           predictions: List[PredictionEvent]):
        """Calculate statistical significance metrics"""
        if aggregated.prediction_count < 30:  # Too few for meaningful stats
            aggregated.is_statistically_significant = False
            return
        
        # Calculate standard error for confidence
        if aggregated.confidence_stddev > 0:
            se = aggregated.confidence_stddev / math.sqrt(aggregated.prediction_count)
            aggregated.standard_error = se
            
            # 95% confidence interval
            z_score = 1.96  # For 95% confidence
            aggregated.confidence_interval_lower = aggregated.avg_confidence - z_score * se
            aggregated.confidence_interval_upper = aggregated.avg_confidence + z_score * se
            
            # Check if confidence is significantly different from 0.5
            if aggregated.avg_confidence > 0.5:
                test_statistic = (aggregated.avg_confidence - 0.5) / se
                # One-tailed test
                aggregated.is_statistically_significant = test_statistic > 1.645  # 95% confidence
    
    def _detect_anomalies(self, aggregated: AggregatedPrediction, context: ProcessWindowFunction.Context):
        """Detect anomalies in aggregated data"""
        anomalies = []
        
        # Check for low confidence
        if aggregated.avg_confidence < self.config.confidence_threshold * 0.7:
            anomalies.append("Low average confidence")
            aggregated.is_anomaly = True
        
        # Check for high volatility in confidence
        if aggregated.confidence_stddev > 0.3:
            anomalies.append("High confidence volatility")
            aggregated.is_anomaly = True
        
        # Check for negative expected value
        if aggregated.avg_expected_value < -0.1:
            anomalies.append("Negative expected value")
            aggregated.is_anomaly = True
        
        # Update anomaly reason
        if anomalies:
            aggregated.anomaly_reason = "; ".join(anomalies)

# Anomaly Detection Function
class AnomalyDetector(KeyedProcessFunction):
    """Detect anomalies in real-time prediction stream"""
    
    def __init__(self, config: FlinkConfig, metrics: AggregationMetrics):
        self.config = config
        self.metrics = metrics
        self.confidence_state = None
        self.volume_state = None
    
    def open(self, runtime_context):
        """Initialize state"""
        # State TTL configuration
        ttl_config = StateTtlConfig \
            .new_builder(Duration.hours(24)) \
            .set_update_type(StateTtlConfig.UpdateType.OnCreateAndWrite) \
            .set_state_visibility(StateTtlConfig.StateVisibility.NeverReturnExpired) \
            .build()
        
        # Confidence history state (last 24 hours)
        confidence_desc = ListStateDescriptor(
            "confidence_history",
            Types.DOUBLE()
        ).enable_time_to_live(ttl_config)
        
        # Volume history state
        volume_desc = ListStateDescriptor(
            "volume_history",
            Types.LONG()
        ).enable_time_to_live(ttl_config)
        
        self.confidence_state = runtime_context.get_list_state(confidence_desc)
        self.volume_state = runtime_context.get_list_state(volume_desc)
    
    def process_element(self, value: PredictionEvent, ctx: KeyedProcessFunction.Context):
        """Process each prediction for anomaly detection"""
        try:
            # Update state
            current_time = ctx.timestamp()
            
            # Clean old state
            self._clean_old_state(current_time)
            
            # Update confidence history
            confidence_history = list(self.confidence_state.get())
            confidence_history.append(value.confidence)
            if len(confidence_history) > 1000:  # Keep last 1000 values
                confidence_history = confidence_history[-1000:]
            self.confidence_state.update(confidence_history)
            
            # Detect anomalies
            anomalies = self._check_anomalies(value, confidence_history)
            
            # Emit anomaly if detected
            if anomalies:
                anomaly_event = {
                    'timestamp': current_time,
                    'prediction_id': value.prediction_id,
                    'sport_id': value.sport_id,
                    'league_id': value.league_id,
                    'anomalies': anomalies,
                    'confidence': value.confidence,
                    'expected_value': value.expected_value,
                    'prediction_data': value.to_dict()
                }
                
                self.metrics.anomalies_detected.inc()
                
                # Output anomaly
                yield json.dumps(anomaly_event).encode('utf-8')
            
        except Exception as e:
            self.metrics.errors.inc()
            logging.error(f"Error in anomaly detection: {e}")
    
    def _clean_old_state(self, current_time: int):
        """Clean state older than 24 hours"""
        # State TTL handles this automatically
        pass
    
    def _check_anomalies(self, prediction: PredictionEvent, confidence_history: List[float]) -> List[str]:
        """Check for various anomalies"""
        anomalies = []
        
        if len(confidence_history) < 100:  # Need sufficient history
            return anomalies
        
        # Calculate statistics
        import numpy as np
        history_array = np.array(confidence_history[-100:])  # Last 100 values
        mean_conf = np.mean(history_array)
        std_conf = np.std(history_array)
        
        # Check for confidence anomaly (z-score)
        if std_conf > 0:
            z_score = (prediction.confidence - mean_conf) / std_conf
            if abs(z_score) > self.config.anomaly_z_score_threshold:
                anomalies.append(f"Confidence z-score anomaly: {z_score:.2f}")
        
        # Check for sudden confidence drop
        if len(confidence_history) >= 10:
            recent_mean = np.mean(history_array[-10:])
            if recent_mean < mean_conf - self.config.confidence_drop_threshold:
                anomalies.append("Sudden confidence drop")
        
        # Check for extreme odds
        if prediction.odds > 20.0 and prediction.confidence > 0.8:
            anomalies.append("Extreme odds with high confidence")
        
        # Check for suspicious probability
        if 0.49 <= prediction.probability <= 0.51 and prediction.confidence > 0.9:
            anomalies.append("High confidence on near 50% probability")
        
        # Check for value bet anomaly
        if prediction.expected_value > 0.2 and prediction.confidence < 0.4:
            anomalies.append("High value but low confidence")
        
        return anomalies

# Value Bet Detector
class ValueBetDetector(MapFunction):
    """Detect value bets in real-time"""
    
    def __init__(self, config: FlinkConfig, metrics: AggregationMetrics):
        self.config = config
        self.metrics = metrics
    
    def map(self, value: PredictionEvent) -> Optional[PredictionEvent]:
        """Identify value bets"""
        try:
            # Check if it's a value bet
            is_value_bet = (
                value.expected_value > self.config.value_bet_threshold and
                value.confidence >= self.config.confidence_threshold and
                value.odds > value.fair_odds and
                not value.is_test_prediction
            )
            
            if is_value_bet != value.is_value_bet:
                value.is_value_bet = is_value_bet
                
                if is_value_bet:
                    self.metrics.value_bets_detected.inc()
                    
                    # Add value bet metadata
                    if value.metadata is None:
                        value.metadata = {}
                    value.metadata['value_bet_detected_at'] = int(datetime.utcnow().timestamp() * 1000)
                    value.metadata['value_threshold'] = self.config.value_bet_threshold
            
            return value
            
        except Exception as e:
            self.metrics.errors.inc()
            logging.error(f"Error in value bet detection: {e}")
            return value

# Database Writer
class DatabaseWriter:
    """Write aggregated predictions to TimescaleDB"""
    
    def __init__(self, config: FlinkConfig):
        self.config = config
        self.connection_pool = None
        self.redis_client = None
    
    def open(self, runtime_context):
        """Initialize database connections"""
        # Initialize PostgreSQL connection pool
        self.connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 10,
            host=self.config.timescaledb_host,
            database=self.config.timescaledb_database,
            user=self.config.timescaledb_user,
            password=self.config.timescaledb_password
        )
        
        # Initialize Redis client
        self.redis_client = redis.Redis(
            host=self.config.redis_host,
            password=self.config.redis_password,
            db=self.config.redis_db,
            decode_responses=True
        )
    
    def invoke(self, aggregated: AggregatedPrediction):
        """Write aggregated prediction to database"""
        conn = None
        try:
            # Get connection from pool
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            # Insert into TimescaleDB
            insert_query = """
            INSERT INTO predictions.hourly_predictions_agg (
                hour_bucket, sport_id, league_id, market_type, model_id,
                prediction_count, unique_matches, unique_models, active_users,
                avg_confidence, min_confidence, max_confidence, confidence_stddev,
                confidence_p25, confidence_median, confidence_p75,
                high_confidence_count, medium_confidence_count, low_confidence_count, very_low_confidence_count,
                avg_expected_value, min_expected_value, max_expected_value,
                high_value_predictions, medium_value_predictions, negative_value_predictions,
                avg_kelly_fraction, min_kelly_fraction, max_kelly_fraction,
                aggressive_bets, moderate_bets, conservative_bets, no_bet_recommendations,
                avg_odds, min_odds, max_odds, avg_fair_odds, avg_value_gap, high_value_opportunities,
                avg_stake, total_stake_volume, stake_p95, stake_p99,
                win_count, loss_count, push_count, pending_count,
                total_profit, total_loss, avg_win_return,
                avg_prediction_accuracy, accurate_predictions,
                avg_hours_before_match, min_hours_before_match, max_hours_before_match,
                win_rate, roi_percentage, sharpe_ratio_approx,
                hit_rate_high_confidence, hit_rate_medium_plus_confidence,
                avg_probability, value_bets_identified,
                avg_risk_score, high_risk_predictions,
                model_versions_used,
                hour_of_day, day_of_week, month_of_year,
                is_statistically_significant, standard_error,
                confidence_interval_lower, confidence_interval_upper,
                z_score, is_anomaly, anomaly_reason,
                processed_at, processing_latency_ms, aggregation_version
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (hour_bucket, sport_id, league_id, market_type, model_id) 
            DO UPDATE SET
                prediction_count = EXCLUDED.prediction_count,
                avg_confidence = EXCLUDED.avg_confidence,
                win_rate = EXCLUDED.win_rate,
                roi_percentage = EXCLUDED.roi_percentage,
                total_profit = EXCLUDED.total_profit,
                total_loss = EXCLUDED.total_loss,
                is_anomaly = EXCLUDED.is_anomaly,
                anomaly_reason = EXCLUDED.anomaly_reason,
                processed_at = EXCLUDED.processed_at,
                processing_latency_ms = EXCLUDED.processing_latency_ms
            """
            
            # Convert window times
            hour_bucket = datetime.fromtimestamp(aggregated.window_start / 1000)
            
            # Prepare values
            values = (
                hour_bucket,
                aggregated.sport_id,
                aggregated.league_id,
                aggregated.market_type,
                aggregated.model_id,
                aggregated.prediction_count,
                aggregated.unique_matches,
                aggregated.unique_models,
                aggregated.active_users,
                aggregated.avg_confidence,
                aggregated.min_confidence,
                aggregated.max_confidence,
                aggregated.confidence_stddev,
                aggregated.confidence_p25,
                aggregated.confidence_median,
                aggregated.confidence_p75,
                aggregated.high_confidence_count,
                aggregated.medium_confidence_count,
                aggregated.low_confidence_count,
                aggregated.very_low_confidence_count,
                aggregated.avg_expected_value,
                aggregated.min_expected_value,
                aggregated.max_expected_value,
                aggregated.high_value_predictions,
                aggregated.medium_value_predictions,
                aggregated.negative_value_predictions,
                aggregated.avg_kelly_fraction,
                aggregated.min_kelly_fraction,
                aggregated.max_kelly_fraction,
                aggregated.aggressive_bets,
                aggregated.moderate_bets,
                aggregated.conservative_bets,
                aggregated.no_bet_recommendations,
                aggregated.avg_odds,
                aggregated.min_odds,
                aggregated.max_odds,
                aggregated.avg_fair_odds,
                aggregated.avg_value_gap,
                aggregated.high_value_opportunities,
                aggregated.avg_stake,
                aggregated.total_stake_volume,
                aggregated.stake_p95,
                aggregated.stake_p99,
                aggregated.win_count,
                aggregated.loss_count,
                aggregated.push_count,
                aggregated.pending_count,
                aggregated.total_profit,
                aggregated.total_loss,
                aggregated.avg_win_return,
                aggregated.avg_prediction_accuracy,
                aggregated.accurate_predictions,
                aggregated.avg_hours_before_match,
                aggregated.min_hours_before_match,
                aggregated.max_hours_before_match,
                aggregated.win_rate,
                aggregated.roi_percentage,
                aggregated.sharpe_ratio_approx,
                aggregated.hit_rate_high_confidence,
                aggregated.hit_rate_medium_plus_confidence,
                aggregated.avg_probability,
                aggregated.value_bets_identified,
                aggregated.avg_risk_score,
                aggregated.high_risk_predictions,
                aggregated.model_versions_used,
                aggregated.hour_of_day,
                aggregated.day_of_week,
                aggregated.month_of_year,
                aggregated.is_statistically_significant,
                aggregated.standard_error,
                aggregated.confidence_interval_lower,
                aggregated.confidence_interval_upper,
                aggregated.z_score,
                aggregated.is_anomaly,
                aggregated.anomaly_reason,
                datetime.fromtimestamp(aggregated.processed_at / 1000),
                aggregated.processing_latency_ms,
                aggregated.aggregation_version
            )
            
            cursor.execute(insert_query, values)
            conn.commit()
            
            # Update Redis cache for real-time dashboard
            self._update_redis_cache(aggregated)
            
            # Log successful write
            logging.info(f"Written aggregation for {hour_bucket}: {aggregated.prediction_count} predictions")
            
        except Exception as e:
            logging.error(f"Error writing to database: {e}")
            if conn:
                conn.rollback()
            raise
        
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def _update_redis_cache(self, aggregated: AggregatedPrediction):
        """Update Redis cache with aggregated data"""
        try:
            # Create cache key
            cache_key = f"aggregation:{aggregated.sport_id}:{aggregated.league_id}:{aggregated.market_type}"
            
            # Update recent aggregations list
            recent_key = f"{cache_key}:recent"
            aggregation_data = aggregated.to_dict()
            
            # Add to sorted set with timestamp as score
            self.redis_client.zadd(recent_key, {json.dumps(aggregation_data): aggregated.processed_at})
            
            # Keep only last 100 aggregations
            self.redis_client.zremrangebyrank(recent_key, 0, -101)
            
            # Update latest aggregation
            latest_key = f"{cache_key}:latest"
            self.redis_client.setex(
                latest_key,
                300,  # 5 minutes TTL
                json.dumps(aggregation_data)
            )
            
            # Update statistics
            stats_key = f"{cache_key}:stats"
            stats = {
                'last_updated': aggregated.processed_at,
                'prediction_count': aggregated.prediction_count,
                'avg_confidence': aggregated.avg_confidence,
                'avg_expected_value': aggregated.avg_expected_value,
                'win_rate': aggregated.win_rate,
                'is_anomaly': aggregated.is_anomaly
            }
            self.redis_client.hmset(stats_key, stats)
            self.redis_client.expire(stats_key, 600)  # 10 minutes TTL
            
        except Exception as e:
            logging.error(f"Error updating Redis cache: {e}")

# Main Flink Job
class RealTimeAggregationsJob:
    """Main Flink job for real-time aggregations"""
    
    def __init__(self, config: FlinkConfig = None):
        self.config = config or FlinkConfig()
        self.metrics = AggregationMetrics(self.config.metrics_prefix)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_pipeline(self, env: StreamExecutionEnvironment):
        """Create the Flink processing pipeline"""
        
        # Start Prometheus metrics server
        start_http_server(self.config.prometheus_port)
        
        # Set streaming environment configuration
        env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
        env.set_parallelism(self.config.parallelism)
        env.enable_checkpointing(self.config.checkpoint_interval_ms)
        
        # Create Kafka source for predictions
        predictions_source = self._create_predictions_source()
        
        # Create main processing pipeline
        predictions_stream = env \
            .from_source(
                predictions_source,
                WatermarkStrategy.for_bounded_out_of_orderness(
                    Duration.seconds(self.config.watermark_delay_seconds)
                ).with_timestamp_assigner(PredictionTimestampAssigner()),
                "Predictions Source"
            )
        
        # Parse JSON to PredictionEvent
        parsed_stream = predictions_stream \
            .map(self._parse_prediction_event) \
            .name("Parse Prediction Event")
        
        # Filter out test predictions
        filtered_stream = parsed_stream \
            .filter(lambda x: not x.is_test_prediction) \
            .name("Filter Test Predictions")
        
        # Detect value bets
        value_bet_stream = filtered_stream \
            .map(ValueBetDetector(self.config, self.metrics)) \
            .name("Value Bet Detection")
        
        # Key by sport, league, market for aggregation
        keyed_stream = value_bet_stream \
            .key_by(lambda x: (x.sport_id, x.league_id, x.market_type, x.model_id))
        
        # Create tumbling windows of 5 minutes
        windowed_stream = keyed_stream \
            .window(TumblingEventTimeWindows.of(
                Time.minutes(self.config.window_size_minutes)
            ))
        
        # Aggregate predictions within windows
        aggregated_stream = windowed_stream \
            .aggregate(
                PredictionAggregator(),
                WindowAggregationFunction(self.config, self.metrics)
            ) \
            .name("Window Aggregation")
        
        # Write aggregated predictions to database
        aggregated_stream \
            .map(self._write_to_database) \
            .name("Database Writer")
        
        # Also write to Kafka for other consumers
        aggregated_stream \
            .map(lambda x: json.dumps(x.to_dict()).encode('utf-8')) \
            .add_sink(self._create_kafka_sink(self.config.kafka_aggregated_topic)) \
            .name("Kafka Sink - Aggregated")
        
        # Create anomaly detection stream (parallel processing)
        anomaly_stream = filtered_stream \
            .key_by(lambda x: x.sport_id) \
            .process(AnomalyDetector(self.config, self.metrics)) \
            .name("Anomaly Detection")
        
        # Send anomalies to Kafka
        anomaly_stream \
            .add_sink(self._create_kafka_sink(self.config.kafka_anomalies_topic)) \
            .name("Kafka Sink - Anomalies")
        
        # Create sliding windows for real-time dashboards
        sliding_stream = keyed_stream \
            .window(SlidingEventTimeWindows.of(
                Time.minutes(self.config.window_size_minutes),
                Time.minutes(self.config.sliding_window_minutes)
            ))
        
        # Create real-time statistics
        realtime_stats = sliding_stream \
            .aggregate(
                PredictionAggregator(),
                WindowAggregationFunction(self.config, self.metrics)
            ) \
            .name("Sliding Window Aggregation")
        
        # Write real-time stats to Redis
        realtime_stats \
            .map(self._write_to_redis) \
            .name("Redis Writer")
        
        self.logger.info("Flink pipeline created successfully")
    
    def _create_predictions_source(self) -> KafkaSource:
        """Create Kafka source for predictions"""
        return KafkaSource.builder() \
            .set_bootstrap_servers(self.config.kafka_bootstrap_servers) \
            .set_topics(self.config.kafka_predictions_topic) \
            .set_group_id("flink-aggregations-group") \
            .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
            .set_value_only_deserializer(PredictionEventDeserializer()) \
            .build()
    
    def _parse_prediction_event(self, row) -> PredictionEvent:
        """Parse Flink Row to PredictionEvent"""
        try:
            event = PredictionEvent(
                prediction_id=row[0],
                prediction_time=row[1],
                match_id=row[2],
                sport_id=row[3],
                league_id=row[4],
                market_type=row[5],
                model_id=row[6],
                probability=row[7],
                confidence=row[8],
                odds=row[9],
                fair_odds=row[10],
                expected_value=row[11],
                bookmaker_id=row[12],
                bookmaker_name=row[13],
                odds_timestamp=row[14],
                home_team_id=row[15],
                away_team_id=row[16],
                home_team_name=row[17],
                away_team_name=row[18],
                match_start_time=row[19],
                kelly_fraction=row[20],
                risk_score=row[21],
                is_value_bet=row[22],
                feature_importance=row[23],
                shap_values=row[24],
                user_id=row[25],
                session_id=row[26],
                is_test_prediction=row[27],
                is_live_bet=row[28],
                metadata=row[29]
            )
            
            # Update metrics
            self.metrics.predictions_processed.inc()
            
            # Calculate processing lag
            current_time = datetime.utcnow().timestamp() * 1000
            lag_ms = current_time - event.prediction_time
            self.metrics.processing_lag.set(lag_ms / 1000)
            
            return event
            
        except Exception as e:
            self.metrics.errors.inc()
            self.logger.error(f"Error parsing prediction event: {e}")
            raise
    
    def _create_kafka_sink(self, topic: str) -> KafkaSink:
        """Create Kafka sink"""
        return KafkaSink.builder() \
            .set_bootstrap_servers(self.config.kafka_bootstrap_servers) \
            .set_record_serializer(
                KafkaRecordSerializationSchema.builder()
                .set_topic(topic)
                .set_value_serialization_schema(lambda x: x)
                .build()
            ) \
            .build()
    
    def _write_to_database(self, aggregated: AggregatedPrediction) -> AggregatedPrediction:
        """Write aggregated prediction to database"""
        try:
            writer = DatabaseWriter(self.config)
            writer.open(None)  # Runtime context not needed for simple writer
            writer.invoke(aggregated)
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Error writing to database: {e}")
            raise
    
    def _write_to_redis(self, aggregated: AggregatedPrediction) -> AggregatedPrediction:
        """Write real-time stats to Redis"""
        try:
            redis_client = redis.Redis(
                host=self.config.redis_host,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True
            )
            
            # Create cache key
            cache_key = f"realtime:{aggregated.sport_id}:{aggregated.league_id}:{aggregated.market_type}"
            
            # Store aggregation data
            redis_client.setex(
                cache_key,
                60,  # 1 minute TTL for real-time data
                json.dumps(aggregated.to_dict())
            )
            
            # Update dashboard metrics
            dashboard_key = f"dashboard:realtime_metrics"
            metrics = {
                'timestamp': aggregated.processed_at,
                'sport_id': aggregated.sport_id,
                'league_id': aggregated.league_id,
                'prediction_count': aggregated.prediction_count,
                'avg_confidence': aggregated.avg_confidence,
                'avg_expected_value': aggregated.avg_expected_value,
                'value_bets_identified': aggregated.value_bets_identified,
                'is_anomaly': aggregated.is_anomaly
            }
            
            redis_client.hset(dashboard_key, mapping=metrics)
            redis_client.expire(dashboard_key, 30)  # 30 seconds TTL
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Error writing to Redis: {e}")
            return aggregated

# Health Check and Monitoring
class HealthChecker:
    """Health check and monitoring for Flink job"""
    
    def __init__(self, config: FlinkConfig):
        self.config = config
        self.redis_client = None
        self.last_check_time = datetime.utcnow()
    
    def check_health(self):
        """Perform health checks"""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'HEALTHY',
            'checks': {}
        }
        
        try:
            # Check Redis connection
            self._check_redis(health_status)
            
            # Check Kafka connectivity
            self._check_kafka(health_status)
            
            # Check database connection
            self._check_database(health_status)
            
            # Update health status in Redis
            if self.redis_client:
                self.redis_client.setex(
                    "health:flink_aggregations",
                    60,
                    json.dumps(health_status)
                )
            
        except Exception as e:
            health_status['status'] = 'UNHEALTHY'
            health_status['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health_status
    
    def _check_redis(self, health_status: Dict):
        """Check Redis connection"""
        try:
            client = redis.Redis(
                host=self.config.redis_host,
                password=self.config.redis_password,
                db=self.config.redis_db,
                socket_connect_timeout=2
            )
            client.ping()
            health_status['checks']['redis'] = 'HEALTHY'
            self.redis_client = client
            
        except Exception as e:
            health_status['checks']['redis'] = 'UNHEALTHY'
            raise
    
    def _check_kafka(self, health_status: Dict):
        """Check Kafka connection"""
        try:
            from confluent_kafka import Consumer
            consumer = Consumer({
                'bootstrap.servers': self.config.kafka_bootstrap_servers,
                'group.id': 'health-check',
                'auto.offset.reset': 'latest'
            })
            consumer.list_topics(timeout=5)
            consumer.close()
            health_status['checks']['kafka'] = 'HEALTHY'
            
        except Exception as e:
            health_status['checks']['kafka'] = 'UNHEALTHY'
            raise
    
    def _check_database(self, health_status: Dict):
        """Check database connection"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.config.timescaledb_host,
                database=self.config.timescaledb_database,
                user=self.config.timescaledb_user,
                password=self.config.timescaledb_password,
                connect_timeout=5
            )
            conn.close()
            health_status['checks']['database'] = 'HEALTHY'
            
        except Exception as e:
            health_status['checks']['database'] = 'UNHEALTHY'
            raise

# Main execution
def main():
    """Main entry point for the Flink job"""
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Real-time Aggregations Flink Job')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--check-health', action='store_true', help='Run health check and exit')
    args = parser.parse_args()
    
    # Load configuration
    config = FlinkConfig()
    if args.config:
        import yaml
        with open(args.config, 'r') as f:
            config_data = yaml.safe_load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Health check mode
    if args.check_health:
        checker = HealthChecker(config)
        health_status = checker.check_health()
        print(json.dumps(health_status, indent=2))
        return 0 if health_status['status'] == 'HEALTHY' else 1
    
    # Create and run Flink job
    job = RealTimeAggregationsJob(config)
    
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # Add Flink connectors and dependencies
    env.add_jars(
        "file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar",
        "file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar",
        "file:///opt/flink/lib/postgresql-42.6.0.jar"
    )
    
    # Create and execute pipeline
    try:
        job.create_pipeline(env)
        
        # Execute the job
        job_name = "RealTimeAggregationsJob"
        env.execute(job_name)
        
    except Exception as e:
        job.logger.error(f"Job execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
