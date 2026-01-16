#!/usr/bin/env python3
"""
Windowed Calculations Job for Goat Prediction
Apache Flink Streaming Job for Advanced Windowed Calculations on Sports Predictions
Processing: Real-time statistical analysis, trend detection, and ML feature calculation
"""

import os
import json
import logging
import math
import statistics
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict, field
from decimal import Decimal
from collections import defaultdict, deque
import hashlib

import numpy as np
import pandas as pd
from scipy import stats, signal
from scipy.spatial.distance import euclidean
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import DBSCAN, KMeans
import redis
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import confluent_kafka
from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server

from pyflink.datastream import StreamExecutionEnvironment, TimeCharacteristic
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer,
    KafkaRecordSerializationSchema,
    KafkaSink
)
from pyflink.datastream.formats.json import JsonRowDeserializationSchema
from pyflink.common import WatermarkStrategy, Duration, Time, Types
from pyflink.common.typeinfo import Types as FlinkTypes
from pyflink.datastream.window import (
    TumblingEventTimeWindows,
    SlidingEventTimeWindows,
    SessionWindows,
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
    WindowFunction,
    RichFlatMapFunction,
    CoProcessFunction,
    KeySelector
)
from pyflink.common.watermark_strategy import TimestampAssigner
from pyflink.datastream.state import (
    ValueStateDescriptor,
    ListStateDescriptor,
    MapStateDescriptor,
    ReducingStateDescriptor,
    AggregatingStateDescriptor,
    StateTtlConfig,
    ValueState,
    ListState,
    MapState
)
from pyflink.datastream.connectors.jdbc import (
    JdbcSink,
    JdbcConnectionOptions,
    JdbcExecutionOptions
)

# Configuration
@dataclass
class WindowedConfig:
    """Windowed calculations configuration"""
    # Kafka Configuration
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_predictions_topic: str = "predictions-raw"
    kafka_odds_topic: str = "odds-raw"
    kafka_aggregated_topic: str = "predictions-aggregated"
    kafka_windowed_metrics_topic: str = "windowed-metrics"
    kafka_trends_topic: str = "trends-detected"
    kafka_patterns_topic: str = "patterns-identified"
    
    # Window Configuration
    tumbling_window_minutes: int = 5
    sliding_window_minutes: int = 15
    sliding_window_step_minutes: int = 1
    session_gap_minutes: int = 30
    count_window_size: int = 100
    
    # Calculation Windows
    short_term_window_minutes: int = 5
    medium_term_window_minutes: int = 30
    long_term_window_minutes: int = 120
    
    # Statistical Analysis
    confidence_level: float = 0.95
    anomaly_z_score: float = 3.0
    trend_threshold: float = 0.1
    volatility_threshold: float = 0.15
    
    # Pattern Detection
    pattern_window_size: int = 50
    pattern_similarity_threshold: float = 0.8
    min_pattern_length: int = 10
    
    # Machine Learning
    feature_window_size: int = 100
    pca_components: int = 5
    clustering_epsilon: float = 0.3
    clustering_min_samples: int = 5
    
    # Database
    timescaledb_host: str = "timescaledb:5432"
    timescaledb_database: str = "goat_prediction"
    timescaledb_user: str = "prediction_service"
    timescaledb_password: str = os.getenv("TIMESCALEDB_PASSWORD", "")
    
    redis_host: str = "redis:6379"
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_db: int = 1  # Different DB for windowed calculations
    
    # Performance
    watermark_delay_seconds: int = 30
    checkpoint_interval_ms: int = 30000
    parallelism: int = 12
    max_out_of_orderness_ms: int = 5000
    
    # Feature Engineering
    feature_lag_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10])
    rolling_window_sizes: List[int] = field(default_factory=lambda: [5, 10, 20])
    
    # Alerting
    alert_cooldown_minutes: int = 5
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'confidence_drop': 0.2,
        'volume_spike': 2.0,
        'volatility_spike': 3.0,
        'anomaly_score': 0.8
    })

# Metrics
class WindowedMetrics:
    """Metrics for windowed calculations"""
    
    def __init__(self, prefix: str = "flink_windowed_"):
        self.prefix = prefix
        
        # Counters
        self.windows_processed = Counter(
            f'{prefix}windows_processed_total',
            'Total windows processed'
        )
        self.calculations_completed = Counter(
            f'{prefix}calculations_completed_total',
            'Total calculations completed'
        )
        self.trends_detected = Counter(
            f'{prefix}trends_detected_total',
            'Total trends detected'
        )
        self.patterns_identified = Counter(
            f'{prefix}patterns_identified_total',
            'Total patterns identified'
        )
        self.anomalies_found = Counter(
            f'{prefix}anomalies_found_total',
            'Total anomalies found'
        )
        self.alerts_triggered = Counter(
            f'{prefix}alerts_triggered_total',
            'Total alerts triggered'
        )
        
        # Gauges
        self.active_windows = Gauge(
            f'{prefix}active_windows',
            'Number of active windows'
        )
        self.window_latency = Gauge(
            f'{prefix}window_latency_seconds',
            'Current window processing latency'
        )
        self.feature_vector_size = Gauge(
            f'{prefix}feature_vector_size',
            'Current feature vector size'
        )
        self.trend_strength = Gauge(
            f'{prefix}trend_strength',
            'Current trend strength'
        )
        
        # Histograms
        self.window_processing_time = Histogram(
            f'{prefix}window_processing_time_seconds',
            'Time spent processing windows',
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        self.calculation_time = Histogram(
            f'{prefix}calculation_time_seconds',
            'Time spent on calculations',
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
        )
        self.feature_engineering_time = Histogram(
            f'{prefix}feature_engineering_time_seconds',
            'Time spent on feature engineering',
            buckets=[0.005, 0.01, 0.05, 0.1, 0.5]
        )
        
        # Summaries
        self.window_size_summary = Summary(
            f'{prefix}window_size_summary',
            'Summary of window sizes'
        )
        self.confidence_summary = Summary(
            f'{prefix}confidence_summary',
            'Summary of confidence values'
        )
        self.volatility_summary = Summary(
            f'{prefix}volatility_summary',
            'Summary of volatility values'
        )

# Data Models
@dataclass
class WindowedPrediction:
    """Enhanced prediction for windowed calculations"""
    prediction_id: str
    timestamp: int
    sport_id: int
    league_id: int
    market_type: str
    model_id: str
    confidence: float
    probability: float
    expected_value: float
    odds: float
    fair_odds: float
    kelly_fraction: Optional[float]
    risk_score: Optional[float]
    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WindowMetrics:
    """Comprehensive window metrics"""
    window_start: int
    window_end: int
    window_type: str
    sport_id: int
    league_id: int
    market_type: str
    model_id: Optional[str] = None
    
    # Basic Statistics
    count: int = 0
    sum_confidence: float = 0.0
    sum_expected_value: float = 0.0
    sum_odds: float = 0.0
    
    # Advanced Statistics
    mean_confidence: float = 0.0
    median_confidence: float = 0.0
    std_confidence: float = 0.0
    skew_confidence: float = 0.0
    kurtosis_confidence: float = 0.0
    
    mean_expected_value: float = 0.0
    std_expected_value: float = 0.0
    
    mean_odds: float = 0.0
    std_odds: float = 0.0
    
    # Percentiles
    confidence_p10: float = 0.0
    confidence_p25: float = 0.0
    confidence_p50: float = 0.0
    confidence_p75: float = 0.0
    confidence_p90: float = 0.0
    
    expected_value_p10: float = 0.0
    expected_value_p90: float = 0.0
    
    # Rolling Statistics
    rolling_mean_5: float = 0.0
    rolling_mean_10: float = 0.0
    rolling_mean_20: float = 0.0
    
    rolling_std_5: float = 0.0
    rolling_std_10: float = 0.0
    rolling_std_20: float = 0.0
    
    # Volatility Measures
    garman_klass_volatility: float = 0.0
    parkinson_volatility: float = 0.0
    rogers_satchell_volatility: float = 0.0
    
    # Trend Analysis
    trend_direction: str = "NEUTRAL"  # UP, DOWN, NEUTRAL
    trend_strength: float = 0.0
    trend_slope: float = 0.0
    trend_r_squared: float = 0.0
    
    short_term_trend: str = "NEUTRAL"
    medium_term_trend: str = "NEUTRAL"
    long_term_trend: str = "NEUTRAL"
    
    # Time Series Features
    autocorrelation_lag1: float = 0.0
    autocorrelation_lag5: float = 0.0
    partial_autocorrelation_lag1: float = 0.0
    
    hurst_exponent: float = 0.5
    lyapunov_exponent: float = 0.0
    
    # Anomaly Detection
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    anomaly_type: Optional[str] = None
    z_score: float = 0.0
    modified_z_score: float = 0.0
    
    # Pattern Recognition
    pattern_detected: bool = False
    pattern_type: Optional[str] = None
    pattern_confidence: float = 0.0
    pattern_similarity: float = 0.0
    
    # Clustering
    cluster_id: Optional[int] = None
    cluster_confidence: float = 0.0
    distance_to_centroid: float = 0.0
    
    # Feature Engineering
    feature_vector: List[float] = field(default_factory=list)
    pca_components: List[float] = field(default_factory=list)
    
    # Prediction Quality
    brier_score: float = 0.0
    calibration_score: float = 0.0
    sharp_ratio: float = 0.0
    information_ratio: float = 0.0
    
    # Market Dynamics
    market_efficiency: float = 0.0
    price_discovery: float = 0.0
    information_asymmetry: float = 0.0
    
    # Risk Metrics
    value_at_risk_95: float = 0.0
    expected_shortfall_95: float = 0.0
    downside_deviation: float = 0.0
    
    # Performance Metrics
    processing_time_ms: int = 0
    calculations_version: str = "2.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

# Statistical Calculator
class StatisticalCalculator:
    """Advanced statistical calculations for time windows"""
    
    @staticmethod
    def calculate_basic_stats(values: List[float]) -> Dict[str, float]:
        """Calculate basic statistics"""
        if not values:
            return {}
        
        np_array = np.array(values)
        return {
            'mean': float(np.mean(np_array)),
            'median': float(np.median(np_array)),
            'std': float(np.std(np_array)),
            'min': float(np.min(np_array)),
            'max': float(np.max(np_array)),
            'range': float(np.max(np_array) - np.min(np_array)),
            'iqr': float(np.percentile(np_array, 75) - np.percentile(np_array, 25)),
            'cv': float(np.std(np_array) / np.mean(np_array)) if np.mean(np_array) != 0 else 0.0
        }
    
    @staticmethod
    def calculate_advanced_stats(values: List[float]) -> Dict[str, float]:
        """Calculate advanced statistics"""
        if len(values) < 10:
            return {}
        
        np_array = np.array(values)
        
        # Higher moments
        skew = stats.skew(np_array) if len(np_array) > 2 else 0.0
        kurtosis = stats.kurtosis(np_array) if len(np_array) > 3 else 0.0
        
        # Normality tests
        shapiro_stat, shapiro_p = stats.shapiro(np_array) if 3 <= len(np_array) <= 5000 else (0.0, 1.0)
        
        return {
            'skew': float(skew),
            'kurtosis': float(kurtosis),
            'shapiro_stat': float(shapiro_stat),
            'shapiro_p': float(shapiro_p),
            'is_normal': shapiro_p > 0.05,
            'entropy': float(stats.entropy(np.histogram(np_array, bins='auto')[0]))
        }
    
    @staticmethod
    def calculate_volatility(high: List[float], low: List[float], 
                           open: List[float], close: List[float]) -> Dict[str, float]:
        """Calculate various volatility measures"""
        if len(high) < 2:
            return {}
        
        h = np.array(high)
        l = np.array(low)
        o = np.array(open)
        c = np.array(close)
        
        # Garman-Klass volatility
        gk = np.sqrt(np.mean(0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2))
        
        # Parkinson volatility
        pk = np.sqrt(np.mean((np.log(h / l) ** 2) / (4 * np.log(2))))
        
        # Rogers-Satchell volatility
        rs = np.sqrt(np.mean(
            np.log(h / c) * np.log(h / o) +
            np.log(l / c) * np.log(l / o)
        ))
        
        return {
            'garman_klass': float(gk),
            'parkinson': float(pk),
            'rogers_satchell': float(rs),
            'realized_vol': float(np.std(np.log(c[1:] / c[:-1]))) if len(c) > 1 else 0.0
        }
    
    @staticmethod
    def detect_trend(values: List[float], timestamps: List[int]) -> Dict[str, Any]:
        """Detect trend in time series"""
        if len(values) < 3:
            return {'direction': 'NEUTRAL', 'strength': 0.0, 'slope': 0.0}
        
        # Linear regression for trend
        x = np.array(timestamps).astype(float)
        y = np.array(values)
        
        # Normalize timestamps
        x_norm = (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else x
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_norm, y)
        
        # Mann-Kendall test for trend
        try:
            mk_result = stats.kendalltau(x, y)
            mk_tau = mk_result.statistic
            mk_p = mk_result.pvalue
        except:
            mk_tau = 0.0
            mk_p = 1.0
        
        # Determine trend direction and strength
        direction = "UP" if slope > 0 else "DOWN" if slope < 0 else "NEUTRAL"
        strength = abs(slope) * r_value ** 2
        
        return {
            'direction': direction,
            'strength': float(strength),
            'slope': float(slope),
            'r_squared': float(r_value ** 2),
            'p_value': float(p_value),
            'mk_tau': float(mk_tau),
            'mk_p': float(mk_p),
            'significant': p_value < 0.05
        }
    
    @staticmethod
    def calculate_autocorrelation(values: List[float], max_lag: int = 10) -> Dict[int, float]:
        """Calculate autocorrelation for various lags"""
        if len(values) < max_lag * 2:
            return {}
        
        acf = {}
        n = len(values)
        mean = np.mean(values)
        
        for lag in range(1, min(max_lag + 1, n // 2)):
            cov = np.sum((values[lag:] - mean) * (values[:-lag] - mean)) / n
            var = np.var(values)
            acf[lag] = float(cov / var) if var != 0 else 0.0
        
        return acf
    
    @staticmethod
    def calculate_hurst_exponent(values: List[float]) -> float:
        """Calculate Hurst exponent for time series"""
        if len(values) < 100:
            return 0.5
        
        # Create the range of lag values
        lags = range(2, min(100, len(values) // 4))
        
        # Calculate the array of the variances of the lagged differences
        tau = []
        for lag in lags:
            pp = np.subtract(values[lag:], values[:-lag])
            tau.append(np.sqrt(np.std(pp)))
        
        # Calculate the Hurst exponent
        try:
            hurst = np.polyfit(np.log(lags), np.log(tau), 1)[0]
            return float(hurst)
        except:
            return 0.5

# Pattern Detector
class PatternDetector:
    """Detect patterns in time series data"""
    
    PATTERNS = {
        'head_shoulders': [1, 2, 3, 2, 1],
        'inverse_head_shoulders': [-1, -2, -3, -2, -1],
        'double_top': [1, 2, 1, 2, 1],
        'double_bottom': [-1, -2, -1, -2, -1],
        'triangle_ascending': [1, 1.5, 2, 2.5, 3],
        'triangle_descending': [3, 2.5, 2, 1.5, 1],
        'wedge_rising': [1, 2, 3, 4, 5],
        'wedge_falling': [5, 4, 3, 2, 1]
    }
    
    @staticmethod
    def detect_patterns(values: List[float], threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Detect known patterns in time series"""
        if len(values) < 10:
            return []
        
        detected_patterns = []
        values_normalized = StandardScaler().fit_transform(np.array(values).reshape(-1, 1)).flatten()
        
        for pattern_name, pattern_template in PatternDetector.PATTERNS.items():
            # Normalize pattern template
            pattern_norm = (pattern_template - np.mean(pattern_template)) / np.std(pattern_template)
            
            # Calculate similarity using sliding window
            max_similarity = 0
            best_position = -1
            
            for i in range(len(values_normalized) - len(pattern_norm) + 1):
                window = values_normalized[i:i + len(pattern_norm)]
                similarity = np.corrcoef(window, pattern_norm)[0, 1]
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_position = i
            
            if max_similarity > threshold:
                detected_patterns.append({
                    'name': pattern_name,
                    'similarity': float(max_similarity),
                    'position': best_position,
                    'length': len(pattern_norm),
                    'confidence': float(min(1.0, max_similarity * 1.2))
                })
        
        return detected_patterns
    
    @staticmethod
    def extract_features(values: List[float]) -> Dict[str, float]:
        """Extract time series features for pattern recognition"""
        if len(values) < 20:
            return {}
        
        np_array = np.array(values)
        
        # Statistical features
        features = {
            'mean': float(np.mean(np_array)),
            'std': float(np.std(np_array)),
            'skew': float(stats.skew(np_array)) if len(np_array) > 2 else 0.0,
            'kurtosis': float(stats.kurtosis(np_array)) if len(np_array) > 3 else 0.0,
            'entropy': float(stats.entropy(np.histogram(np_array, bins='auto')[0]))
        }
        
        # Shape features
        q1, q3 = np.percentile(np_array, [25, 75])
        features.update({
            'iqr': float(q3 - q1),
            'range': float(np.max(np_array) - np.min(np_array)),
            'median': float(np.median(np_array)),
            'mad': float(np.median(np.abs(np_array - np.median(np_array))))
        })
        
        # Time series features
        if len(np_array) > 10:
            # Autocorrelation
            acf1 = np.corrcoef(np_array[1:], np_array[:-1])[0, 1] if len(np_array) > 1 else 0.0
            acf5 = np.corrcoef(np_array[5:], np_array[:-5])[0, 1] if len(np_array) > 5 else 0.0
            
            # Partial autocorrelation approximation
            pacf1 = acf1
            if len(np_array) > 2:
                pacf2 = (np.corrcoef(np_array[2:], np_array[:-2])[0, 1] - acf1 ** 2) / (1 - acf1 ** 2) if 1 - acf1 ** 2 != 0 else 0.0
            else:
                pacf2 = 0.0
            
            features.update({
                'acf1': float(acf1),
                'acf5': float(acf5),
                'pacf1': float(pacf1),
                'pacf2': float(pacf2),
                'hurst': StatisticalCalculator.calculate_hurst_exponent(values.tolist() if hasattr(values, 'tolist') else values)
            })
        
        return features

# Anomaly Detector
class AnomalyDetector:
    """Detect anomalies in time series data"""
    
    @staticmethod
    def detect_anomalies_statistical(values: List[float], z_threshold: float = 3.0) -> Dict[str, Any]:
        """Detect anomalies using statistical methods"""
        if len(values) < 10:
            return {'anomalies': [], 'scores': [], 'threshold': z_threshold}
        
        np_array = np.array(values)
        mean = np.mean(np_array)
        std = np.std(np_array)
        
        if std == 0:
            return {'anomalies': [False] * len(values), 'scores': [0.0] * len(values), 'threshold': z_threshold}
        
        z_scores = np.abs((np_array - mean) / std)
        anomalies = z_scores > z_threshold
        anomaly_scores = z_scores / z_threshold  # Normalize to [0, ∞)
        
        return {
            'anomalies': anomalies.tolist(),
            'scores': anomaly_scores.tolist(),
            'threshold': z_threshold,
            'mean': float(mean),
            'std': float(std)
        }
    
    @staticmethod
    def detect_anomalies_iqr(values: List[float], multiplier: float = 1.5) -> Dict[str, Any]:
        """Detect anomalies using IQR method"""
        if len(values) < 4:
            return {'anomalies': [], 'bounds': [0, 0]}
        
        np_array = np.array(values)
        q1 = np.percentile(np_array, 25)
        q3 = np.percentile(np_array, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        anomalies = (np_array < lower_bound) | (np_array > upper_bound)
        
        return {
            'anomalies': anomalies.tolist(),
            'bounds': [float(lower_bound), float(upper_bound)],
            'q1': float(q1),
            'q3': float(q3),
            'iqr': float(iqr)
        }
    
    @staticmethod
    def detect_anomalies_moving_average(values: List[float], window: int = 10, 
                                       sigma: float = 2.0) -> Dict[str, Any]:
        """Detect anomalies using moving average"""
        if len(values) < window * 2:
            return {'anomalies': [], 'scores': []}
        
        df = pd.DataFrame({'value': values})
        df['rolling_mean'] = df['value'].rolling(window=window).mean()
        df['rolling_std'] = df['value'].rolling(window=window).std()
        
        # Handle NaN values
        df['rolling_mean'].fillna(method='bfill', inplace=True)
        df['rolling_std'].fillna(method='bfill', inplace=True)
        df['rolling_std'].replace(0, 1e-10, inplace=True)  # Avoid division by zero
        
        # Calculate z-scores relative to moving statistics
        df['z_score'] = (df['value'] - df['rolling_mean']) / df['rolling_std']
        anomalies = np.abs(df['z_score']) > sigma
        
        return {
            'anomalies': anomalies.tolist(),
            'scores': df['z_score'].abs().tolist(),
            'rolling_mean': df['rolling_mean'].tolist(),
            'rolling_std': df['rolling_std'].tolist()
        }

# Feature Engineering
class FeatureEngineer:
    """Engineer features for machine learning"""
    
    @staticmethod
    def create_lag_features(values: List[float], lags: List[int]) -> Dict[str, List[float]]:
        """Create lag features"""
        features = {}
        max_lag = max(lags)
        
        if len(values) <= max_lag:
            return features
        
        for lag in lags:
            features[f'lag_{lag}'] = values[lag:] + [0.0] * (len(values) - len(values[lag:]))
        
        return features
    
    @staticmethod
    def create_rolling_features(values: List[float], windows: List[int]) -> Dict[str, List[float]]:
        """Create rolling window features"""
        features = {}
        
        for window in windows:
            if len(values) >= window:
                rolling_mean = pd.Series(values).rolling(window=window).mean().tolist()
                rolling_std = pd.Series(values).rolling(window=window).std().tolist()
                rolling_min = pd.Series(values).rolling(window=window).min().tolist()
                rolling_max = pd.Series(values).rolling(window=window).max().tolist()
                
                # Fill NaN values
                rolling_mean = [0.0 if np.isnan(x) else x for x in rolling_mean]
                rolling_std = [0.0 if np.isnan(x) else x for x in rolling_std]
                rolling_min = [0.0 if np.isnan(x) else x for x in rolling_min]
                rolling_max = [0.0 if np.isnan(x) else x for x in rolling_max]
                
                features.update({
                    f'rolling_mean_{window}': rolling_mean,
                    f'rolling_std_{window}': rolling_std,
                    f'rolling_min_{window}': rolling_min,
                    f'rolling_max_{window}': rolling_max
                })
        
        return features
    
    @staticmethod
    def create_technical_indicators(values: List[float]) -> Dict[str, List[float]]:
        """Create technical indicators"""
        if len(values) < 20:
            return {}
        
        df = pd.DataFrame({'close': values})
        
        # Simple Moving Average
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        
        # Exponential Moving Average
        df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
        df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
        
        # RSI (simplified)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Fill NaN values
        df = df.fillna(0)
        
        return {col: df[col].tolist() for col in df.columns if col != 'close'}

# Flink Functions
class WindowAggregator(AggregateFunction):
    """Aggregate predictions within windows for advanced calculations"""
    
    def create_accumulator(self) -> Dict:
        """Create initial accumulator"""
        return {
            'predictions': [],
            'confidences': [],
            'expected_values': [],
            'odds': [],
            'timestamps': [],
            'features': defaultdict(list),
            'metadata': {
                'sport_id': None,
                'league_id': None,
                'market_type': None,
                'model_id': None,
                'count': 0
            }
        }
    
    def add(self, accumulator: Dict, value: WindowedPrediction) -> Dict:
        """Add prediction to accumulator"""
        accumulator['predictions'].append(value)
        accumulator['confidences'].append(value.confidence)
        accumulator['expected_values'].append(value.expected_value)
        accumulator['odds'].append(value.odds)
        accumulator['timestamps'].append(value.timestamp)
        
        # Store features if available
        for feature_name, feature_value in value.features.items():
            accumulator['features'][feature_name].append(feature_value)
        
        # Update metadata
        if accumulator['metadata']['sport_id'] is None:
            accumulator['metadata'].update({
                'sport_id': value.sport_id,
                'league_id': value.league_id,
                'market_type': value.market_type,
                'model_id': value.model_id
            })
        
        accumulator['metadata']['count'] += 1
        
        return accumulator
    
    def get_result(self, accumulator: Dict) -> Dict:
        """Get aggregation result with advanced calculations"""
        if accumulator['metadata']['count'] == 0:
            return None
        
        # Perform statistical calculations
        stats_calculator = StatisticalCalculator()
        
        # Basic statistics
        basic_stats = stats_calculator.calculate_basic_stats(accumulator['confidences'])
        advanced_stats = stats_calculator.calculate_advanced_stats(accumulator['confidences'])
        
        # Volatility calculations (using confidence as proxy for high/low)
        if len(accumulator['confidences']) >= 2:
            volatility = stats_calculator.calculate_volatility(
                accumulator['confidences'],
                accumulator['confidences'],  # Using same for low (simplified)
                accumulator['confidences'][:-1] if len(accumulator['confidences']) > 1 else accumulator['confidences'],
                accumulator['confidences'][1:] if len(accumulator['confidences']) > 1 else accumulator['confidences']
            )
        else:
            volatility = {}
        
        # Trend detection
        trend = stats_calculator.detect_trend(accumulator['confidences'], accumulator['timestamps'])
        
        # Autocorrelation
        autocorrelation = stats_calculator.calculate_autocorrelation(accumulator['confidences'], max_lag=5)
        
        # Hurst exponent
        hurst = stats_calculator.calculate_hurst_exponent(accumulator['confidences'])
        
        # Anomaly detection
        anomaly_detector = AnomalyDetector()
        anomalies_stats = anomaly_detector.detect_anomalies_statistical(accumulator['confidences'])
        
        # Pattern detection
        pattern_detector = PatternDetector()
        patterns = pattern_detector.detect_patterns(accumulator['confidences'])
        features = pattern_detector.extract_features(accumulator['confidences'])
        
        # Prepare result
        result = {
            'predictions': accumulator['predictions'],
            'statistics': {
                'basic': basic_stats,
                'advanced': advanced_stats,
                'volatility': volatility,
                'trend': trend,
                'autocorrelation': autocorrelation,
                'hurst': hurst
            },
            'anomalies': anomalies_stats,
            'patterns': patterns,
            'features': features,
            'metadata': accumulator['metadata'],
            'timestamps': accumulator['timestamps'],
            'values': {
                'confidences': accumulator['confidences'],
                'expected_values': accumulator['expected_values'],
                'odds': accumulator['odds']
            }
        }
        
        return result
    
    def merge(self, accumulator: Dict, accumulator1: Dict) -> Dict:
        """Merge two accumulators"""
        # Merge lists
        for key in ['predictions', 'confidences', 'expected_values', 'odds', 'timestamps']:
            accumulator[key].extend(accumulator1[key])
        
        # Merge features
        for feature_name, feature_values in accumulator1['features'].items():
            if feature_name in accumulator['features']:
                accumulator['features'][feature_name].extend(feature_values)
            else:
                accumulator['features'][feature_name] = feature_values
        
        # Update metadata
        accumulator['metadata']['count'] += accumulator1['metadata']['count']
        
        return accumulator

class AdvancedWindowProcessor(ProcessWindowFunction):
    """Process window with advanced calculations"""
    
    def __init__(self, config: WindowedConfig, metrics: WindowedMetrics):
        self.config = config
        self.metrics = metrics
        self.stat_calculator = StatisticalCalculator()
        self.pattern_detector = PatternDetector()
        self.anomaly_detector = AnomalyDetector()
        self.feature_engineer = FeatureEngineer()
    
    def process(self, key: Tuple, context: ProcessWindowFunction.Context, 
                elements: Iterable[Dict]) -> Iterable[WindowMetrics]:
        """Process window with advanced calculations"""
        start_time = datetime.utcnow()
        
        try:
            # Get window info
            window = context.window()
            window_start = int(window.start)
            window_end = int(window.end)
            
            # Get aggregation result
            aggregation_result = list(elements)[0]
            if not aggregation_result:
                return
            
            metadata = aggregation_result['metadata']
            values = aggregation_result['values']
            statistics = aggregation_result['statistics']
            anomalies = aggregation_result['anomalies']
            patterns = aggregation_result['patterns']
            features = aggregation_result['features']
            
            # Skip if not enough data
            if metadata['count'] < 5:
                return
            
            # Create WindowMetrics
            window_metrics = WindowMetrics(
                window_start=window_start,
                window_end=window_end,
                window_type=context.window().__class__.__name__,
                sport_id=metadata['sport_id'],
                league_id=metadata['league_id'],
                market_type=metadata['market_type'],
                model_id=metadata['model_id'],
                count=metadata['count']
            )
            
            # Calculate basic metrics
            self._calculate_basic_metrics(window_metrics, values, statistics)
            
            # Calculate advanced metrics
            self._calculate_advanced_metrics(window_metrics, values, statistics, context)
            
            # Detect anomalies
            self._detect_anomalies(window_metrics, anomalies, values['confidences'])
            
            # Detect patterns
            self._detect_patterns(window_metrics, patterns)
            
            # Engineer features
            self._engineer_features(window_metrics, values['confidences'], features)
            
            # Calculate risk metrics
            self._calculate_risk_metrics(window_metrics, values)
            
            # Calculate performance metrics
            self._calculate_performance_metrics(window_metrics, values)
            
            # Update metrics
            self.metrics.windows_processed.inc()
            self.metrics.calculations_completed.inc()
            
            if window_metrics.trend_strength > 0.5:
                self.metrics.trends_detected.inc()
                self.metrics.trend_strength.set(window_metrics.trend_strength)
            
            if window_metrics.pattern_detected:
                self.metrics.patterns_identified.inc()
            
            if window_metrics.is_anomaly:
                self.metrics.anomalies_found.inc()
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            window_metrics.processing_time_ms = int(processing_time * 1000)
            
            self.metrics.window_processing_time.observe(processing_time)
            self.metrics.window_size_summary.observe(window_metrics.count)
            self.metrics.confidence_summary.observe(window_metrics.mean_confidence)
            
            yield window_metrics
            
        except Exception as e:
            self.metrics.calculations_completed.inc()
            logging.error(f"Error processing window: {e}")
            raise
    
    def _calculate_basic_metrics(self, metrics: WindowMetrics, values: Dict, statistics: Dict):
        """Calculate basic statistical metrics"""
        # Confidence statistics
        metrics.mean_confidence = statistics['basic'].get('mean', 0.0)
        metrics.median_confidence = statistics['basic'].get('median', 0.0)
        metrics.std_confidence = statistics['basic'].get('std', 0.0)
        
        # Expected value statistics
        ev_stats = self.stat_calculator.calculate_basic_stats(values['expected_values'])
        metrics.mean_expected_value = ev_stats.get('mean', 0.0)
        metrics.std_expected_value = ev_stats.get('std', 0.0)
        
        # Odds statistics
        odds_stats = self.stat_calculator.calculate_basic_stats(values['odds'])
        metrics.mean_odds = odds_stats.get('mean', 0.0)
        metrics.std_odds = odds_stats.get('std', 0.0)
        
        # Percentiles
        confidences = values['confidences']
        if confidences:
            metrics.confidence_p10 = float(np.percentile(confidences, 10))
            metrics.confidence_p25 = float(np.percentile(confidences, 25))
            metrics.confidence_p50 = float(np.percentile(confidences, 50))
            metrics.confidence_p75 = float(np.percentile(confidences, 75))
            metrics.confidence_p90 = float(np.percentile(confidences, 90))
        
        expected_values = values['expected_values']
        if expected_values:
            metrics.expected_value_p10 = float(np.percentile(expected_values, 10))
            metrics.expected_value_p90 = float(np.percentile(expected_values, 90))
    
    def _calculate_advanced_metrics(self, metrics: WindowMetrics, values: Dict, 
                                   statistics: Dict, context: ProcessWindowFunction.Context):
        """Calculate advanced metrics"""
        confidences = values['confidences']
        
        # Advanced statistics
        advanced_stats = statistics.get('advanced', {})
        metrics.skew_confidence = advanced_stats.get('skew', 0.0)
        metrics.kurtosis_confidence = advanced_stats.get('kurtosis', 0.0)
        
        # Volatility
        volatility = statistics.get('volatility', {})
        metrics.garman_klass_volatility = volatility.get('garman_klass', 0.0)
        metrics.parkinson_volatility = volatility.get('parkinson', 0.0)
        metrics.rogers_satchell_volatility = volatility.get('rogers_satchell', 0.0)
        
        # Trend analysis
        trend = statistics.get('trend', {})
        metrics.trend_direction = trend.get('direction', 'NEUTRAL')
        metrics.trend_strength = trend.get('strength', 0.0)
        metrics.trend_slope = trend.get('slope', 0.0)
        metrics.trend_r_squared = trend.get('r_squared', 0.0)
        
        # Time series features
        metrics.hurst_exponent = statistics.get('hurst', 0.5)
        
        autocorrelation = statistics.get('autocorrelation', {})
        metrics.autocorrelation_lag1 = autocorrelation.get(1, 0.0)
        metrics.autocorrelation_lag5 = autocorrelation.get(5, 0.0)
        
        # Calculate partial autocorrelation (simplified)
        if len(confidences) > 2:
            pacf1 = metrics.autocorrelation_lag1
            if len(confidences) > 3:
                acf2 = autocorrelation.get(2, 0.0)
                metrics.partial_autocorrelation_lag1 = (acf2 - pacf1 ** 2) / (1 - pacf1 ** 2) if 1 - pacf1 ** 2 != 0 else 0.0
        
        # Rolling statistics
        if len(confidences) >= 20:
            metrics.rolling_mean_20 = float(np.mean(confidences[-20:]))
            metrics.rolling_std_20 = float(np.std(confidences[-20:]))
        
        if len(confidences) >= 10:
            metrics.rolling_mean_10 = float(np.mean(confidences[-10:]))
            metrics.rolling_std_10 = float(np.std(confidences[-10:]))
        
        if len(confidences) >= 5:
            metrics.rolling_mean_5 = float(np.mean(confidences[-5:]))
            metrics.rolling_std_5 = float(np.std(confidences[-5:]))
    
    def _detect_anomalies(self, metrics: WindowMetrics, anomalies: Dict, confidences: List[float]):
        """Detect and score anomalies"""
        if not anomalies or 'anomalies' not in anomalies:
            return
        
        anomaly_list = anomalies['anomalies']
        scores = anomalies.get('scores', [])
        
        # Check if any anomalies detected
        if any(anomaly_list):
            metrics.is_anomaly = True
            metrics.anomaly_score = max(scores) if scores else 1.0
            
            # Determine anomaly type
            if len(confidences) >= 3:
                recent_trend = np.polyfit(range(3), confidences[-3:], 1)[0]
                if recent_trend < -self.config.trend_threshold:
                    metrics.anomaly_type = 'CONFIDENCE_DROP'
                elif recent_trend > self.config.trend_threshold:
                    metrics.anomaly_type = 'CONFIDENCE_SPIKE'
                else:
                    metrics.anomaly_type = 'STATISTICAL_OUTLIER'
            
            # Calculate z-scores
            if 'mean' in anomalies and 'std' in anomalies and anomalies['std'] > 0:
                last_confidence = confidences[-1] if confidences else 0.0
                metrics.z_score = (last_confidence - anomalies['mean']) / anomalies['std']
                
                # Modified z-score using median absolute deviation
                median = np.median(confidences)
                mad = np.median(np.abs(confidences - median))
                metrics.modified_z_score = 0.6745 * (last_confidence - median) / mad if mad > 0 else 0.0
    
    def _detect_patterns(self, metrics: WindowMetrics, patterns: List[Dict]):
        """Detect and record patterns"""
        if patterns:
            # Get the highest confidence pattern
            best_pattern = max(patterns, key=lambda x: x['confidence'])
            metrics.pattern_detected = True
            metrics.pattern_type = best_pattern['name']
            metrics.pattern_confidence = best_pattern['confidence']
            metrics.pattern_similarity = best_pattern['similarity']
    
    def _engineer_features(self, metrics: WindowMetrics, confidences: List[float], extracted_features: Dict):
        """Engineer features for machine learning"""
        if len(confidences) < 10:
            return
        
        # Create feature vector
        feature_vector = []
        
        # Basic features
        feature_vector.extend([
            metrics.mean_confidence,
            metrics.std_confidence,
            metrics.skew_confidence,
            metrics.kurtosis_confidence,
            metrics.trend_strength,
            metrics.hurst_exponent
        ])
        
        # Add extracted features
        for key in ['mean', 'std', 'skew', 'kurtosis', 'entropy', 'acf1', 'hurst']:
            if key in extracted_features:
                feature_vector.append(extracted_features[key])
        
        # Add volatility features
        feature_vector.extend([
            metrics.garman_klass_volatility,
            metrics.parkinson_volatility,
            metrics.rolling_std_5 if hasattr(metrics, 'rolling_std_5') else 0.0
        ])
        
        # Store feature vector
        metrics.feature_vector = feature_vector
        metrics.feature_vector_size = len(feature_vector)
        
        # Update metrics gauge
        self.metrics.feature_vector_size.set(len(feature_vector))
        
        # Apply PCA if enough features
        if len(feature_vector) >= self.config.pca_components:
            try:
                scaler = StandardScaler()
                features_scaled = scaler.fit_transform(np.array(feature_vector).reshape(1, -1))
                
                # Note: In production, PCA should be trained offline and loaded
                # Here we just store the raw features for now
                metrics.pca_components = feature_vector[:self.config.pca_components]
                
            except Exception as e:
                logging.warning(f"PCA failed: {e}")
    
    def _calculate_risk_metrics(self, metrics: WindowMetrics, values: Dict):
        """Calculate risk metrics"""
        expected_values = values['expected_values']
        if len(expected_values) < 10:
            return
        
        # Value at Risk (95%)
        sorted_ev = sorted(expected_values)
        var_index = int(len(sorted_ev) * 0.05)
        metrics.value_at_risk_95 = sorted_ev[var_index] if var_index < len(sorted_ev) else 0.0
        
        # Expected Shortfall (95%)
        if var_index > 0:
            metrics.expected_shortfall_95 = np.mean(sorted_ev[:var_index])
        
        # Downside deviation (semi-standard deviation)
        mean_ev = np.mean(expected_values)
        downside_values = [ev for ev in expected_values if ev < mean_ev]
        if downside_values:
            metrics.downside_deviation = np.std(downside_values)
    
    def _calculate_performance_metrics(self, metrics: WindowMetrics, values: Dict):
        """Calculate performance metrics"""
        # Sharpe ratio approximation (using expected value as return)
        expected_values = values['expected_values']
        if len(expected_values) > 1 and np.std(expected_values) > 0:
            metrics.sharp_ratio = np.mean(expected_values) / np.std(expected_values)
        
        # Information ratio (relative to confidence)
        confidences = values['confidences']
        if len(confidences) > 1 and len(expected_values) > 1:
            active_return = np.array(expected_values) - np.array(confidences)
            tracking_error = np.std(active_return)
            if tracking_error > 0:
                metrics.information_ratio = np.mean(active_return) / tracking_error

class TrendAnalyzer(KeyedProcessFunction):
    """Analyze trends across multiple time windows"""
    
    def __init__(self, config: WindowedConfig, metrics: WindowedMetrics):
        self.config = config
        self.metrics = metrics
        self.trend_state = None
        self.alert_state = None
        self.last_alert_time = {}
    
    def open(self, runtime_context):
        """Initialize state"""
        # State TTL configuration
        ttl_config = StateTtlConfig \
            .new_builder(Duration.hours(6)) \
            .set_update_type(StateTtlConfig.UpdateType.OnCreateAndWrite) \
            .set_state_visibility(StateTtlConfig.StateVisibility.NeverReturnExpired) \
            .build()
        
        # Trend history state
        trend_desc = ListStateDescriptor(
            "trend_history",
            Types.ROW([Types.STRING(), Types.DOUBLE(), Types.LONG()])  # trend_type, strength, timestamp
        ).enable_time_to_live(ttl_config)
        
        # Alert state
        alert_desc = MapStateDescriptor(
            "alert_timestamps",
            Types.STRING(),  # alert_type + key
            Types.LONG()     # last_alert_time
        )
        
        self.trend_state = runtime_context.get_list_state(trend_desc)
        self.alert_state = runtime_context.get_map_state(alert_desc)
    
    def process_element(self, value: WindowMetrics, ctx: KeyedProcessFunction.Context):
        """Process window metrics for trend analysis"""
        try:
            current_time = ctx.timestamp()
            key = (value.sport_id, value.league_id, value.market_type)
            key_str = f"{key[0]}:{key[1]}:{key[2]}"
            
            # Store trend information
            trend_info = (value.trend_direction, value.trend_strength, current_time)
            self.trend_state.add(trend_info)
            
            # Analyze multi-window trends
            trend_history = list(self.trend_state.get())
            
            if len(trend_history) >= 3:
                # Get recent trends
                recent_trends = sorted(trend_history, key=lambda x: x[2], reverse=True)[:3]
                
                # Check for consistent trends
                directions = [t[0] for t in recent_trends]
                strengths = [t[1] for t in recent_trends]
                
                # Detect strong consistent trend
                if all(d == 'UP' for d in directions) and all(s > 0.3 for s in strengths):
                    self._trigger_alert('STRONG_UPTREND', key_str, value, current_time)
                
                elif all(d == 'DOWN' for d in directions) and all(s > 0.3 for s in strengths):
                    self._trigger_alert('STRONG_DOWNTREND', key_str, value, current_time)
                
                # Detect trend reversal
                if len(trend_history) >= 4:
                    older_trends = sorted(trend_history, key=lambda x: x[2], reverse=True)[3:4]
                    if older_trends and older_trends[0][0] != directions[0]:
                        self._trigger_alert('TREND_REVERSAL', key_str, value, current_time)
            
            # Check for anomaly alerts
            if value.is_anomaly and value.anomaly_score > self.config.alert_thresholds['anomaly_score']:
                self._trigger_alert('HIGH_ANOMALY_SCORE', key_str, value, current_time)
            
            # Check for volatility spikes
            if value.garman_klass_volatility > self.config.volatility_threshold:
                self._trigger_alert('HIGH_VOLATILITY', key_str, value, current_time)
            
        except Exception as e:
            logging.error(f"Error in trend analysis: {e}")
    
    def _trigger_alert(self, alert_type: str, key: str, metrics: WindowMetrics, timestamp: int):
        """Trigger an alert with cooldown"""
        alert_key = f"{alert_type}:{key}"
        
        # Check cooldown
        last_alert = self.alert_state.get(alert_key)
        cooldown_ms = self.config.alert_cooldown_minutes * 60 * 1000
        
        if last_alert is None or timestamp - last_alert > cooldown_ms:
            # Update alert timestamp
            self.alert_state.put(alert_key, timestamp)
            
            # Create alert event
            alert_event = {
                'alert_type': alert_type,
                'timestamp': timestamp,
                'sport_id': metrics.sport_id,
                'league_id': metrics.league_id,
                'market_type': metrics.market_type,
                'metrics': {
                    'trend_strength': metrics.trend_strength,
                    'anomaly_score': metrics.anomaly_score,
                    'volatility': metrics.garman_klass_volatility,
                    'mean_confidence': metrics.mean_confidence
                },
                'message': self._get_alert_message(alert_type, metrics)
            }
            
            # Emit alert
            yield json.dumps(alert_event).encode('utf-8')
            
            # Update metrics
            self.metrics.alerts_triggered.inc()
    
    def _get_alert_message(self, alert_type: str, metrics: WindowMetrics) -> str:
        """Generate alert message"""
        base = f"Alert for {metrics.sport_id}/{metrics.league_id}/{metrics.market_type}: "
        
        if alert_type == 'STRONG_UPTREND':
            return base + f"Strong uptrend detected (strength: {metrics.trend_strength:.2f})"
        elif alert_type == 'STRONG_DOWNTREND':
            return base + f"Strong downtrend detected (strength: {metrics.trend_strength:.2f})"
        elif alert_type == 'TREND_REVERSAL':
            return base + f"Trend reversal detected (from {metrics.trend_direction})"
        elif alert_type == 'HIGH_ANOMALY_SCORE':
            return base + f"High anomaly score detected ({metrics.anomaly_score:.2f})"
        elif alert_type == 'HIGH_VOLATILITY':
            return base + f"High volatility detected ({metrics.garman_klass_volatility:.3f})"
        else:
            return base + alert_type

class PatternTracker(ProcessWindowFunction):
    """Track and identify recurring patterns"""
    
    def __init__(self, config: WindowedConfig):
        self.config = config
        self.patterns_db = {}  # In production, use external storage
    
    def process(self, key: Tuple, context: ProcessWindowFunction.Context, 
                elements: Iterable[WindowMetrics]) -> Iterable[Dict]:
        """Track patterns across windows"""
        try:
            window_metrics = list(elements)
            if not window_metrics:
                return
            
            # Extract feature vectors
            feature_vectors = []
            timestamps = []
            
            for metrics in window_metrics:
                if metrics.feature_vector:
                    feature_vectors.append(metrics.feature_vector)
                    timestamps.append(metrics.window_start)
            
            if len(feature_vectors) < self.config.min_pattern_length:
                return
            
            # Convert to numpy array
            X = np.array(feature_vectors)
            
            # Apply DBSCAN clustering to find similar patterns
            clustering = DBSCAN(
                eps=self.config.clustering_epsilon,
                min_samples=self.config.clustering_min_samples,
                metric='euclidean'
            ).fit(X)
            
            # Identify clusters
            labels = clustering.labels_
            unique_labels = set(labels)
            
            for label in unique_labels:
                if label != -1:  # -1 is noise in DBSCAN
                    # Get indices of points in this cluster
                    cluster_indices = np.where(labels == label)[0]
                    
                    if len(cluster_indices) >= self.config.min_pattern_length:
                        # This is a recurring pattern
                        pattern_data = {
                            'pattern_id': f"pattern_{label}_{int(datetime.utcnow().timestamp())}",
                            'cluster_label': int(label),
                            'size': len(cluster_indices),
                            'first_seen': min(timestamps[i] for i in cluster_indices),
                            'last_seen': max(timestamps[i] for i in cluster_indices),
                            'metrics_indices': cluster_indices.tolist(),
                            'centroid': np.mean(X[cluster_indices], axis=0).tolist(),
                            'stability': self._calculate_pattern_stability(X[cluster_indices])
                        }
                        
                        yield pattern_data
            
        except Exception as e:
            logging.error(f"Error in pattern tracking: {e}")
    
    def _calculate_pattern_stability(self, cluster_points: np.ndarray) -> float:
        """Calculate stability of a pattern cluster"""
        if len(cluster_points) < 2:
            return 0.0
        
        # Calculate centroid
        centroid = np.mean(cluster_points, axis=0)
        
        # Calculate average distance to centroid
        distances = np.linalg.norm(cluster_points - centroid, axis=1)
        avg_distance = np.mean(distances)
        std_distance = np.std(distances)
        
        # Stability is inverse of relative spread
        if avg_distance > 0:
            stability = 1.0 / (1.0 + std_distance / avg_distance)
        else:
            stability = 1.0
        
        return float(stability)

# Main Flink Job
class WindowedCalculationsJob:
    """Main Flink job for windowed calculations"""
    
    def __init__(self, config: WindowedConfig = None):
        self.config = config or WindowedConfig()
        self.metrics = WindowedMetrics()
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def create_pipeline(self, env: StreamExecutionEnvironment):
        """Create the Flink processing pipeline"""
        
        # Start Prometheus metrics server
        start_http_server(9092)  # Different port from other jobs
        
        # Set streaming environment
        env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
        env.set_parallelism(self.config.parallelism)
        env.enable_checkpointing(self.config.checkpoint_interval_ms)
        
        # Create Kafka source
        predictions_source = self._create_predictions_source()
        
        # Create main stream
        predictions_stream = env \
            .from_source(
                predictions_source,
                WatermarkStrategy.for_bounded_out_of_orderness(
                    Duration.seconds(self.config.watermark_delay_seconds)
                ).with_timestamp_assigner(self._create_timestamp_assigner()),
                "Predictions Source"
            )
        
        # Parse and enrich predictions
        enriched_stream = predictions_stream \
            .map(self._enrich_prediction) \
            .name("Enrich Predictions")
        
        # Create multiple window types for different analyses
        
        # 1. Tumbling Windows (5 minutes) - Basic aggregation
        tumbling_stream = enriched_stream \
            .key_by(lambda x: (x.sport_id, x.league_id, x.market_type, x.model_id)) \
            .window(TumblingEventTimeWindows.of(
                Time.minutes(self.config.tumbling_window_minutes)
            )) \
            .aggregate(
                WindowAggregator(),
                AdvancedWindowProcessor(self.config, self.metrics)
            ) \
            .name("Tumbling Window Aggregation")
        
        # 2. Sliding Windows (15 minutes, 1 minute slide) - Trend analysis
        sliding_stream = enriched_stream \
            .key_by(lambda x: (x.sport_id, x.league_id, x.market_type)) \
            .window(SlidingEventTimeWindows.of(
                Time.minutes(self.config.sliding_window_minutes),
                Time.minutes(self.config.sliding_window_step_minutes)
            )) \
            .aggregate(
                WindowAggregator(),
                AdvancedWindowProcessor(self.config, self.metrics)
            ) \
            .name("Sliding Window Aggregation")
        
        # 3. Session Windows - Event-based segmentation
        session_stream = enriched_stream \
            .key_by(lambda x: (x.sport_id, x.league_id)) \
            .window(SessionWindows.with_gap(
                Time.minutes(self.config.session_gap_minutes)
            )) \
            .aggregate(
                WindowAggregator(),
                AdvancedWindowProcessor(self.config, self.metrics)
            ) \
            .name("Session Window Aggregation")
        
        # Process tumbling windows (main pipeline)
        tumbling_stream \
            .map(lambda x: json.dumps(x.to_dict()).encode('utf-8')) \
            .add_sink(self._create_kafka_sink(self.config.kafka_windowed_metrics_topic)) \
            .name("Kafka Sink - Windowed Metrics")
        
        # Analyze trends from sliding windows
        sliding_stream \
            .key_by(lambda x: (x.sport_id, x.league_id, x.market_type)) \
            .process(TrendAnalyzer(self.config, self.metrics)) \
            .add_sink(self._create_kafka_sink(self.config.kafka_trends_topic)) \
            .name("Kafka Sink - Trends")
        
        # Track patterns from session windows
        session_stream \
            .key_by(lambda x: (x.sport_id, x.league_id)) \
            .window(TumblingEventTimeWindows.of(Time.minutes(30))) \
            .process(PatternTracker(self.config)) \
            .add_sink(self._create_kafka_sink(self.config.kafka_patterns_topic)) \
            .name("Kafka Sink - Patterns")
        
        # Store metrics in TimescaleDB
        tumbling_stream \
            .map(self._store_metrics_in_db) \
            .name("Database Storage")
        
        # Cache metrics in Redis for real-time access
        tumbling_stream \
            .map(self._cache_metrics_in_redis) \
            .name("Redis Caching")
        
        self.logger.info("Windowed calculations pipeline created successfully")
    
    def _create_predictions_source(self) -> KafkaSource:
        """Create Kafka source for predictions"""
        return KafkaSource.builder() \
            .set_bootstrap_servers(self.config.kafka_bootstrap_servers) \
            .set_topics(self.config.kafka_predictions_topic) \
            .set_group_id("flink-windowed-calculations") \
            .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
            .set_value_only_deserializer(JsonRowDeserializationSchema.builder()
                .type_info(FlinkTypes.ROW([
                    ("prediction_id", FlinkTypes.STRING()),
                    ("timestamp", FlinkTypes.BIG_INT()),
                    ("sport_id", FlinkTypes.INT()),
                    ("league_id", FlinkTypes.INT()),
                    ("market_type", FlinkTypes.STRING()),
                    ("model_id", FlinkTypes.STRING()),
                    ("confidence", FlinkTypes.DOUBLE()),
                    ("probability", FlinkTypes.DOUBLE()),
                    ("expected_value", FlinkTypes.DOUBLE()),
                    ("odds", FlinkTypes.DOUBLE()),
                    ("fair_odds", FlinkTypes.DOUBLE()),
                    ("kelly_fraction", FlinkTypes.DOUBLE()),
                    ("risk_score", FlinkTypes.DOUBLE()),
                    ("metadata", FlinkTypes.MAP(FlinkTypes.STRING(), FlinkTypes.STRING()))
                ]))
                .build()) \
            .build()
    
    def _create_timestamp_assigner(self) -> TimestampAssigner:
        """Create timestamp assigner for predictions"""
        class PredictionTimestampAssigner(TimestampAssigner):
            def extract_timestamp(self, value, record_timestamp: int) -> int:
                return value[1]  # timestamp field
        
        return PredictionTimestampAssigner()
    
    def _enrich_prediction(self, row) -> WindowedPrediction:
        """Enrich prediction with features"""
        try:
            prediction = WindowedPrediction(
                prediction_id=row[0],
                timestamp=row[1],
                sport_id=row[2],
                league_id=row[3],
                market_type=row[4],
                model_id=row[5],
                confidence=row[6],
                probability=row[7],
                expected_value=row[8],
                odds=row[9],
                fair_odds=row[10],
                kelly_fraction=row[11],
                risk_score=row[12],
                metadata=row[13] or {}
            )
            
            # Add basic features
            prediction.features = {
                'confidence': prediction.confidence,
                'expected_value': prediction.expected_value,
                'value_gap': prediction.odds - prediction.fair_odds,
                'kelly_ratio': prediction.kelly_fraction or 0.0,
                'risk_adjusted_value': prediction.expected_value * (1 - (prediction.risk_score or 0.0))
            }
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error enriching prediction: {e}")
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
    
    def _store_metrics_in_db(self, metrics: WindowMetrics) -> WindowMetrics:
        """Store window metrics in TimescaleDB"""
        try:
            conn = psycopg2.connect(
                host=self.config.timescaledb_host,
                database=self.config.timescaledb_database,
                user=self.config.timescaledb_user,
                password=self.config.timescaledb_password
            )
            cursor = conn.cursor()
            
            # Insert into windowed_metrics table
            insert_query = """
            INSERT INTO analytics.windowed_metrics (
                window_start, window_end, window_type,
                sport_id, league_id, market_type, model_id,
                count, mean_confidence, median_confidence, std_confidence,
                skew_confidence, kurtosis_confidence,
                confidence_p10, confidence_p25, confidence_p50, confidence_p75, confidence_p90,
                mean_expected_value, std_expected_value, expected_value_p10, expected_value_p90,
                mean_odds, std_odds,
                rolling_mean_5, rolling_mean_10, rolling_mean_20,
                rolling_std_5, rolling_std_10, rolling_std_20,
                garman_klass_volatility, parkinson_volatility, rogers_satchell_volatility,
                trend_direction, trend_strength, trend_slope, trend_r_squared,
                short_term_trend, medium_term_trend, long_term_trend,
                autocorrelation_lag1, autocorrelation_lag5, partial_autocorrelation_lag1,
                hurst_exponent, lyapunov_exponent,
                is_anomaly, anomaly_score, anomaly_type, z_score, modified_z_score,
                pattern_detected, pattern_type, pattern_confidence, pattern_similarity,
                cluster_id, cluster_confidence, distance_to_centroid,
                brier_score, calibration_score, sharp_ratio, information_ratio,
                market_efficiency, price_discovery, information_asymmetry,
                value_at_risk_95, expected_shortfall_95, downside_deviation,
                processing_time_ms, calculations_version, metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s
            )
            ON CONFLICT (window_start, sport_id, league_id, market_type, model_id) 
            DO UPDATE SET
                count = EXCLUDED.count,
                mean_confidence = EXCLUDED.mean_confidence,
                trend_direction = EXCLUDED.trend_direction,
                is_anomaly = EXCLUDED.is_anomaly,
                anomaly_score = EXCLUDED.anomaly_score,
                pattern_detected = EXCLUDED.pattern_detected,
                processing_time_ms = EXCLUDED.processing_time_ms
            """
            
            # Prepare values
            window_start = datetime.fromtimestamp(metrics.window_start / 1000)
            window_end = datetime.fromtimestamp(metrics.window_end / 1000)
            
            values = (
                window_start, window_end, metrics.window_type,
                metrics.sport_id, metrics.league_id, metrics.market_type, metrics.model_id,
                metrics.count, metrics.mean_confidence, metrics.median_confidence, metrics.std_confidence,
                metrics.skew_confidence, metrics.kurtosis_confidence,
                metrics.confidence_p10, metrics.confidence_p25, metrics.confidence_p50,
                metrics.confidence_p75, metrics.confidence_p90,
                metrics.mean_expected_value, metrics.std_expected_value,
                metrics.expected_value_p10, metrics.expected_value_p90,
                metrics.mean_odds, metrics.std_odds,
                metrics.rolling_mean_5, metrics.rolling_mean_10, metrics.rolling_mean_20,
                metrics.rolling_std_5, metrics.rolling_std_10, metrics.rolling_std_20,
                metrics.garman_klass_volatility, metrics.parkinson_volatility,
                metrics.rogers_satchell_volatility,
                metrics.trend_direction, metrics.trend_strength, metrics.trend_slope,
                metrics.trend_r_squared,
                metrics.short_term_trend, metrics.medium_term_trend, metrics.long_term_trend,
                metrics.autocorrelation_lag1, metrics.autocorrelation_lag5,
                metrics.partial_autocorrelation_lag1,
                metrics.hurst_exponent, metrics.lyapunov_exponent,
                metrics.is_anomaly, metrics.anomaly_score, metrics.anomaly_type,
                metrics.z_score, metrics.modified_z_score,
                metrics.pattern_detected, metrics.pattern_type, metrics.pattern_confidence,
                metrics.pattern_similarity,
                metrics.cluster_id, metrics.cluster_confidence, metrics.distance_to_centroid,
                metrics.brier_score, metrics.calibration_score, metrics.sharp_ratio,
                metrics.information_ratio,
                metrics.market_efficiency, metrics.price_discovery, metrics.information_asymmetry,
                metrics.value_at_risk_95, metrics.expected_shortfall_95, metrics.downside_deviation,
                metrics.processing_time_ms, metrics.calculations_version,
                Json(metrics.metadata) if metrics.metadata else None
            )
            
            cursor.execute(insert_query, values)
            conn.commit()
            cursor.close()
            conn.close()
            
            self.logger.info(f"Stored window metrics for {window_start}")
            
        except Exception as e:
            self.logger.error(f"Error storing metrics in database: {e}")
        
        return metrics
    
    def _cache_metrics_in_redis(self, metrics: WindowMetrics) -> WindowMetrics:
        """Cache metrics in Redis for real-time access"""
        try:
            redis_client = redis.Redis(
                host=self.config.redis_host,
                password=self.config.redis_password,
                db=self.config.redis_db,
                decode_responses=True
            )
            
            # Create cache key
            cache_key = f"windowed:{metrics.sport_id}:{metrics.league_id}:{metrics.market_type}:{metrics.model_id}"
            
            # Store latest metrics
            metrics_dict = metrics.to_dict()
            redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(metrics_dict)
            )
            
            # Update dashboard metrics
            dashboard_key = f"dashboard:windowed_metrics"
            dashboard_data = {
                'timestamp': metrics.window_start,
                'sport_id': metrics.sport_id,
                'league_id': metrics.league_id,
                'mean_confidence': metrics.mean_confidence,
                'trend_strength': metrics.trend_strength,
                'anomaly_score': metrics.anomaly_score,
                'pattern_detected': metrics.pattern_detected,
                'processing_time_ms': metrics.processing_time_ms
            }
            
            redis_client.hset(dashboard_key, mapping=dashboard_data)
            redis_client.expire(dashboard_key, 60)  # 1 minute TTL
            
            # Update time series data for charts
            ts_key = f"timeseries:{metrics.sport_id}:confidence"
            ts_data = {
                'timestamp': metrics.window_start,
                'value': metrics.mean_confidence
            }
            redis_client.zadd(ts_key, {json.dumps(ts_data): metrics.window_start})
            redis_client.zremrangebyrank(ts_key, 0, -101)  # Keep last 100 points
            
        except Exception as e:
            self.logger.error(f"Error caching metrics in Redis: {e}")
        
        return metrics

# Health Check
class WindowedHealthChecker:
    """Health check for windowed calculations job"""
    
    def __init__(self, config: WindowedConfig):
        self.config = config
    
    def check_health(self) -> Dict:
        """Perform health checks"""
        health = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'windowed_calculations',
            'status': 'HEALTHY',
            'checks': {}
        }
        
        try:
            # Check Redis
            redis_client = redis.Redis(
                host=self.config.redis_host,
                password=self.config.redis_password,
                db=self.config.redis_db,
                socket_connect_timeout=2
            )
            redis_client.ping()
            health['checks']['redis'] = 'HEALTHY'
            
            # Check Kafka
            from confluent_kafka import Consumer
            consumer = Consumer({
                'bootstrap.servers': self.config.kafka_bootstrap_servers,
                'group.id': 'health-check-windowed',
                'auto.offset.reset': 'latest'
            })
            consumer.list_topics(timeout=5)
            consumer.close()
            health['checks']['kafka'] = 'HEALTHY'
            
            # Check database
            conn = psycopg2.connect(
                host=self.config.timescaledb_host,
                database=self.config.timescaledb_database,
                user=self.config.timescaledb_user,
                password=self.config.timescaledb_password,
                connect_timeout=5
            )
            conn.close()
            health['checks']['database'] = 'HEALTHY'
            
        except Exception as e:
            health['status'] = 'UNHEALTHY'
            health['error'] = str(e)
        
        return health

# Main execution
def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windowed Calculations Flink Job')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--health-check', action='store_true', help='Run health check')
    args = parser.parse_args()
    
    # Load configuration
    config = WindowedConfig()
    if args.config:
        import yaml
        with open(args.config, 'r') as f:
            config_data = yaml.safe_load(f)
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Health check mode
    if args.health_check:
        checker = WindowedHealthChecker(config)
        health = checker.check_health()
        print(json.dumps(health, indent=2))
        return 0 if health['status'] == 'HEALTHY' else 1
    
    # Create and run job
    job = WindowedCalculationsJob(config)
    
    # Set up Flink environment
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # Add required jars
    env.add_jars(
        "file:///opt/flink/lib/flink-sql-connector-kafka-3.0.2-1.18.jar",
        "file:///opt/flink/lib/flink-connector-jdbc-3.1.2-1.18.jar",
        "file:///opt/flink/lib/postgresql-42.6.0.jar"
    )
    
    try:
        job.create_pipeline(env)
        job_name = "WindowedCalculationsJob"
        env.execute(job_name)
        
    except Exception as e:
        job.logger.error(f"Job execution failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
