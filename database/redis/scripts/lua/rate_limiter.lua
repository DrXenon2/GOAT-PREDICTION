# database/redis/scripts/lua/rate_limiter.lua
-- Rate limiter Lua script pour Redis
-- Version: 2.0.0
-- Date: 2026-01-16

local function rate_limiter(key, limit, window)
    local current_time = redis.call('TIME')
    local now = tonumber(current_time[1]) * 1000 + math.floor(tonumber(current_time[2]) / 1000)
    local clear_before = now - window
    
    -- Nettoyer les anciennes requêtes
    redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
    
    -- Compter les requêtes actuelles
    local request_count = redis.call('ZCARD', key)
    
    if request_count >= limit then
        -- Retourner le temps d'attente
        local oldest_request = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
        local wait_time = window - (now - oldest_request)
        return {0, wait_time}
    end
    
    -- Ajouter la nouvelle requête
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, math.ceil(window / 1000))
    
    -- Retourner le nombre de requêtes restantes
    local remaining = limit - request_count - 1
    local reset_time = now + window
    
    return {1, remaining, reset_time}
end

-- API Rate Limiter par clé
local function api_rate_limiter(api_key, endpoint, limit, window)
    local key = 'rate_limit:' .. api_key .. ':' .. endpoint
    return rate_limiter(key, limit, window)
end

-- User Rate Limiter
local function user_rate_limiter(user_id, action, limit, window)
    local key = 'user_rate_limit:' .. user_id .. ':' .. action
    return rate_limiter(key, limit, window)
end

-- IP Rate Limiter
local function ip_rate_limiter(ip_address, endpoint, limit, window)
    local key = 'ip_rate_limit:' .. ip_address .. ':' .. endpoint
    return rate_limiter(key, limit, window)
end

-- Global Rate Limiter
local function global_rate_limiter(endpoint, limit, window)
    local key = 'global_rate_limit:' .. endpoint
    return rate_limiter(key, limit, window)
end

-- Token Bucket Rate Limiter
local function token_bucket_rate_limiter(key, capacity, refill_rate, tokens)
    local current_time = redis.call('TIME')
    local now = tonumber(current_time[1]) * 1000 + math.floor(tonumber(current_time[2]) / 1000)
    
    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local current_tokens = tonumber(bucket[1] or capacity)
    local last_refill = tonumber(bucket[2] or now)
    
    -- Calculer les tokens à réapprovisionner
    local time_passed = now - last_refill
    local tokens_to_add = math.floor(time_passed * refill_rate / 1000)
    
    -- Mettre à jour les tokens
    current_tokens = math.min(capacity, current_tokens + tokens_to_add)
    
    -- Vérifier si suffisamment de tokens
    if current_tokens < tokens then
        local wait_time = math.ceil((tokens - current_tokens) / refill_rate * 1000)
        return {0, wait_time}
    end
    
    -- Consommer les tokens
    current_tokens = current_tokens - tokens
    
    -- Mettre à jour Redis
    redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
    redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 60)
    
    return {1, current_tokens}
end

-- Sliding Window Rate Limiter
local function sliding_window_rate_limiter(key, limit, window)
    local current_time = redis.call('TIME')
    local now = tonumber(current_time[1]) * 1000 + math.floor(tonumber(current_time[2]) / 1000)
    
    -- Récupérer toutes les requêtes dans la fenêtre
    local requests = redis.call('ZRANGEBYSCORE', key, now - window, now)
    local request_count = #requests
    
    if request_count >= limit then
        -- Trouver le timestamp le plus ancien pour calculer le temps d'attente
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')[2]
        local wait_time = window - (now - oldest)
        return {0, wait_time}
    end
    
    -- Ajouter la nouvelle requête
    redis.call('ZADD', key, now, now)
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    redis.call('EXPIRE', key, math.ceil(window / 1000))
    
    return {1, limit - request_count - 1}
end

-- Rate Limiter avec différents niveaux
local function tiered_rate_limiter(user_id, tier, endpoint, limit_multiplier, window)
    local limits = {
        free = 100,
        basic = 500,
        premium = 2000,
        enterprise = 10000
    }
    
    local base_limit = limits[tier] or limits.free
    local limit = base_limit * limit_multiplier
    local key = 'tiered_rate_limit:' .. user_id .. ':' .. endpoint
    
    return rate_limiter(key, limit, window)
end

-- Rate Limiter pour les modèles ML
local function ml_model_rate_limiter(model_id, user_id, limit, window)
    local key = 'ml_rate_limit:' .. model_id .. ':' .. user_id
    return rate_limiter(key, limit, window)
end

-- Rate Limiter pour les données sportives
local function sports_data_rate_limiter(sport, endpoint, limit, window)
    local key = 'sports_rate_limit:' .. sport .. ':' .. endpoint
    return rate_limiter(key, limit, window)
end

-- Rate Limiter distribué pour cluster Redis
local function distributed_rate_limiter(resource_key, limit, window, node_count)
    local effective_limit = math.floor(limit / node_count)
    local key = 'distributed_rate_limit:' .. resource_key
    
    return rate_limiter(key, effective_limit, window)
end

-- Rate Limiter avec penalité
local function penalty_rate_limiter(user_id, endpoint, base_limit, window, penalty_factor)
    local key = 'penalty_rate_limit:' .. user_id .. ':' .. endpoint
    local penalty_key = 'penalty:' .. user_id .. ':' .. endpoint
    
    -- Vérifier les pénalités
    local penalty_count = tonumber(redis.call('GET', penalty_key) or 0)
    local actual_limit = math.floor(base_limit / math.pow(penalty_factor, penalty_count))
    
    local result = rate_limiter(key, actual_limit, window)
    
    -- Si limit dépassée, ajouter une pénalité
    if result[1] == 0 then
        redis.call('INCR', penalty_key)
        redis.call('EXPIRE', penalty_key, 3600) -- 1 heure
    end
    
    return result
end

-- Rate Limiter intelligent basé sur la charge
local function adaptive_rate_limiter(endpoint, base_limit, window, load_factor)
    local load_key = 'system_load'
    local current_load = tonumber(redis.call('GET', load_key) or 50)
    
    -- Ajuster la limite basée sur la charge système
    local adjusted_limit = math.floor(base_limit * (100 - current_load) / 100)
    adjusted_limit = math.max(10, math.min(base_limit, adjusted_limit))
    
    local key = 'adaptive_rate_limit:' .. endpoint
    return rate_limiter(key, adjusted_limit, window)
end

-- Rate Limiter avec répartition par période
local function time_based_rate_limiter(user_id, endpoint, limits_config)
    local current_time = redis.call('TIME')
    local hour = tonumber(current_time[1]) % 24
    
    -- Trouver la limite pour l'heure actuelle
    local limit = limits_config.default or 100
    for _, period in ipairs(limits_config.periods or {}) do
        if hour >= period.start and hour < period.finish then
            limit = period.limit
            break
        end
    end
    
    local key = 'time_based_rate_limit:' .. user_id .. ':' .. endpoint .. ':' .. tostring(hour)
    local window = 3600000 -- 1 heure en millisecondes
    
    return rate_limiter(key, limit, window)
end

-- Rate Limiter pour les webhooks
local function webhook_rate_limiter(webhook_id, limit, window)
    local key = 'webhook_rate_limit:' .. webhook_id
    return rate_limiter(key, limit, window)
end

-- Rate Limiter pour les notifications
local function notification_rate_limiter(user_id, notification_type, limit, window)
    local key = 'notification_rate_limit:' .. user_id .. ':' .. notification_type
    return rate_limiter(key, limit, window)
end

-- Rate Limiter combiné (multi-facteurs)
local function combined_rate_limiter(user_id, ip_address, endpoint, limits)
    local results = {}
    
    -- Appliquer différents rate limiters
    table.insert(results, api_rate_limiter(user_id, endpoint, limits.api, 60000))
    table.insert(results, ip_rate_limiter(ip_address, endpoint, limits.ip, 60000))
    table.insert(results, global_rate_limiter(endpoint, limits.global, 60000))
    
    -- Vérifier si tous les limiters ont passé
    for _, result in ipairs(results) do
        if result[1] == 0 then
            return result -- Retourner le premier échec
        end
    end
    
    -- Tous ont passé, retourner le plus restrictif
    local min_remaining = math.min(
        results[1][2] or math.huge,
        results[2][2] or math.huge,
        results[3][2] or math.huge
    )
    
    return {1, min_remaining}
end

-- Fonction principale pour router les appels
local function main(command, ...)
    if command == 'api' then
        return api_rate_limiter(...)
    elseif command == 'user' then
        return user_rate_limiter(...)
    elseif command == 'ip' then
        return ip_rate_limiter(...)
    elseif command == 'global' then
        return global_rate_limiter(...)
    elseif command == 'token_bucket' then
        return token_bucket_rate_limiter(...)
    elseif command == 'sliding_window' then
        return sliding_window_rate_limiter(...)
    elseif command == 'tiered' then
        return tiered_rate_limiter(...)
    elseif command == 'ml_model' then
        return ml_model_rate_limiter(...)
    elseif command == 'sports_data' then
        return sports_data_rate_limiter(...)
    elseif command == 'distributed' then
        return distributed_rate_limiter(...)
    elseif command == 'penalty' then
        return penalty_rate_limiter(...)
    elseif command == 'adaptive' then
        return adaptive_rate_limiter(...)
    elseif command == 'time_based' then
        return time_based_rate_limiter(...)
    elseif command == 'webhook' then
        return webhook_rate_limiter(...)
    elseif command == 'notification' then
        return notification_rate_limiter(...)
    elseif command == 'combined' then
        return combined_rate_limiter(...)
    else
        return {'error', 'Unknown command'}
    end
end

return main
