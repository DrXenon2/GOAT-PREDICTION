-- database/supabase/functions/calculate_metrics.sql
-- Fonction de calcul des métriques pour Goat Prediction
-- Version: 2.0.0
-- Date: 2026-01-16

-- ============================================
-- 1. FONCTIONS DE CALCUL DES MÉTRIQUES DE BASE
-- ============================================

-- Fonction pour calculer la précision globale
CREATE OR REPLACE FUNCTION calculate_accuracy(
    correct_predictions INTEGER,
    total_predictions INTEGER
) 
RETURNS DECIMAL(5,4) AS $$
BEGIN
    IF total_predictions = 0 THEN
        RETURN 0;
    END IF;
    RETURN ROUND(correct_predictions::DECIMAL / total_predictions::DECIMAL, 4);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour calculer le ROI (Return on Investment)
CREATE OR REPLACE FUNCTION calculate_roi(
    total_stake DECIMAL(10,2),
    total_return DECIMAL(10,2)
) 
RETURNS DECIMAL(7,4) AS $$
BEGIN
    IF total_stake = 0 THEN
        RETURN 0;
    END IF;
    RETURN ROUND(((total_return - total_stake) / total_stake) * 100, 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour calculer le Profit Factor
CREATE OR REPLACE FUNCTION calculate_profit_factor(
    gross_profit DECIMAL(10,2),
    gross_loss DECIMAL(10,2)
) 
RETURNS DECIMAL(6,2) AS $$
BEGIN
    IF gross_loss = 0 THEN
        RETURN 100.00; -- Arbitrary large number for no losses
    END IF;
    RETURN ROUND(gross_profit / ABS(gross_loss), 2);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Fonction pour calculer le Sharpe Ratio
CREATE OR REPLACE FUNCTION calculate_sharpe_ratio(
    avg_daily_return DECIMAL(10,4),
    risk_free_rate DECIMAL(5,4),
    std_dev_daily_return DECIMAL(10,4)
)
RETURNS DECIMAL(8,4) AS $$
BEGIN
    IF std_dev_daily_return = 0 THEN
        RETURN 0;
    END IF;
    RETURN ROUND((avg_daily_return - risk_free_rate) / std_dev_daily_return, 4);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- 2. FONCTIONS POUR LES PRÉDICTIONS
-- ============================================

-- Fonction pour calculer la précision par sport
CREATE OR REPLACE FUNCTION calculate_sport_accuracy(
    sport_id UUID,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    sport_id UUID,
    sport_name VARCHAR(100),
    total_predictions BIGINT,
    correct_predictions BIGINT,
    accuracy DECIMAL(5,4),
    profit DECIMAL(10,2),
    roi DECIMAL(7,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH prediction_stats AS (
        SELECT 
            s.id,
            s.name,
            COUNT(p.id) as total,
            COUNT(p.id) FILTER (WHERE p.is_correct = true) as correct,
            COALESCE(SUM(b.profit_loss), 0) as total_profit
        FROM predictions p
        JOIN matches m ON p.match_id = m.id
        JOIN sports s ON m.sport_id = s.id
        LEFT JOIN bets b ON p.id = b.prediction_id
        WHERE s.id = calculate_sport_accuracy.sport_id
        AND (calculate_sport_accuracy.start_date IS NULL OR m.match_date >= calculate_sport_accuracy.start_date)
        AND (calculate_sport_accuracy.end_date IS NULL OR m.match_date <= calculate_sport_accuracy.end_date)
        AND p.status = 'settled'
        GROUP BY s.id, s.name
    )
    SELECT 
        ps.id,
        ps.name,
        ps.total,
        ps.correct,
        calculate_accuracy(ps.correct::INTEGER, ps.total::INTEGER) as accuracy,
        ps.total_profit,
        calculate_roi(ps.total * 10, ps.total_profit + (ps.total * 10)) as roi -- Assuming average stake of 10
    FROM prediction_stats ps;
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction pour calculer la précision par marché
CREATE OR REPLACE FUNCTION calculate_market_accuracy(
    market_type VARCHAR(50),
    sport_id UUID DEFAULT NULL,
    days_back INTEGER DEFAULT 30
)
RETURNS TABLE (
    market_type VARCHAR(50),
    total_predictions BIGINT,
    correct_predictions BIGINT,
    accuracy DECIMAL(5,4),
    avg_confidence DECIMAL(4,3),
    avg_odds DECIMAL(6,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH market_stats AS (
        SELECT 
            p.market_type,
            COUNT(p.id) as total,
            COUNT(p.id) FILTER (WHERE p.is_correct = true) as correct,
            AVG(p.confidence) as avg_conf,
            AVG(p.implied_odds) as avg_odds
        FROM predictions p
        JOIN matches m ON p.match_id = m.id
        WHERE p.market_type = calculate_market_accuracy.market_type
        AND (calculate_market_accuracy.sport_id IS NULL OR m.sport_id = calculate_market_accuracy.sport_id)
        AND m.match_date >= CURRENT_DATE - (calculate_market_accuracy.days_back || ' days')::INTERVAL
        AND p.status = 'settled'
        GROUP BY p.market_type
    )
    SELECT 
        ms.market_type,
        ms.total,
        ms.correct,
        calculate_accuracy(ms.correct::INTEGER, ms.total::INTEGER) as accuracy,
        ROUND(ms.avg_conf::DECIMAL, 3),
        ROUND(ms.avg_odds::DECIMAL, 2)
    FROM market_stats ms;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 3. FONCTIONS POUR LES PARIS
-- ============================================

-- Fonction pour calculer les métriques de betting
CREATE OR REPLACE FUNCTION calculate_betting_metrics(
    user_id UUID DEFAULT NULL,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    total_bets BIGINT,
    winning_bets BIGINT,
    losing_bets BIGINT,
    void_bets BIGINT,
    win_rate DECIMAL(5,4),
    total_stake DECIMAL(12,2),
    total_return DECIMAL(12,2),
    total_profit DECIMAL(12,2),
    roi DECIMAL(7,2),
    avg_odds DECIMAL(6,2),
    avg_stake DECIMAL(10,2),
    biggest_win DECIMAL(10,2),
    biggest_loss DECIMAL(10,2),
    profit_factor DECIMAL(6,2),
    strike_rate DECIMAL(5,4)
) AS $$
BEGIN
    RETURN QUERY
    WITH bet_stats AS (
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            COUNT(*) FILTER (WHERE status = 'lost') as lost,
            COUNT(*) FILTER (WHERE status = 'void') as voided,
            SUM(stake) as total_stake,
            SUM(payout) as total_payout,
            AVG(odds) as avg_odds_val,
            AVG(stake) as avg_stake_val,
            MAX(CASE WHEN status = 'won' THEN payout - stake ELSE 0 END) as max_win,
            MAX(CASE WHEN status = 'lost' THEN stake ELSE 0 END) as max_loss,
            SUM(CASE WHEN status = 'won' THEN payout - stake ELSE 0 END) as gross_profit,
            SUM(CASE WHEN status = 'lost' THEN stake ELSE 0 END) as gross_loss,
            COUNT(DISTINCT DATE(placed_at)) as betting_days
        FROM bets
        WHERE (calculate_betting_metrics.user_id IS NULL OR user_id = calculate_betting_metrics.user_id)
        AND (calculate_betting_metrics.start_date IS NULL OR DATE(placed_at) >= calculate_betting_metrics.start_date)
        AND (calculate_betting_metrics.end_date IS NULL OR DATE(placed_at) <= calculate_betting_metrics.end_date)
        AND status IN ('won', 'lost', 'void')
    )
    SELECT 
        bs.total,
        bs.won,
        bs.lost,
        bs.voided,
        calculate_accuracy(bs.won::INTEGER, (bs.won + bs.lost)::INTEGER) as win_rate,
        COALESCE(bs.total_stake, 0),
        COALESCE(bs.total_payout, 0),
        COALESCE(bs.total_payout - bs.total_stake, 0) as total_profit,
        calculate_roi(COALESCE(bs.total_stake, 0), COALESCE(bs.total_payout, 0)) as roi,
        ROUND(COALESCE(bs.avg_odds_val, 0)::DECIMAL, 2),
        ROUND(COALESCE(bs.avg_stake_val, 0)::DECIMAL, 2),
        COALESCE(bs.max_win, 0),
        COALESCE(bs.max_loss, 0),
        calculate_profit_factor(COALESCE(bs.gross_profit, 0), COALESCE(bs.gross_loss, 0)) as profit_factor,
        CASE 
            WHEN bs.betting_days > 0 THEN ROUND(bs.total::DECIMAL / bs.betting_days::DECIMAL, 2)
            ELSE 0 
        END as strike_rate
    FROM bet_stats bs;
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction pour calculer le ROI par sport
CREATE OR REPLACE FUNCTION calculate_roi_by_sport(
    user_id UUID DEFAULT NULL,
    days_back INTEGER DEFAULT 90
)
RETURNS TABLE (
    sport_id UUID,
    sport_name VARCHAR(100),
    total_bets BIGINT,
    winning_bets BIGINT,
    win_rate DECIMAL(5,4),
    total_stake DECIMAL(12,2),
    total_return DECIMAL(12,2),
    total_profit DECIMAL(12,2),
    roi DECIMAL(7,2),
    avg_odds DECIMAL(6,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH sport_bets AS (
        SELECT 
            s.id as sport_id,
            s.name as sport_name,
            COUNT(b.id) as total_bets,
            COUNT(b.id) FILTER (WHERE b.status = 'won') as winning_bets,
            SUM(b.stake) as total_stake,
            SUM(b.payout) as total_return,
            AVG(b.odds) as avg_odds
        FROM bets b
        JOIN predictions p ON b.prediction_id = p.id
        JOIN matches m ON p.match_id = m.id
        JOIN sports s ON m.sport_id = s.id
        WHERE (calculate_roi_by_sport.user_id IS NULL OR b.user_id = calculate_roi_by_sport.user_id)
        AND b.placed_at >= CURRENT_DATE - (calculate_roi_by_sport.days_back || ' days')::INTERVAL
        AND b.status IN ('won', 'lost')
        GROUP BY s.id, s.name
    )
    SELECT 
        sb.sport_id,
        sb.sport_name,
        sb.total_bets,
        sb.winning_bets,
        calculate_accuracy(sb.winning_bets::INTEGER, sb.total_bets::INTEGER) as win_rate,
        COALESCE(sb.total_stake, 0),
        COALESCE(sb.total_return, 0),
        COALESCE(sb.total_return - sb.total_stake, 0) as total_profit,
        calculate_roi(COALESCE(sb.total_stake, 0), COALESCE(sb.total_return, 0)) as roi,
        ROUND(COALESCE(sb.avg_odds, 0)::DECIMAL, 2)
    FROM sport_bets sb
    ORDER BY roi DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 4. FONCTIONS POUR LE RISK MANAGEMENT
-- ============================================

-- Fonction pour calculer le drawdown
CREATE OR REPLACE FUNCTION calculate_drawdown(
    user_id UUID,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    max_drawdown DECIMAL(10,2),
    max_drawdown_percent DECIMAL(7,2),
    avg_drawdown DECIMAL(10,2),
    drawdown_duration_days INTEGER
) AS $$
DECLARE
    peak_balance DECIMAL(12,2) := 0;
    current_balance DECIMAL(12,2) := 0;
    max_dd DECIMAL(12,2) := 0;
    max_dd_percent DECIMAL(7,2) := 0;
    total_dd DECIMAL(12,2) := 0;
    dd_count INTEGER := 0;
    in_drawdown BOOLEAN := false;
    dd_start_date DATE;
    max_dd_duration INTEGER := 0;
BEGIN
    FOR balance_rec IN 
        SELECT 
            DATE(created_at) as balance_date,
            balance
        FROM user_balance_history
        WHERE user_id = calculate_drawdown.user_id
        AND (calculate_drawdown.start_date IS NULL OR DATE(created_at) >= calculate_drawdown.start_date)
        AND (calculate_drawdown.end_date IS NULL OR DATE(created_at) <= calculate_drawdown.end_date)
        ORDER BY created_at
    LOOP
        current_balance := balance_rec.balance;
        
        -- Update peak balance
        IF current_balance > peak_balance THEN
            peak_balance := current_balance;
            in_drawdown := false;
        END IF;
        
        -- Calculate drawdown
        IF current_balance < peak_balance THEN
            IF NOT in_drawdown THEN
                in_drawdown := true;
                dd_start_date := balance_rec.balance_date;
            END IF;
            
            DECLARE
                drawdown_amount DECIMAL(12,2) := peak_balance - current_balance;
                drawdown_percent DECIMAL(7,2) := (drawdown_amount / peak_balance) * 100;
                drawdown_duration INTEGER := EXTRACT(DAY FROM (balance_rec.balance_date - dd_start_date));
            BEGIN
                -- Update max drawdown
                IF drawdown_amount > max_dd THEN
                    max_dd := drawdown_amount;
                    max_dd_percent := drawdown_percent;
                    max_dd_duration := drawdown_duration;
                END IF;
                
                -- Accumulate for average
                total_dd := total_dd + drawdown_amount;
                dd_count := dd_count + 1;
            END;
        END IF;
    END LOOP;
    
    RETURN QUERY
    SELECT 
        COALESCE(max_dd, 0),
        COALESCE(max_dd_percent, 0),
        CASE WHEN dd_count > 0 THEN ROUND(total_dd / dd_count, 2) ELSE 0 END,
        COALESCE(max_dd_duration, 0);
END;
$$ LANGUAGE plpgsql STABLE;

-- Fonction pour calculer le Value at Risk (VaR)
CREATE OR REPLACE FUNCTION calculate_var(
    user_id UUID,
    confidence_level DECIMAL(4,3) DEFAULT 0.95,
    lookback_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    var_95 DECIMAL(10,2),
    var_99 DECIMAL(10,2),
    expected_shortfall DECIMAL(10,2),
    worst_loss DECIMAL(10,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH daily_returns AS (
        SELECT 
            DATE(placed_at) as bet_date,
            SUM(payout - stake) as daily_profit
        FROM bets
        WHERE user_id = calculate_var.user_id
        AND placed_at >= CURRENT_DATE - (calculate_var.lookback_days || ' days')::INTERVAL
        AND status IN ('won', 'lost')
        GROUP BY DATE(placed_at)
        ORDER BY daily_profit
    ),
    var_calc AS (
        SELECT 
            PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY daily_profit) as var_95,
            PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY daily_profit) as var_99,
            AVG(daily_profit) FILTER (WHERE daily_profit <= PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY daily_profit)) as expected_shortfall,
            MIN(daily_profit) as worst_loss
        FROM daily_returns
    )
    SELECT 
        COALESCE(ABS(vc.var_95), 0),
        COALESCE(ABS(vc.var_99), 0),
        COALESCE(ABS(vc.expected_shortfall), 0),
        COALESCE(ABS(vc.worst_loss), 0)
    FROM var_calc vc;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 5. FONCTIONS POUR LES MODÈLES ML
-- ============================================

-- Fonction pour calculer les métriques de performance des modèles
CREATE OR REPLACE FUNCTION calculate_model_performance(
    model_id UUID,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    model_name VARCHAR(255),
    sport_name VARCHAR(100),
    market_type VARCHAR(50),
    total_predictions BIGINT,
    correct_predictions BIGINT,
    accuracy DECIMAL(5,4),
    avg_confidence DECIMAL(4,3),
    brier_score DECIMAL(5,4),
    log_loss DECIMAL(6,4),
    roc_auc DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4)
) AS $$
BEGIN
    RETURN QUERY
    WITH model_predictions AS (
        SELECT 
            mlm.name as model_name,
            s.name as sport_name,
            p.market_type,
            COUNT(p.id) as total,
            COUNT(p.id) FILTER (WHERE p.is_correct = true) as correct,
            AVG(p.confidence) as avg_conf,
            -- Brier Score: mean squared difference between predicted probability and actual outcome
            AVG(POWER(p.confidence - CASE WHEN p.is_correct THEN 1 ELSE 0 END, 2)) as brier,
            -- Log Loss: negative log likelihood
            AVG(-1 * (CASE WHEN p.is_correct THEN LN(GREATEST(p.confidence, 0.0001)) 
                          ELSE LN(GREATEST(1 - p.confidence, 0.0001)) END)) as logloss,
            -- For ROC AUC we need more complex calculation
            COUNT(p.id) FILTER (WHERE p.is_correct = true AND p.confidence >= 0.5) as true_positives,
            COUNT(p.id) FILTER (WHERE p.is_correct = false AND p.confidence >= 0.5) as false_positives,
            COUNT(p.id) FILTER (WHERE p.is_correct = true AND p.confidence < 0.5) as false_negatives,
            COUNT(p.id) FILTER (WHERE p.is_correct = false AND p.confidence < 0.5) as true_negatives
        FROM predictions p
        JOIN ml_models mlm ON p.model_id = mlm.id
        JOIN matches m ON p.match_id = m.id
        JOIN sports s ON m.sport_id = s.id
        WHERE p.model_id = calculate_model_performance.model_id
        AND (calculate_model_performance.start_date IS NULL OR m.match_date >= calculate_model_performance.start_date)
        AND (calculate_model_performance.end_date IS NULL OR m.match_date <= calculate_model_performance.end_date)
        AND p.status = 'settled'
        GROUP BY mlm.name, s.name, p.market_type
    )
    SELECT 
        mp.model_name,
        mp.sport_name,
        mp.market_type,
        mp.total,
        mp.correct,
        calculate_accuracy(mp.correct::INTEGER, mp.total::INTEGER) as accuracy,
        ROUND(mp.avg_conf::DECIMAL, 3),
        ROUND(mp.brier::DECIMAL, 4),
        ROUND(mp.logloss::DECIMAL, 4),
        -- ROC AUC approximation
        ROUND(
            (mp.true_positives::DECIMAL / (mp.true_positives + mp.false_negatives) +
             mp.true_negatives::DECIMAL / (mp.true_negatives + mp.false_positives)) / 2, 4
        ) as roc_auc,
        -- Precision
        ROUND(
            CASE WHEN mp.true_positives + mp.false_positives > 0 
                 THEN mp.true_positives::DECIMAL / (mp.true_positives + mp.false_positives)
                 ELSE 0 END, 4
        ) as precision,
        -- Recall
        ROUND(
            CASE WHEN mp.true_positives + mp.false_negatives > 0
                 THEN mp.true_positives::DECIMAL / (mp.true_positives + mp.false_negatives)
                 ELSE 0 END, 4
        ) as recall,
        -- F1 Score
        ROUND(
            CASE WHEN (mp.true_positives + mp.false_positives > 0) AND (mp.true_positives + mp.false_negatives > 0)
                 THEN 2 * (mp.true_positives::DECIMAL / (mp.true_positives + mp.false_positives)) *
                          (mp.true_positives::DECIMAL / (mp.true_positives + mp.false_negatives)) /
                          ((mp.true_positives::DECIMAL / (mp.true_positives + mp.false_positives)) +
                           (mp.true_positives::DECIMAL / (mp.true_positives + mp.false_negatives)))
                 ELSE 0 END, 4
        ) as f1_score
    FROM model_predictions mp;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 6. FONCTIONS POUR LES UTILISATEURS
-- ============================================

-- Fonction pour calculer les classements des utilisateurs
CREATE OR REPLACE FUNCTION calculate_user_leaderboard(
    sport_id UUID DEFAULT NULL,
    time_period VARCHAR(20) DEFAULT 'monthly' -- daily, weekly, monthly, yearly, all_time
)
RETURNS TABLE (
    user_id UUID,
    username VARCHAR(255),
    total_profit DECIMAL(12,2),
    roi DECIMAL(7,2),
    win_rate DECIMAL(5,4),
    total_bets BIGINT,
    rank INTEGER
) AS $$
DECLARE
    start_date DATE;
BEGIN
    -- Determine start date based on time period
    CASE time_period
        WHEN 'daily' THEN
            start_date := CURRENT_DATE;
        WHEN 'weekly' THEN
            start_date := CURRENT_DATE - INTERVAL '7 days';
        WHEN 'monthly' THEN
            start_date := CURRENT_DATE - INTERVAL '30 days';
        WHEN 'yearly' THEN
            start_date := CURRENT_DATE - INTERVAL '365 days';
        ELSE
            start_date := NULL; -- all time
    END CASE;
    
    RETURN QUERY
    WITH user_stats AS (
        SELECT 
            u.id as user_id,
            u.username,
            SUM(b.payout - b.stake) as total_profit,
            SUM(b.stake) as total_stake,
            SUM(b.payout) as total_return,
            COUNT(b.id) as total_bets,
            COUNT(b.id) FILTER (WHERE b.status = 'won') as winning_bets
        FROM users u
        JOIN bets b ON u.id = b.user_id
        JOIN predictions p ON b.prediction_id = p.id
        JOIN matches m ON p.match_id = m.id
        WHERE (calculate_user_leaderboard.sport_id IS NULL OR m.sport_id = calculate_user_leaderboard.sport_id)
        AND (start_date IS NULL OR b.placed_at >= start_date)
        AND b.status IN ('won', 'lost')
        GROUP BY u.id, u.username
        HAVING COUNT(b.id) >= 10 -- Minimum 10 bets to qualify
    ),
    ranked_users AS (
        SELECT 
            us.user_id,
            us.username,
            COALESCE(us.total_profit, 0) as total_profit,
            calculate_roi(COALESCE(us.total_stake, 0), COALESCE(us.total_return, 0)) as roi,
            calculate_accuracy(us.winning_bets::INTEGER, us.total_bets::INTEGER) as win_rate,
            us.total_bets,
            RANK() OVER (ORDER BY COALESCE(us.total_profit, 0) DESC) as user_rank
        FROM user_stats us
    )
    SELECT *
    FROM ranked_users
    ORDER BY user_rank
    LIMIT 100;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 7. FONCTIONS DE RAPPORT DÉTAILLÉ
-- ============================================

-- Fonction pour générer un rapport complet de performance
CREATE OR REPLACE FUNCTION generate_performance_report(
    user_id UUID DEFAULT NULL,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    report_section VARCHAR(50),
    metric_name VARCHAR(100),
    metric_value DECIMAL(12,4),
    metric_unit VARCHAR(50),
    description TEXT
) AS $$
BEGIN
    -- Section 1: Betting Performance
    RETURN QUERY
    SELECT 
        'Betting Performance'::VARCHAR(50) as report_section,
        'Total Bets'::VARCHAR(100) as metric_name,
        total_bets::DECIMAL as metric_value,
        'count'::VARCHAR(50) as metric_unit,
        'Total number of placed bets'::TEXT as description
    FROM calculate_betting_metrics(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Betting Performance',
        'Win Rate',
        win_rate,
        'percentage',
        'Percentage of winning bets'
    FROM calculate_betting_metrics(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Betting Performance',
        'ROI',
        roi,
        'percentage',
        'Return on Investment'
    FROM calculate_betting_metrics(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Betting Performance',
        'Profit Factor',
        profit_factor,
        'ratio',
        'Gross profit divided by gross loss'
    FROM calculate_betting_metrics(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Betting Performance',
        'Total Profit',
        total_profit,
        'currency',
        'Net profit/loss'
    FROM calculate_betting_metrics(user_id, start_date, end_date);
    
    -- Section 2: Risk Metrics
    RETURN QUERY
    SELECT 
        'Risk Metrics'::VARCHAR(50),
        'Max Drawdown',
        max_drawdown,
        'currency',
        'Maximum peak-to-trough decline'
    FROM calculate_drawdown(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Risk Metrics',
        'Max Drawdown %',
        max_drawdown_percent,
        'percentage',
        'Maximum drawdown as percentage of peak'
    FROM calculate_drawdown(user_id, start_date, end_date)
    UNION ALL
    SELECT 
        'Risk Metrics',
        'VaR (95%)',
        var_95,
        'currency',
        'Value at Risk at 95% confidence'
    FROM calculate_var(user_id, 0.95, 90)
    UNION ALL
    SELECT 
        'Risk Metrics',
        'Expected Shortfall',
        expected_shortfall,
        'currency',
        'Average loss in worst 5% of cases'
    FROM calculate_var(user_id, 0.95, 90);
    
    -- Section 3: Model Performance (if user has predictions)
    IF EXISTS (SELECT 1 FROM predictions WHERE user_id = generate_performance_report.user_id) THEN
        RETURN QUERY
        SELECT 
            'Model Performance'::VARCHAR(50),
            'Prediction Accuracy',
            AVG(accuracy),
            'percentage',
            'Overall prediction accuracy'
        FROM calculate_sport_accuracy(NULL, start_date, end_date)
        UNION ALL
        SELECT 
            'Model Performance',
            'Average Confidence',
            AVG(avg_confidence),
            'score',
            'Average confidence score of predictions'
        FROM calculate_market_accuracy('match_winner', NULL, 90);
    END IF;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 8. FONCTIONS DE CALCUL EN TEMPS RÉEL
-- ============================================

-- Fonction pour mettre à jour les métriques en temps réel (à appeler via triggers)
CREATE OR REPLACE FUNCTION update_realtime_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Cette fonction est appelée par des triggers pour mettre à jour les métriques en temps réel
    -- Elle met à jour les tables de cache des métriques
    
    -- Mettre à jour les métriques utilisateur
    IF TG_TABLE_NAME = 'bets' THEN
        -- Mettre à jour les statistiques de l'utilisateur
        PERFORM refresh_user_stats(NEW.user_id);
        
        -- Mettre à jour les classements
        PERFORM refresh_leaderboards();
        
        -- Mettre à jour les métriques de sport
        PERFORM refresh_sport_metrics();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour rafraîchir les statistiques utilisateur
CREATE OR REPLACE FUNCTION refresh_user_stats(target_user_id UUID)
RETURNS VOID AS $$
BEGIN
    -- Supprimer les anciennes statistiques
    DELETE FROM user_statistics_cache WHERE user_id = target_user_id;
    
    -- Insérer les nouvelles statistiques
    INSERT INTO user_statistics_cache (
        user_id,
        total_bets,
        winning_bets,
        losing_bets,
        win_rate,
        total_stake,
        total_return,
        total_profit,
        roi,
        profit_factor,
        last_updated
    )
    SELECT 
        user_id,
        total_bets,
        winning_bets,
        losing_bets,
        win_rate,
        total_stake,
        total_return,
        total_profit,
        roi,
        profit_factor,
        NOW()
    FROM calculate_betting_metrics(target_user_id);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 9. FONCTIONS D'ANALYSE AVANCÉE
-- ============================================

-- Fonction pour analyser les tendances de performance
CREATE OR REPLACE FUNCTION analyze_performance_trends(
    user_id UUID,
    metric_type VARCHAR(50), -- 'accuracy', 'roi', 'profit'
    window_size INTEGER DEFAULT 7,
    lookback_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    period_date DATE,
    metric_value DECIMAL(10,4),
    moving_avg DECIMAL(10,4),
    trend_direction VARCHAR(10),
    trend_strength DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    WITH daily_metrics AS (
        SELECT 
            DATE(b.placed_at) as metric_date,
            CASE metric_type
                WHEN 'accuracy' THEN 
                    COUNT(b.id) FILTER (WHERE b.status = 'won')::DECIMAL / 
                    NULLIF(COUNT(b.id) FILTER (WHERE b.status IN ('won', 'lost')), 0)
                WHEN 'roi' THEN 
                    (SUM(CASE WHEN b.status = 'won' THEN b.payout - b.stake ELSE -b.stake END) /
                     NULLIF(SUM(b.stake), 0)) * 100
                WHEN 'profit' THEN 
                    SUM(CASE WHEN b.status = 'won' THEN b.payout - b.stake ELSE -b.stake END)
                ELSE 0
            END as daily_value
        FROM bets b
        WHERE b.user_id = analyze_performance_trends.user_id
        AND b.placed_at >= CURRENT_DATE - (lookback_days || ' days')::INTERVAL
        AND b.status IN ('won', 'lost')
        GROUP BY DATE(b.placed_at)
    ),
    moving_stats AS (
        SELECT 
            metric_date,
            daily_value,
            AVG(daily_value) OVER (
                ORDER BY metric_date 
                ROWS BETWEEN window_size - 1 PRECEDING AND CURRENT ROW
            ) as moving_average,
            STDDEV(daily_value) OVER (
                ORDER BY metric_date 
                ROWS BETWEEN window_size - 1 PRECEDING AND CURRENT ROW
            ) as moving_stddev
        FROM daily_metrics
    )
    SELECT 
        ms.metric_date,
        COALESCE(ms.daily_value, 0),
        COALESCE(ms.moving_average, 0),
        CASE 
            WHEN ms.daily_value > ms.moving_average THEN 'up'
            WHEN ms.daily_value < ms.moving_average THEN 'down'
            ELSE 'stable'
        END as trend,
        CASE 
            WHEN ms.moving_stddev > 0 
            THEN ABS((ms.daily_value - ms.moving_average) / ms.moving_stddev)
            ELSE 0 
        END as strength
    FROM moving_stats ms
    ORDER BY ms.metric_date;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 10. FONCTIONS DE VALIDATION
-- ============================================

-- Fonction pour valider les données de métriques
CREATE OR REPLACE FUNCTION validate_metrics_data()
RETURNS TABLE (
    validation_type VARCHAR(50),
    table_name VARCHAR(100),
    issue_count INTEGER,
    issue_description TEXT,
    severity VARCHAR(20)
) AS $$
BEGIN
    -- Validation 1: Bets avec des montants négatifs
    RETURN QUERY
    SELECT 
        'Data Integrity'::VARCHAR(50),
        'bets'::VARCHAR(100),
        COUNT(*)::INTEGER,
        'Bets with negative stakes or odds'::TEXT,
        'HIGH'::VARCHAR(20)
    FROM bets
    WHERE stake < 0 OR odds < 1.0
    UNION ALL
    
    -- Validation 2: Prédictions sans correspondance
    SELECT 
        'Referential Integrity',
        'predictions',
        COUNT(*)::INTEGER,
        'Predictions without valid match reference',
        'HIGH'
    FROM predictions p
    LEFT JOIN matches m ON p.match_id = m.id
    WHERE m.id IS NULL
    UNION ALL
    
    -- Validation 3: Métriques de performance invalides
    SELECT 
        'Business Logic',
        'user_statistics_cache',
        COUNT(*)::INTEGER,
        'Cached statistics with invalid calculations',
        'MEDIUM'
    FROM user_statistics_cache
    WHERE win_rate < 0 OR win_rate > 1
       OR roi < -100 OR roi > 10000
       OR profit_factor < 0;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================
-- 11. TRIGGERS POUR LA MISE À JOUR AUTOMATIQUE
-- ============================================

-- Trigger pour mettre à jour les métriques après chaque pari
CREATE OR REPLACE FUNCTION bets_update_metrics()
RETURNS TRIGGER AS $$
BEGIN
    -- Appeler la fonction de mise à jour en temps réel
    PERFORM refresh_user_stats(NEW.user_id);
    
    -- Mettre à jour les métriques globales si nécessaire
    IF NEW.status IN ('won', 'lost') THEN
        PERFORM refresh_sport_metrics();
        PERFORM refresh_leaderboards();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour mettre à jour les métriques après chaque prédiction
CREATE OR REPLACE FUNCTION predictions_update_metrics()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'settled' AND OLD.status != 'settled' THEN
        -- Mettre à jour les métriques du modèle
        PERFORM refresh_model_metrics(NEW.model_id);
        
        -- Mettre à jour les métriques de sport
        PERFORM refresh_sport_metrics();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 12. FONCTIONS DE SUPPORT
-- ============================================

-- Fonction pour rafraîchir les métriques de sport
CREATE OR REPLACE FUNCTION refresh_sport_metrics()
RETURNS VOID AS $$
BEGIN
    -- Implémentation simplifiée
    -- En production, cette fonction serait plus complexe
    RAISE NOTICE 'Refreshing sport metrics...';
END;
$$ LANGUAGE plpgsql;

-- Fonction pour rafraîchir les classements
CREATE OR REPLACE FUNCTION refresh_leaderboards()
RETURNS VOID AS $$
BEGIN
    -- Implémentation simplifiée
    RAISE NOTICE 'Refreshing leaderboards...';
END;
$$ LANGUAGE plpgsql;

-- Fonction pour rafraîchir les métriques de modèle
CREATE OR REPLACE FUNCTION refresh_model_metrics(model_uuid UUID)
RETURNS VOID AS $$
BEGIN
    -- Implémentation simplifiée
    RAISE NOTICE 'Refreshing model metrics for %', model_uuid;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- COMMENTAIRES ET DOCUMENTATION
-- ============================================

COMMENT ON FUNCTION calculate_accuracy IS 'Calcule la précision basée sur les prédictions correctes et totales';
COMMENT ON FUNCTION calculate_roi IS 'Calcule le Return on Investment en pourcentage';
COMMENT ON FUNCTION calculate_profit_factor IS 'Calcule le facteur de profit (profit brut / perte brute)';
COMMENT ON FUNCTION calculate_sharpe_ratio IS 'Calcule le ratio de Sharpe pour les rendements ajustés au risque';

COMMENT ON FUNCTION calculate_sport_accuracy IS 'Calcule la précision des prédictions par sport';
COMMENT ON FUNCTION calculate_market_accuracy IS 'Calcule la précision des prédictions par type de marché';

COMMENT ON FUNCTION calculate_betting_metrics IS 'Calcule les métriques de betting complètes pour un utilisateur';
COMMENT ON FUNCTION calculate_roi_by_sport IS 'Calcule le ROI par sport pour un utilisateur';

COMMENT ON FUNCTION calculate_drawdown IS 'Calcule les métriques de drawdown pour un utilisateur';
COMMENT ON FUNCTION calculate_var IS 'Calcule le Value at Risk et l Expected Shortfall';

COMMENT ON FUNCTION calculate_model_performance IS 'Calcule les métriques de performance détaillées pour un modèle ML';
COMMENT ON FUNCTION calculate_user_leaderboard IS 'Calcule le classement des utilisateurs';

COMMENT ON FUNCTION generate_performance_report IS 'Génère un rapport complet de performance';
COMMENT ON FUNCTION update_realtime_metrics IS 'Met à jour les métriques en temps réel (trigger function)';

COMMENT ON FUNCTION analyze_performance_trends IS 'Analyse les tendances de performance sur une période';
COMMENT ON FUNCTION validate_metrics_data IS 'Valide l intégrité des données de métriques';

-- ============================================
-- GRANT DES PERMISSIONS
-- ============================================

-- Donner les permissions d'exécution aux rôles appropriés
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Permissions spécifiques pour les fonctions sensibles
REVOKE EXECUTE ON FUNCTION calculate_var FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION calculate_drawdown FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION refresh_user_stats FROM PUBLIC;
