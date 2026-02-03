"""
GOAT PREDICTION ULTIMATE - Sports Schemas
Schémas pour les données sportives
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import uuid


# ============================================
# ENUMS
# ============================================

class SportType(str, Enum):
    """Types de sports"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    AMERICAN_FOOTBALL = "american_football"
    CRICKET = "cricket"
    VOLLEYBALL = "volleyball"


class MatchStatus(str, Enum):
    """Statuts de match"""
    SCHEDULED = "scheduled"
    LIVE = "live"
    HALFTIME = "halftime"
    FINISHED = "finished"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    INTERRUPTED = "interrupted"
    ABANDONED = "abandoned"


class CompetitionLevel(str, Enum):
    """Niveaux de compétition"""
    INTERNATIONAL = "international"
    NATIONAL = "national"
    REGIONAL = "regional"
    LOCAL = "local"
    FRIENDLY = "friendly"


class VenueType(str, Enum):
    """Types de lieux"""
    STADIUM = "stadium"
    ARENA = "arena"
    COURT = "court"
    FIELD = "field"
    TRACK = "track"
    ONLINE = "online"  # Pour esports


# ============================================
# SPORT SCHEMAS
# ============================================

class Sport(BaseModel):
    """Sport disponible"""
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=10)
    
    icon: Optional[str] = None
    description: Optional[str] = None
    
    # Marchés disponibles
    available_markets: List[str] = Field(default_factory=list)
    
    # Ligues couvertes
    leagues: List[str] = Field(default_factory=list)
    league_count: int = 0
    
    # Métadonnées
    is_active: bool = True
    popularity_rank: Optional[int] = None
    
    # Stats
    total_matches: int = 0
    total_predictions: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "id": "football",
                "name": "Football",
                "code": "FB",
                "icon": "⚽",
                "description": "Association Football / Soccer",
                "available_markets": [
                    "match_winner",
                    "over_under",
                    "both_teams_to_score"
                ],
                "leagues": ["Premier League", "La Liga", "Serie A"],
                "league_count": 50,
                "is_active": True,
                "popularity_rank": 1,
                "total_matches": 15000,
                "total_predictions": 50000
            }
        }


class SportList(BaseModel):
    """Liste de sports"""
    sports: List[Sport]
    total: int = Field(..., ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "sports": [],
                "total": 7
            }
        }


# ============================================
# LEAGUE/COMPETITION SCHEMAS
# ============================================

class League(BaseModel):
    """Ligue/Compétition sportive"""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    short_name: Optional[str] = None
    
    sport: SportType
    country: str = Field(..., min_length=2, max_length=100)
    country_code: Optional[str] = Field(None, min_length=2, max_length=3)
    
    logo: Optional[str] = None
    banner: Optional[str] = None
    
    level: CompetitionLevel = CompetitionLevel.NATIONAL
    
    # Métadonnées
    is_active: bool = True
    is_international: bool = False
    
    # Saison
    current_season: Optional[str] = None
    season_start: Optional[date] = None
    season_end: Optional[date] = None
    
    # Stats
    total_teams: int = 0
    total_matches: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "id": "premier_league",
                "name": "Premier League",
                "short_name": "EPL",
                "sport": "football",
                "country": "England",
                "country_code": "ENG",
                "logo": "https://example.com/leagues/epl.png",
                "level": "national",
                "is_active": True,
                "is_international": False,
                "current_season": "2025-2026",
                "total_teams": 20,
                "total_matches": 380
            }
        }


class LeagueStandings(BaseModel):
    """Classement de ligue"""
    league: League
    season: str
    
    standings: List[Dict[str, Any]] = Field(default_factory=list)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "league": {},
                "season": "2025-2026",
                "standings": [
                    {
                        "position": 1,
                        "team": "Arsenal",
                        "played": 25,
                        "won": 18,
                        "drawn": 4,
                        "lost": 3,
                        "goals_for": 55,
                        "goals_against": 20,
                        "goal_difference": 35,
                        "points": 58
                    }
                ],
                "last_updated": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# TEAM SCHEMAS
# ============================================

class Team(BaseModel):
    """Équipe sportive"""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    short_name: str = Field(..., min_length=1, max_length=50)
    
    sport: SportType
    league: str
    
    logo: Optional[str] = None
    banner: Optional[str] = None
    colors: Optional[Dict[str, str]] = None
    
    country: str
    city: Optional[str] = None
    
    venue: Optional[str] = None
    founded: Optional[int] = Field(None, ge=1800, le=2030)
    
    # Stats
    ranking: Optional[int] = None
    form: Optional[List[str]] = Field(None, max_items=10)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "arsenal",
                "name": "Arsenal FC",
                "short_name": "ARS",
                "sport": "football",
                "league": "premier_league",
                "logo": "https://example.com/teams/arsenal.png",
                "colors": {
                    "primary": "#EF0107",
                    "secondary": "#FFFFFF"
                },
                "country": "England",
                "city": "London",
                "venue": "Emirates Stadium",
                "founded": 1886,
                "ranking": 3,
                "form": ["W", "W", "D", "W", "L"]
            }
        }


class TeamStats(BaseModel):
    """Statistiques d'équipe"""
    team_id: str
    season: str
    
    # Matchs
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    
    # Buts (Football)
    goals_scored: Optional[int] = None
    goals_conceded: Optional[int] = None
    goal_difference: Optional[int] = None
    
    # Points (Basketball)
    points_scored: Optional[float] = None
    points_conceded: Optional[float] = None
    
    # Performance
    win_percentage: float = Field(0.0, ge=0.0, le=100.0)
    home_record: Optional[str] = None
    away_record: Optional[str] = None
    
    # Forme récente
    recent_form: List[str] = Field(default_factory=list, max_items=10)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "team_id": "arsenal",
                "season": "2025-2026",
                "matches_played": 25,
                "wins": 18,
                "draws": 4,
                "losses": 3,
                "goals_scored": 55,
                "goals_conceded": 20,
                "goal_difference": 35,
                "win_percentage": 72.0,
                "home_record": "10-2-1",
                "away_record": "8-2-2",
                "recent_form": ["W", "W", "D", "W", "L"],
                "last_updated": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# PLAYER SCHEMAS
# ============================================

class Player(BaseModel):
    """Joueur"""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    short_name: Optional[str] = None
    
    team_id: str
    sport: SportType
    
    photo: Optional[str] = None
    
    # Informations personnelles
    nationality: str
    date_of_birth: Optional[date] = None
    age: Optional[int] = Field(None, ge=15, le=50)
    
    # Position
    position: str
    jersey_number: Optional[int] = Field(None, ge=1, le=99)
    
    # Stats
    market_value: Optional[float] = None
    rating: Optional[float] = Field(None, ge=0.0, le=100.0)
    
    # État
    is_injured: bool = False
    is_suspended: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "id": "player_123",
                "name": "Bukayo Saka",
                "short_name": "B. Saka",
                "team_id": "arsenal",
                "sport": "football",
                "nationality": "England",
                "date_of_birth": "2001-09-05",
                "age": 24,
                "position": "Right Winger",
                "jersey_number": 7,
                "market_value": 120000000.0,
                "rating": 87.5,
                "is_injured": False,
                "is_suspended": False
            }
        }


class Injury(BaseModel):
    """Blessure"""
    player_id: str
    player_name: str
    
    injury_type: str
    severity: str = Field(..., regex="^(minor|moderate|severe|unknown)$")
    
    injury_date: date
    expected_return: Optional[date] = None
    days_out: Optional[int] = None
    
    status: str = Field(..., regex="^(injured|recovering|fit|doubtful)$")
    
    class Config:
        schema_extra = {
            "example": {
                "player_id": "player_456",
                "player_name": "Gabriel Jesus",
                "injury_type": "Knee injury",
                "severity": "moderate",
                "injury_date": "2026-01-20",
                "expected_return": "2026-02-15",
                "days_out": 26,
                "status": "recovering"
            }
        }


# ============================================
# MATCH SCHEMAS
# ============================================

class Venue(BaseModel):
    """Lieu de match"""
    id: Optional[str] = None
    name: str
    city: str
    country: str
    
    capacity: Optional[int] = Field(None, ge=0)
    type: VenueType = VenueType.STADIUM
    
    surface: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "emirates_stadium",
                "name": "Emirates Stadium",
                "city": "London",
                "country": "England",
                "capacity": 60704,
                "type": "stadium",
                "surface": "Grass"
            }
        }


class Weather(BaseModel):
    """Conditions météo"""
    temperature: float = Field(..., description="Température en °C")
    feels_like: Optional[float] = None
    
    condition: str
    description: Optional[str] = None
    
    wind_speed: Optional[float] = Field(None, ge=0, description="Vitesse du vent en km/h")
    humidity: Optional[int] = Field(None, ge=0, le=100, description="Humidité en %")
    precipitation: Optional[float] = Field(None, ge=0, description="Précipitations en mm")
    
    class Config:
        schema_extra = {
            "example": {
                "temperature": 15.5,
                "feels_like": 13.2,
                "condition": "Partly Cloudy",
                "description": "Partly cloudy with light winds",
                "wind_speed": 12.5,
                "humidity": 65,
                "precipitation": 0.0
            }
        }


class MatchScore(BaseModel):
    """Score de match"""
    home: int = Field(..., ge=0)
    away: int = Field(..., ge=0)
    
    # Scores par période
    halftime: Optional[Dict[str, int]] = None
    fulltime: Optional[Dict[str, int]] = None
    
    # Tennis
    sets: Optional[List[Dict[str, int]]] = None
    
    # Basketball
    quarters: Optional[List[Dict[str, int]]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "home": 2,
                "away": 1,
                "halftime": {"home": 1, "away": 0},
                "fulltime": {"home": 2, "away": 1}
            }
        }


class Match(BaseModel):
    """Match sportif"""
    id: str = Field(..., min_length=1, max_length=100)
    
    sport: SportType
    league: str
    
    home_team: str
    away_team: str
    
    home_team_id: str
    away_team_id: str
    
    # Date et heure
    match_date: datetime
    timezone: str = "UTC"
    
    # Lieu
    venue: Optional[Venue] = None
    
    # Statut
    status: MatchStatus = MatchStatus.SCHEDULED
    
    # Score
    score: Optional[MatchScore] = None
    
    # Temps de jeu (pour matchs live)
    minute: Optional[int] = None
    period: Optional[str] = None
    
    # Saison
    season: Optional[str] = None
    round: Optional[Union[int, str]] = None
    
    # Cotes
    odds: Optional[Dict[str, float]] = None
    
    # Arbitre
    referee: Optional[str] = None
    
    # Météo
    weather: Optional[Weather] = None
    
    # Métadonnées
    is_important: bool = False
    attendance: Optional[int] = None
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "match_12345",
                "sport": "football",
                "league": "premier_league",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_team_id": "arsenal",
                "away_team_id": "chelsea",
                "match_date": "2026-02-15T15:00:00Z",
                "venue": {
                    "name": "Emirates Stadium",
                    "city": "London",
                    "country": "England"
                },
                "status": "scheduled",
                "season": "2025-2026",
                "round": 25,
                "odds": {
                    "home": 2.10,
                    "draw": 3.40,
                    "away": 3.50
                },
                "is_important": True
            }
        }


class MatchDetail(Match):
    """Détails complets d'un match"""
    # Équipes détaillées
    home_team_info: Optional[Team] = None
    away_team_info: Optional[Team] = None
    
    # Stats des équipes
    home_team_stats: Optional[TeamStats] = None
    away_team_stats: Optional[TeamStats] = None
    
    # Head to head
    h2h_record: Optional[Dict[str, Any]] = None
    h2h_matches: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Forme récente
    home_team_form: List[str] = Field(default_factory=list)
    away_team_form: List[str] = Field(default_factory=list)
    
    # Absences
    home_team_injuries: List[Injury] = Field(default_factory=list)
    away_team_injuries: List[Injury] = Field(default_factory=list)
    home_team_suspensions: List[str] = Field(default_factory=list)
    away_team_suspensions: List[str] = Field(default_factory=list)
    
    # Compositions (si disponibles)
    home_team_lineup: Optional[List[Player]] = None
    away_team_lineup: Optional[List[Player]] = None
    
    # Statistiques de match (si live/terminé)
    match_statistics: Optional[Dict[str, Any]] = None
    
    # Événements (buts, cartons, etc.)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        orm_mode = True


class MatchList(BaseModel):
    """Liste de matchs"""
    matches: List[Match]
    total: int = Field(..., ge=0)
    
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "matches": [],
                "total": 50,
                "filters": {
                    "sport": "football",
                    "league": "premier_league",
                    "date": "2026-02-15"
                }
            }
        }


# ============================================
# ODDS SCHEMAS
# ============================================

class Bookmaker(BaseModel):
    """Bookmaker"""
    id: str
    name: str
    logo: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "id": "bet365",
                "name": "Bet365",
                "logo": "https://example.com/bookmakers/bet365.png"
            }
        }


class MarketOdds(BaseModel):
    """Cotes d'un marché"""
    market: str
    bookmaker: Bookmaker
    
    odds: Dict[str, float]
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "market": "match_winner",
                "bookmaker": {
                    "id": "bet365",
                    "name": "Bet365"
                },
                "odds": {
                    "home": 2.10,
                    "draw": 3.40,
                    "away": 3.50
                },
                "last_updated": "2026-02-03T10:00:00Z"
            }
        }


class OddsComparison(BaseModel):
    """Comparaison de cotes"""
    match_id: str
    market: str
    
    bookmakers: List[MarketOdds] = Field(default_factory=list)
    
    best_odds: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    average_odds: Optional[Dict[str, float]] = None
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_12345",
                "market": "match_winner",
                "bookmakers": [],
                "best_odds": {
                    "home": {"bookmaker": "Bet365", "odds": 2.15},
                    "draw": {"bookmaker": "William Hill", "odds": 3.50},
                    "away": {"bookmaker": "Pinnacle", "odds": 3.60}
                },
                "average_odds": {
                    "home": 2.10,
                    "draw": 3.40,
                    "away": 3.50
                },
                "last_updated": "2026-02-03T10:00:00Z"
            }
        }


# ============================================
# SEARCH & FILTER SCHEMAS
# ============================================

class MatchFilter(BaseModel):
    """Filtres de recherche de matchs"""
    sport: Optional[SportType] = None
    league: Optional[str] = None
    team: Optional[str] = None
    
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    status: Optional[MatchStatus] = None
    
    has_odds: Optional[bool] = None
    important_only: Optional[bool] = False
    
    class Config:
        schema_extra = {
            "example": {
                "sport": "football",
                "league": "premier_league",
                "date_from": "2026-02-03T00:00:00Z",
                "date_to": "2026-02-10T23:59:59Z",
                "status": "scheduled",
                "important_only": True
            }
        }
