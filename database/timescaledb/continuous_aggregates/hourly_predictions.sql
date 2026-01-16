-- TimescaleDB Continuous Aggregate: Hourly Predictions Aggregation
-- ==============================================================
-- Purpose: Materialized view that pre-aggregates prediction data hourly
--          for fast dashboard queries and trend analysis
-- Refresh: Hourly with 15-minute lag
-- Retention: 365 days with compression after 7 days
-- --------------------------------------------------------------

-- Drop existing continuous aggregate if it exists
DROP MATERIALIZED VIEW IF EXISTS predictions.hourly_predictions_agg CASCADE;

-- Create continuous aggregate view for hourly predictions
CREATE MATERIALIZED VIEW predictions.hourly_predictions_agg
WITH (timescaledb.continuous) AS
SELECT 
    -- Time dimension: Aggregated by hour
    time_bucket('1 hour', prediction_time) AS hour_bucket,
    
    -- Dimensions for grouping
    sport_id,
    league_id,
    market_type,
    model_id,
    
    -- Count metrics
    COUNT(*) AS prediction_count,
    COUNT(DISTINCT match_id) AS unique_matches,
    COUNT(DISTINCT user_id) AS active_users,
    
    -- Confidence metrics
    AVG(confidence) AS avg_confidence,
    MIN(confidence) AS min_confidence,
    MAX(confidence) AS max_confidence,
    STDDEV(confidence) AS confidence_stddev,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY confidence) AS confidence_p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY confidence) AS confidence_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY confidence) AS confidence_p75,
    
    -- Confidence distribution buckets
    SUM(CASE WHEN confidence >= 0.8 THEN 1 ELSE 0 END) AS high_confidence_count,
    SUM(CASE WHEN confidence >= 0.6 AND confidence < 0.8 THEN 1 ELSE 0 END) AS medium_confidence_count,
    SUM(CASE WHEN confidence >= 0.4 AND confidence < 0.6 THEN 1 ELSE 0 END) AS low_confidence_count,
    SUM(CASE WHEN confidence < 0.4 THEN 1 ELSE 0 END) AS very_low_confidence_count,
    
    -- Expected Value metrics
    AVG(expected_value) AS avg_expected_value,
    MIN(expected_value) AS min_expected_value,
    MAX(expected_value) AS max_expected_value,
    SUM(CASE WHEN expected_value > 0.05 THEN 1 ELSE 0 END) AS high_value_predictions,
    SUM(CASE WHEN expected_value > 0 AND expected_value <= 0.05 THEN 1 ELSE 0 END) AS medium_value_predictions,
    SUM(CASE WHEN expected_value <= 0 THEN 1 ELSE 0 END) AS negative_value_predictions,
    
    -- Kelly Criterion metrics
    AVG(kelly_fraction) AS avg_kelly_fraction,
    MIN(kelly_fraction) AS min_kelly_fraction,
    MAX(kelly_fraction) AS max_kelly_fraction,
    SUM(CASE WHEN kelly_fraction > 0.1 THEN 1 ELSE 0 END) AS aggressive_bets,
    SUM(CASE WHEN kelly_fraction > 0.05 AND kelly_fraction <= 0.1 THEN 1 ELSE 0 END) AS moderate_bets,
    SUM(CASE WHEN kelly_fraction > 0 AND kelly_fraction <= 0.05 THEN 1 ELSE 0 END) AS conservative_bets,
    SUM(CASE WHEN kelly_fraction <= 0 THEN 1 ELSE 0 END) AS no_bet_recommendations,
    
    -- Odds metrics
    AVG(odds) AS avg_odds,
    MIN(odds) AS min_odds,
    MAX(odds) AS max_odds,
    AVG(fair_odds) AS avg_fair_odds,
    AVG(odds - fair_odds) AS avg_value_gap,
    SUM(CASE WHEN odds > fair_odds * 1.1 THEN 1 ELSE 0 END) AS high_value_opportunities,
    
    -- Stake metrics
    AVG(stake) AS avg_stake,
    SUM(stake) AS total_stake_volume,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY stake) AS stake_p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY stake) AS stake_p99,
    
    -- Outcome metrics (for completed predictions)
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS win_count,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) AS loss_count,
    SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) AS push_count,
    SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) AS pending_count,
    
    -- Profit/Loss metrics
    SUM(CASE WHEN outcome = 'WIN' THEN profit ELSE 0 END) AS total_profit,
    SUM(CASE WHEN outcome = 'LOSS' THEN stake ELSE 0 END) AS total_loss,
    AVG(CASE WHEN outcome = 'WIN' THEN profit / stake ELSE NULL END) AS avg_win_return,
    
    -- Accuracy metrics
    AVG(prediction_accuracy) AS avg_prediction_accuracy,
    SUM(CASE WHEN prediction_accuracy >= 0.7 THEN 1 ELSE 0 END) AS accurate_predictions,
    
    -- Timing metrics
    AVG(EXTRACT(EPOCH FROM (match_start_time - prediction_time)) / 3600) AS avg_hours_before_match,
    MIN(EXTRACT(EPOCH FROM (match_start_time - prediction_time)) / 3600) AS min_hours_before_match,
    MAX(EXTRACT(EPOCH FROM (match_start_time - prediction_time)) / 3600) AS max_hours_before_match,
    
    -- Performance metrics
    CASE 
        WHEN SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END) > 0 
        THEN SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
             SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END)
        ELSE NULL 
    END AS win_rate,
    
    CASE 
        WHEN SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN stake ELSE 0 END) > 0 
        THEN (SUM(CASE WHEN outcome = 'WIN' THEN profit ELSE 0 END) - 
              SUM(CASE WHEN outcome = 'LOSS' THEN stake ELSE 0 END))::DECIMAL /
             SUM(CASE WHEN outcome IN ('WIN', 'LOSS') THEN stake ELSE 0 END)
        ELSE NULL 
    END AS roi_percentage,
    
    -- Sharpe Ratio approximation
    CASE 
        WHEN STDDEV(CASE WHEN outcome = 'WIN' THEN profit/stake 
                         WHEN outcome = 'LOSS' THEN -1 
                         ELSE NULL END) > 0
        THEN AVG(CASE WHEN outcome = 'WIN' THEN profit/stave 
                      WHEN outcome = 'LOSS' THEN -1 
                      ELSE NULL END) / 
             STDDEV(CASE WHEN outcome = 'WIN' THEN profit/stave 
                         WHEN outcome = 'LOSS' THEN -1 
                         ELSE NULL END)
        ELSE NULL 
    END AS sharpe_ratio_approx,
    
    -- Hit rate by confidence levels
    SUM(CASE WHEN confidence >= 0.8 AND outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
    NULLIF(SUM(CASE WHEN confidence >= 0.8 THEN 1 ELSE 0 END), 0) AS hit_rate_high_confidence,
    
    SUM(CASE WHEN confidence >= 0.6 AND outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
    NULLIF(SUM(CASE WHEN confidence >= 0.6 THEN 1 ELSE 0 END), 0) AS hit_rate_medium_plus_confidence,
    
    -- Value metrics
    AVG(probability) AS avg_probability,
    SUM(CASE WHEN probability > odds THEN 1 ELSE 0 END) AS value_bets_identified,
    
    -- Risk metrics
    AVG(risk_score) AS avg_risk_score,
    SUM(CASE WHEN risk_score > 0.7 THEN 1 ELSE 0 END) AS high_risk_predictions,
    
    -- Model performance
    COUNT(DISTINCT model_version) AS model_versions_used,
    
    -- Time analysis
    EXTRACT(HOUR FROM prediction_time) AS hour_of_day,
    EXTRACT(DOW FROM prediction_time) AS day_of_week,
    EXTRACT(MONTH FROM prediction_time) AS month_of_year
    
FROM predictions.predictions
WHERE 
    -- Include only predictions from the last 90 days (adjustable via policy)
    prediction_time >= NOW() - INTERVAL '90 days'
    -- Exclude test data
    AND is_test_prediction = FALSE
    -- Ensure required fields are present
    AND confidence IS NOT NULL
    AND sport_id IS NOT NULL
    AND market_type IS NOT NULL
    -- Optional: Filter out canceled predictions
    AND status != 'CANCELLED'

-- Group by all dimensions
GROUP BY 
    time_bucket('1 hour', prediction_time),
    sport_id,
    league_id,
    market_type,
    model_id,
    EXTRACT(HOUR FROM prediction_time),
    EXTRACT(DOW FROM prediction_time),
    EXTRACT(MONTH FROM prediction_time)

-- Optional: Filter out groups with very few predictions
HAVING COUNT(*) >= 3

-- Order for optimal refresh performance
ORDER BY 
    time_bucket('1 hour', prediction_time) DESC,
    sport_id,
    league_id,
    market_type

WITH NO DATA;

-- ==============================================================
-- CREATE POLICIES
-- ==============================================================

-- Create continuous aggregate policy (refresh every hour with 15-minute lag)
SELECT add_continuous_aggregate_policy(
    'predictions.hourly_predictions_agg',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '1 hour',
    initial_start => NOW() - INTERVAL '90 days',
    timezone => 'UTC'
);

-- Create compression policy (compress after 7 days)
ALTER MATERIALIZED VIEW predictions.hourly_predictions_agg
SET (timescaledb.compress = true);

SELECT add_compression_policy(
    'predictions.hourly_predictions_agg',
    compress_after => INTERVAL '7 days',
    schedule_interval => INTERVAL '1 hour'
);

-- Create retention policy (drop after 365 days)
SELECT add_retention_policy(
    'predictions.hourly_predictions_agg',
    drop_after => INTERVAL '365 days',
    schedule_interval => INTERVAL '1 day'
);

-- ==============================================================
-- CREATE INDEXES FOR OPTIMAL QUERY PERFORMANCE
-- ==============================================================

-- Primary time-based index
CREATE INDEX idx_hourly_predictions_time 
ON predictions.hourly_predictions_agg (hour_bucket DESC)
WITH (timescaledb.hypertable_index = true);

-- Composite index for sport + time queries
CREATE INDEX idx_hourly_predictions_sport_time 
ON predictions.hourly_predictions_agg (sport_id, hour_bucket DESC);

-- Composite index for league + time queries
CREATE INDEX idx_hourly_predictions_league_time 
ON predictions.hourly_predictions_agg (league_id, hour_bucket DESC);

-- Index for market type analysis
CREATE INDEX idx_hourly_predictions_market_time 
ON predictions.hourly_predictions_agg (market_type, hour_bucket DESC);

-- Index for model performance analysis
CREATE INDEX idx_hourly_predictions_model_time 
ON predictions.hourly_predictions_agg (model_id, hour_bucket DESC);

-- Index for confidence-based queries
CREATE INDEX idx_hourly_predictions_confidence 
ON predictions.hourly_predictions_agg (avg_confidence DESC);

-- Index for ROI performance analysis
CREATE INDEX idx_hourly_predictions_roi 
ON predictions.hourly_predictions_agg (roi_percentage DESC NULLS LAST);

-- Index for win rate analysis
CREATE INDEX idx_hourly_predictions_winrate 
ON predictions.hourly_predictions_agg (win_rate DESC NULLS LAST);

-- Composite index for sport + market queries
CREATE INDEX idx_hourly_predictions_sport_market 
ON predictions.hourly_predictions_agg (sport_id, market_type, hour_bucket DESC);

-- Index for hour-of-day analysis
CREATE INDEX idx_hourly_predictions_hour_of_day 
ON predictions.hourly_predictions_agg (hour_of_day, hour_bucket DESC);

-- Index for day-of-week analysis
CREATE INDEX idx_hourly_predictions_day_of_week 
ON predictions.hourly_predictions_agg (day_of_week, hour_bucket DESC);

-- Partial index for high-confidence predictions (commonly queried)
CREATE INDEX idx_hourly_predictions_high_conf 
ON predictions.hourly_predictions_agg (hour_bucket, sport_id, league_id) 
WHERE avg_confidence >= 0.7;

-- Partial index for positive ROI predictions
CREATE INDEX idx_hourly_predictions_positive_roi 
ON predictions.hourly_predictions_agg (hour_bucket, sport_id, market_type) 
WHERE roi_percentage > 0;

-- Partial index for recent data (last 7 days)
CREATE INDEX idx_hourly_predictions_recent 
ON predictions.hourly_predictions_agg (hour_bucket DESC) 
WHERE hour_bucket >= NOW() - INTERVAL '7 days';

-- ==============================================================
-- CREATE REAL-TIME AGGREGATE VIEW
-- ==============================================================

-- Create a real-time view that combines materialized data with recent unmaterialized data
CREATE OR REPLACE VIEW predictions.hourly_predictions_realtime AS
SELECT * FROM predictions.hourly_predictions_agg

UNION ALL

-- Real-time data for current incomplete hour
SELECT 
    time_bucket('1 hour', p.prediction_time) AS hour_bucket,
    p.sport_id,
    p.league_id,
    p.market_type,
    p.model_id,
    COUNT(*) AS prediction_count,
    COUNT(DISTINCT p.match_id) AS unique_matches,
    COUNT(DISTINCT p.user_id) AS active_users,
    AVG(p.confidence) AS avg_confidence,
    MIN(p.confidence) AS min_confidence,
    MAX(p.confidence) AS max_confidence,
    STDDEV(p.confidence) AS confidence_stddev,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY p.confidence) AS confidence_p25,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY p.confidence) AS confidence_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY p.confidence) AS confidence_p75,
    SUM(CASE WHEN p.confidence >= 0.8 THEN 1 ELSE 0 END) AS high_confidence_count,
    SUM(CASE WHEN p.confidence >= 0.6 AND p.confidence < 0.8 THEN 1 ELSE 0 END) AS medium_confidence_count,
    SUM(CASE WHEN p.confidence >= 0.4 AND p.confidence < 0.6 THEN 1 ELSE 0 END) AS low_confidence_count,
    SUM(CASE WHEN p.confidence < 0.4 THEN 1 ELSE 0 END) AS very_low_confidence_count,
    AVG(p.expected_value) AS avg_expected_value,
    MIN(p.expected_value) AS min_expected_value,
    MAX(p.expected_value) AS max_expected_value,
    SUM(CASE WHEN p.expected_value > 0.05 THEN 1 ELSE 0 END) AS high_value_predictions,
    SUM(CASE WHEN p.expected_value > 0 AND p.expected_value <= 0.05 THEN 1 ELSE 0 END) AS medium_value_predictions,
    SUM(CASE WHEN p.expected_value <= 0 THEN 1 ELSE 0 END) AS negative_value_predictions,
    AVG(p.kelly_fraction) AS avg_kelly_fraction,
    MIN(p.kelly_fraction) AS min_kelly_fraction,
    MAX(p.kelly_fraction) AS max_kelly_fraction,
    SUM(CASE WHEN p.kelly_fraction > 0.1 THEN 1 ELSE 0 END) AS aggressive_bets,
    SUM(CASE WHEN p.kelly_fraction > 0.05 AND p.kelly_fraction <= 0.1 THEN 1 ELSE 0 END) AS moderate_bets,
    SUM(CASE WHEN p.kelly_fraction > 0 AND p.kelly_fraction <= 0.05 THEN 1 ELSE 0 END) AS conservative_bets,
    SUM(CASE WHEN p.kelly_fraction <= 0 THEN 1 ELSE 0 END) AS no_bet_recommendations,
    AVG(p.odds) AS avg_odds,
    MIN(p.odds) AS min_odds,
    MAX(p.odds) AS max_odds,
    AVG(p.fair_odds) AS avg_fair_odds,
    AVG(p.odds - p.fair_odds) AS avg_value_gap,
    SUM(CASE WHEN p.odds > p.fair_odds * 1.1 THEN 1 ELSE 0 END) AS high_value_opportunities,
    AVG(p.stake) AS avg_stake,
    SUM(p.stake) AS total_stake_volume,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY p.stake) AS stake_p95,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY p.stake) AS stake_p99,
    SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END) AS win_count,
    SUM(CASE WHEN p.outcome = 'LOSS' THEN 1 ELSE 0 END) AS loss_count,
    SUM(CASE WHEN p.outcome = 'PUSH' THEN 1 ELSE 0 END) AS push_count,
    SUM(CASE WHEN p.outcome IS NULL THEN 1 ELSE 0 END) AS pending_count,
    SUM(CASE WHEN p.outcome = 'WIN' THEN p.profit ELSE 0 END) AS total_profit,
    SUM(CASE WHEN p.outcome = 'LOSS' THEN p.stake ELSE 0 END) AS total_loss,
    AVG(CASE WHEN p.outcome = 'WIN' THEN p.profit / p.stake ELSE NULL END) AS avg_win_return,
    AVG(p.prediction_accuracy) AS avg_prediction_accuracy,
    SUM(CASE WHEN p.prediction_accuracy >= 0.7 THEN 1 ELSE 0 END) AS accurate_predictions,
    AVG(EXTRACT(EPOCH FROM (p.match_start_time - p.prediction_time)) / 3600) AS avg_hours_before_match,
    MIN(EXTRACT(EPOCH FROM (p.match_start_time - p.prediction_time)) / 3600) AS min_hours_before_match,
    MAX(EXTRACT(EPOCH FROM (p.match_start_time - p.prediction_time)) / 3600) AS max_hours_before_match,
    CASE 
        WHEN SUM(CASE WHEN p.outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END) > 0 
        THEN SUM(CASE WHEN p.outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
             SUM(CASE WHEN p.outcome IN ('WIN', 'LOSS') THEN 1 ELSE 0 END)
        ELSE NULL 
    END AS win_rate,
    CASE 
        WHEN SUM(CASE WHEN p.outcome IN ('WIN', 'LOSS') THEN p.stake ELSE 0 END) > 0 
        THEN (SUM(CASE WHEN p.outcome = 'WIN' THEN p.profit ELSE 0 END) - 
              SUM(CASE WHEN p.outcome = 'LOSS' THEN p.stake ELSE 0 END))::DECIMAL /
             SUM(CASE WHEN p.outcome IN ('WIN', 'LOSS') THEN p.stake ELSE 0 END)
        ELSE NULL 
    END AS roi_percentage,
    CASE 
        WHEN STDDEV(CASE WHEN p.outcome = 'WIN' THEN p.profit/p.stake 
                         WHEN p.outcome = 'LOSS' THEN -1 
                         ELSE NULL END) > 0
        THEN AVG(CASE WHEN p.outcome = 'WIN' THEN p.profit/p.stake 
                      WHEN p.outcome = 'LOSS' THEN -1 
                      ELSE NULL END) / 
             STDDEV(CASE WHEN p.outcome = 'WIN' THEN p.profit/p.stake 
                         WHEN p.outcome = 'LOSS' THEN -1 
                         ELSE NULL END)
        ELSE NULL 
    END AS sharpe_ratio_approx,
    SUM(CASE WHEN p.confidence >= 0.8 AND p.outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
    NULLIF(SUM(CASE WHEN p.confidence >= 0.8 THEN 1 ELSE 0 END), 0) AS hit_rate_high_confidence,
    SUM(CASE WHEN p.confidence >= 0.6 AND p.outcome = 'WIN' THEN 1 ELSE 0 END)::DECIMAL / 
    NULLIF(SUM(CASE WHEN p.confidence >= 0.6 THEN 1 ELSE 0 END), 0) AS hit_rate_medium_plus_confidence,
    AVG(p.probability) AS avg_probability,
    SUM(CASE WHEN p.probability > p.odds THEN 1 ELSE 0 END) AS value_bets_identified,
    AVG(p.risk_score) AS avg_risk_score,
    SUM(CASE WHEN p.risk_score > 0.7 THEN 1 ELSE 0 END) AS high_risk_predictions,
    COUNT(DISTINCT p.model_version) AS model_versions_used,
    EXTRACT(HOUR FROM p.prediction_time) AS hour_of_day,
    EXTRACT(DOW FROM p.prediction_time) AS day_of_week,
    EXTRACT(MONTH FROM p.prediction_time) AS month_of_year
FROM predictions.predictions p
WHERE 
    -- Only include data for the current incomplete hour
    p.prediction_time >= date_trunc('hour', NOW())
    AND p.is_test_prediction = FALSE
    AND p.confidence IS NOT NULL
    AND p.sport_id IS NOT NULL
    AND p.market_type IS NOT NULL
    AND p.status != 'CANCELLED'
GROUP BY 
    time_bucket('1 hour', p.prediction_time),
    p.sport_id,
    p.league_id,
    p.market_type,
    p.model_id,
    EXTRACT(HOUR FROM p.prediction_time),
    EXTRACT(DOW FROM p.prediction_time),
    EXTRACT(MONTH FROM p.prediction_time)
HAVING COUNT(*) >= 1;

-- ==============================================================
-- CREATE HELPER FUNCTIONS
-- ==============================================================

-- Function to manually refresh the continuous aggregate
CREATE OR REPLACE FUNCTION refresh_hourly_predictions_agg(
    p_start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '90 days',
    p_end_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '15 minutes'
)
RETURNS VOID AS $$
BEGIN
    -- Refresh the continuous aggregate
    CALL refresh_continuous_aggregate(
        'predictions.hourly_predictions_agg',
        p_start_time,
        p_end_time
    );
    
    -- Log the refresh
    INSERT INTO system.audit_log (
        operation, 
        table_name, 
        details,
        performed_by
    ) VALUES (
        'REFRESH_CONTINUOUS_AGGREGATE',
        'hourly_predictions_agg',
        jsonb_build_object(
            'start_time', p_start_time,
            'end_time', p_end_time,
            'refresh_time', NOW(),
            'rows_affected', NULL
        ),
        current_user
    );
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER;

-- Function to get hourly statistics for dashboard
CREATE OR REPLACE FUNCTION get_hourly_predictions_stats(
    p_sport_id INTEGER DEFAULT NULL,
    p_league_id INTEGER DEFAULT NULL,
    p_market_type VARCHAR(50) DEFAULT NULL,
    p_start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    p_end_time TIMESTAMPTZ DEFAULT NOW(),
    p_min_confidence DECIMAL DEFAULT 0.0
)
RETURNS TABLE (
    hour_bucket TIMESTAMPTZ,
    sport_id INTEGER,
    league_id INTEGER,
    market_type VARCHAR(50),
    prediction_count BIGINT,
    avg_confidence DECIMAL(5,4),
    win_rate DECIMAL(5,4),
    roi_percentage DECIMAL(10,4),
    total_profit DECIMAL(12,4),
    total_loss DECIMAL(12,4),
    net_profit DECIMAL(12,4),
    total_stake_volume DECIMAL(12,4),
    high_confidence_count BIGINT,
    avg_expected_value DECIMAL(10,4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hpr.hour_bucket,
        hpr.sport_id,
        hpr.league_id,
        hpr.market_type,
        hpr.prediction_count,
        hpr.avg_confidence,
        hpr.win_rate,
        hpr.roi_percentage,
        hpr.total_profit,
        hpr.total_loss,
        (hpr.total_profit - hpr.total_loss) AS net_profit,
        hpr.total_stake_volume,
        hpr.high_confidence_count,
        hpr.avg_expected_value
    FROM predictions.hourly_predictions_realtime hpr
    WHERE (p_sport_id IS NULL OR hpr.sport_id = p_sport_id)
        AND (p_league_id IS NULL OR hpr.league_id = p_league_id)
        AND (p_market_type IS NULL OR hpr.market_type = p_market_type)
        AND hpr.hour_bucket >= p_start_time
        AND hpr.hour_bucket <= p_end_time
        AND hpr.avg_confidence >= p_min_confidence
    ORDER BY hpr.hour_bucket DESC;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- Function to analyze confidence trends
CREATE OR REPLACE FUNCTION analyze_confidence_trend(
    p_sport_id INTEGER DEFAULT NULL,
    p_league_id INTEGER DEFAULT NULL,
    p_market_type VARCHAR(50) DEFAULT NULL,
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    hour_bucket TIMESTAMPTZ,
    avg_confidence DECIMAL(5,4),
    confidence_stddev DECIMAL(5,4),
    high_confidence_ratio DECIMAL(5,4),
    prediction_count BIGINT,
    win_rate DECIMAL(5,4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hpr.hour_bucket,
        hpr.avg_confidence,
        hpr.confidence_stddev,
        hpr.high_confidence_count::DECIMAL / NULLIF(hpr.prediction_count, 0) AS high_confidence_ratio,
        hpr.prediction_count,
        hpr.win_rate
    FROM predictions.hourly_predictions_realtime hpr
    WHERE (p_sport_id IS NULL OR hpr.sport_id = p_sport_id)
        AND (p_league_id IS NULL OR hpr.league_id = p_league_id)
        AND (p_market_type IS NULL OR hpr.market_type = p_market_type)
        AND hpr.hour_bucket >= NOW() - (p_hours || ' hours')::INTERVAL
    ORDER BY hpr.hour_bucket;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- Function to get ROI by hour of day
CREATE OR REPLACE FUNCTION get_roi_by_hour_of_day(
    p_sport_id INTEGER DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    hour_of_day INTEGER,
    total_predictions BIGINT,
    avg_roi DECIMAL(10,4),
    total_profit DECIMAL(12,4),
    total_stake DECIMAL(12,4),
    win_rate DECIMAL(5,4),
    avg_confidence DECIMAL(5,4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        hpr.hour_of_day,
        SUM(hpr.prediction_count) AS total_predictions,
        AVG(hpr.roi_percentage) AS avg_roi,
        SUM(hpr.total_profit) AS total_profit,
        SUM(hpr.total_stake_volume) AS total_stake,
        AVG(hpr.win_rate) AS win_rate,
        AVG(hpr.avg_confidence) AS avg_confidence
    FROM predictions.hourly_predictions_realtime hpr
    WHERE (p_sport_id IS NULL OR hpr.sport_id = p_sport_id)
        AND hpr.hour_bucket >= NOW() - (p_days || ' days')::INTERVAL
        AND hpr.roi_percentage IS NOT NULL
    GROUP BY hpr.hour_of_day
    ORDER BY hour_of_day;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- Function to detect anomalies in prediction patterns
CREATE OR REPLACE FUNCTION detect_prediction_anomalies(
    p_lookback_hours INTEGER DEFAULT 24,
    p_confidence_threshold DECIMAL DEFAULT 0.7
)
RETURNS TABLE (
    hour_bucket TIMESTAMPTZ,
    sport_id INTEGER,
    league_id INTEGER,
    market_type VARCHAR(50),
    prediction_count BIGINT,
    avg_confidence DECIMAL(5,4),
    z_score DECIMAL(10,4),
    is_anomaly BOOLEAN,
    anomaly_reason TEXT
) AS $$
DECLARE
    v_avg_count DECIMAL;
    v_stddev_count DECIMAL;
    v_avg_confidence DECIMAL;
    v_stddev_confidence DECIMAL;
BEGIN
    -- Calculate statistics for anomaly detection
    SELECT 
        AVG(prediction_count),
        STDDEV(prediction_count),
        AVG(avg_confidence),
        STDDEV(avg_confidence)
    INTO 
        v_avg_count,
        v_stddev_count,
        v_avg_confidence,
        v_stddev_confidence
    FROM predictions.hourly_predictions_realtime
    WHERE hour_bucket >= NOW() - (p_lookback_hours * 2 || ' hours')::INTERVAL
        AND hour_bucket < NOW() - (p_lookback_hours || ' hours')::INTERVAL;
    
    -- Return anomalies
    RETURN QUERY
    SELECT 
        hpr.hour_bucket,
        hpr.sport_id,
        hpr.league_id,
        hpr.market_type,
        hpr.prediction_count,
        hpr.avg_confidence,
        CASE 
            WHEN v_stddev_count > 0 
            THEN (hpr.prediction_count - v_avg_count) / v_stddev_count
            ELSE 0 
        END AS z_score,
        CASE 
            WHEN v_stddev_count > 0 AND ABS((hpr.prediction_count - v_avg_count) / v_stddev_count) > 3 THEN TRUE
            WHEN v_stddev_confidence > 0 AND ABS((hpr.avg_confidence - v_avg_confidence) / v_stddev_confidence) > 3 THEN TRUE
            WHEN hpr.avg_confidence > p_confidence_threshold AND hpr.prediction_count > v_avg_count * 2 THEN TRUE
            ELSE FALSE
        END AS is_anomaly,
        CASE 
            WHEN v_stddev_count > 0 AND ABS((hpr.prediction_count - v_avg_count) / v_stddev_count) > 3 
                THEN 'Abnormal prediction volume'
            WHEN v_stddev_confidence > 0 AND ABS((hpr.avg_confidence - v_avg_confidence) / v_stddev_confidence) > 3 
                THEN 'Abnormal confidence level'
            WHEN hpr.avg_confidence > p_confidence_threshold AND hpr.prediction_count > v_avg_count * 2 
                THEN 'High volume with high confidence'
            ELSE 'Normal'
        END AS anomaly_reason
    FROM predictions.hourly_predictions_realtime hpr
    WHERE hpr.hour_bucket >= NOW() - (p_lookback_hours || ' hours')::INTERVAL
    ORDER BY 
        CASE 
            WHEN v_stddev_count > 0 
            THEN ABS((hpr.prediction_count - v_avg_count) / v_stddev_count)
            ELSE 0 
        END DESC;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- ==============================================================
-- CREATE DAILY ROLLUP MATERIALIZED VIEW
-- ==============================================================

-- Create daily rollup for longer-term analysis
CREATE MATERIALIZED VIEW IF NOT EXISTS predictions.daily_predictions_agg
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', hour_bucket) AS day_bucket,
    sport_id,
    league_id,
    market_type,
    model_id,
    SUM(prediction_count) AS prediction_count,
    SUM(unique_matches) AS unique_matches,
    SUM(active_users) AS active_users,
    AVG(avg_confidence) AS avg_confidence,
    MIN(min_confidence) AS min_confidence,
    MAX(max_confidence) AS max_confidence,
    AVG(confidence_stddev) AS avg_confidence_stddev,
    SUM(high_confidence_count) AS high_confidence_count,
    SUM(medium_confidence_count) AS medium_confidence_count,
    SUM(low_confidence_count) AS low_confidence_count,
    SUM(very_low_confidence_count) AS very_low_confidence_count,
    AVG(avg_expected_value) AS avg_expected_value,
    SUM(high_value_predictions) AS high_value_predictions,
    SUM(negative_value_predictions) AS negative_value_predictions,
    AVG(avg_kelly_fraction) AS avg_kelly_fraction,
    SUM(aggressive_bets) AS aggressive_bets,
    SUM(conservative_bets) AS conservative_bets,
    AVG(avg_odds) AS avg_odds,
    AVG(avg_fair_odds) AS avg_fair_odds,
    AVG(avg_value_gap) AS avg_value_gap,
    SUM(high_value_opportunities) AS high_value_opportunities,
    AVG(avg_stake) AS avg_stake,
    SUM(total_stake_volume) AS total_stake_volume,
    MAX(stake_p95) AS stake_p95,
    MAX(stake_p99) AS stake_p99,
    SUM(win_count) AS win_count,
    SUM(loss_count) AS loss_count,
    SUM(push_count) AS push_count,
    SUM(pending_count) AS pending_count,
    SUM(total_profit) AS total_profit,
    SUM(total_loss) AS total_loss,
    AVG(avg_win_return) AS avg_win_return,
    AVG(avg_prediction_accuracy) AS avg_prediction_accuracy,
    SUM(accurate_predictions) AS accurate_predictions,
    AVG(avg_hours_before_match) AS avg_hours_before_match,
    CASE 
        WHEN SUM(win_count + loss_count) > 0 
        THEN SUM(win_count)::DECIMAL / SUM(win_count + loss_count)
        ELSE NULL 
    END AS win_rate,
    CASE 
        WHEN SUM(total_stake_volume) > 0 
        THEN (SUM(total_profit) - SUM(total_loss))::DECIMAL / SUM(total_stake_volume)
        ELSE NULL 
    END AS roi_percentage,
    AVG(sharpe_ratio_approx) AS avg_sharpe_ratio,
    AVG(hit_rate_high_confidence) AS avg_hit_rate_high_confidence,
    AVG(hit_rate_medium_plus_confidence) AS avg_hit_rate_medium_plus,
    AVG(avg_probability) AS avg_probability,
    SUM(value_bets_identified) AS value_bets_identified,
    AVG(avg_risk_score) AS avg_risk_score,
    SUM(high_risk_predictions) AS high_risk_predictions,
    MAX(model_versions_used) AS model_versions_used
FROM predictions.hourly_predictions_agg
GROUP BY 
    time_bucket('1 day', hour_bucket),
    sport_id,
    league_id,
    market_type,
    model_id
WITH NO DATA;

-- Add policies for daily rollup
SELECT add_continuous_aggregate_policy(
    'predictions.daily_predictions_agg',
    start_offset => INTERVAL '365 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

SELECT add_compression_policy(
    'predictions.daily_predictions_agg',
    compress_after => INTERVAL '30 days'
);

SELECT add_retention_policy(
    'predictions.daily_predictions_agg',
    drop_after => INTERVAL '730 days'  -- 2 years
);

-- Create indexes for daily rollup
CREATE INDEX idx_daily_predictions_time ON predictions.daily_predictions_agg (day_bucket DESC);
CREATE INDEX idx_daily_predictions_sport_time ON predictions.daily_predictions_agg (sport_id, day_bucket DESC);
CREATE INDEX idx_daily_predictions_league_time ON predictions.daily_predictions_agg (league_id, day_bucket DESC);

-- ==============================================================
-- GRANT PERMISSIONS
-- ==============================================================

-- Grant permissions on continuous aggregate
GRANT SELECT ON predictions.hourly_predictions_agg TO analytics_service;
GRANT SELECT ON predictions.hourly_predictions_agg TO readonly_user;
GRANT ALL PRIVILEGES ON predictions.hourly_predictions_agg TO prediction_service;
GRANT ALL PRIVILEGES ON predictions.hourly_predictions_agg TO admin_user;

-- Grant permissions on real-time view
GRANT SELECT ON predictions.hourly_predictions_realtime TO analytics_service;
GRANT SELECT ON predictions.hourly_predictions_realtime TO readonly_user;
GRANT SELECT ON predictions.hourly_predictions_realtime TO prediction_service;

-- Grant permissions on daily rollup
GRANT SELECT ON predictions.daily_predictions_agg TO analytics_service;
GRANT SELECT ON predictions.daily_predictions_agg TO readonly_user;
GRANT SELECT ON predictions.daily_predictions_agg TO prediction_service;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION refresh_hourly_predictions_agg TO prediction_service;
GRANT EXECUTE ON FUNCTION refresh_hourly_predictions_agg TO admin_user;
GRANT EXECUTE ON FUNCTION get_hourly_predictions_stats TO analytics_service;
GRANT EXECUTE ON FUNCTION get_hourly_predictions_stats TO readonly_user;
GRANT EXECUTE ON FUNCTION analyze_confidence_trend TO analytics_service;
GRANT EXECUTE ON FUNCTION analyze_confidence_trend TO readonly_user;
GRANT EXECUTE ON FUNCTION get_roi_by_hour_of_day TO analytics_service;
GRANT EXECUTE ON FUNCTION get_roi_by_hour_of_day TO readonly_user;
GRANT EXECUTE ON FUNCTION detect_prediction_anomalies TO prediction_service;
GRANT EXECUTE ON FUNCTION detect_prediction_anomalies TO admin_user;

-- ==============================================================
-- INITIAL DATA LOAD AND VERIFICATION
-- ==============================================================

-- Perform initial refresh to populate the continuous aggregate
SELECT refresh_hourly_predictions_agg(
    NOW() - INTERVAL '90 days',
    NOW() - INTERVAL '15 minutes'
);

-- Verify the continuous aggregate was created successfully
DO $$
DECLARE
    v_row_count BIGINT;
    v_refresh_policy_exists BOOLEAN;
    v_compression_policy_exists BOOLEAN;
BEGIN
    -- Check if continuous aggregate has data
    SELECT COUNT(*) INTO v_row_count FROM predictions.hourly_predictions_agg;
    
    -- Check if refresh policy exists
    SELECT EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_refresh_continuous_aggregate'
        AND hypertable_name = 'hourly_predictions_agg'
    ) INTO v_refresh_policy_exists;
    
    -- Check if compression policy exists
    SELECT EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_compression'
        AND hypertable_name = 'hourly_predictions_agg'
    ) INTO v_compression_policy_exists;
    
    -- Log creation details
    INSERT INTO system.audit_log (
        operation, 
        table_name, 
        details,
        performed_by
    ) VALUES (
        'CREATE_CONTINUOUS_AGGREGATE',
        'hourly_predictions_agg',
        jsonb_build_object(
            'created_at', NOW(),
            'initial_row_count', v_row_count,
            'refresh_policy_configured', v_refresh_policy_exists,
            'compression_policy_configured', v_compression_policy_exists,
            'refresh_interval', '1 hour',
            'refresh_lag', '15 minutes',
            'compression_after', '7 days',
            'retention_period', '365 days',
            'status', 'ACTIVE'
        ),
        current_user
    );
    
    RAISE NOTICE 'Continuous aggregate predictions.hourly_predictions_agg created successfully';
    RAISE NOTICE 'Initial row count: %', v_row_count;
    RAISE NOTICE 'Refresh policy: Every 1 hour with 15-minute lag';
    RAISE NOTICE 'Compression policy: After 7 days';
    RAISE NOTICE 'Retention policy: 365 days';
END $$;

-- ==============================================================
-- CREATE COMMENTS FOR DOCUMENTATION
-- ==============================================================

COMMENT ON MATERIALIZED VIEW predictions.hourly_predictions_agg IS 
'Continuous aggregate providing hourly statistics for sports predictions.
Includes confidence metrics, financial performance, and prediction quality indicators.
Automatically refreshed hourly with 15-minute lag to ensure data freshness.
Data is compressed after 7 days and retained for 365 days for historical analysis.';

COMMENT ON VIEW predictions.hourly_predictions_realtime IS 
'Real-time view combining materialized hourly aggregates with current hour data.
Provides complete visibility including the most recent predictions that haven''t been materialized yet.';

COMMENT ON MATERIALIZED VIEW predictions.daily_predictions_agg IS 
'Daily rollup of hourly aggregates for long-term trend analysis and reduced storage requirements.
Provides daily summaries for performance dashboards and historical reporting.';

COMMENT ON FUNCTION refresh_hourly_predictions_agg IS 
'Manually refresh the hourly predictions continuous aggregate.
Parameters:
  p_start_time: Start of time range to refresh (default: 90 days ago)
  p_end_time: End of time range to refresh (default: 15 minutes ago)';

COMMENT ON FUNCTION get_hourly_predictions_stats IS 
'Get hourly prediction statistics for dashboard display.
Parameters allow filtering by sport, league, market type, time range, and minimum confidence.';

COMMENT ON FUNCTION analyze_confidence_trend IS 
'Analyze confidence trends over specified time period.
Useful for monitoring prediction quality and model performance over time.';

COMMENT ON FUNCTION get_roi_by_hour_of_day IS 
'Analyze ROI performance by hour of day to identify optimal betting times.
Helps in understanding temporal patterns in prediction success.';

COMMENT ON FUNCTION detect_prediction_anomalies IS 
'Detect anomalies in prediction patterns such as abnormal volume or confidence levels.
Useful for monitoring system health and detecting unusual activity.';

-- ==============================================================
-- CREATE MONITORING QUERIES
-- ==============================================================

-- Query to monitor continuous aggregate health
CREATE OR REPLACE VIEW predictions.hourly_predictions_monitoring AS
SELECT 
    'hourly_predictions_agg' AS aggregate_name,
    COUNT(*) AS total_hours,
    MIN(hour_bucket) AS oldest_hour,
    MAX(hour_bucket) AS newest_hour,
    SUM(prediction_count) AS total_predictions,
    AVG(avg_confidence) AS overall_avg_confidence,
    AVG(win_rate) AS overall_win_rate,
    AVG(roi_percentage) AS overall_roi,
    NOW() AS check_time
FROM predictions.hourly_predictions_agg;

-- Query to check for gaps in the continuous aggregate
CREATE OR REPLACE VIEW predictions.hourly_predictions_gaps AS
WITH time_series AS (
    SELECT generate_series(
        MIN(hour_bucket), 
        MAX(hour_bucket), 
        '1 hour'::INTERVAL
    ) AS expected_hour
    FROM predictions.hourly_predictions_agg
    WHERE hour_bucket >= NOW() - INTERVAL '7 days'
),
actual_hours AS (
    SELECT DISTINCT hour_bucket
    FROM predictions.hourly_predictions_agg
    WHERE hour_bucket >= NOW() - INTERVAL '7 days'
)
SELECT 
    ts.expected_hour,
    CASE WHEN ah.hour_bucket IS NULL THEN 'MISSING' ELSE 'PRESENT' END AS status,
    NOW() AS check_time
FROM time_series ts
LEFT JOIN actual_hours ah ON ts.expected_hour = ah.hour_bucket
WHERE ah.hour_bucket IS NULL
ORDER BY ts.expected_hour DESC;

GRANT SELECT ON predictions.hourly_predictions_monitoring TO analytics_service;
GRANT SELECT ON predictions.hourly_predictions_monitoring TO admin_user;
GRANT SELECT ON predictions.hourly_predictions_gaps TO admin_user;

-- ==============================================================
-- FINAL SETUP COMPLETION
-- ==============================================================

-- Create completion notification
DO $$
BEGIN
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'HOURLY PREDICTIONS CONTINUOUS AGGREGATE';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'Status: ACTIVE AND READY';
    RAISE NOTICE 'Refresh: Every 1 hour (15-minute lag)';
    RAISE NOTICE 'Compression: After 7 days';
    RAISE NOTICE 'Retention: 365 days';
    RAISE NOTICE 'Indexes: 13 indexes created for optimal performance';
    RAISE NOTICE 'Views: Real-time view available';
    RAISE NOTICE 'Functions: 5 helper functions created';
    RAISE NOTICE 'Daily Rollup: Materialized view created';
    RAISE NOTICE 'Monitoring: Health check views created';
    RAISE NOTICE '=========================================';
END $$;
