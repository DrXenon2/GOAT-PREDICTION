# 📄 docs/api/v2/realtime.md

```markdown
# Real-Time API v2

## 📋 Aperçu

L'API Real-Time v2 fournit un accès en temps réel aux prédictions sportives, aux données de marché, et aux mises à jour live. Cette version introduit WebSockets pour des communications bidirectionnelles et une latence ultra-faible.

## 🚀 Caractéristiques Principales

- **WebSocket Support**: Connexions persistantes pour données temps réel
- **SSE (Server-Sent Events)**: Alternative aux WebSockets
- **Streaming gRPC**: Pour une performance optimale
- **Heartbeat & Health Checks**: Surveillance continue
- **Reconnexion automatique**: Gestion robuste des déconnexions
- **Compression**: Réduction de la bande passante
- **Authentification temps réel**: JWT refresh automatique

## 🔌 Endpoints

### WebSocket Connections

#### 1. Connexion WebSocket Principale
```
wss://api.goat-prediction.com/v2/realtime/ws
```

**Protocole de Connexion:**
```javascript
// Établir la connexion
const ws = new WebSocket('wss://api.goat-prediction.com/v2/realtime/ws', {
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'X-Client-Version': '2.0.0',
    'X-Client-ID': 'your-client-id'
  }
});
```

**Messages d'ouverture:**
```json
{
  "type": "connection_init",
  "payload": {
    "subscriptions": ["predictions", "odds", "live_matches"],
    "compression": "gzip",
    "heartbeat_interval": 30000
  }
}
```

#### 2. Connexion SSE (Server-Sent Events)
```
GET /v2/realtime/sse
```

**Headers requis:**
```http
Authorization: Bearer YOUR_JWT_TOKEN
Accept: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

#### 3. Connexion gRPC
```
grpc.goat-prediction.com:443
```

**Protobuf Definitions:**
```proto
syntax = "proto3";

package goatprediction.realtime.v2;

service RealTimeService {
  // Stream bidirectionnel pour données temps réel
  rpc Stream(stream ClientMessage) returns (stream ServerMessage);
  
  // Stream unidirectionnel pour mises à jour
  rpc Subscribe(SubscriptionRequest) returns (stream Update);
  
  // Health check
  rpc HealthCheck(HealthRequest) returns (HealthResponse);
}

message ClientMessage {
  string client_id = 1;
  oneof message {
    Subscription subscription = 2;
    Unsubscription unsubscription = 3;
    Ping ping = 4;
    FilterUpdate filter = 5;
  }
}

message ServerMessage {
  oneof message {
    Pong pong = 1;
    DataUpdate update = 2;
    Error error = 3;
    SystemNotification notification = 4;
  }
}
```

## 📡 Channels de Données

### 1. Prédictions en Temps Réel
```json
{
  "channel": "predictions",
  "events": [
    "prediction_created",
    "prediction_updated",
    "prediction_expired",
    "confidence_change",
    "value_alert"
  ],
  "filters": {
    "sport": ["football", "basketball", "tennis"],
    "league": ["premier-league", "nba", "atp"],
    "confidence_min": 0.7,
    "value_min": 1.2
  }
}
```

### 2. Cotes et Marchés
```json
{
  "channel": "odds",
  "events": [
    "odds_update",
    "market_suspension",
    "arbitrage_opportunity",
    "line_movement",
    "volume_change"
  ],
  "filters": {
    "bookmakers": ["bet365", "pinnacle", "betfair"],
    "market_types": ["match_winner", "over_under", "handicap"],
    "movement_threshold": 0.05
  }
}
```

### 3. Matchs en Direct
```json
{
  "channel": "live_matches",
  "events": [
    "match_start",
    "goal_scored",
    "card_issued",
    "substitution",
    "match_end",
    "injury_update",
    "momentum_shift"
  ],
  "filters": {
    "sport": "football",
    "importance_min": 0.5,
    "has_video": true
  }
}
```

### 4. Analytics et Performances
```json
{
  "channel": "analytics",
  "events": [
    "model_performance",
    "accuracy_update",
    "roi_calculation",
    "risk_alert",
    "anomaly_detected"
  ],
  "filters": {
    "update_frequency": "realtime",
    "include_historical": true
  }
}
```

## 🔐 Authentification

### 1. JWT Authentication
```javascript
// Header d'authentification
{
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

// Refresh token automatique
ws.on('token_expired', async () => {
  const newToken = await refreshToken();
  ws.send(JSON.stringify({
    type: 'auth_refresh',
    token: newToken
  }));
});
```

### 2. API Key Authentication
```javascript
// Pour les intégrations B2B
{
  "X-API-Key": "gp_sk_live_...",
  "X-API-Secret": "your_secret_here"
}
```

### 3. OAuth 2.0
```javascript
// Pour les partenaires
{
  "Authorization": "Bearer {oauth_token}",
  "X-Partner-ID": "partner_123"
}
```

## 📊 Formats de Messages

### Structure Standard
```json
{
  "id": "msg_123456789",
  "type": "data_update",
  "timestamp": "2024-01-15T14:30:00Z",
  "channel": "predictions",
  "event": "prediction_created",
  "data": {
    "prediction_id": "pred_abc123",
    "match_id": "match_xyz789",
    "sport": "football",
    "league": "premier-league",
    "home_team": "Manchester United",
    "away_team": "Manchester City",
    "market": "match_winner",
    "prediction": "home_win",
    "probability": 0.65,
    "confidence": 0.82,
    "value": 1.45,
    "odds": {
      "home_win": 2.10,
      "draw": 3.50,
      "away_win": 3.20
    },
    "kelly_fraction": 0.03,
    "expected_value": 0.0925,
    "model_metadata": {
      "model_version": "2.1.0",
      "ensemble_weight": 0.85,
      "features_used": ["form", "h2h", "injuries", "motivation"],
      "prediction_time": "2024-01-15T14:29:45Z"
    },
    "valid_until": "2024-01-15T15:00:00Z"
  },
  "metadata": {
    "sequence": 12345,
    "priority": "high",
    "compression": "gzip",
    "size_bytes": 1024
  }
}
```

### Message de Système
```json
{
  "id": "sys_987654321",
  "type": "system_notification",
  "timestamp": "2024-01-15T14:30:00Z",
  "channel": "system",
  "event": "maintenance_scheduled",
  "data": {
    "message": "Maintenance planifiée à 02:00 UTC",
    "start_time": "2024-01-16T02:00:00Z",
    "end_time": "2024-01-16T04:00:00Z",
    "impact": "read_only",
    "services_affected": ["predictions", "odds_streaming"]
  }
}
```

### Message d'Erreur
```json
{
  "id": "err_555666777",
  "type": "error",
  "timestamp": "2024-01-15T14:30:00Z",
  "channel": "error",
  "event": "validation_error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid subscription filter",
    "details": {
      "field": "confidence_min",
      "issue": "Value must be between 0 and 1"
    },
    "suggestion": "Set confidence_min to a value between 0 and 1"
  }
}
```

## ⚙️ Configuration du Client

### Options de Connexion
```javascript
const options = {
  // Authentification
  auth: {
    type: 'jwt',
    token: 'YOUR_TOKEN',
    autoRefresh: true,
    refreshInterval: 300000 // 5 minutes
  },
  
  // Reconnexion
  reconnect: {
    enabled: true,
    maxAttempts: 10,
    initialDelay: 1000,
    maxDelay: 30000,
    backoffFactor: 1.5
  },
  
  // Performance
  performance: {
    heartbeatInterval: 30000,
    timeout: 10000,
    bufferSize: 1000,
    compression: 'gzip'
  },
  
  // Logging
  logging: {
    level: 'info',
    format: 'json',
    maxEntries: 1000
  },
  
  // Abonnements
  subscriptions: {
    predictions: {
      enabled: true,
      filters: {
        sport: ['football', 'basketball'],
        confidence_min: 0.7
      }
    },
    odds: {
      enabled: true,
      filters: {
        bookmakers: ['pinnacle', 'betfair']
      }
    }
  }
};
```

### Gestion des Événements
```javascript
// Événements WebSocket
ws.on('open', () => {
  console.log('Connexion établie');
  initializeSubscriptions();
});

ws.on('message', (data) => {
  const message = JSON.parse(data);
  handleMessage(message);
});

ws.on('error', (error) => {
  console.error('Erreur WebSocket:', error);
  handleError(error);
});

ws.on('close', (code, reason) => {
  console.log('Connexion fermée:', code, reason);
  attemptReconnect();
});

// Gestion des messages
function handleMessage(message) {
  switch (message.type) {
    case 'data_update':
      processDataUpdate(message);
      break;
    case 'system_notification':
      showNotification(message);
      break;
    case 'error':
      handleError(message.error);
      break;
    case 'pong':
      updateLastPong();
      break;
  }
}
```

## 🔄 Opérations de Gestion

### 1. Souscription aux Channels
```json
{
  "type": "subscribe",
  "id": "sub_123",
  "channel": "predictions",
  "filters": {
    "sport": ["football"],
    "league": ["premier-league", "la-liga"],
    "confidence_min": 0.75,
    "value_min": 1.3
  },
  "options": {
    "historical_data": true,
    "update_frequency": "realtime",
    "batch_size": 10
  }
}
```

**Réponse:**
```json
{
  "type": "subscription_confirmed",
  "id": "sub_123",
  "channel": "predictions",
  "subscription_id": "sub_abc123",
  "active_filters": {
    "sport": ["football"],
    "league": ["premier-league", "la-liga"],
    "confidence_min": 0.75,
    "value_min": 1.3
  },
  "estimated_volume": "10-20 messages/minute",
  "created_at": "2024-01-15T14:30:00Z"
}
```

### 2. Désabonnement
```json
{
  "type": "unsubscribe",
  "subscription_id": "sub_abc123"
}
```

### 3. Mise à jour des Filtres
```json
{
  "type": "update_filters",
  "subscription_id": "sub_abc123",
  "filters": {
    "confidence_min": 0.8,
    "value_min": 1.5,
    "sport": ["football", "tennis"]
  }
}
```

### 4. Heartbeat & Ping/Pong
```json
// Client ping
{
  "type": "ping",
  "id": "ping_123",
  "timestamp": "2024-01-15T14:30:00Z"
}

// Server pong
{
  "type": "pong",
  "id": "ping_123",
  "timestamp": "2024-01-15T14:30:00Z",
  "server_time": "2024-01-15T14:30:00.123Z",
  "latency_ms": 123
}
```

## 📈 Métriques de Performance

### Métriques de Connexion
```json
{
  "connection_id": "conn_abc123",
  "metrics": {
    "uptime": "5h 30m",
    "messages_sent": 1250,
    "messages_received": 2540,
    "bytes_sent": "2.5 MB",
    "bytes_received": "5.1 MB",
    "avg_latency": 45,
    "max_latency": 210,
    "reconnect_count": 2,
    "subscription_count": 3
  },
  "quality": {
    "connection_stability": 0.99,
    "message_delivery_rate": 0.999,
    "compression_ratio": 0.65
  }
}
```

## 🛡️ Sécurité

### 1. Chiffrement
- **TLS 1.3** obligatoire
- **AES-256-GCM** pour le chiffrement des messages
- **Perfect Forward Secrecy** avec ECDHE

### 2. Rate Limiting
```json
{
  "limits": {
    "connections_per_ip": 10,
    "messages_per_minute": 1000,
    "subscriptions_per_connection": 20,
    "bandwidth_per_hour": "100 MB"
  }
}
```

### 3. Validation des Messages
```javascript
// Schema validation avec JSON Schema
const messageSchema = {
  type: 'object',
  required: ['id', 'type', 'timestamp'],
  properties: {
    id: { type: 'string', pattern: '^[a-z]+_[a-zA-Z0-9]+$' },
    type: { 
      type: 'string', 
      enum: ['data_update', 'system_notification', 'error', 'ping', 'pong']
    },
    timestamp: { type: 'string', format: 'date-time' }
  }
};
```

## 🧪 Exemples Complets

### Exemple 1: Client JavaScript
```javascript
class RealTimeClient {
  constructor(options = {}) {
    this.options = {
      endpoint: 'wss://api.goat-prediction.com/v2/realtime/ws',
      autoReconnect: true,
      ...options
    };
    
    this.ws = null;
    this.subscriptions = new Map();
    this.messageHandlers = new Map();
    this.reconnectAttempts = 0;
    
    this.initialize();
  }
  
  async initialize() {
    await this.connect();
    this.setupEventHandlers();
    this.startHeartbeat();
  }
  
  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.options.endpoint, {
        headers: {
          'Authorization': `Bearer ${this.options.token}`,
          'X-Client-Version': '2.0.0'
        }
      });
      
      this.ws.onopen = () => {
        console.log('✅ Connected to real-time API');
        this.reconnectAttempts = 0;
        this.authenticate();
        resolve();
      };
      
      this.ws.onerror = (error) => {
        console.error('❌ Connection error:', error);
        reject(error);
      };
    });
  }
  
  async authenticate() {
    const authMessage = {
      type: 'auth',
      token: this.options.token,
      client_info: {
        version: '2.0.0',
        platform: 'web',
        features: ['predictions', 'odds', 'analytics']
      }
    };
    
    this.send(authMessage);
  }
  
  subscribe(channel, filters = {}) {
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const subscription = {
      type: 'subscribe',
      id: subscriptionId,
      channel,
      filters,
      timestamp: new Date().toISOString()
    };
    
    this.subscriptions.set(subscriptionId, {
      channel,
      filters,
      active: false
    });
    
    this.send(subscription);
    
    return subscriptionId;
  }
  
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const messageStr = JSON.stringify(message);
      this.ws.send(messageStr);
      return true;
    }
    return false;
  }
  
  // ... autres méthodes
}

// Utilisation
const client = new RealTimeClient({
  token: 'YOUR_JWT_TOKEN',
  onMessage: (message) => {
    console.log('Received:', message);
  }
});

const subId = client.subscribe('predictions', {
  sport: ['football'],
  confidence_min: 0.7
});
```

### Exemple 2: Client Python
```python
import asyncio
import websockets
import json
from typing import Dict, Any, Optional
import logging

class RealTimeClient:
    def __init__(self, token: str, endpoint: str = "wss://api.goat-prediction.com/v2/realtime/ws"):
        self.token = token
        self.endpoint = endpoint
        self.websocket = None
        self.subscriptions = {}
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Établir la connexion WebSocket"""
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Client-Version": "2.0.0"
        }
        
        try:
            self.websocket = await websockets.connect(
                self.endpoint,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=5
            )
            
            self.is_connected = True
            self.logger.info("✅ Connected to real-time API")
            
            # Authentification automatique
            await self.authenticate()
            
            # Démarrer la lecture des messages
            asyncio.create_task(self.listen())
            
        except Exception as e:
            self.logger.error(f"❌ Connection failed: {e}")
            raise
            
    async def authenticate(self):
        """Envoyer le message d'authentification"""
        auth_message = {
            "type": "auth",
            "token": self.token,
            "client_info": {
                "version": "2.0.0",
                "platform": "python",
                "language": "python"
            }
        }
        
        await self.send(auth_message)
        
    async def subscribe(self, channel: str, filters: Dict[str, Any] = None) -> str:
        """Souscrire à un channel"""
        if filters is None:
            filters = {}
            
        subscription_id = f"sub_{int(asyncio.get_event_loop().time() * 1000)}"
        
        subscription = {
            "type": "subscribe",
            "id": subscription_id,
            "channel": channel,
            "filters": filters,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        self.subscriptions[subscription_id] = {
            "channel": channel,
            "filters": filters,
            "active": False
        }
        
        await self.send(subscription)
        return subscription_id
        
    async def send(self, message: Dict[str, Any]):
        """Envoyer un message"""
        if self.websocket and self.is_connected:
            try:
                message_str = json.dumps(message)
                await self.websocket.send(message_str)
            except Exception as e:
                self.logger.error(f"Failed to send message: {e}")
                
    async def listen(self):
        """Écouter les messages entrants"""
        try:
            async for message in self.websocket:
                await self.handle_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            self.logger.warning("Connection closed")
            self.is_connected = False
            await self.reconnect()
        except Exception as e:
            self.logger.error(f"Error in listen: {e}")
            
    async def handle_message(self, message: Dict[str, Any]):
        """Gérer un message reçu"""
        message_type = message.get("type")
        
        if message_type == "data_update":
            await self.handle_data_update(message)
        elif message_type == "subscription_confirmed":
            await self.handle_subscription_confirmed(message)
        elif message_type == "error":
            await self.handle_error(message)
        elif message_type == "pong":
            self.last_pong = asyncio.get_event_loop().time()
            
    async def handle_data_update(self, message: Dict[str, Any]):
        """Gérer une mise à jour de données"""
        channel = message.get("channel")
        data = message.get("data", {})
        
        # Traiter selon le channel
        if channel == "predictions":
            await self.process_prediction(data)
        elif channel == "odds":
            await self.process_odds(data)
        elif channel == "live_matches":
            await self.process_live_match(data)
            
    async def process_prediction(self, prediction: Dict[str, Any]):
        """Traiter une prédiction"""
        print(f"🎯 New prediction: {prediction.get('home_team')} vs {prediction.get('away_team')}")
        print(f"   Market: {prediction.get('market')}")
        print(f"   Prediction: {prediction.get('prediction')}")
        print(f"   Probability: {prediction.get('probability'):.2%}")
        print(f"   Value: {prediction.get('value'):.2f}")
        
    async def reconnect(self, max_attempts: int = 10):
        """Tentative de reconnexion"""
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")
                await self.connect()
                return
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                await asyncio.sleep(min(2 ** attempt, 30))
                
        self.logger.error("Max reconnection attempts reached")

# Exemple d'utilisation
async def main():
    client = RealTimeClient(token="YOUR_JWT_TOKEN")
    
    try:
        await client.connect()
        
        # Souscrire aux prédictions football
        sub_id = await client.subscribe("predictions", {
            "sport": ["football"],
            "confidence_min": 0.7,
            "value_min": 1.3
        })
        
        print(f"Subscribed with ID: {sub_id}")
        
        # Garder le programme en cours d'exécution
        await asyncio.sleep(3600)  # 1 heure
        
    except KeyboardInterrupt:
        print("Interrupted")
    finally:
        if client.websocket:
            await client.websocket.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🚨 Codes d'Erreur

| Code | Description | Solution |
|------|-------------|----------|
| `AUTH_REQUIRED` | Authentification requise | Envoyer un token JWT valide |
| `INVALID_TOKEN` | Token invalide ou expiré | Rafraîchir le token |
| `RATE_LIMITED` | Rate limit atteint | Réduire la fréquence des requêtes |
| `CHANNEL_NOT_FOUND` | Channel inexistant | Vérifier le nom du channel |
| `INVALID_FILTER` | Filtre invalide | Vérifier la syntaxe des filtres |
| `SUBSCRIPTION_LIMIT` | Trop d'abonnements | Réduire le nombre d'abonnements |
| `CONNECTION_TIMEOUT` | Timeout de connexion | Vérifier la stabilité réseau |
| `SERVER_ERROR` | Erreur serveur interne | Réessayer plus tard |

## 📡 Webhooks (Alternative)

Pour les intégrations qui ne supportent pas WebSockets:

### Configuration Webhook
```json
POST /v2/webhooks/subscribe
{
  "url": "https://your-server.com/webhook-handler",
  "events": ["prediction_created", "odds_update"],
  "filters": {
    "sport": ["football"],
    "confidence_min": 0.8
  },
  "secret": "your_webhook_secret",
  "retry_policy": {
    "max_attempts": 3,
    "backoff_ms": [1000, 5000, 30000]
  }
}
```

### Payload Webhook
```json
{
  "event": "prediction_created",
  "timestamp": "2024-01-15T14:30:00Z",
  "data": {
    "prediction_id": "pred_abc123",
    // ... données complètes
  },
  "signature": "sha256=..."
}
```

## 🔄 Migration depuis v1

### Changements Majeurs
1. **WebSocket obligatoire** pour temps réel (SSE déprécié)
2. **Compression** automatique des messages
3. **Gestion améliorée** des reconnexions
4. **Filtres avancés** avec opérateurs logiques
5. **Métriques détaillées** par connexion

### Guide de Migration
```javascript
// v1 (ancien)
const sse = new EventSource('/v1/stream');

// v2 (nouveau)
const ws = new WebSocket('wss://api.goat-prediction.com/v2/realtime/ws');
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  // Traitement identique
};
```

## 📞 Support

- **Documentation API complète**: https://docs.goat-prediction.com/api/v2
- **Exemples GitHub**: https://github.com/goat-prediction/examples
- **Support Discord**: https://discord.gg/goat-prediction
- **Email**: api-support@goat-prediction.com

## 📝 Notes de Version

### v2.1.0 (Prochainement)
- Support gRPC streaming
- Compression Brotli
- Filtres géographiques
- Analytics temps réel avancés

### v2.0.0 (Actuel)
- WebSocket stable
- Authentification améliorée
- Gestion d'erreurs complète
- Documentation exhaustive

---

**Dernière mise à jour**: 15 Janvier 2024  
**Statut**: Stable  
**Supporté jusqu'à**: Décembre 2025  
**Contact**: dev@goat-prediction.com
```

Ce document fournit une documentation complète et opérationnelle pour l'API Real-Time v2 de GOAT-PREDICTION. Il inclut:

1. **Tous les endpoints** avec exemples concrets
2. **Protocoles de communication** (WebSocket, SSE, gRPC)
3. **Formats de messages** détaillés
4. **Exemples de code** JavaScript et Python
5. **Gestion d'erreurs** complète
6. **Sécurité** et authentification
7. **Guide de migration** depuis v1
8. **Webhooks** pour intégrations alternatives

La documentation est prête à être utilisée par les développeurs et inclut tout le nécessaire pour implémenter une intégration robuste avec l'API temps réel.
