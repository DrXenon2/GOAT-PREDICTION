# API Predictions v1

## 📋 Vue d'ensemble

L'API Predictions v1 est le cœur du système GOAT Prediction Ultimate. Elle permet d'accéder aux prédictions, de soumettre des données pour analyse, et de récupérer des insights basés sur l'intelligence artificielle.

**Version**: 1.0.0  
**Base URL**: `https://api.goat-prediction.com/v1`  
**Contact**: api-support@goat-prediction.com

## 🔐 Authentification

Toutes les requêtes nécessitent une authentification via JWT Bearer Token.

```http
Authorization: Bearer <votre_jwt_token>
```

### Obtenir un token :
```bash
curl -X POST https://api.goat-prediction.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "votre@email.com",
    "password": "votre_mot_de_passe"
  }'
```

## 📊 Endpoints

### 1. Prédictions de matchs

#### GET `/predictions/matches`
Récupère les prédictions pour les matchs à venir.

**Query Parameters :**
| Paramètre | Type | Requis | Description | Exemple |
|-----------|------|--------|-------------|---------|
| `sport` | string | Non | Filtre par sport | `football`, `basketball` |
| `league` | string | Non | Filtre par ligue | `premier_league`, `nba` |
| `date_from` | datetime | Non | Date de début | `2024-01-15T00:00:00Z` |
| `date_to` | datetime | Non | Date de fin | `2024-01-20T23:59:59Z` |
| `limit` | integer | Non | Nombre de résultats (max 100) | `50` |
| `offset` | integer | Non | Pagination | `0` |
| `min_confidence` | float | Non | Confiance minimale | `0.6` |
| `min_ev` | float | Non | Valeur attendue minimale | `0.05` |

**Exemple de requête :**
```bash
curl -X GET "https://api.goat-prediction.com/v1/predictions/matches?sport=football&date_from=2024-01-15T00:00:00Z&limit=10" \
  -H "Authorization: Bearer votre_jwt_token"
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "predictions": [
      {
        "prediction_id": "pred_abc123def456",
        "match_id": "match_123456",
        "sport": "football",
        "league": "premier_league",
        "home_team": {
          "team_id": "team_123",
          "name": "Manchester United",
          "short_name": "MUN"
        },
        "away_team": {
          "team_id": "team_456",
          "name": "Manchester City",
          "short_name": "MCI"
        },
        "match_date": "2024-01-20T15:00:00Z",
        "predictions": {
          "match_winner": {
            "home_probability": 0.35,
            "away_probability": 0.45,
            "draw_probability": 0.20,
            "confidence": 0.78,
            "expected_value": 0.12,
            "recommended_bet": "AWAY",
            "kelly_fraction": 0.02
          },
          "over_under": {
            "over_probability": 0.62,
            "under_probability": 0.38,
            "line": 2.5,
            "confidence": 0.65,
            "expected_value": 0.08,
            "recommended_bet": "OVER",
            "kelly_fraction": 0.015
          }
        },
        "model_metadata": {
          "model_version": "v2.1.0",
          "features_used": ["form", "h2h", "injuries", "weather"],
          "training_date": "2024-01-10T00:00:00Z"
        },
        "last_updated": "2024-01-19T10:30:00Z"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 10,
      "offset": 0,
      "has_more": true
    },
    "summary": {
      "total_predictions": 150,
      "average_confidence": 0.72,
      "average_ev": 0.09
    }
  },
  "timestamp": "2024-01-19T12:00:00Z"
}
```

### 2. Prédiction spécifique

#### GET `/predictions/matches/{match_id}`
Récupère les prédictions détaillées pour un match spécifique.

**Path Parameters :**
| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `match_id` | string | Oui | ID du match |

**Exemple de requête :**
```bash
curl -X GET "https://api.goat-prediction.com/v1/predictions/matches/match_123456" \
  -H "Authorization: Bearer votre_jwt_token"
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "prediction_id": "pred_abc123def456",
    "match_id": "match_123456",
    "sport": "football",
    "league": "premier_league",
    "home_team": {
      "team_id": "team_123",
      "name": "Manchester United",
      "short_name": "MUN",
      "form": ["W", "D", "L", "W", "W"],
      "home_record": "8-2-1",
      "recent_goals": 12
    },
    "away_team": {
      "team_id": "team_456",
      "name": "Manchester City",
      "short_name": "MCI",
      "form": ["W", "W", "D", "W", "L"],
      "away_record": "7-3-1",
      "recent_goals": 15
    },
    "match_date": "2024-01-20T15:00:00Z",
    "venue": "Old Trafford",
    "weather": {
      "condition": "partly_cloudy",
      "temperature_c": 12.5,
      "precipitation_mm": 0.0,
      "wind_speed_kmh": 15.2
    },
    "detailed_predictions": {
      "match_winner": {
        "probabilities": {
          "home": 0.35,
          "away": 0.45,
          "draw": 0.20
        },
        "odds": {
          "best_home": 3.10,
          "best_away": 2.20,
          "best_draw": 3.50
        },
        "expected_value": {
          "home": -0.05,
          "away": 0.12,
          "draw": -0.15
        },
        "kelly_fraction": {
          "home": 0.0,
          "away": 0.02,
          "draw": 0.0
        },
        "confidence": 0.78,
        "model_explanations": [
          {
            "feature": "away_team_form",
            "impact": 0.15,
            "description": "City a gagné 4 de ses 5 derniers matchs"
          },
          {
            "feature": "head_to_head",
            "impact": 0.10,
            "description": "City a gagné 3 des 5 derniers derbys"
          }
        ]
      },
      "over_under": {
        "line": 2.5,
        "probabilities": {
          "over": 0.62,
          "under": 0.38
        },
        "odds": {
          "best_over": 1.95,
          "best_under": 1.90
        },
        "expected_value": {
          "over": 0.08,
          "under": -0.12
        },
        "confidence": 0.65,
        "model_explanations": [
          {
            "feature": "average_goals_last_5",
            "impact": 0.20,
            "description": "Moyenne de 3.2 buts par match pour ces équipes"
          }
        ]
      }
    },
    "injuries": {
      "home_team": [
        {
          "player": "Marcus Rashford",
          "position": "Forward",
          "status": "doubtful",
          "impact_score": 0.7
        }
      ],
      "away_team": []
    },
    "model_insights": {
      "key_factors": [
        "La forme récente de City est excellente",
        "United a des problèmes défensifs à domicile",
        "Historiquement, les derbys sont prolifiques en buts"
      ],
      "risk_factors": [
        "Rashford pourrait être absent pour United",
        "Conditions météo favorables au jeu offensif"
      ],
      "confidence_level": "high"
    },
    "last_updated": "2024-01-19T10:30:00Z",
    "next_update": "2024-01-19T18:00:00Z"
  },
  "timestamp": "2024-01-19T12:00:00Z"
}
```

### 3. Soumettre un match pour prédiction

#### POST `/predictions/submit`
Soumet un match pour analyse et prédiction.

**Body Parameters :**
```json
{
  "sport": "football",
  "league": "premier_league",
  "home_team_id": "team_123",
  "away_team_id": "team_456",
  "match_date": "2024-01-20T15:00:00Z",
  "additional_data": {
    "venue": "Old Trafford",
    "referee": "Anthony Taylor",
    "weather_forecast": {
      "condition": "partly_cloudy",
      "temperature_c": 12.5
    }
  },
  "priority": "high",
  "callback_url": "https://votre-site.com/webhooks/predictions"
}
```

**Exemple de requête :**
```bash
curl -X POST "https://api.goat-prediction.com/v1/predictions/submit" \
  -H "Authorization: Bearer votre_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "sport": "football",
    "league": "premier_league",
    "home_team_id": "team_123",
    "away_team_id": "team_456",
    "match_date": "2024-01-20T15:00:00Z",
    "priority": "high"
  }'
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "prediction_request_id": "req_xyz789abc123",
    "match_id": "match_123456",
    "status": "processing",
    "estimated_completion": "2024-01-19T14:30:00Z",
    "queue_position": 5,
    "webhook_url": "https://api.goat-prediction.com/v1/webhooks/predictions/req_xyz789abc123",
    "check_status_url": "https://api.goat-prediction.com/v1/predictions/status/req_xyz789abc123"
  },
  "timestamp": "2024-01-19T12:00:00Z"
}
```

### 4. Statut de prédiction

#### GET `/predictions/status/{request_id}`
Vérifie le statut d'une demande de prédiction.

**Exemple de requête :**
```bash
curl -X GET "https://api.goat-prediction.com/v1/predictions/status/req_xyz789abc123" \
  -H "Authorization: Bearer votre_jwt_token"
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "prediction_request_id": "req_xyz789abc123",
    "match_id": "match_123456",
    "status": "completed",
    "progress": 100,
    "prediction_id": "pred_abc123def456",
    "prediction_url": "https://api.goat-prediction.com/v1/predictions/matches/match_123456",
    "processing_time_ms": 2450,
    "models_used": ["xgboost_v2", "neural_network_v3", "ensemble"],
    "completed_at": "2024-01-19T12:02:30Z"
  },
  "timestamp": "2024-01-19T12:05:00Z"
}
```

### 5. Historique des prédictions

#### GET `/predictions/history`
Récupère l'historique des prédictions avec leurs résultats.

**Query Parameters :**
| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `sport` | string | Non | Filtre par sport |
| `date_from` | datetime | Non | Date de début |
| `date_to` | datetime | Non | Date de fin |
| `outcome` | string | Non | Filtre par résultat | `win`, `loss`, `push` |
| `min_accuracy` | float | Non | Précision minimale |
| `limit` | integer | Non | Nombre de résultats |
| `offset` | integer | Non | Pagination |

**Exemple de requête :**
```bash
curl -X GET "https://api.goat-prediction.com/v1/predictions/history?date_from=2024-01-01T00:00:00Z&limit=5" \
  -H "Authorization: Bearer votre_jwt_token"
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "history": [
      {
        "prediction_id": "pred_old123",
        "match_id": "match_789",
        "sport": "football",
        "match_date": "2024-01-10T20:00:00Z",
        "home_team": "Liverpool",
        "away_team": "Chelsea",
        "prediction": {
          "market": "match_winner",
          "recommended_bet": "HOME",
          "probability": 0.68,
          "confidence": 0.75,
          "odds_taken": 1.80
        },
        "outcome": {
          "result": "2-0",
          "winner": "HOME",
          "prediction_correct": true,
          "profit_loss": 0.8,
          "accuracy_score": 0.92
        },
        "evaluation": {
          "brier_score": 0.12,
          "log_loss": 0.45,
          "calibration_error": 0.03
        }
      }
    ],
    "performance_metrics": {
      "total_predictions": 1250,
      "winning_predictions": 812,
      "accuracy": 0.65,
      "profit_loss": 124.5,
      "roi": 0.15,
      "sharpe_ratio": 2.1,
      "max_drawdown": -8.2
    },
    "pagination": {
      "total": 1250,
      "limit": 5,
      "offset": 0,
      "has_more": true
    }
  },
  "timestamp": "2024-01-19T12:00:00Z"
}
```

### 6. Modèles disponibles

#### GET `/predictions/models`
Récupère la liste des modèles de prédiction disponibles.

**Query Parameters :**
| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `sport` | string | Non | Filtre par sport |
| `active` | boolean | Non | Modèles actifs seulement |

**Exemple de requête :**
```bash
curl -X GET "https://api.goat-prediction.com/v1/predictions/models?sport=football" \
  -H "Authorization: Bearer votre_jwt_token"
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "models": [
      {
        "model_id": "xgboost_football_v2",
        "name": "XGBoost Football Predictor v2",
        "sport": "football",
        "version": "2.1.0",
        "description": "Modèle gradient boosting pour prédictions football",
        "markets": ["match_winner", "over_under", "btts"],
        "performance": {
          "accuracy": 0.68,
          "precision": 0.71,
          "recall": 0.65,
          "f1_score": 0.68,
          "roc_auc": 0.72,
          "training_date": "2024-01-01T00:00:00Z",
          "last_updated": "2024-01-15T10:00:00Z"
        },
        "features": [
          "team_form",
          "head_to_head",
          "home_advantage",
          "injuries",
          "weather_impact"
        ],
        "status": "active",
        "api_endpoint": "/v1/predictions/models/xgboost_football_v2/predict"
      },
      {
        "model_id": "neural_network_football_v3",
        "name": "Neural Network Football Predictor v3",
        "sport": "football",
        "version": "3.0.1",
        "description": "Réseau de neurones profond pour prédictions avancées",
        "markets": ["match_winner", "correct_score", "handicap"],
        "performance": {
          "accuracy": 0.65,
          "precision": 0.68,
          "recall": 0.62,
          "f1_score": 0.65,
          "roc_auc": 0.70,
          "training_date": "2023-12-15T00:00:00Z",
          "last_updated": "2024-01-10T14:30:00Z"
        },
        "features": [
          "player_ratings",
          "tactical_analysis",
          "momentum_metrics",
          "fatigue_factors"
        ],
        "status": "active",
        "api_endpoint": "/v1/predictions/models/neural_network_football_v3/predict"
      }
    ],
    "ensemble_models": [
      {
        "name": "GOAT Ensemble Predictor",
        "strategy": "weighted_average",
        "component_models": ["xgboost_football_v2", "neural_network_football_v3"],
        "weights": [0.6, 0.4],
        "overall_accuracy": 0.70,
        "description": "Combinaison optimisée de plusieurs modèles"
      }
    ]
  },
  "timestamp": "2024-01-19T12:00:00Z"
}
```

### 7. Prédiction avec modèle spécifique

#### POST `/predictions/models/{model_id}/predict`
Utilise un modèle spécifique pour faire une prédiction.

**Body Parameters :**
```json
{
  "match_data": {
    "sport": "football",
    "home_team": {
      "team_id": "team_123",
      "recent_form": ["W", "D", "W", "L", "W"],
      "home_record": "8-2-1",
      "goals_scored": 25,
      "goals_conceded": 12
    },
    "away_team": {
      "team_id": "team_456",
      "recent_form": ["W", "W", "D", "W", "L"],
      "away_record": "7-3-1",
      "goals_scored": 30,
      "goals_conceded": 15
    },
    "head_to_head": [
      {"date": "2023-08-15", "home_score": 2, "away_score": 1},
      {"date": "2023-02-10", "home_score": 0, "away_score": 2}
    ],
    "additional_features": {
      "weather": "clear",
      "venue_type": "home_stadium",
      "importance": "high"
    }
  },
  "market": "match_winner",
  "return_explanations": true
}
```

**Exemple de requête :**
```bash
curl -X POST "https://api.goat-prediction.com/v1/predictions/models/xgboost_football_v2/predict" \
  -H "Authorization: Bearer votre_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "match_data": {
      "sport": "football",
      "home_team": {
        "team_id": "team_123",
        "recent_form": ["W", "D", "W", "L", "W"]
      },
      "away_team": {
        "team_id": "team_456",
        "recent_form": ["W", "W", "D", "W", "L"]
      }
    },
    "market": "match_winner",
    "return_explanations": true
  }'
```

**Réponse :**
```json
{
  "status": "success",
  "data": {
    "model_id": "xgboost_football_v2",
    "prediction_id": "model_pred_123",
    "market": "match_winner",
    "probabilities": {
      "home": 0.62,
      "away": 0.25,
      "draw": 0.13
    },
    "confidence": 0.78,
    "inference_time_ms": 45,
    "explanations": {
      "feature_importance": [
        {"feature": "home_team_form", "importance": 0.32},
        {"feature": "head_to_head_home", "importance": 0.25},
        {"feature": "home_advantage", "importance": 0.18},
        {"feature": "recent_goals_diff", "importance": 0.15},
        {"feature": "days_since_last_match", "importance": 0.10}
      ],
      "key_factors": [
        "L'équipe à domicile a une excellente forme récente",
        "Historiquement forte performance à domicile contre cet adversaire",
        "Différence positive de buts récents"
      ]
    },
    "model_metadata": {
      "version": "2.1.0",
      "training_date": "2024-01-01T00:00:00Z",
      "features_used": ["form", "h2h", "home_adv", "goals", "rest_days"]
    },
    "timestamp": "2024-01-19T12:00:00Z"
  }
}
```

## 🎯 Codes de statut HTTP

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Mauvaise requête - Vérifiez les paramètres |
| 401 | Non authentifié - Token invalide ou manquant |
| 403 | Interdit - Permissions insuffisantes |
| 404 | Ressource non trouvée |
| 422 | Entité non traitable - Validation échouée |
| 429 | Trop de requêtes - Rate limit atteint |
| 500 | Erreur interne du serveur |
| 503 | Service indisponible - Maintenance ou surcharge |

## ⚡ Rate Limiting

Les limites de taux sont appliquées par plan d'API :

| Plan | Requêtes/minute | Requêtes/jour | Concurrent |
|------|----------------|---------------|------------|
| Free | 10 | 1,000 | 2 |
| Pro | 60 | 10,000 | 10 |
| Enterprise | 500 | 100,000 | 50 |

**Headers de rate limiting :**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1617032400
```

## 🔄 Webhooks

### Configuration webhook :
```json
{
  "url": "https://votre-site.com/webhooks/predictions",
  "events": ["prediction.completed", "prediction.updated", "match.started"],
  "secret": "votre_secret_signature"
}
```

### Payload webhook :
```json
{
  "event": "prediction.completed",
  "data": {
    "prediction_id": "pred_abc123def456",
    "match_id": "match_123456",
    "status": "completed",
    "prediction_url": "https://api.goat-prediction.com/v1/predictions/matches/match_123456",
    "completed_at": "2024-01-19T12:02:30Z"
  },
  "timestamp": "2024-01-19T12:02:35Z",
  "signature": "sha256=..."
}
```

## 📈 Monitoring et métriques

### Métriques disponibles :
```bash
# Statistiques d'utilisation
GET /v1/metrics/usage

# Performance des modèles
GET /v1/metrics/model-performance

# Latence des prédictions
GET /v1/metrics/latency

# Précision historique
GET /v1/metrics/accuracy
```

## 🛡️ Sécurité

### Best practices :
1. **Stockage sécurisé des tokens** : Ne jamais exposer les tokens JWT côté client
2. **HTTPS obligatoire** : Toutes les requêtes doivent utiliser HTTPS
3. **Validation des inputs** : Valider tous les paramètres d'entrée
4. **Logging d'audit** : Conserver les logs d'accès pendant 90 jours
5. **Rotation des clés** : Changer régulièrement les clés d'API

### Headers de sécurité :
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## 🚀 Exemples d'intégration

### Python :
```python
import requests
from datetime import datetime, timezone

class GoatPredictionClient:
    def __init__(self, api_key, base_url="https://api.goat-prediction.com/v1"):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_predictions(self, sport=None, date_from=None, limit=10):
        params = {}
        if sport:
            params["sport"] = sport
        if date_from:
            params["date_from"] = date_from.isoformat()
        params["limit"] = limit
        
        response = requests.get(
            f"{self.base_url}/predictions/matches",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def submit_prediction_request(self, match_data):
        response = requests.post(
            f"{self.base_url}/predictions/submit",
            headers=self.headers,
            json=match_data
        )
        response.raise_for_status()
        return response.json()

# Utilisation
client = GoatPredictionClient(api_key="votre_api_key")
predictions = client.get_predictions(
    sport="football",
    date_from=datetime.now(timezone.utc),
    limit=5
)
```

### JavaScript/Node.js :
```javascript
const axios = require('axios');

class GoatPredictionClient {
  constructor(apiKey, baseUrl = 'https://api.goat-prediction.com/v1') {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      }
    });
  }

  async getPredictions(options = {}) {
    const params = {
      sport: options.sport,
      date_from: options.dateFrom?.toISOString(),
      limit: options.limit || 10
    };
    
    const response = await this.client.get('/predictions/matches', { params });
    return response.data;
  }

  async submitPrediction(matchData) {
    const response = await this.client.post('/predictions/submit', matchData);
    return response.data;
  }
}

// Utilisation
const client = new GoatPredictionClient('votre_api_key');
const predictions = await client.getPredictions({
  sport: 'football',
  limit: 5
});
```

## 🔍 Dépannage

### Problèmes courants :

1. **401 Unauthorized** :
   - Vérifiez que le token JWT est valide
   - Assurez-vous qu'il n'a pas expiré
   - Vérifiez le format du header Authorization

2. **429 Too Many Requests** :
   - Implémentez un système de retry avec backoff exponentiel
   - Surveillez les headers X-RateLimit-*
   - Passez à un plan supérieur si nécessaire

3. **400 Bad Request** :
   - Validez le format des dates (ISO 8601)
   - Vérifiez les types de données des paramètres
   - Consultez la documentation pour les valeurs autorisées

4. **503 Service Unavailable** :
   - Attendez quelques minutes avant de réessayer
   - Vérifiez le status page à status.goat-prediction.com
   - Contactez le support si le problème persiste

### Logs d'erreur :
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid date format. Use ISO 8601 format.",
    "details": {
      "field": "date_from",
      "value": "2024-01-20",
      "expected_format": "YYYY-MM-DDThh:mm:ssZ"
    },
    "timestamp": "2024-01-19T12:00:00Z",
    "request_id": "req_123456789"
  }
}
```

## 📞 Support

Pour le support technique :
- **Email** : api-support@goat-prediction.com
- **Documentation** : docs.goat-prediction.com
- **Status Page** : status.goat-prediction.com
- **Community** : community.goat-prediction.com

## 📄 Licence

L'utilisation de cette API est soumise aux termes de notre [Accord de Service](https://goat-prediction.com/terms) et [Politique de Confidentialité](https://goat-prediction.com/privacy).

---

**Dernière mise à jour** : 2024-01-19  
**Version API** : 1.0.0  
**Contact** : api-support@goat-prediction.com
