# database/redis/scripts/python/redis_client.py
#!/usr/bin/env python3
"""
Client Redis avancé pour Goat Prediction
Version: 2.0.0
Date: 2026-01-16
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import aioredis
from aioredis import Redis, ConnectionPool
import msgpack
import pickle
from contextlib import asynccontextmanager
import backoff
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisMode(Enum):
    """Modes de fonctionnement Redis"""
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"

class CacheStrategy(Enum):
    """Stratégies de cache"""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"

@dataclass
class RedisConfig:
    """Configuration Redis"""
    host: str = "redis-master.goat-prediction.svc.cluster.local"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    mode: RedisMode = RedisMode.CLUSTER
    pool_min_size: int = 5
    pool_max_size: int = 20
    ssl: bool = False
    encoding: str = "utf-8"
    decode_responses: bool = True
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # Configuration cluster
    startup_nodes: Optional[List[Dict[str, Any]]] = None
    cluster_error_retry_attempts: int = 3
    
    # Configuration Sentinel
    sentinels: Optional[List[tuple]] = None
    service_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        config = asdict(self)
        config['mode'] = self.mode.value
        return config

class RedisSerializer:
    """Sérialiseur pour les données Redis"""
    
    @staticmethod
    def serialize(value: Any) -> bytes:
        """Sérialiser une valeur"""
        if isinstance(value, (str, int, float, bool, type(None))):
            return str(value).encode('utf-8')
        elif isinstance(value, (dict, list)):
            return msgpack.packb(value, use_bin_type=True)
        elif isinstance(value, bytes):
            return value
        else:
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
    
    @staticmethod
    def deserialize(value: bytes, target_type: Optional[type] = None) -> Any:
        """Désérialiser une valeur"""
        if value is None:
            return None
        
        try:
            # Essayer msgpack en premier
            return msgpack.unpackb(value, raw=False)
        except:
            try:
                # Essayer pickle
                return pickle.loads(value)
            except:
                # Retourner comme string
                return value.decode('utf-8')

class RedisClient:
    """Client Redis avancé avec fonctionnalités étendues"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self._redis: Optional[Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self.serializer = RedisSerializer()
        self._initialized = False
        
    async def initialize(self):
        """Initialiser la connexion Redis"""
        if self._initialized:
            return
        
        try:
            if self.config.mode == RedisMode.CLUSTER:
                await self._init_cluster()
            elif self.config.mode == RedisMode.SENTINEL:
                await self._init_sentinel()
            else:
                await self._init_standalone()
            
            self._initialized = True
            logger.info(f"Redis client initialized in {self.config.mode.value} mode")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    async def _init_standalone(self):
        """Initialiser Redis standalone"""
        self._pool = ConnectionPool.from_url(
            f"redis://:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.db}",
            minsize=self.config.pool_min_size,
            maxsize=self.config.pool_max_size,
            ssl=self.config.ssl,
            encoding=self.config.encoding,
            decode_responses=self.config.decode_responses,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            health_check_interval=self.config.health_check_interval
        )
        self._redis = Redis(connection_pool=self._pool)
    
    async def _init_cluster(self):
        """Initialiser Redis cluster"""
        from aioredis import RedisCluster
        
        startup_nodes = self.config.startup_nodes or [
            {"host": self.config.host, "port": self.config.port}
        ]
        
        self._redis = RedisCluster(
            startup_nodes=startup_nodes,
            password=self.config.password,
            ssl=self.config.ssl,
            encoding=self.config.encoding,
            decode_responses=self.config.decode_responses,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            health_check_interval=self.config.health_check_interval,
            skip_full_coverage_check=True
        )
    
    async def _init_sentinel(self):
        """Initialiser Redis avec Sentinel"""
        if not self.config.sentinels or not self.config.service_name:
            raise ValueError("Sentinels and service_name required for Sentinel mode")
        
        self._pool = ConnectionPool.from_url(
            f"redis+sentinel://:{self.config.password}@",
            sentinels=self.config.sentinels,
            service_name=self.config.service_name,
            minsize=self.config.pool_min_size,
            maxsize=self.config.pool_max_size,
            ssl=self.config.ssl,
            encoding=self.config.encoding,
            decode_responses=self.config.decode_responses,
            socket_timeout=self.config.socket_timeout,
            socket_connect_timeout=self.config.socket_connect_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
            health_check_interval=self.config.health_check_interval
        )
        self._redis = Redis(connection_pool=self._pool)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def execute_command(self, command: str, *args, **kwargs) -> Any:
        """Exécuter une commande Redis"""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await getattr(self._redis, command)(*args, **kwargs)
        except Exception as e:
            logger.error(f"Redis command failed: {command} - {e}")
            raise
    
    # ============================================
    # MÉTHODES DE BASE AVANCÉES
    # ============================================
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, 
                  nx: bool = False, xx: bool = False) -> bool:
        """Définir une valeur avec options avancées"""
        serialized = self.serializer.serialize(value)
        
        if ttl:
            if nx:
                return await self.execute_command('set', key, serialized, 'EX', ttl, 'NX')
            elif xx:
                return await self.execute_command('set', key, serialized, 'EX', ttl, 'XX')
            else:
                return await self.execute_command('setex', key, ttl, serialized)
        else:
            if nx:
                return await self.execute_command('set', key, serialized, 'NX')
            elif xx:
                return await self.execute_command('set', key, serialized, 'XX')
            else:
                return await self.execute_command('set', key, serialized)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Récupérer une valeur"""
        value = await self.execute_command('get', key)
        if value is None:
            return default
        return self.serializer.deserialize(value)
    
    async def mget(self, keys: List[str]) -> List[Any]:
        """Récupérer plusieurs valeurs"""
        values = await self.execute_command('mget', *keys)
        return [self.serializer.deserialize(v) if v else None for v in values]
    
    async def delete(self, *keys: str) -> int:
        """Supprimer des clés"""
        return await self.execute_command('delete', *keys)
    
    async def exists(self, *keys: str) -> int:
        """Vérifier l'existence de clés"""
        return await self.execute_command('exists', *keys)
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Définir un TTL sur une clé"""
        return await self.execute_command('expire', key, ttl)
    
    async def ttl(self, key: str) -> int:
        """Récupérer le TTL d'une clé"""
        return await self.execute_command('ttl', key)
    
    # ============================================
    # STRUCTURES DE DONNÉES AVANCÉES
    # ============================================
    
    # --- Hash ---
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Définir un champ de hash"""
        serialized = self.serializer.serialize(value)
        return await self.execute_command('hset', key, field, serialized)
    
    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """Récupérer un champ de hash"""
        value = await self.execute_command('hget', key, field)
        if value is None:
            return default
        return self.serializer.deserialize(value)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Récupérer tous les champs d'un hash"""
        result = await self.execute_command('hgetall', key)
        return {k: self.serializer.deserialize(v) for k, v in result.items()}
    
    # --- List ---
    async def lpush(self, key: str, *values: Any) -> int:
        """Push à gauche"""
        serialized = [self.serializer.serialize(v) for v in values]
        return await self.execute_command('lpush', key, *serialized)
    
    async def rpush(self, key: str, *values: Any) -> int:
        """Push à droite"""
        serialized = [self.serializer.serialize(v) for v in values]
        return await self.execute_command('rpush', key, *serialized)
    
    async def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """Récupérer une plage d'éléments"""
        values = await self.execute_command('lrange', key, start, end)
        return [self.serializer.deserialize(v) for v in values]
    
    # --- Set ---
    async def sadd(self, key: str, *values: Any) -> int:
        """Ajouter des membres à un set"""
        serialized = [self.serializer.serialize(v) for v in values]
        return await self.execute_command('sadd', key, *serialized)
    
    async def smembers(self, key: str) -> List[Any]:
        """Récupérer tous les membres d'un set"""
        values = await self.execute_command('smembers', key)
        return [self.serializer.deserialize(v) for v in values]
    
    async def sismember(self, key: str, value: Any) -> bool:
        """Vérifier l'appartenance à un set"""
        serialized = self.serializer.serialize(value)
        return await self.execute_command('sismember', key, serialized)
    
    # --- Sorted Set ---
    async def zadd(self, key: str, mapping: Dict[Any, float], nx: bool = False, 
                   xx: bool = False, ch: bool = False, incr: bool = False) -> int:
        """Ajouter des membres à un sorted set"""
        redis_mapping = {}
        for member, score in mapping.items():
            redis_mapping[self.serializer.serialize(member)] = score
        
        args = []
        if nx:
            args.append('NX')
        if xx:
            args.append('XX')
        if ch:
            args.append('CH')
        if incr:
            args.append('INCR')
        
        return await self.execute_command('zadd', key, *args, **redis_mapping)
    
    async def zrange(self, key: str, start: int, end: int, 
                     withscores: bool = False) -> List[Any]:
        """Récupérer une plage d'éléments d'un sorted set"""
        args = [key, start, end]
        if withscores:
            args.append('WITHSCORES')
        
        result = await self.execute_command('zrange', *args)
        
        if withscores:
            return [
                (self.serializer.deserialize(result[i]), float(result[i + 1]))
                for i in range(0, len(result), 2)
            ]
        else:
            return [self.serializer.deserialize(v) for v in result]
    
    async def zrangebyscore(self, key: str, min_score: float, max_score: float,
                            withscores: bool = False, offset: Optional[int] = None,
                            count: Optional[int] = None) -> List[Any]:
        """Récupérer des éléments par score"""
        args = [key, min_score, max_score]
        if withscores:
            args.append('WITHSCORES')
        if offset is not None and count is not None:
            args.extend(['LIMIT', offset, count])
        
        result = await self.execute_command('zrangebyscore', *args)
        
        if withscores:
            return [
                (self.serializer.deserialize(result[i]), float(result[i + 1]))
                for i in range(0, len(result), 2)
            ]
        else:
            return [self.serializer.deserialize(v) for v in result]
    
    # ============================================
    # FONCTIONNALITÉS CACHE AVANCÉES
    # ============================================
    
    async def cache_get(self, key: str, default: Any = None) -> Any:
        """Récupérer du cache avec fallback"""
        value = await self.get(key)
        if value is not None:
            return value
        
        # Si une fonction de fallback est fournie
        if callable(default):
            try:
                value = default()
                await self.set(key, value, ttl=300)  # Cache pour 5 minutes
                return value
            except Exception as e:
                logger.error(f"Fallback function failed: {e}")
                return None
        
        return default
    
    async def cache_set(self, key: str, value: Any, ttl: int = 300,
                        strategy: CacheStrategy = CacheStrategy.TTL) -> bool:
        """Définir une valeur en cache avec stratégie"""
        if strategy == CacheStrategy.LRU:
            # Implémentation LRU simplifiée
            lru_key = f"lru:{key}"
            await self.execute_command('zadd', 'cache:lru', {lru_key: datetime.now().timestamp()})
        
        return await self.set(key, value, ttl=ttl)
    
    async def cache_delete_pattern(self, pattern: str) -> int:
        """Supprimer les clés correspondant à un pattern"""
        keys = await self.execute_command('keys', pattern)
        if keys:
            return await self.delete(*keys)
        return 0
    
    async def cache_clear(self) -> int:
        """Nettoyer tout le cache"""
        return await self.cache_delete_pattern("cache:*")
    
    # ============================================
    # FONCTIONNALITÉS PUB/SUB
    # ============================================
    
    async def publish(self, channel: str, message: Any) -> int:
        """Publier un message sur un channel"""
        serialized = self.serializer.serialize(message)
        return await self.execute_command('publish', channel, serialized)
    
    async def subscribe(self, channel: str, callback):
        """S'abonner à un channel"""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = self.serializer.deserialize(message['data'])
                    await callback(channel, data)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    
    async def psubscribe(self, pattern: str, callback):
        """S'abonner à un pattern"""
        pubsub = self._redis.pubsub()
        await pubsub.psubscribe(pattern)
        
        async for message in pubsub.listen():
            if message['type'] == 'pmessage':
                try:
                    data = self.serializer.deserialize(message['data'])
                    await callback(message['pattern'], message['channel'], data)
                except Exception as e:
                    logger.error(f"Error processing pattern message: {e}")
    
    # ============================================
    # FONCTIONNALITÉS TRANSACTIONS
    # ============================================
    
    @asynccontextmanager
    async def pipeline(self):
        """Pipeline Redis"""
        async with self._redis.pipeline() as pipe:
            yield pipe
    
    async def transaction(self, *commands, **kwargs):
        """Exécuter une transaction"""
        return await self._redis.transaction(*commands, **kwargs)
    
    # ============================================
    # FONCTIONNALITÉS SPÉCIFIQUES GOAT PREDICTION
    # ============================================
    
    async def store_prediction(self, prediction_id: str, prediction_data: Dict[str, Any]) -> bool:
        """Stocker une prédiction"""
        key = f"prediction:{prediction_id}"
        return await self.set(key, prediction_data, ttl=86400)  # 24 heures
    
    async def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une prédiction"""
        key = f"prediction:{prediction_id}"
        return await self.get(key)
    
    async def store_match_data(self, match_id: str, match_data: Dict[str, Any]) -> bool:
        """Stocker les données d'un match"""
        key = f"match:{match_id}"
        return await self.set(key, match_data, ttl=172800)  # 48 heures
    
    async def get_match_data(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer les données d'un match"""
        key = f"match:{match_id}"
        return await self.get(key)
    
    async def cache_model_prediction(self, model_id: str, features_hash: str, 
                                     prediction: Any) -> bool:
        """Cache une prédiction de modèle"""
        key = f"model_cache:{model_id}:{features_hash}"
        return await self.set(key, prediction, ttl=1800)  # 30 minutes
    
    async def get_cached_prediction(self, model_id: str, features_hash: str) -> Optional[Any]:
        """Récupérer une prédiction mise en cache"""
        key = f"model_cache:{model_id}:{features_hash}"
        return await self.get(key)
    
    async def store_user_session(self, session_id: str, user_data: Dict[str, Any]) -> bool:
        """Stocker une session utilisateur"""
        key = f"session:{session_id}"
        return await self.set(key, user_data, ttl=3600)  # 1 heure
    
    async def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupérer une session utilisateur"""
        key = f"session:{session_id}"
        return await self.get(key)
    
    async def increment_rate_limit(self, key: str, limit: int, window: int) -> tuple:
        """Incrémenter un compteur de rate limiting"""
        current = await self.execute_command('incr', key)
        
        if current == 1:
            await self.execute_command('expire', key, window)
        
        return current, limit - current
    
    async def get_rate_limit_status(self, key: str, limit: int) -> Dict[str, Any]:
        """Récupérer le statut du rate limiting"""
        current = int(await self.execute_command('get', key) or 0)
        ttl = await self.execute_command('ttl', key)
        
        return {
            'current': current,
            'limit': limit,
            'remaining': max(0, limit - current),
            'reset_in': ttl if ttl > 0 else 0
        }
    
    async def store_leaderboard(self, sport: str, date: str, entries: List[Dict[str, Any]]) -> bool:
        """Stocker un classement"""
        key = f"leaderboard:{sport}:{date}"
        
        # Utiliser sorted set pour le classement
        mapping = {}
        for entry in entries:
            member = self.serializer.serialize(entry)
            score = entry.get('score', 0)
            mapping[member] = score
        
        await self.zadd(key, mapping)
        await self.expire(key, 604800)  # 1 semaine
        
        return True
    
    async def get_leaderboard(self, sport: str, date: str, 
                              start: int = 0, end: int = -1) -> List[Dict[str, Any]]:
        """Récupérer un classement"""
        key = f"leaderboard:{sport}:{date}"
        entries = await self.zrange(key, start, end, withscores=True)
        
        return [
            {
                **self.serializer.deserialize(member),
                'score': score,
                'rank': start + i + 1
            }
            for i, (member, score) in enumerate(entries)
        ]
    
    async def store_realtime_update(self, update_type: str, data: Dict[str, Any]) -> bool:
        """Stocker une mise à jour en temps réel"""
        timestamp = datetime.now().timestamp()
        key = f"realtime:{update_type}:{timestamp}"
        
        # Stocker la mise à jour
        await self.set(key, data, ttl=300)  # 5 minutes
        
        # Ajouter à la liste des dernières mises à jour
        list_key = f"realtime_updates:{update_type}"
        await self.lpush(list_key, key)
        await self.ltrim(list_key, 0, 99)  # Garder seulement les 100 dernières
        await self.expire(list_key, 3600)  # 1 heure
        
        # Publier sur le channel Pub/Sub
        await self.publish(f"updates:{update_type}", data)
        
        return True
    
    async def get_recent_updates(self, update_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupérer les mises à jour récentes"""
        list_key = f"realtime_updates:{update_type}"
        keys = await self.lrange(list_key, 0, limit - 1)
        
        updates = []
        for key in keys:
            data = await self.get(key)
            if data:
                updates.append(data)
        
        return updates
    
    # ============================================
    # FONCTIONNALITÉS DE MAINTENANCE
    # ============================================
    
    async def get_info(self) -> Dict[str, Any]:
        """Récupérer les informations Redis"""
        info = await self.execute_command('info')
        return dict(line.split(':') for line in info.split('\r\n') if ':' in line)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Récupérer les statistiques"""
        info = await self.get_info()
        
        return {
            'connected_clients': int(info.get('connected_clients', 0)),
            'used_memory': int(info.get('used_memory', 0)),
            'used_memory_peak': int(info.get('used_memory_peak', 0)),
            'total_commands_processed': int(info.get('total_commands_processed', 0)),
            'instantaneous_ops_per_sec': int(info.get('instantaneous_ops_per_sec', 0)),
            'keyspace_hits': int(info.get('keyspace_hits', 0)),
            'keyspace_misses': int(info.get('keyspace_misses', 0)),
            'hit_rate': (
                int(info.get('keyspace_hits', 0)) / 
                (int(info.get('keyspace_hits', 0)) + int(info.get('keyspace_misses', 0)) + 1)
            ) * 100
        }
    
    async def cleanup_old_data(self, pattern: str, older_than_hours: int = 24) -> int:
        """Nettoyer les anciennes données"""
        keys = await self.execute_command('keys', pattern)
        
        deleted = 0
        for key in keys:
            ttl = await self.ttl(key)
            if ttl == -1:  # Pas de TTL, vérifier le timestamp dans la clé
                try:
                    # Essayer d'extraire le timestamp de la clé
                    timestamp = float(key.split(':')[-1])
                    age_hours = (datetime.now().timestamp() - timestamp) / 3600
                    
                    if age_hours > older_than_hours:
                        await self.delete(key)
                        deleted += 1
                except:
                    continue
        
        return deleted
    
    async def backup_keys(self, pattern: str) -> Dict[str, Any]:
        """Sauvegarder les clés correspondant à un pattern"""
        keys = await self.execute_command('keys', pattern)
        
        backup = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                backup[key] = value
        
        return backup
    
    async def restore_keys(self, backup: Dict[str, Any]) -> int:
        """Restaurer des clés depuis une sauvegarde"""
        restored = 0
        for key, value in backup.items():
            await self.set(key, value)
            restored += 1
        
        return restored
    
    # ============================================
    # FONCTIONNALITÉS DE SANTÉ
    # ============================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérifier la santé de Redis"""
        try:
            # Ping Redis
            await self.execute_command('ping')
            
            # Récupérer des informations
            info = await self.get_info()
            stats = await self.get_stats()
            
            return {
                'status': 'healthy',
                'version': info.get('redis_version', 'unknown'),
                'uptime_days': int(info.get('uptime_in_days', 0)),
                'memory_used_mb': stats['used_memory'] / 1024 / 1024,
                'connected_clients': stats['connected_clients'],
                'hit_rate': stats['hit_rate'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def close(self):
        """Fermer les connexions Redis"""
        if self._redis:
            await self._redis.close()
        if self._pool:
            await self._pool.disconnect()
        self._initialized = False
        logger.info("Redis client closed")

# ============================================
# FONCTIONS UTILITAIRES
# ============================================

def create_redis_client(config: Optional[Dict[str, Any]] = None) -> RedisClient:
    """Créer un client Redis avec configuration par défaut"""
    default_config = RedisConfig()
    
    if config:
        # Mettre à jour la configuration par défaut
        for key, value in config.items():
            if hasattr(default_config, key):
                if key == 'mode' and isinstance(value, str):
                    value = RedisMode(value)
                setattr(default_config, key, value)
    
    return RedisClient(default_config)

async def test_redis_connection():
    """Tester la connexion Redis"""
    client = create_redis_client()
    
    try:
        await client.initialize()
        
        # Test de base
        await client.set("test:key", {"message": "Hello Redis"})
        value = await client.get("test:key")
        
        logger.info(f"Redis test successful: {value}")
        
        # Test de santé
        health = await client.health_check()
        logger.info(f"Redis health: {health}")
        
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"Redis test failed: {e}")
        return False

if __name__ == "__main__":
    # Exemple d'utilisation
    async def main():
        # Tester la connexion
        success = await test_redis_connection()
        print(f"Test connection: {'Success' if success else 'Failed'}")
        
        # Exemple d'utilisation avancée
        client = create_redis_client()
        await client.initialize()
        
        # Stocker des données de match
        match_data = {
            "match_id": "MATCH_123456",
            "home_team": "Team A",
            "away_team": "Team B",
            "prediction": {
                "home_win_prob": 0.65,
                "draw_prob": 0.20,
                "away_win_prob": 0.15,
                "confidence": 0.85
            }
        }
        
        await client.store_match_data("MATCH_123456", match_data)
        
        # Récupérer les données
        retrieved = await client.get_match_data("MATCH_123456")
        print(f"Retrieved match data: {retrieved}")
        
        # Rate limiting example
        key = "rate_limit:user_123:api"
        current, remaining = await client.increment_rate_limit(key, 100, 60)
        print(f"Rate limit: {current}/100, remaining: {remaining}")
        
        await client.close()
    
    asyncio.run(main())
