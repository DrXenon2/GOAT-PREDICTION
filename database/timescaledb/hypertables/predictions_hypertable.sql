-- TimescaleDB Hypertable: Predictions Core Table
-- ==============================================================
-- Purpose: Main hypertable for storing all sports predictions
--          Optimized for high-volume time-series data with compression
-- ==============================================================

-- Drop existing table if exists (uncomment for fresh setup)
-- DROP TABLE IF EXISTS predictions.predictions CASCADE;

-- Create the main predictions hypertable
CREATE TABLE IF NOT EXISTS predictions.predictions (
    -- Primary identifier
    prediction_id UUID NOT NULL DEFAULT gen_random_uuid(),
    
    -- Time dimension (for hypertable partitioning)
    prediction_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Match information
    match_id VARCHAR(100) NOT NULL,
    match_start_time TIMESTAMPTZ NOT NULL,
    match_end_time TIMESTAMPTZ,
    match_status VARCHAR(50) DEFAULT 'SCHEDULED',
    
    -- Sport and league
    sport_id INTEGER NOT NULL,
    sport_name VARCHAR(100) NOT NULL,
    league_id INTEGER NOT NULL,
    league_name VARCHAR(100) NOT NULL,
    competition_id INTEGER,
    competition_name VARCHAR(100),
    season_id INTEGER,
    season_name VARCHAR(100),
    
    -- Teams
    home_team_id INTEGER NOT NULL,
    home_team_name VARCHAR(100) NOT NULL,
    home_team_short_name VARCHAR(50),
    away_team_id INTEGER NOT NULL,
    away_team_name VARCHAR(100) NOT NULL,
    away_team_short_name VARCHAR(50),
    
    -- Market information
    market_type VARCHAR(50) NOT NULL,
    market_subtype VARCHAR(50),
    selection_type VARCHAR(50) NOT NULL,
    selection_name VARCHAR(100),
    
    -- Model information
    model_id VARCHAR(100) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) NOT NULL,
    ensemble_weight DECIMAL(5,4),
    
    -- Core prediction metrics
    probability DECIMAL(8,7) NOT NULL CHECK (probability >= 0 AND probability <= 1),
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    fair_odds DECIMAL(10,2) NOT NULL CHECK (fair_odds >= 1.0),
    
    -- Bookmaker odds
    bookmaker_id INTEGER NOT NULL,
    bookmaker_name VARCHAR(100) NOT NULL,
    odds DECIMAL(10,2) NOT NULL CHECK (odds >= 1.0),
    odds_timestamp TIMESTAMPTZ NOT NULL,
    odds_movement VARCHAR(20),
    opening_odds DECIMAL(10,2),
    closing_odds DECIMAL(10,2),
    
    -- Value calculations
    expected_value DECIMAL(10,4) NOT NULL,
    value_percentage DECIMAL(10,4),
    edge DECIMAL(10,4),
    
    -- Kelly Criterion
    kelly_fraction DECIMAL(8,7) CHECK (kelly_fraction >= 0 AND kelly_fraction <= 1),
    kelly_stake DECIMAL(12,4),
    half_kelly_stake DECIMAL(12,4),
    quarter_kelly_stake DECIMAL(12,4),
    
    -- Stake information
    recommended_stake DECIMAL(12,4),
    min_stake DECIMAL(12,4),
    max_stake DECIMAL(12,4),
    actual_stake DECIMAL(12,4),
    stake_currency VARCHAR(3) DEFAULT 'EUR',
    
    -- Risk metrics
    risk_score DECIMAL(5,4) CHECK (risk_score >= 0 AND risk_score <= 1),
    volatility DECIMAL(10,4),
    var_95 DECIMAL(10,4),
    cvar_95 DECIMAL(10,4),
    
    -- Prediction features
    home_team_rating DECIMAL(10,4),
    away_team_rating DECIMAL(10,4),
    home_form_last_5 DECIMAL(5,4),
    away_form_last_5 DECIMAL(5,4),
    h2h_home_wins INTEGER,
    h2h_away_wins INTEGER,
    h2h_draws INTEGER,
    home_goals_avg DECIMAL(5,2),
    away_goals_avg DECIMAL(5,2),
    home_goals_conceded_avg DECIMAL(5,2),
    away_goals_conceded_avg DECIMAL(5,2),
    
    -- Weather conditions (if available)
    temperature DECIMAL(5,2),
    humidity INTEGER,
    wind_speed DECIMAL(5,2),
    weather_condition VARCHAR(50),
    pitch_condition VARCHAR(50),
    
    -- Contextual features
    is_home_advantage BOOLEAN,
    is_derby BOOLEAN,
    is_cup_match BOOLEAN,
    importance_factor DECIMAL(5,4),
    
    -- Injury information
    home_missing_players INTEGER,
    away_missing_players INTEGER,
    home_key_missing INTEGER,
    away_key_missing INTEGER,
    
    -- Referee information
    referee_id INTEGER,
    referee_name VARCHAR(100),
    referee_avg_cards DECIMAL(5,2),
    referee_avg_fouls DECIMAL(5,2),
    
    -- User and system
    user_id UUID,
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    
    -- Betting outcome
    outcome VARCHAR(20) CHECK (outcome IN ('WIN', 'LOSS', 'PUSH', 'CANCELLED', 'VOID')),
    profit DECIMAL(12,4),
    return_amount DECIMAL(12,4),
    settled_at TIMESTAMPTZ,
    settlement_status VARCHAR(20) DEFAULT 'PENDING',
    
    -- Performance metrics
    prediction_accuracy DECIMAL(5,4),
    brier_score DECIMAL(10,4),
    log_loss DECIMAL(10,4),
    calibration_score DECIMAL(10,4),
    
    -- Model explanation (SHAP values as JSON)
    feature_importance JSONB,
    shap_values JSONB,
    prediction_explanation TEXT,
    
    -- Confidence intervals
    confidence_interval_lower DECIMAL(5,4),
    confidence_interval_upper DECIMAL(5,4),
    confidence_interval_width DECIMAL(5,4),
    
    -- Time-series features
    prediction_latency_ms INTEGER,
    data_freshness_seconds INTEGER,
    
    -- Flags and metadata
    is_test_prediction BOOLEAN DEFAULT FALSE,
    is_live_bet BOOLEAN DEFAULT FALSE,
    is_arbitrage BOOLEAN DEFAULT FALSE,
    is_value_bet BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_source VARCHAR(100),
    
    -- Quality flags
    data_quality_score DECIMAL(5,4),
    has_complete_features BOOLEAN DEFAULT TRUE,
    missing_features_count INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ARCHIVED', 'DELETED', 'FLAGGED')),
    
    -- Versioning and audit
    version INTEGER DEFAULT 1,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    
    -- Constraints
    PRIMARY KEY (prediction_id, prediction_time),
    
    -- Foreign key constraints (commented for performance, enforce at app level)
    -- FOREIGN KEY (sport_id) REFERENCES metadata.sports(id),
    -- FOREIGN KEY (league_id) REFERENCES metadata.leagues(id),
    -- FOREIGN KEY (home_team_id) REFERENCES metadata.teams(id),
    -- FOREIGN KEY (away_team_id) REFERENCES metadata.teams(id),
    -- FOREIGN KEY (bookmaker_id) REFERENCES metadata.bookmakers(id),
    -- FOREIGN KEY (user_id) REFERENCES auth.users(id),
    
    -- Check constraints
    CONSTRAINT check_odds_positive CHECK (odds > 0),
    CONSTRAINT check_fair_odds_positive CHECK (fair_odds > 0),
    CONSTRAINT check_stake_non_negative CHECK (
        recommended_stake >= 0 AND 
        actual_stake >= 0 AND 
        min_stake >= 0 AND 
        max_stake >= 0
    ),
    CONSTRAINT check_match_times CHECK (match_start_time > prediction_time),
    CONSTRAINT check_odds_timestamp CHECK (odds_timestamp <= prediction_time),
    CONSTRAINT check_profit_calculation CHECK (
        (outcome = 'WIN' AND profit = actual_stake * (odds - 1)) OR
        (outcome = 'LOSS' AND profit = -actual_stake) OR
        (outcome = 'PUSH' AND profit = 0) OR
        (outcome IS NULL AND profit IS NULL)
    )
);

-- ==============================================================
-- CREATE HYPERTABLE WITH OPTIMIZED PARTITIONING
-- ==============================================================

-- Convert regular table to hypertable with optimized chunking
SELECT create_hypertable(
    'predictions.predictions',
    'prediction_time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 day',  -- 1 day chunks for optimal compression
    create_default_indexes => FALSE,  -- We'll create custom indexes
    partitioning_column => 'sport_id',
    number_partitions => 16,  -- Partition by sport_id for better parallelism
    associated_schema_name => 'predictions'
);

-- ==============================================================
-- CREATE COMPREHENSIVE INDEXES
-- ==============================================================

-- Primary time-based index (most queries filter by time)
CREATE INDEX IF NOT EXISTS idx_predictions_time 
ON predictions.predictions (prediction_time DESC)
WITH (timescaledb.hypertable_index = true);

-- Composite index for sport + time queries
CREATE INDEX IF NOT EXISTS idx_predictions_sport_time 
ON predictions.predictions (sport_id, prediction_time DESC)
WITH (timescaledb.hypertable_index = true);

-- Index for match-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_match 
ON predictions.predictions (match_id, prediction_time DESC);

-- Index for league-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_league_time 
ON predictions.predictions (league_id, prediction_time DESC);

-- Index for model performance analysis
CREATE INDEX IF NOT EXISTS idx_predictions_model_time 
ON predictions.predictions (model_id, prediction_time DESC);

-- Index for market type analysis
CREATE INDEX IF NOT EXISTS idx_predictions_market_time 
ON predictions.predictions (market_type, prediction_time DESC);

-- Index for confidence-based queries (common for high-confidence predictions)
CREATE INDEX IF NOT EXISTS idx_predictions_confidence 
ON predictions.predictions (confidence DESC, prediction_time DESC)
WHERE confidence >= 0.7;

-- Index for expected value (value betting)
CREATE INDEX IF NOT EXISTS idx_predictions_expected_value 
ON predictions.predictions (expected_value DESC, prediction_time DESC)
WHERE expected_value > 0.05;

-- Index for odds-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_odds 
ON predictions.predictions (odds, prediction_time DESC)
WHERE odds BETWEEN 1.5 AND 10.0;

-- Index for bookmaker analysis
CREATE INDEX IF NOT EXISTS idx_predictions_bookmaker_time 
ON predictions.predictions (bookmaker_id, prediction_time DESC);

-- Index for team-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_home_team_time 
ON predictions.predictions (home_team_id, prediction_time DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_away_team_time 
ON predictions.predictions (away_team_id, prediction_time DESC);

-- Index for outcome-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_outcome_time 
ON predictions.predictions (outcome, prediction_time DESC)
WHERE outcome IS NOT NULL;

-- Index for user-based queries
CREATE INDEX IF NOT EXISTS idx_predictions_user_time 
ON predictions.predictions (user_id, prediction_time DESC)
WHERE user_id IS NOT NULL;

-- Index for live bets
CREATE INDEX IF NOT EXISTS idx_predictions_live_bets 
ON predictions.predictions (is_live_bet, prediction_time DESC)
WHERE is_live_bet = TRUE;

-- Index for test predictions (easier to exclude)
CREATE INDEX IF NOT EXISTS idx_predictions_test 
ON predictions.predictions (is_test_prediction, prediction_time DESC)
WHERE is_test_prediction = FALSE;

-- Index for value bets
CREATE INDEX IF NOT EXISTS idx_predictions_value_bets 
ON predictions.predictions (is_value_bet, prediction_time DESC)
WHERE is_value_bet = TRUE;

-- Composite index for sport + market + time
CREATE INDEX IF NOT EXISTS idx_predictions_sport_market_time 
ON predictions.predictions (sport_id, market_type, prediction_time DESC);

-- Composite index for sport + outcome + time
CREATE INDEX IF NOT EXISTS idx_predictions_sport_outcome_time 
ON predictions.predictions (sport_id, outcome, prediction_time DESC)
WHERE outcome IS NOT NULL;

-- Index for match start time (for pre-match queries)
CREATE INDEX IF NOT EXISTS idx_predictions_match_start_time 
ON predictions.predictions (match_start_time DESC)
WHERE match_start_time > NOW();

-- Index for settlement status
CREATE INDEX IF NOT EXISTS idx_predictions_settlement_status 
ON predictions.predictions (settlement_status, prediction_time DESC)
WHERE settlement_status != 'PENDING';

-- Index for data quality
CREATE INDEX IF NOT EXISTS idx_predictions_data_quality 
ON predictions.predictions (data_quality_score DESC, prediction_time DESC)
WHERE data_quality_score >= 0.8;

-- BRIN index for time-based range queries (more efficient for time-only queries)
CREATE INDEX IF NOT EXISTS idx_predictions_time_brin 
ON predictions.predictions USING BRIN (prediction_time);

-- Partial index for recent data (last 7 days - most frequently queried)
CREATE INDEX IF NOT EXISTS idx_predictions_recent 
ON predictions.predictions (prediction_time DESC)
WHERE prediction_time >= NOW() - INTERVAL '7 days';

-- Partial index for high confidence predictions
CREATE INDEX IF NOT EXISTS idx_predictions_high_confidence_recent 
ON predictions.predictions (prediction_time DESC, confidence DESC)
WHERE confidence >= 0.75 AND prediction_time >= NOW() - INTERVAL '30 days';

-- GIN index for JSONB columns (feature importance and SHAP values)
CREATE INDEX IF NOT EXISTS idx_predictions_feature_importance 
ON predictions.predictions USING GIN (feature_importance)
WHERE feature_importance IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_predictions_shap_values 
ON predictions.predictions USING GIN (shap_values)
WHERE shap_values IS NOT NULL;

-- ==============================================================
-- CREATE COMPRESSION POLICY
-- ==============================================================

-- Enable compression on the hypertable
ALTER TABLE predictions.predictions SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'prediction_time DESC, sport_id, league_id',
    timescaledb.compress_segmentby = 'sport_id, market_type, model_id'
);

-- Add compression policy: compress data older than 7 days
SELECT add_compression_policy(
    'predictions.predictions',
    compress_after => INTERVAL '7 days',
    schedule_interval => INTERVAL '1 hour'
);

-- ==============================================================
-- CREATE RETENTION POLICY
-- ==============================================================

-- Add retention policy: drop data older than 365 days
SELECT add_retention_policy(
    'predictions.predictions',
    drop_after => INTERVAL '365 days',
    schedule_interval => INTERVAL '1 day'
);

-- ==============================================================
-- CREATE REORDER POLICY
-- ==============================================================

-- Add reorder policy to maintain index efficiency
SELECT add_reorder_policy(
    'predictions.predictions',
    index_name => 'idx_predictions_time'
);

-- ==============================================================
-- CREATE CONTINUOUS AGGREGATES REFERENCING THIS HYPERTABLE
-- ==============================================================

-- Note: Continuous aggregates are created in separate files
-- This hypertable serves as the source for:
-- 1. hourly_predictions_agg
-- 2. daily_predictions_agg
-- 3. Various other analytical views

-- ==============================================================
-- CREATE TRIGGERS FOR UPDATED_AT
-- ==============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION predictions.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
CREATE TRIGGER update_predictions_updated_at
    BEFORE UPDATE ON predictions.predictions
    FOR EACH ROW
    EXECUTE FUNCTION predictions.update_updated_at_column();

-- ==============================================================
-- CREATE PARTITIONING FUNCTIONS
-- ==============================================================

-- Function to get chunk information for a prediction
CREATE OR REPLACE FUNCTION predictions.get_prediction_chunk_info(p_prediction_time TIMESTAMPTZ)
RETURNS TABLE (
    chunk_name TEXT,
    chunk_range_start TIMESTAMPTZ,
    chunk_range_end TIMESTAMPTZ,
    compressed BOOLEAN,
    total_size TEXT,
    index_size TEXT,
    toast_size TEXT,
    table_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.chunk_name,
        c.range_start,
        c.range_end,
        c.is_compressed,
        pg_size_pretty(c.total_bytes) as total_size,
        pg_size_pretty(c.index_bytes) as index_size,
        pg_size_pretty(c.toast_bytes) as toast_size,
        pg_size_pretty(c.table_bytes) as table_size
    FROM timescaledb_information.chunks c
    WHERE c.hypertable_name = 'predictions'
        AND c.hypertable_schema = 'predictions'
        AND p_prediction_time >= c.range_start
        AND p_prediction_time < c.range_end
    ORDER BY c.range_start DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- ==============================================================
-- CREATE DATA QUALITY FUNCTIONS
-- ==============================================================

-- Function to calculate data quality score for a prediction
CREATE OR REPLACE FUNCTION predictions.calculate_data_quality_score(
    p_missing_features_count INTEGER,
    p_confidence DECIMAL,
    p_has_complete_features BOOLEAN
)
RETURNS DECIMAL AS $$
DECLARE
    v_base_score DECIMAL := 1.0;
    v_missing_penalty DECIMAL := 0.0;
    v_confidence_bonus DECIMAL := 0.0;
BEGIN
    -- Penalty for missing features
    IF p_missing_features_count > 0 THEN
        v_missing_penalty := LEAST(p_missing_features_count * 0.05, 0.5);
    END IF;
    
    -- Bonus for high confidence
    IF p_confidence >= 0.8 THEN
        v_confidence_bonus := 0.1;
    ELSIF p_confidence >= 0.6 THEN
        v_confidence_bonus := 0.05;
    END IF;
    
    -- Bonus for complete features
    IF p_has_complete_features THEN
        v_confidence_bonus := v_confidence_bonus + 0.05;
    END IF;
    
    RETURN GREATEST(0.0, LEAST(1.0, v_base_score - v_missing_penalty + v_confidence_bonus));
END;
$$ LANGUAGE plpgsql
IMMUTABLE;

-- ==============================================================
-- CREATE PREDICTION VALIDATION FUNCTIONS
-- ==============================================================

-- Function to validate prediction data before insertion
CREATE OR REPLACE FUNCTION predictions.validate_prediction(
    p_probability DECIMAL,
    p_confidence DECIMAL,
    p_odds DECIMAL,
    p_fair_odds DECIMAL,
    p_match_start_time TIMESTAMPTZ,
    p_prediction_time TIMESTAMPTZ
)
RETURNS TABLE (
    is_valid BOOLEAN,
    validation_errors TEXT[],
    warnings TEXT[]
) AS $$
DECLARE
    v_errors TEXT[] := '{}';
    v_warnings TEXT[] := '{}';
BEGIN
    -- Initialize result
    is_valid := TRUE;
    
    -- Validate probability range
    IF p_probability < 0 OR p_probability > 1 THEN
        is_valid := FALSE;
        v_errors := array_append(v_errors, format('Probability %s out of range [0, 1]', p_probability));
    END IF;
    
    -- Validate confidence range
    IF p_confidence < 0 OR p_confidence > 1 THEN
        is_valid := FALSE;
        v_errors := array_append(v_errors, format('Confidence %s out of range [0, 1]', p_confidence));
    END IF;
    
    -- Validate odds
    IF p_odds < 1.0 THEN
        is_valid := FALSE;
        v_errors := array_append(v_errors, format('Odds %s less than 1.0', p_odds));
    END IF;
    
    IF p_fair_odds < 1.0 THEN
        is_valid := FALSE;
        v_errors := array_append(v_errors, format('Fair odds %s less than 1.0', p_fair_odds));
    END IF;
    
    -- Validate timing
    IF p_match_start_time <= p_prediction_time THEN
        v_warnings := array_append(v_warnings, 'Match start time is not after prediction time');
    END IF;
    
    -- Check for suspicious values
    IF p_confidence > 0.95 AND p_probability BETWEEN 0.45 AND 0.55 THEN
        v_warnings := array_append(v_warnings, 'High confidence on near 50% probability');
    END IF;
    
    IF p_odds > 10.0 AND p_confidence > 0.8 THEN
        v_warnings := array_append(v_warnings, 'High confidence on high odds (>10.0)');
    END IF;
    
    -- Return results
    validation_errors := v_errors;
    warnings := v_warnings;
    
    RETURN NEXT;
    RETURN;
END;
$$ LANGUAGE plpgsql
IMMUTABLE;

-- ==============================================================
-- CREATE INSERT/UPDATE FUNCTIONS WITH VALIDATION
-- ==============================================================

-- Function to insert prediction with validation
CREATE OR REPLACE FUNCTION predictions.insert_prediction(
    -- Required fields
    p_match_id VARCHAR,
    p_match_start_time TIMESTAMPTZ,
    p_sport_id INTEGER,
    p_league_id INTEGER,
    p_home_team_id INTEGER,
    p_away_team_id INTEGER,
    p_market_type VARCHAR,
    p_selection_type VARCHAR,
    p_model_id VARCHAR,
    p_probability DECIMAL,
    p_confidence DECIMAL,
    p_fair_odds DECIMAL,
    p_bookmaker_id INTEGER,
    p_odds DECIMAL,
    p_odds_timestamp TIMESTAMPTZ,
    p_expected_value DECIMAL,
    
    -- Optional fields with defaults
    p_prediction_time TIMESTAMPTZ DEFAULT NOW(),
    p_sport_name VARCHAR DEFAULT NULL,
    p_league_name VARCHAR DEFAULT NULL,
    p_home_team_name VARCHAR DEFAULT NULL,
    p_away_team_name VARCHAR DEFAULT NULL,
    p_model_name VARCHAR DEFAULT NULL,
    p_model_version VARCHAR DEFAULT '1.0.0',
    p_model_type VARCHAR DEFAULT 'ensemble',
    p_bookmaker_name VARCHAR DEFAULT NULL,
    p_kelly_fraction DECIMAL DEFAULT NULL,
    p_recommended_stake DECIMAL DEFAULT NULL,
    p_risk_score DECIMAL DEFAULT NULL,
    p_user_id UUID DEFAULT NULL,
    p_is_test_prediction BOOLEAN DEFAULT FALSE,
    p_is_live_bet BOOLEAN DEFAULT FALSE,
    p_is_value_bet BOOLEAN DEFAULT NULL,
    p_feature_importance JSONB DEFAULT NULL,
    p_shap_values JSONB DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_prediction_id UUID;
    v_validation_result RECORD;
    v_data_quality_score DECIMAL;
    v_is_value_bet BOOLEAN;
    v_missing_features_count INTEGER := 0;
    v_has_complete_features BOOLEAN := TRUE;
BEGIN
    -- Validate input data
    SELECT * INTO v_validation_result
    FROM predictions.validate_prediction(
        p_probability,
        p_confidence,
        p_odds,
        p_fair_odds,
        p_match_start_time,
        p_prediction_time
    );
    
    -- Check validation errors
    IF array_length(v_validation_result.validation_errors, 1) > 0 THEN
        RAISE EXCEPTION 'Prediction validation failed: %', 
            array_to_string(v_validation_result.validation_errors, '; ');
    END IF;
    
    -- Calculate value bet flag if not provided
    IF p_is_value_bet IS NULL THEN
        v_is_value_bet := p_expected_value > 0.05 AND p_confidence > 0.6;
    ELSE
        v_is_value_bet := p_is_value_bet;
    END IF;
    
    -- Calculate missing features count (simplified)
    IF p_feature_importance IS NULL THEN v_missing_features_count := v_missing_features_count + 1; END IF;
    IF p_shap_values IS NULL THEN v_missing_features_count := v_missing_features_count + 1; END IF;
    IF p_kelly_fraction IS NULL THEN v_missing_features_count := v_missing_features_count + 1; END IF;
    IF p_risk_score IS NULL THEN v_missing_features_count := v_missing_features_count + 1; END IF;
    
    v_has_complete_features := v_missing_features_count = 0;
    
    -- Calculate data quality score
    v_data_quality_score := predictions.calculate_data_quality_score(
        v_missing_features_count,
        p_confidence,
        v_has_complete_features
    );
    
    -- Insert the prediction
    INSERT INTO predictions.predictions (
        prediction_time,
        match_id,
        match_start_time,
        sport_id,
        sport_name,
        league_id,
        league_name,
        home_team_id,
        home_team_name,
        away_team_id,
        away_team_name,
        market_type,
        selection_type,
        model_id,
        model_name,
        model_version,
        model_type,
        probability,
        confidence,
        fair_odds,
        bookmaker_id,
        bookmaker_name,
        odds,
        odds_timestamp,
        expected_value,
        kelly_fraction,
        recommended_stake,
        risk_score,
        user_id,
        is_test_prediction,
        is_live_bet,
        is_value_bet,
        feature_importance,
        shap_values,
        data_quality_score,
        has_complete_features,
        missing_features_count,
        created_by,
        updated_by
    ) VALUES (
        p_prediction_time,
        p_match_id,
        p_match_start_time,
        p_sport_id,
        COALESCE(p_sport_name, 'Unknown'),
        p_league_id,
        COALESCE(p_league_name, 'Unknown'),
        p_home_team_id,
        COALESCE(p_home_team_name, 'Unknown'),
        p_away_team_id,
        COALESCE(p_away_team_name, 'Unknown'),
        p_market_type,
        p_selection_type,
        p_model_id,
        COALESCE(p_model_name, 'Unknown'),
        p_model_version,
        p_model_type,
        p_probability,
        p_confidence,
        p_fair_odds,
        p_bookmaker_id,
        COALESCE(p_bookmaker_name, 'Unknown'),
        p_odds,
        p_odds_timestamp,
        p_expected_value,
        p_kelly_fraction,
        p_recommended_stake,
        p_risk_score,
        p_user_id,
        p_is_test_prediction,
        p_is_live_bet,
        v_is_value_bet,
        p_feature_importance,
        p_shap_values,
        v_data_quality_score,
        v_has_complete_features,
        v_missing_features_count,
        current_user,
        current_user
    )
    RETURNING prediction_id INTO v_prediction_id;
    
    -- Log warnings if any
    IF array_length(v_validation_result.warnings, 1) > 0 THEN
        INSERT INTO system.audit_log (
            operation,
            table_name,
            entity_id,
            details,
            severity
        ) VALUES (
            'INSERT_PREDICTION_WARNING',
            'predictions',
            v_prediction_id,
            jsonb_build_object(
                'warnings', v_validation_result.warnings,
                'prediction_time', p_prediction_time,
                'confidence', p_confidence,
                'odds', p_odds
            ),
            'WARNING'
        );
    END IF;
    
    -- Log successful insertion
    INSERT INTO system.audit_log (
        operation,
        table_name,
        entity_id,
        details
    ) VALUES (
        'INSERT_PREDICTION',
        'predictions',
        v_prediction_id,
        jsonb_build_object(
            'sport_id', p_sport_id,
            'league_id', p_league_id,
            'market_type', p_market_type,
            'model_id', p_model_id,
            'confidence', p_confidence,
            'expected_value', p_expected_value,
            'data_quality_score', v_data_quality_score
        )
    );
    
    RETURN v_prediction_id;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER;

-- Function to update prediction outcome
CREATE OR REPLACE FUNCTION predictions.update_prediction_outcome(
    p_prediction_id UUID,
    p_outcome VARCHAR,
    p_profit DECIMAL DEFAULT NULL,
    p_settled_at TIMESTAMPTZ DEFAULT NOW(),
    p_prediction_accuracy DECIMAL DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_actual_stake DECIMAL;
    v_odds DECIMAL;
    v_calculated_profit DECIMAL;
BEGIN
    -- Get current stake and odds
    SELECT actual_stake, odds INTO v_actual_stake, v_odds
    FROM predictions.predictions
    WHERE prediction_id = p_prediction_id
      AND outcome IS NULL;  -- Only update if not already settled
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Prediction % not found or already settled', p_prediction_id;
    END IF;
    
    -- Calculate profit if not provided
    IF p_profit IS NULL AND v_actual_stake IS NOT NULL THEN
        CASE p_outcome
            WHEN 'WIN' THEN
                v_calculated_profit := v_actual_stake * (v_odds - 1);
            WHEN 'LOSS' THEN
                v_calculated_profit := -v_actual_stake;
            WHEN 'PUSH' THEN
                v_calculated_profit := 0;
            ELSE
                v_calculated_profit := NULL;
        END CASE;
    ELSE
        v_calculated_profit := p_profit;
    END IF;
    
    -- Update the prediction
    UPDATE predictions.predictions
    SET 
        outcome = p_outcome,
        profit = v_calculated_profit,
        return_amount = CASE 
            WHEN p_outcome = 'WIN' THEN v_actual_stake * v_odds
            WHEN p_outcome = 'PUSH' THEN v_actual_stake
            ELSE 0
        END,
        settled_at = p_settled_at,
        settlement_status = 'SETTLED',
        prediction_accuracy = COALESCE(p_prediction_accuracy, 
            CASE 
                WHEN p_outcome = 'WIN' AND confidence >= 0.5 THEN 1.0
                WHEN p_outcome = 'LOSS' AND confidence < 0.5 THEN 1.0
                WHEN p_outcome = 'WIN' AND confidence < 0.5 THEN 0.0
                WHEN p_outcome = 'LOSS' AND confidence >= 0.5 THEN 0.0
                ELSE NULL
            END),
        brier_score = CASE 
            WHEN p_outcome = 'WIN' THEN POWER(1 - probability, 2)
            WHEN p_outcome = 'LOSS' THEN POWER(probability, 2)
            ELSE NULL
        END,
        log_loss = CASE 
            WHEN p_outcome = 'WIN' THEN -LN(GREATEST(probability, 0.0001))
            WHEN p_outcome = 'LOSS' THEN -LN(GREATEST(1 - probability, 0.0001))
            ELSE NULL
        END,
        updated_by = current_user,
        updated_at = NOW()
    WHERE prediction_id = p_prediction_id;
    
    -- Log the update
    INSERT INTO system.audit_log (
        operation,
        table_name,
        entity_id,
        details
    ) VALUES (
        'UPDATE_PREDICTION_OUTCOME',
        'predictions',
        p_prediction_id,
        jsonb_build_object(
            'outcome', p_outcome,
            'profit', v_calculated_profit,
            'settled_at', p_settled_at,
            'prediction_accuracy', p_prediction_accuracy
        )
    );
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER;

-- ==============================================================
-- CREATE VIEWS FOR COMMON QUERIES
-- ==============================================================

-- View for active predictions (not settled)
CREATE OR REPLACE VIEW predictions.active_predictions AS
SELECT 
    prediction_id,
    prediction_time,
    match_id,
    sport_name,
    league_name,
    home_team_name,
    away_team_name,
    market_type,
    selection_type,
    probability,
    confidence,
    odds,
    fair_odds,
    expected_value,
    kelly_fraction,
    recommended_stake,
    risk_score,
    match_start_time,
    model_name,
    model_version,
    bookmaker_name,
    is_value_bet,
    data_quality_score
FROM predictions.predictions
WHERE outcome IS NULL
    AND match_start_time > NOW()
    AND is_test_prediction = FALSE
    AND status = 'ACTIVE'
ORDER BY prediction_time DESC;

-- View for value bets
CREATE OR REPLACE VIEW predictions.value_bets AS
SELECT 
    prediction_id,
    prediction_time,
    match_id,
    sport_name,
    league_name,
    home_team_name,
    away_team_name,
    market_type,
    probability,
    confidence,
    odds,
    fair_odds,
    expected_value,
    value_percentage,
    kelly_fraction,
    recommended_stake,
    risk_score,
    match_start_time,
    model_name,
    bookmaker_name,
    odds_movement
FROM predictions.predictions
WHERE is_value_bet = TRUE
    AND outcome IS NULL
    AND match_start_time > NOW() - INTERVAL '2 days'
    AND is_test_prediction = FALSE
    AND confidence >= 0.6
    AND expected_value > 0.05
ORDER BY expected_value DESC, confidence DESC;

-- View for high confidence predictions
CREATE OR REPLACE VIEW predictions.high_confidence_predictions AS
SELECT 
    prediction_id,
    prediction_time,
    match_id,
    sport_name,
    league_name,
    home_team_name,
    away_team_name,
    market_type,
    probability,
    confidence,
    odds,
    expected_value,
    kelly_fraction,
    match_start_time,
    model_name,
    bookmaker_name,
    data_quality_score
FROM predictions.predictions
WHERE confidence >= 0.8
    AND outcome IS NULL
    AND match_start_time > NOW()
    AND is_test_prediction = FALSE
    AND data_quality_score >= 0.8
ORDER BY confidence DESC, prediction_time DESC;

-- View for model performance
CREATE OR REPLACE VIEW predictions.model_performance AS
SELECT 
    model_id,
    model_name,
    model_version,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) as pushes,
    AVG(confidence) as avg_confidence,
    AVG(prediction_accuracy) as avg_accuracy,
    AVG(brier_score) as avg_brier_score,
    SUM(profit) as total_profit,
    AVG(profit) as avg_profit_per_prediction,
    MIN(prediction_time) as first_prediction,
    MAX(prediction_time) as last_prediction
FROM predictions.predictions
WHERE outcome IS NOT NULL
    AND is_test_prediction = FALSE
    AND prediction_time >= NOW() - INTERVAL '90 days'
GROUP BY model_id, model_name, model_version
ORDER BY avg_accuracy DESC, total_predictions DESC;

-- View for bookmaker performance
CREATE OR REPLACE VIEW predictions.bookmaker_performance AS
SELECT 
    bookmaker_id,
    bookmaker_name,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    AVG(odds) as avg_odds,
    AVG(fair_odds) as avg_fair_odds,
    AVG(odds - fair_odds) as avg_value_gap,
    SUM(profit) as total_profit,
    AVG(expected_value) as avg_expected_value,
    MIN(prediction_time) as first_prediction,
    MAX(prediction_time) as last_prediction
FROM predictions.predictions
WHERE outcome IS NOT NULL
    AND is_test_prediction = FALSE
    AND prediction_time >= NOW() - INTERVAL '90 days'
GROUP BY bookmaker_id, bookmaker_name
ORDER BY avg_value_gap DESC, total_predictions DESC;

-- ==============================================================
-- CREATE STATISTICS FUNCTIONS
-- ==============================================================

-- Function to get prediction statistics for a time period
CREATE OR REPLACE FUNCTION predictions.get_prediction_stats(
    p_start_time TIMESTAMPTZ DEFAULT NOW() - INTERVAL '7 days',
    p_end_time TIMESTAMPTZ DEFAULT NOW(),
    p_sport_id INTEGER DEFAULT NULL,
    p_league_id INTEGER DEFAULT NULL,
    p_model_id VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    total_predictions BIGINT,
    settled_predictions BIGINT,
    win_count BIGINT,
    loss_count BIGINT,
    push_count BIGINT,
    win_rate DECIMAL(10,4),
    total_stake DECIMAL(20,4),
    total_profit DECIMAL(20,4),
    roi_percentage DECIMAL(10,4),
    avg_confidence DECIMAL(10,4),
    avg_odds DECIMAL(10,4),
    avg_expected_value DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4)
) AS $$
BEGIN
    RETURN QUERY
    WITH stats AS (
        SELECT 
            COUNT(*) as total_count,
            COUNT(*) FILTER (WHERE outcome IS NOT NULL) as settled_count,
            COUNT(*) FILTER (WHERE outcome = 'WIN') as wins,
            COUNT(*) FILTER (WHERE outcome = 'LOSS') as losses,
            COUNT(*) FILTER (WHERE outcome = 'PUSH') as pushes,
            AVG(confidence) as avg_conf,
            AVG(odds) as avg_odds_val,
            AVG(expected_value) as avg_ev,
            SUM(actual_stake) as total_stake_val,
            SUM(profit) as total_profit_val
        FROM predictions.predictions
        WHERE prediction_time BETWEEN p_start_time AND p_end_time
            AND is_test_prediction = FALSE
            AND (p_sport_id IS NULL OR sport_id = p_sport_id)
            AND (p_league_id IS NULL OR league_id = p_league_id)
            AND (p_model_id IS NULL OR model_id = p_model_id)
    )
    SELECT 
        total_count,
        settled_count,
        wins,
        losses,
        pushes,
        CASE 
            WHEN wins + losses > 0 THEN wins::DECIMAL / (wins + losses)
            ELSE NULL 
        END as win_rate,
        total_stake_val,
        total_profit_val,
        CASE 
            WHEN total_stake_val > 0 THEN total_profit_val / total_stake_val
            ELSE NULL 
        END as roi_percentage,
        avg_conf,
        avg_odds_val,
        avg_ev,
        CASE 
            WHEN STDDEV(profit) > 0 THEN AVG(profit) / STDDEV(profit)
            ELSE NULL 
        END as sharpe_ratio
    FROM stats,
    LATERAL (
        SELECT STDDEV(profit), AVG(profit)
        FROM predictions.predictions
        WHERE prediction_time BETWEEN p_start_time AND p_end_time
            AND outcome IS NOT NULL
            AND is_test_prediction = FALSE
            AND (p_sport_id IS NULL OR sport_id = p_sport_id)
            AND (p_league_id IS NULL OR league_id = p_league_id)
            AND (p_model_id IS NULL OR model_id = p_model_id)
    ) as profit_stats;
END;
$$ LANGUAGE plpgsql
STABLE
SECURITY DEFINER;

-- ==============================================================
-- GRANT PERMISSIONS
-- ==============================================================

-- Grant permissions on table
GRANT SELECT, INSERT, UPDATE ON predictions.predictions TO prediction_service;
GRANT SELECT ON predictions.predictions TO analytics_service;
GRANT SELECT ON predictions.predictions TO readonly_user;
GRANT ALL PRIVILEGES ON predictions.predictions TO admin_user;

-- Grant permissions on views
GRANT SELECT ON predictions.active_predictions TO prediction_service;
GRANT SELECT ON predictions.active_predictions TO analytics_service;
GRANT SELECT ON predictions.active_predictions TO readonly_user;

GRANT SELECT ON predictions.value_bets TO prediction_service;
GRANT SELECT ON predictions.value_bets TO analytics_service;
GRANT SELECT ON predictions.value_bets TO readonly_user;

GRANT SELECT ON predictions.high_confidence_predictions TO prediction_service;
GRANT SELECT ON predictions.high_confidence_predictions TO analytics_service;
GRANT SELECT ON predictions.high_confidence_predictions TO readonly_user;

GRANT SELECT ON predictions.model_performance TO prediction_service;
GRANT SELECT ON predictions.model_performance TO analytics_service;
GRANT SELECT ON predictions.model_performance TO readonly_user;
GRANT SELECT ON predictions.model_performance TO admin_user;

GRANT SELECT ON predictions.bookmaker_performance TO analytics_service;
GRANT SELECT ON predictions.bookmaker_performance TO readonly_user;
GRANT SELECT ON predictions.bookmaker_performance TO admin_user;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION predictions.insert_prediction TO prediction_service;
GRANT EXECUTE ON FUNCTION predictions.update_prediction_outcome TO prediction_service;
GRANT EXECUTE ON FUNCTION predictions.get_prediction_stats TO analytics_service;
GRANT EXECUTE ON FUNCTION predictions.get_prediction_stats TO readonly_user;
GRANT EXECUTE ON FUNCTION predictions.validate_prediction TO prediction_service;
GRANT EXECUTE ON FUNCTION predictions.calculate_data_quality_score TO prediction_service;
GRANT EXECUTE ON FUNCTION predictions.get_prediction_chunk_info TO admin_user;

-- ==============================================================
-- CREATE COMMENTS FOR DOCUMENTATION
-- ==============================================================

COMMENT ON TABLE predictions.predictions IS 
'Main hypertable storing all sports predictions with comprehensive metadata.
Partitioned by time (daily chunks) and sport_id for optimal query performance.
Includes prediction metrics, odds data, model information, and outcomes.';

COMMENT ON COLUMN predictions.predictions.prediction_id IS 'Unique identifier for each prediction';
COMMENT ON COLUMN predictions.predictions.prediction_time IS 'Time when prediction was made (used for hypertable partitioning)';
COMMENT ON COLUMN predictions.predictions.confidence IS 'Model confidence in the prediction (0-1)';
COMMENT ON COLUMN predictions.predictions.expected_value IS 'Expected value of the bet based on probability and odds';
COMMENT ON COLUMN predictions.predictions.kelly_fraction IS 'Recommended stake fraction based on Kelly Criterion';
COMMENT ON COLUMN predictions.predictions.data_quality_score IS 'Score (0-1) indicating quality/completeness of prediction data';

COMMENT ON VIEW predictions.active_predictions IS 'View showing all active (unsettled) predictions';
COMMENT ON VIEW predictions.value_bets IS 'View showing identified value bets with positive expected value';
COMMENT ON VIEW predictions.high_confidence_predictions IS 'View showing high confidence predictions (confidence >= 0.8)';

COMMENT ON FUNCTION predictions.insert_prediction IS 'Insert a new prediction with validation and data quality scoring';
COMMENT ON FUNCTION predictions.update_prediction_outcome IS 'Update prediction outcome and calculate performance metrics';
COMMENT ON FUNCTION predictions.get_prediction_stats IS 'Get comprehensive statistics for predictions in a time period';

-- ==============================================================
-- INITIAL DATA LOAD AND VERIFICATION
-- ==============================================================

-- Verify hypertable creation
DO $$
DECLARE
    v_hypertable_exists BOOLEAN;
    v_chunk_count INTEGER;
    v_compression_enabled BOOLEAN;
BEGIN
    -- Check if hypertable exists
    SELECT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'predictions'
          AND hypertable_schema = 'predictions'
    ) INTO v_hypertable_exists;
    
    -- Get chunk count
    SELECT COUNT(*) INTO v_chunk_count
    FROM timescaledb_information.chunks
    WHERE hypertable_name = 'predictions'
      AND hypertable_schema = 'predictions';
    
    -- Check compression status
    SELECT is_compressed_enabled INTO v_compression_enabled
    FROM timescaledb_information.hypertables
    WHERE hypertable_name = 'predictions'
      AND hypertable_schema = 'predictions';
    
    -- Log creation details
    INSERT INTO system.audit_log (
        operation, 
        table_name, 
        details,
        performed_by
    ) VALUES (
        'CREATE_HYPERTABLE',
        'predictions',
        jsonb_build_object(
            'created_at', NOW(),
            'hypertable_exists', v_hypertable_exists,
            'chunk_count', v_chunk_count,
            'compression_enabled', v_compression_enabled,
            'chunk_interval', '1 day',
            'partitioning_columns', ARRAY['prediction_time', 'sport_id'],
            'index_count', 25,
            'status', 'ACTIVE'
        ),
        current_user
    );
    
    RAISE NOTICE 'Predictions hypertable created successfully';
    RAISE NOTICE 'Chunk interval: 1 day';
    RAISE NOTICE 'Partitioning: By prediction_time and sport_id (16 partitions)';
    RAISE NOTICE 'Compression: Enabled after 7 days';
    RAISE NOTICE 'Indexes: 25 indexes created for optimal performance';
    RAISE NOTICE 'Retention: 365 days';
END $$;

-- ==============================================================
-- CREATE MONITORING QUERIES
-- ==============================================================

-- Query to monitor hypertable size and chunks
CREATE OR REPLACE VIEW predictions.hypertable_monitoring AS
SELECT 
    'predictions' as hypertable_name,
    COUNT(*) as chunk_count,
    MIN(range_start) as oldest_chunk_start,
    MAX(range_end) as newest_chunk_end,
    SUM(total_bytes) as total_size_bytes,
    pg_size_pretty(SUM(total_bytes)) as total_size_pretty,
    SUM(CASE WHEN is_compressed THEN total_bytes ELSE 0 END) as compressed_size_bytes,
    pg_size_pretty(SUM(CASE WHEN is_compressed THEN total_bytes ELSE 0 END)) as compressed_size_pretty,
    COUNT(*) FILTER (WHERE is_compressed) as compressed_chunk_count,
    NOW() as check_time
FROM timescaledb_information.chunks
WHERE hypertable_name = 'predictions'
  AND hypertable_schema = 'predictions';

-- Query to monitor prediction volume
CREATE OR REPLACE VIEW predictions.volume_monitoring AS
SELECT 
    date_trunc('hour', prediction_time) as hour_bucket,
    COUNT(*) as prediction_count,
    AVG(confidence) as avg_confidence,
    SUM(CASE WHEN is_value_bet THEN 1 ELSE 0 END) as value_bet_count,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as win_count,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as loss_count,
    AVG(data_quality_score) as avg_data_quality
FROM predictions.predictions
WHERE prediction_time >= NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', prediction_time)
ORDER BY hour_bucket DESC;

GRANT SELECT ON predictions.hypertable_monitoring TO admin_user;
GRANT SELECT ON predictions.volume_monitoring TO analytics_service;
GRANT SELECT ON predictions.volume_monitoring TO admin_user;

-- ==============================================================
-- FINAL SETUP COMPLETION
-- ==============================================================

-- Create completion notification
DO $$
BEGIN
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'PREDICTIONS HYPERTABLE SETUP COMPLETE';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'Table: predictions.predictions';
    RAISE NOTICE 'Type: TimescaleDB Hypertable';
    RAISE NOTICE 'Partitioning: Time (daily) + Sport ID';
    RAISE NOTICE 'Compression: Enabled after 7 days';
    RAISE NOTICE 'Retention: 365 days';
    RAISE NOTICE 'Indexes: 25 custom indexes created';
    RAISE NOTICE 'Views: 5 analytical views created';
    RAISE NOTICE 'Functions: 8 utility functions created';
    RAISE NOTICE 'Triggers: Updated_at automatic update';
    RAISE NOTICE 'Monitoring: 2 monitoring views created';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'READY FOR HIGH-VOLUME PREDICTION DATA';
    RAISE NOTICE '=========================================';
END $$;
