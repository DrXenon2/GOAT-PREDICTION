# 🐐 GOAT-PREDICTION-ULTIMATE

**L'IA la plus avancée au monde pour les prédictions sportives et le betting intelligent**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker-✓-blue.svg)](https://docker.com)

## 🎯 Objectif

Atteindre **85%+ de précision** sur les prédictions sportives à travers toutes les disciplines grâce à une architecture multi-couches avancée combinant :

- 🧠 **Machine Learning Quantique Émulé**
- ⚡ **Traitement en Temps Réel**
- 📊 **Analytics Avancées**
- 🏦 **Gestion de Risque Institutionnelle**

## 🏗️ Architecture

### Couche 1 : Perception Temps Réel
- 27 APIs sportives simultanées
- Flux de données temps réel
- Analyse sentimentale des médias sociaux
- Données météorologiques et conditions terrain

### Couche 2 : Traitement Quantique Émulé
- Réseaux de neurones quantiques simulés
- Transformers multi-attention (64 têtes)
- Graph Neural Networks pour relations joueurs/équipes
- Architectures NeuroSymbolic

### Couche 3 : Raisonnement Stratégique
- Théorie des jeux appliquée aux sports
- Mathématiques financières pour bankroll management
- Physique du sport (trajectoires, énergie)
- Psychologie sportive et momentum

### Couche 4 : Méta-Apprentissage
- Transfer learning cross-sport
- Apprentissage par renforcement profond
- Détection automatique de concept drift
- Auto-ML avec optimisation bayésienne

## 🚀 Démarrage Rapide

### Prérequis
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Git

### Installation
```
# 1. Cloner le projet
git clone https://github.com/goat-prediction/ultimate.git
cd GOAT-PREDICTION

# 2. Configuration initiale
make setup
# Éditer .env.local avec vos configurations

# 3. Lancer l'infrastructure
make init
make build
make start

# 4. Initialiser la base de données
make db-init
make db-migrate

# 5. Accéder à l'application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Documentation API: http://localhost:8000/docs
# Grafana: http://localhost:3001 (admin/admin)

```bash
GOAT-PREDICTION/
├── .babelrc
├── .backups/
│   ├── config/
│   │   ├── daily/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── monthly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── weekly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── database/
│   │   ├── daily/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── monthly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── weekly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── logs/
│   │   ├── daily/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── monthly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── weekly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── models/
│   │   ├── daily/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── monthly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── weekly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── README.md
│   └── xenon.js
├── .cache/
│   ├── data/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── logs/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── ml-models/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── tmp/
│   │   ├── README.md
│   │   └── xenon.js
│   └── xenon.js
├── .config/
│   ├── certbot/
│   │   ├── conf/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── renewal/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── elasticsearch/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── grafana/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── nginx/
│   │   ├── nginx.conf
│   │   ├── README.md
│   │   ├── sites-available/
│   │   │   ├── goat-prediction.conf
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── ssl/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   └── xenon.js
├── .dockerignore
├── .editorconfig
├── .env.development
├── .env.example
├── .env.local
├── .env.production
├── .env.staging
├── .eslintignore
├── .eslintrc.js
├── .github/
│   ├── dependabot.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   ├── README.md
│   ├── workflows/
│   │   ├── cd.yml
│   │   ├── ci.yml
│   │   ├── performance-test.yml
│   │   ├── README.md
│   │   ├── security-scan.yml
│   │   └── xenon.js
│   └── xenon.js
├── .gitignore
├── .logs/
│   ├── access/
│   │   ├── admin/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── api-gateway/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── nginx/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── application/
│   │   ├── api/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── database/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── frontend/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── ml/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── audit/
│   │   ├── README.md
│   │   ├── security/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── system/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── user-actions/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── error/
│   │   ├── api/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── database/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── frontend/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── ml/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── rotated/
│   │   ├── daily/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── monthly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── weekly/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   └── xenon.js
├── .nvmrc
├── .prettierignore
├── .prettierrc
├── .python-version
├── .secrets/
│   ├── api-keys/
│   │   ├── README.md
│   │   ├── statsbomb.key
│   │   └── xenon.js
│   ├── auth/
│   │   ├── jwt-secret.key
│   │   ├── README.md
│   │   └── xenon.js
│   ├── database/
│   │   ├── README.md
│   │   ├── supabase.env
│   │   └── xenon.js
│   ├── README.md
│   ├── ssl/
│   │   ├── README.md
│   │   ├── wildcard.crt
│   │   └── xenon.js
│   └── xenon.js
├── .stylelintrc
├── .tmp/
│   ├── backups/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── downloads/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── processing/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── uploads/
│   │   ├── README.md
│   │   └── xenon.js
│   └── xenon.js
├── .vscode/
│   ├── extensions.json
│   ├── launch.json
│   ├── README.md
│   ├── settings.json
│   └── xenon.js
├── backend/
│   ├── api-gateway/
│   │   ├── alembic.ini
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── requirements-dev.txt
│   │   ├── requirements.txt
│   │   ├── setup.cfg
│   │   ├── setup.py
│   │   ├── src/
│   │   │   ├── app.py
│   │   │   ├── config/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── constants.py
│   │   │   │   ├── logging_config.py
│   │   │   │   ├── README.md
│   │   │   │   ├── settings.py
│   │   │   │   └── xenon.js
│   │   │   ├── dependencies.py
│   │   │   ├── main.py
│   │   │   ├── middleware/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── cors.py
│   │   │   │   ├── error_handler.py
│   │   │   │   ├── logging.py
│   │   │   │   ├── rate_limiter.py
│   │   │   │   ├── README.md
│   │   │   │   ├── validation.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── routes/
│   │   │   │   ├── admin/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── models.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── system.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── v1/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── analytics.py
│   │   │   │   │   ├── bets.py
│   │   │   │   │   ├── predictions.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports.py
│   │   │   │   │   ├── subscriptions.py
│   │   │   │   │   ├── users.py
│   │   │   │   │   ├── webhooks.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── v2/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── advanced.py
│   │   │   │   │   ├── insights.py
│   │   │   │   │   ├── predictions.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── realtime.py
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── schemas/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bets.py
│   │   │   │   ├── predictions.py
│   │   │   │   ├── README.md
│   │   │   │   ├── responses.py
│   │   │   │   ├── sports.py
│   │   │   │   ├── users.py
│   │   │   │   └── xenon.js
│   │   │   ├── utils/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── converters.py
│   │   │   │   ├── formatters.py
│   │   │   │   ├── helpers.py
│   │   │   │   ├── README.md
│   │   │   │   ├── validators.py
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── e2e/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_full_flow.py
│   │   │   │   ├── test_performance.py
│   │   │   │   └── xenon.js
│   │   │   ├── integration/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_api.py
│   │   │   │   ├── test_auth.py
│   │   │   │   ├── test_rate_limit.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── unit/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_middleware.py
│   │   │   │   ├── test_routes.py
│   │   │   │   ├── test_utils.py
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── auth-service/
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── notification-service/
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── prediction-engine/
│   │   ├── 1.dockerignore
│   │   ├── 1.env.example
│   │   ├── 1.env.local
│   │   ├── 1.env.production
│   │   ├── 1.flake8
│   │   ├── 1.gitignore
│   │   ├── 1.pylintrc
│   │   ├── CHANGELOG.md
│   │   ├── CODE_OF_CONDUCT.md
│   │   ├── config/
│   │   │   ├── betting_config.yaml
│   │   │   ├── data_sources.yaml
│   │   │   ├── markets/
│   │   │   │   ├── basketball_markets.yaml
│   │   │   │   ├── esports_markets.yaml
│   │   │   │   ├── football_markets.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── tennis_markets.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── ml_config.yaml
│   │   │   ├── models/
│   │   │   │   ├── basketball_models.yaml
│   │   │   │   ├── ensemble_config.yaml
│   │   │   │   ├── football_models.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── tennis_models.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── monitoring_config.yaml
│   │   │   ├── README.md
│   │   │   ├── sports/
│   │   │   │   ├── baseball.yaml
│   │   │   │   ├── basketball.yaml
│   │   │   │   ├── esports.yaml
│   │   │   │   ├── football.yaml
│   │   │   │   ├── hockey.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── rugby.yaml
│   │   │   │   ├── tennis.yaml
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── CONTRIBUTING.md
│   │   ├── data/
│   │   │   ├── backups/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── cache/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── processed/
│   │   │   │   ├── features/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── training/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── raw/
│   │   │   │   ├── basketball/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── football/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── odds/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── tennis/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── docker-compose.dev.yml
│   │   ├── docker-compose.prod.yml
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile
│   │   ├── logs/
│   │   │   ├── access.log
│   │   │   ├── error.log
│   │   │   ├── prediction.log
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── migrations/
│   │   │   ├── env.py
│   │   │   ├── README.md
│   │   │   ├── script.py.mako
│   │   │   ├── versions/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── models/
│   │   │   ├── basketball/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── ensembles/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── football/
│   │   │   │   ├── exact_score/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── match_winner/
│   │   │   │   │   ├── metadata.json
│   │   │   │   │   ├── model.joblib
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── scaler.joblib
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── over_under/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── tennis/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── mypy.ini
│   │   ├── pre-commit-config.yaml
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── requirements-dev.txt
│   │   ├── requirements-ml.txt
│   │   ├── requirements.txt
│   │   ├── scripts/
│   │   │   ├── backtest.py
│   │   │   ├── benchmark.py
│   │   │   ├── cleanup.py
│   │   │   ├── deploy.py
│   │   │   ├── monitor.py
│   │   │   ├── optimize.py
│   │   │   ├── README.md
│   │   │   ├── train_models.py
│   │   │   ├── update_data.py
│   │   │   └── xenon.js
│   │   ├── setup.cfg
│   │   ├── setup.py
│   │   ├── src/
│   │   │   ├── analytics/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── calculators/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── odds_calculator.py
│   │   │   │   │   ├── performance_calculator.py
│   │   │   │   │   ├── probability_calculator.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── risk_calculator.py
│   │   │   │   │   ├── roi_calculator.py
│   │   │   │   │   ├── stake_calculator.py
│   │   │   │   │   ├── value_calculator.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── evaluators/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── market_evaluator.py
│   │   │   │   │   ├── match_evaluator.py
│   │   │   │   │   ├── odds_evaluator.py
│   │   │   │   │   ├── player_evaluator.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── risk_evaluator.py
│   │   │   │   │   ├── team_evaluator.py
│   │   │   │   │   ├── value_evaluator.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── formulas/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── advanced_metrics.py
│   │   │   │   │   ├── elo_formulas.py
│   │   │   │   │   ├── expected_value.py
│   │   │   │   │   ├── glicko_formulas.py
│   │   │   │   │   ├── kelly_criterion.py
│   │   │   │   │   ├── markowitz.py
│   │   │   │   │   ├── monte_carlo.py
│   │   │   │   │   ├── poisson_formulas.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sharpe_ratio.py
│   │   │   │   │   ├── true_skill.py
│   │   │   │   │   ├── value_at_risk.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── visualizers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── chart_generator.py
│   │   │   │   │   ├── dashboard_builder.py
│   │   │   │   │   ├── heatmap_generator.py
│   │   │   │   │   ├── prediction_visualizer.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── report_generator.py
│   │   │   │   │   ├── trend_analyzer.py
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── analytics.py
│   │   │   │   │   ├── markets.py
│   │   │   │   │   ├── odds.py
│   │   │   │   │   ├── predictions.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports.py
│   │   │   │   │   ├── webhooks.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── websockets/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── live_stream.py
│   │   │   │   │   ├── market_stream.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── realtime_updates.py
│   │   │   │   │   ├── ws_manager.py
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── app.py
│   │   │   ├── betting/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── arbitrage_finder.py
│   │   │   │   ├── bankroll_manager.py
│   │   │   │   ├── bet_strategy.py
│   │   │   │   ├── bet_validator.py
│   │   │   │   ├── betting_simulator.py
│   │   │   │   ├── hedge_manager.py
│   │   │   │   ├── portfolio_manager.py
│   │   │   │   ├── README.md
│   │   │   │   ├── risk_manager.py
│   │   │   │   ├── stake_calculator.py
│   │   │   │   └── xenon.js
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── config/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── env_config.py
│   │   │   │   │   ├── loaders.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── settings.py
│   │   │   │   │   ├── validators.py
│   │   │   │   │   ├── xenon.js
│   │   │   │   │   └── yaml_config.py
│   │   │   │   ├── constants/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── currencies.py
│   │   │   │   │   ├── errors.py
│   │   │   │   │   ├── formulas.py
│   │   │   │   │   ├── markets.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports.py
│   │   │   │   │   ├── timezones.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── exceptions/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── api_errors.py
│   │   │   │   │   ├── betting_errors.py
│   │   │   │   │   ├── data_errors.py
│   │   │   │   │   ├── model_errors.py
│   │   │   │   │   ├── prediction_errors.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── logging/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── formatters.py
│   │   │   │   │   ├── handlers.py
│   │   │   │   │   ├── logger.py
│   │   │   │   │   ├── middleware.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── utils/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── cache_utils.py
│   │   │   │   │   ├── date_utils.py
│   │   │   │   │   ├── decorators.py
│   │   │   │   │   ├── math_utils.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── serializers.py
│   │   │   │   │   ├── validators.py
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── data/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── collectors/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_collector.py
│   │   │   │   │   ├── basketball/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── basketball_reference_collector.py
│   │   │   │   │   │   ├── espn_collector.py
│   │   │   │   │   │   ├── euroleague_collector.py
│   │   │   │   │   │   ├── fiba_collector.py
│   │   │   │   │   │   ├── nba_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── collector_manager.py
│   │   │   │   │   ├── esports/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── csgo_collector.py
│   │   │   │   │   │   ├── dota_collector.py
│   │   │   │   │   │   ├── esports_earning_collector.py
│   │   │   │   │   │   ├── lol_collector.py
│   │   │   │   │   │   ├── overwatch_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── valorant_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── football/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── flashscore_collector.py
│   │   │   │   │   │   ├── opta_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── sofascore_collector.py
│   │   │   │   │   │   ├── statsbomb_collector.py
│   │   │   │   │   │   ├── understat_collector.py
│   │   │   │   │   │   ├── whoscored_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── news/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── bbc_collector.py
│   │   │   │   │   │   ├── espn_collector.py
│   │   │   │   │   │   ├── gnews_collector.py
│   │   │   │   │   │   ├── news_analyzer.py
│   │   │   │   │   │   ├── newsapi_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── odds/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── bet365_collector.py
│   │   │   │   │   │   ├── betfair_collector.py
│   │   │   │   │   │   ├── odds_aggregator.py
│   │   │   │   │   │   ├── odds_comparator.py
│   │   │   │   │   │   ├── pinnacle_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── williamhill_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── social/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── instagram_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── reddit_collector.py
│   │   │   │   │   │   ├── sentiment_analyzer.py
│   │   │   │   │   │   ├── social_monitor.py
│   │   │   │   │   │   ├── trend_analyzer.py
│   │   │   │   │   │   ├── twitter_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── tennis/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── atp_collector.py
│   │   │   │   │   │   ├── itf_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── tennisabstract_collector.py
│   │   │   │   │   │   ├── ultimatetennis_collector.py
│   │   │   │   │   │   ├── wta_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── weather/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── accuweather_collector.py
│   │   │   │   │   │   ├── openweather_collector.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── visualcrossing_collector.py
│   │   │   │   │   │   ├── weather_analyzer.py
│   │   │   │   │   │   ├── weather_api_collector.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── processors/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── aggregator.py
│   │   │   │   │   ├── data_cleaner.py
│   │   │   │   │   ├── feature_engineer.py
│   │   │   │   │   ├── normalizer.py
│   │   │   │   │   ├── pipeline.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── transformer.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── storage/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── mongodb_client.py
│   │   │   │   │   ├── postgres_client.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── redis_client.py
│   │   │   │   │   ├── s3_client.py
│   │   │   │   │   ├── supabase_client.py
│   │   │   │   │   ├── timescale_client.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── transformers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── basketball_transformer.py
│   │   │   │   │   ├── esports_transformer.py
│   │   │   │   │   ├── football_transformer.py
│   │   │   │   │   ├── generic_transformer.py
│   │   │   │   │   ├── odds_transformer.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── tennis_transformer.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── validators/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── anomaly_detector.py
│   │   │   │   │   ├── data_validator.py
│   │   │   │   │   ├── integrity_checker.py
│   │   │   │   │   ├── outlier_detector.py
│   │   │   │   │   ├── quality_checker.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── main.py
│   │   │   ├── ml/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── bias_detector.py
│   │   │   │   │   ├── confidence_calibrator.py
│   │   │   │   │   ├── drift_detector.py
│   │   │   │   │   ├── explainability.py
│   │   │   │   │   ├── feature_importance.py
│   │   │   │   │   ├── model_evaluator.py
│   │   │   │   │   ├── performance_tracker.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── ensembles/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── bayesian_ensemble.py
│   │   │   │   │   ├── boosting_ensemble.py
│   │   │   │   │   ├── dynamic_ensemble.py
│   │   │   │   │   ├── ensemble_manager.py
│   │   │   │   │   ├── quantum_ensemble.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── stacking_ensemble.py
│   │   │   │   │   ├── weighted_ensemble.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── features/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── advanced_features.py
│   │   │   │   │   ├── basketball_features.py
│   │   │   │   │   ├── contextual_features.py
│   │   │   │   │   ├── esports_features.py
│   │   │   │   │   ├── feature_extractor.py
│   │   │   │   │   ├── feature_selector.py
│   │   │   │   │   ├── football_features.py
│   │   │   │   │   ├── momentum_features.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── statistical_features.py
│   │   │   │   │   ├── temporal_features.py
│   │   │   │   │   ├── tennis_features.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── models/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── advanced/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── attention_model.py
│   │   │   │   │   │   ├── bayesian_model.py
│   │   │   │   │   │   ├── ensemble_model.py
│   │   │   │   │   │   ├── graph_neural_network.py
│   │   │   │   │   │   ├── quantum_nn.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── time_series_model.py
│   │   │   │   │   │   ├── transformer_model.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── base_model.py
│   │   │   │   │   ├── basketball/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── live_betting_model.py
│   │   │   │   │   │   ├── moneyline_model.py
│   │   │   │   │   │   ├── player_props_model.py
│   │   │   │   │   │   ├── point_spread_model.py
│   │   │   │   │   │   ├── quarter_betting_model.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── total_points_model.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── esports/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── first_blood_model.py
│   │   │   │   │   │   ├── handicap_model.py
│   │   │   │   │   │   ├── map_winner_model.py
│   │   │   │   │   │   ├── match_winner_esports.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── total_kills_model.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── football/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── btts_model.py
│   │   │   │   │   │   ├── cards_model.py
│   │   │   │   │   │   ├── corners_model.py
│   │   │   │   │   │   ├── exact_score_model.py
│   │   │   │   │   │   ├── halftime_model.py
│   │   │   │   │   │   ├── match_winner_model.py
│   │   │   │   │   │   ├── over_under_model.py
│   │   │   │   │   │   ├── player_goals_model.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── model_factory.py
│   │   │   │   │   ├── model_registry.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── tennis/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── games_spread_model.py
│   │   │   │   │   │   ├── match_winner_tennis.py
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── set_betting_model.py
│   │   │   │   │   │   ├── tiebreak_model.py
│   │   │   │   │   │   ├── total_games_model.py
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── predictors/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base_predictor.py
│   │   │   │   │   ├── basketball_predictor.py
│   │   │   │   │   ├── esports_predictor.py
│   │   │   │   │   ├── football_predictor.py
│   │   │   │   │   ├── multi_sport_predictor.py
│   │   │   │   │   ├── predictor_manager.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── realtime_predictor.py
│   │   │   │   │   ├── tennis_predictor.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── trainers/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── cross_validator.py
│   │   │   │   │   ├── distributed_trainer.py
│   │   │   │   │   ├── hyperparameter_tuner.py
│   │   │   │   │   ├── model_trainer.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── retrain_scheduler.py
│   │   │   │   │   ├── trainer_factory.py
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── monitoring/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alert_system.py
│   │   │   │   ├── anomaly_detector.py
│   │   │   │   ├── health_check.py
│   │   │   │   ├── metrics_collector.py
│   │   │   │   ├── performance_monitor.py
│   │   │   │   ├── README.md
│   │   │   │   ├── realtime_monitor.py
│   │   │   │   ├── system_monitor.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── scheduler.py
│   │   │   ├── worker.py
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── e2e/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_betting_flow.py
│   │   │   │   ├── test_full_prediction.py
│   │   │   │   └── xenon.js
│   │   │   ├── integration/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_data_pipeline.py
│   │   │   │   ├── test_ml_pipeline.py
│   │   │   │   ├── test_prediction_flow.py
│   │   │   │   └── xenon.js
│   │   │   ├── performance/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── README.md
│   │   │   │   ├── test_latency.py
│   │   │   │   ├── test_scalability.py
│   │   │   │   ├── test_throughput.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── unit/
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── test_calculators.py
│   │   │   │   │   ├── test_evaluators.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── betting/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── test_risk_manager.py
│   │   │   │   │   ├── test_stake_calculator.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── test_formulas.py
│   │   │   │   │   ├── test_utils.py
│   │   │   │   │   ├── test_validators.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── data/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── test_collectors.py
│   │   │   │   │   ├── test_processors.py
│   │   │   │   │   ├── test_validators.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── ml/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── test_features.py
│   │   │   │   │   ├── test_models.py
│   │   │   │   │   ├── test_predictors.py
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── README.md
│   ├── subscription-service/
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── user-service/
│   │   ├── Dockerfile
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── tests/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   └── xenon.js
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── data-pipeline/
│   ├── batch/
│   │   ├── airflow/
│   │   │   ├── dags/
│   │   │   │   ├── data_collection.py
│   │   │   │   ├── model_training.py
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── docker-compose.airflow.yml
│   │   │   ├── operators/
│   │   │   │   ├── README.md
│   │   │   │   ├── sports_operator.py
│   │   │   │   └── xenon.js
│   │   │   ├── plugins/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── scripts/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── dbt/
│   │   │   ├── analysis/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── dbt_project.yml
│   │   │   ├── macros/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── models/
│   │   │   │   ├── intermediate/
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── team_performance.sql
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── marts/
│   │   │   │   │   ├── analytics.sql
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── seeds/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── staging/
│   │   │   │   │   ├── odds.sql
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports.sql
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── tests/
│   │   │   │   ├── accepted_values/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── not_null/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── relationships/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── uniqueness/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── real-time/
│   │   ├── flink/
│   │   │   ├── Dockerfile
│   │   │   ├── jobs/
│   │   │   │   ├── README.md
│   │   │   │   ├── real-time-aggregations.py
│   │   │   │   ├── windowed-calculations.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── state/
│   │   │   │   ├── checkpoints/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── savepoints/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── kafka/
│   │   │   ├── consumers/
│   │   │   │   ├── analytics-consumer.py
│   │   │   │   ├── prediction-consumer.py
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── docker-compose.kafka.yml
│   │   │   ├── producers/
│   │   │   │   ├── odds-producer.py
│   │   │   │   ├── README.md
│   │   │   │   ├── sports-producer.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── schemas/
│   │   │   │   ├── odds.avsc
│   │   │   │   ├── README.md
│   │   │   │   ├── sports.avsc
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── spark-streaming/
│   │   │   ├── config/
│   │   │   │   ├── README.md
│   │   │   │   ├── spark-config.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── Dockerfile
│   │   │   ├── jobs/
│   │   │   │   ├── odds-processing.py
│   │   │   │   ├── README.md
│   │   │   │   ├── real-time-predictions.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── storage/
│   │   ├── data-lake/
│   │   │   ├── backups/
│   │   │   │   ├── daily/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── monthly/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── weekly/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── features/
│   │   │   │   ├── aggregated/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── historical/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── realtime/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── processed/
│   │   │   │   ├── cleaned/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── normalized/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── validated/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── raw/
│   │   │   │   ├── news/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── odds/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── social/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── sports/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── weather/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── data-warehouse/
│   │   │   ├── aggregates/
│   │   │   │   ├── daily_aggregates.sql
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── dimensions/
│   │   │   │   ├── README.md
│   │   │   │   ├── sport_dimension.sql
│   │   │   │   ├── time_dimension.sql
│   │   │   │   └── xenon.js
│   │   │   ├── facts/
│   │   │   │   ├── bets_fact.sql
│   │   │   │   ├── predictions_fact.sql
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   └── xenon.js
├── database/
│   ├── README.md
│   ├── redis/
│   │   ├── configurations/
│   │   │   ├── README.md
│   │   │   ├── redis.conf
│   │   │   └── xenon.js
│   │   ├── docker-compose.redis.yml
│   │   ├── README.md
│   │   ├── scripts/
│   │   │   ├── lua/
│   │   │   │   ├── rate_limiter.lua
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── python/
│   │   │   │   ├── README.md
│   │   │   │   ├── redis_client.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── shell/
│   │   │   │   ├── backup.sh
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── supabase/
│   │   ├── functions/
│   │   │   ├── calculate_metrics.sql
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── migrations/
│   │   │   ├── 001_initial_schema.sql
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── policies/
│   │   │   ├── README.md
│   │   │   ├── users_policies.sql
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── seeds/
│   │   │   ├── README.md
│   │   │   ├── sports_data.sql
│   │   │   └── xenon.js
│   │   ├── supabase-config.yaml
│   │   ├── triggers/
│   │   │   ├── README.md
│   │   │   ├── update_timestamps.sql
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── timescaledb/
│   │   ├── continuous_aggregates/
│   │   │   ├── hourly_predictions.sql
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── hypertables/
│   │   │   ├── predictions_hypertable.sql
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── retention_policies/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── timescaledb-config.yaml
│   │   └── xenon.js
│   └── xenon.js
├── docker-compose.dev.yml
├── docker-compose.override.yml
├── docker-compose.prod.yml
├── docker-compose.test.yml
├── docker-compose.yml
├── docs/
│   ├── api/
│   │   ├── README.md
│   │   ├── v1/
│   │   │   ├── predictions.md
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── v2/
│   │   │   ├── README.md
│   │   │   ├── realtime.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── architecture/
│   │   ├── README.md
│   │   ├── system-architecture.md
│   │   └── xenon.js
│   ├── deployment/
│   │   ├── local-development.md
│   │   ├── README.md
│   │   └── xenon.js
│   ├── development/
│   │   ├── README.md
│   │   ├── setup.md
│   │   └── xenon.js
│   ├── ml/
│   │   ├── model-development.md
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── user-guide/
│   │   ├── getting-started.md
│   │   ├── README.md
│   │   └── xenon.js
│   └── xenon.js
├── frontend/
│   ├── admin-dashboard/
│   │   ├── package.json
│   │   ├── public/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── landing-page/
│   │   ├── assets/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── index.html
│   │   ├── README.md
│   │   ├── script.js
│   │   ├── style.css
│   │   └── xenon.js
│   ├── mobile-app/
│   │   ├── android/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── ios/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── package.json
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── README.md
│   ├── web-app/
│   │   ├── 1.env.local
│   │   ├── 1.eslintrc.js
│   │   ├── 1.gitignore
│   │   ├── 1.prettierrc
│   │   ├── next-env.d.ts
│   │   ├── next.config.js
│   │   ├── package.json
│   │   ├── postcss.config.js
│   │   ├── public/
│   │   │   ├── favicon/
│   │   │   │   ├── apple-touch-icon.png
│   │   │   │   ├── favicon-16x16.png
│   │   │   │   ├── favicon-32x32.png
│   │   │   │   ├── favicon.ico
│   │   │   │   ├── README.md
│   │   │   │   ├── site.webmanifest
│   │   │   │   └── xenon.js
│   │   │   ├── fonts/
│   │   │   │   ├── Inter/
│   │   │   │   │   ├── Inter-Bold.woff2
│   │   │   │   │   ├── Inter-Light.woff2
│   │   │   │   │   ├── Inter-Medium.woff2
│   │   │   │   │   ├── Inter-Regular.woff2
│   │   │   │   │   ├── Inter-SemiBold.woff2
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── Montserrat/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── Roboto/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── images/
│   │   │   │   ├── flags/
│   │   │   │   │   ├── france.svg
│   │   │   │   │   ├── germany.svg
│   │   │   │   │   ├── italy.svg
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── spain.svg
│   │   │   │   │   ├── uk.svg
│   │   │   │   │   ├── usa.svg
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── icons/
│   │   │   │   │   ├── betting/
│   │   │   │   │   │   ├── bet-placed.svg
│   │   │   │   │   │   ├── bet-won.svg
│   │   │   │   │   │   ├── cashout.svg
│   │   │   │   │   │   ├── draw.svg
│   │   │   │   │   │   ├── lose.svg
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── win.svg
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports/
│   │   │   │   │   │   ├── all-sports.svg
│   │   │   │   │   │   ├── baseball.svg
│   │   │   │   │   │   ├── basketball.svg
│   │   │   │   │   │   ├── esports.svg
│   │   │   │   │   │   ├── football.svg
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── rugby.svg
│   │   │   │   │   │   ├── tennis.svg
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── status/
│   │   │   │   │   │   ├── error.svg
│   │   │   │   │   │   ├── high-confidence.svg
│   │   │   │   │   │   ├── info.svg
│   │   │   │   │   │   ├── low-confidence.svg
│   │   │   │   │   │   ├── medium-confidence.svg
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── success.svg
│   │   │   │   │   │   ├── warning.svg
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── ui/
│   │   │   │   │   │   ├── analytics.svg
│   │   │   │   │   │   ├── bell.svg
│   │   │   │   │   │   ├── betting.svg
│   │   │   │   │   │   ├── download.svg
│   │   │   │   │   │   ├── filter.svg
│   │   │   │   │   │   ├── home.svg
│   │   │   │   │   │   ├── predictions.svg
│   │   │   │   │   │   ├── profile.svg
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── refresh.svg
│   │   │   │   │   │   ├── search.svg
│   │   │   │   │   │   ├── settings.svg
│   │   │   │   │   │   ├── sort.svg
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── logos/
│   │   │   │   │   ├── goat-prediction-dark.svg
│   │   │   │   │   ├── goat-prediction-icon.png
│   │   │   │   │   ├── goat-prediction-light.svg
│   │   │   │   │   ├── goat-prediction-logo.svg
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── sports/
│   │   │   │   │   ├── basketball-court.jpg
│   │   │   │   │   ├── esports-arena.jpg
│   │   │   │   │   ├── football-field.jpg
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── stadium.jpg
│   │   │   │   │   ├── tennis-court.jpg
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── robots.txt
│   │   │   ├── sitemap.xml
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── (dashboard)/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── (marketing)/
│   │   │   │   │   ├── components/
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── account/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── admin/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── api/
│   │   │   │   │   ├── [...nextauth]/
│   │   │   │   │   │   └── authxenon.js
│   │   │   │   │   ├── auth/
│   │   │   │   │   │   ├── [...nextauth]/
│   │   │   │   │   │   │   └── README.md
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── route.ts
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── webhooks/
│   │   │   │   │   │   ├── predictions/
│   │   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   │   ├── route.ts
│   │   │   │   │   │   │   └── xenon.js
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   ├── stripe/
│   │   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   │   ├── route.ts
│   │   │   │   │   │   │   └── xenon.js
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── auth/
│   │   │   │   │   ├── forgot-password/
│   │   │   │   │   │   ├── layout.tsx
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── login/
│   │   │   │   │   │   ├── layout.tsx
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── register/
│   │   │   │   │   │   ├── layout.tsx
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── betting/
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── error.tsx
│   │   │   │   ├── globals.css
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── loading.tsx
│   │   │   │   ├── not-found.tsx
│   │   │   │   ├── page.tsx
│   │   │   │   ├── predictions/
│   │   │   │   │   ├── [sport]/
│   │   │   │   │   │   ├── loading.tsx
│   │   │   │   │   │   ├── page.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── layout.tsx
│   │   │   │   │   ├── loading.tsx
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── components/
│   │   │   │   ├── admin/
│   │   │   │   │   ├── admin-dashboard.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── user-management.tsx
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── charts/
│   │   │   │   │   │   ├── accuracy-chart.tsx
│   │   │   │   │   │   ├── profit-chart.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── betting/
│   │   │   │   │   ├── bet-history.tsx
│   │   │   │   │   ├── bet-slip.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── dashboard/
│   │   │   │   │   ├── live-matches.tsx
│   │   │   │   │   ├── overview.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── forms/
│   │   │   │   │   ├── bet-form.tsx
│   │   │   │   │   ├── filter-form.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── layout/
│   │   │   │   │   ├── footer.tsx
│   │   │   │   │   ├── header.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sidebar.tsx
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── notifications/
│   │   │   │   │   ├── notification-bell.tsx
│   │   │   │   │   ├── notification-list.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── predictions/
│   │   │   │   │   ├── bet-slip.tsx
│   │   │   │   │   ├── prediction-card.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── sports/
│   │   │   │   │   ├── basketball/
│   │   │   │   │   │   ├── match-card.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── esports/
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── football/
│   │   │   │   │   │   ├── match-card.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── tennis/
│   │   │   │   │   │   ├── match-card.tsx
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── ui/
│   │   │   │   │   ├── button.tsx
│   │   │   │   │   ├── card.tsx
│   │   │   │   │   ├── modal.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── table.tsx
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── config/
│   │   │   │   ├── api-config.ts
│   │   │   │   ├── README.md
│   │   │   │   ├── site.ts
│   │   │   │   ├── theme-config.ts
│   │   │   │   └── xenon.js
│   │   │   ├── contexts/
│   │   │   │   ├── auth-context.tsx
│   │   │   │   ├── README.md
│   │   │   │   ├── theme-context.tsx
│   │   │   │   └── xenon.js
│   │   │   ├── hooks/
│   │   │   │   ├── README.md
│   │   │   │   ├── use-analytics.ts
│   │   │   │   ├── use-auth.ts
│   │   │   │   ├── use-predictions.ts
│   │   │   │   ├── use-websocket.ts
│   │   │   │   └── xenon.js
│   │   │   ├── i18n/
│   │   │   │   ├── i18n-config.ts
│   │   │   │   ├── locales/
│   │   │   │   │   ├── en/
│   │   │   │   │   │   ├── common.json
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── fr/
│   │   │   │   │   │   ├── common.json
│   │   │   │   │   │   ├── README.md
│   │   │   │   │   │   └── xenon.js
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── lib/
│   │   │   │   ├── api/
│   │   │   │   │   ├── client.ts
│   │   │   │   │   ├── endpoints.ts
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── constants/
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── sports.ts
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── README.md
│   │   │   │   ├── services/
│   │   │   │   │   ├── auth-service.ts
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── types/
│   │   │   │   │   ├── predictions.ts
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── utils/
│   │   │   │   │   ├── calculations.ts
│   │   │   │   │   ├── formatters.ts
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   ├── middleware/
│   │   │   │   ├── auth-middleware.ts
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── pages/
│   │   │   │   ├── about.tsx
│   │   │   │   ├── blog/
│   │   │   │   │   ├── [slug].tsx
│   │   │   │   │   ├── index.tsx
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── contact.tsx
│   │   │   │   ├── index.tsx
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── store/
│   │   │   │   ├── betting-store.ts
│   │   │   │   ├── predictions-store.ts
│   │   │   │   ├── README.md
│   │   │   │   ├── user-store.ts
│   │   │   │   └── xenon.js
│   │   │   ├── styles/
│   │   │   │   ├── animations/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── components/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── globals.css
│   │   │   │   ├── README.md
│   │   │   │   ├── themes/
│   │   │   │   │   ├── dark.ts
│   │   │   │   │   ├── light.ts
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── utilities/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── tailwind.config.js
│   │   ├── tsconfig.json
│   │   └── xenon.js
│   └── xenon.js
├── infrastructure/
│   ├── kubernetes/
│   │   ├── configmaps/
│   │   │   ├── app-config.yaml
│   │   │   ├── ml-config.yaml
│   │   │   ├── README.md
│   │   │   ├── sports-config.yaml
│   │   │   └── xenon.js
│   │   ├── deployments/
│   │   │   ├── api-gateway.yaml
│   │   │   ├── data-collector.yaml
│   │   │   ├── frontend.yaml
│   │   │   ├── ml-models.yaml
│   │   │   ├── prediction-engine.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── helm-charts/
│   │   │   ├── ml-pipeline/
│   │   │   │   ├── Chart.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── templates/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── values.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── monitoring-stack/
│   │   │   │   ├── Chart.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── templates/
│   │   │   │   │   ├── README.md
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── values.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── prediction-engine/
│   │   │   │   ├── Chart.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── requirements.yaml
│   │   │   │   ├── templates/
│   │   │   │   │   ├── configmap.yaml
│   │   │   │   │   ├── deployment.yaml
│   │   │   │   │   ├── hpa.yaml
│   │   │   │   │   ├── README.md
│   │   │   │   │   ├── service.yaml
│   │   │   │   │   └── xenon.js
│   │   │   │   ├── values.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── ingress/
│   │   │   ├── admin-ingress.yaml
│   │   │   ├── api-ingress.yaml
│   │   │   ├── main-ingress.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── namespaces/
│   │   │   ├── goat-prediction.yaml
│   │   │   ├── ml-pipeline.yaml
│   │   │   ├── monitoring.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── secrets/
│   │   │   ├── api-keys.yaml
│   │   │   ├── database.yaml
│   │   │   ├── README.md
│   │   │   ├── supabase.yaml
│   │   │   └── xenon.js
│   │   ├── services/
│   │   │   ├── api-gateway-svc.yaml
│   │   │   ├── frontend-svc.yaml
│   │   │   ├── ml-models-svc.yaml
│   │   │   ├── prediction-engine-svc.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── monitoring/
│   │   ├── alertmanager/
│   │   │   ├── alertmanager.yml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── dashboards/
│   │   │   ├── financial-metrics.json
│   │   │   ├── model-accuracy.json
│   │   │   ├── prediction-performance.json
│   │   │   ├── README.md
│   │   │   ├── system-health.json
│   │   │   └── xenon.js
│   │   ├── grafana/
│   │   │   ├── dashboards/
│   │   │   │   ├── financial-metrics.json
│   │   │   │   ├── model-accuracy.json
│   │   │   │   ├── prediction-performance.json
│   │   │   │   ├── README.md
│   │   │   │   ├── real-time-monitoring.json
│   │   │   │   ├── system-health.json
│   │   │   │   └── xenon.js
│   │   │   ├── datasources/
│   │   │   │   ├── postgres.yaml
│   │   │   │   ├── prometheus.yaml
│   │   │   │   ├── README.md
│   │   │   │   ├── redis.yaml
│   │   │   │   └── xenon.js
│   │   │   ├── provisioning/
│   │   │   │   ├── dashboards.yaml
│   │   │   │   ├── datasources.yaml
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── loki/
│   │   │   ├── loki-config.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── prometheus/
│   │   │   ├── alerts/
│   │   │   │   ├── business-alerts.yml
│   │   │   │   ├── prediction-alerts.yml
│   │   │   │   ├── README.md
│   │   │   │   ├── system-alerts.yml
│   │   │   │   └── xenon.js
│   │   │   ├── prometheus.yml
│   │   │   ├── README.md
│   │   │   ├── rules/
│   │   │   │   ├── alerting-rules.yml
│   │   │   │   ├── README.md
│   │   │   │   ├── recording-rules.yml
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── modules/
│   │   │   ├── compute/
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   ├── README.md
│   │   │   │   ├── variables.tf
│   │   │   │   └── xenon.js
│   │   │   ├── database/
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   ├── README.md
│   │   │   │   ├── variables.tf
│   │   │   │   └── xenon.js
│   │   │   ├── ml-infra/
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   ├── README.md
│   │   │   │   ├── variables.tf
│   │   │   │   └── xenon.js
│   │   │   ├── monitoring/
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   ├── README.md
│   │   │   │   ├── variables.tf
│   │   │   │   └── xenon.js
│   │   │   ├── networking/
│   │   │   │   ├── main.tf
│   │   │   │   ├── outputs.tf
│   │   │   │   ├── README.md
│   │   │   │   ├── variables.tf
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── outputs.tf
│   │   ├── providers.tf
│   │   ├── README.md
│   │   ├── variables.tf
│   │   └── xenon.js
│   └── xenon.js
├── LICENSE
├── Makefile
├── mlops/
│   ├── experiment-tracking/
│   │   ├── comet/
│   │   │   ├── config.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── neptune/
│   │   │   ├── config.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── wandb/
│   │   │   ├── config.yaml
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── feature-store/
│   │   ├── feast/
│   │   │   ├── entities/
│   │   │   │   ├── README.md
│   │   │   │   ├── teams.py
│   │   │   │   └── xenon.js
│   │   │   ├── feature_repos/
│   │   │   │   ├── football_features.py
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── feature_store.yaml
│   │   │   ├── feature_views/
│   │   │   │   ├── README.md
│   │   │   │   ├── team_features.py
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── hopsworks/
│   │   │   ├── feature_groups/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── models/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   ├── training_datasets/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── model-registry/
│   │   ├── kubeflow/
│   │   │   ├── components/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── experiments/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── pipelines/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── mlflow/
│   │   │   ├── artifacts/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── experiments/
│   │   │   │   ├── football.json
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── mlflow-config.yaml
│   │   │   ├── models/
│   │   │   │   ├── football/
│   │   │   │   │   └── model.yaml
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── serving/
│   │   ├── README.md
│   │   ├── seldon/
│   │   │   ├── README.md
│   │   │   ├── seldon-deployment.yaml
│   │   │   └── xenon.js
│   │   ├── tensorflow-serving/
│   │   │   ├── models.config
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── torchserve/
│   │   │   ├── config.properties
│   │   │   ├── model-store/
│   │   │   │   ├── README.md
│   │   │   │   └── xenon.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   └── xenon.js
├── next.config.js
├── package.json
├── postcss.config.js
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── ROADMAP.md
├── scripts/
│   ├── data/
│   │   ├── collect-data.sh
│   │   ├── README.md
│   │   └── xenon.js
│   ├── deployment/
│   │   ├── deploy.sh
│   │   ├── README.md
│   │   └── xenon.js
│   ├── maintenance/
│   │   ├── backup.sh
│   │   ├── README.md
│   │   └── xenon.js
│   ├── monitoring/
│   │   ├── check-performance.sh
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── utils/
│   │   ├── README.md
│   │   ├── setup-environment.sh
│   │   └── xenon.js
│   └── xenon.js
├── SECURITY.md
├── tailwind.config.js
├── tests/
│   ├── e2e/
│   │   ├── api/
│   │   │   ├── predictions.test.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── mobile/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── performance/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── web/
│   │   │   ├── homepage.test.js
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── integration/
│   │   ├── api-integration.test.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── load/
│   │   ├── api-load.test.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── penetration/
│   │   ├── README.md
│   │   └── xenon.js
│   ├── performance/
│   │   ├── api-performance.test.js
│   │   ├── README.md
│   │   └── xenon.js
│   ├── README.md
│   ├── security/
│   │   ├── audit/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── compliance/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── penetration/
│   │   │   ├── api-pentest.py
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   ├── README.md
│   │   ├── vulnerability/
│   │   │   ├── README.md
│   │   │   └── xenon.js
│   │   └── xenon.js
│   ├── test-setup.js
│   ├── unit/
│   │   ├── backend-unit.test.js
│   │   ├── README.md
│   │   └── xenon.js
│   └── xenon.js
└── tsconfig.json
