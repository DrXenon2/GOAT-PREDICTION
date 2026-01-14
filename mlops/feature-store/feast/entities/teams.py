# mlops/feature-store/feast/entities/teams.py

"""
Team Entities for Goat Prediction Ultimate
Complete entity definitions for all sports teams with advanced metadata and relationships
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid

from feast import Entity, ValueType, FeatureView, FeatureService
from feast.types import (
    Float32,
    Float64,
    Int32,
    Int64,
    String,
    Bool,
    UnixTimestamp,
    Array,
    Bytes
)
from feast.field import Field

# ============================================================================
# ENUM DEFINITIONS
# ============================================================================

class SportType(str, Enum):
    """Sport type enumeration"""
    FOOTBALL = "football"
    BASKETBALL = "basketball"
    TENNIS = "tennis"
    ESPORTS = "esports"
    BASEBALL = "baseball"
    RUGBY = "rugby"
    HOCKEY = "hockey"
    CRICKET = "cricket"
    AMERICAN_FOOTBALL = "american_football"
    VOLLEYBALL = "volleyball"
    HANDBALL = "handball"
    F1 = "formula_1"
    GOLF = "golf"
    BOXING = "boxing"
    MMA = "mma"
    OTHER = "other"

class TeamType(str, Enum):
    """Team type enumeration"""
    CLUB = "club"
    NATIONAL = "national"
    ACADEMY = "academy"
    RESERVE = "reserve"
    YOUTH = "youth"
    ESPORTS = "esports"
    FRANCHISE = "franchise"
    ALL_STAR = "all_star"
    TOURNAMENT = "tournament"
    OTHER = "other"

class CompetitionLevel(str, Enum):
    """Competition level enumeration"""
    INTERNATIONAL = "international"
    CONTINENTAL = "continental"
    DOMESTIC_TOP = "domestic_top"
    DOMESTIC_SECOND = "domestic_second"
    DOMESTIC_THIRD = "domestic_third"
    DOMESTIC_LOWER = "domestic_lower"
    REGIONAL = "regional"
    LOCAL = "local"
    AMATEUR = "amateur"
    YOUTH = "youth"
    ACADEMY = "academy"

class OwnershipType(str, Enum):
    """Team ownership type enumeration"""
    PRIVATE = "private"
    PUBLIC = "public"
    MEMBER_OWNED = "member_owned"
    GOVERNMENT = "government"
    UNIVERSITY = "university"
    CORPORATE = "corporate"
    COMMUNITY = "community"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"

class StadiumType(str, Enum):
    """Stadium type enumeration"""
    OPEN_AIR = "open_air"
    DOME = "dome"
    RETRACTABLE_ROOF = "retractable_roof"
    INDOOR = "indoor"
    MULTI_PURPOSE = "multi_purpose"
    TEMPORARY = "temporary"
    TRAINING = "training"
    HISTORIC = "historic"
    MODERN = "modern"

# ============================================================================
# DATACLASSES FOR ENTITY METADATA
# ============================================================================

@dataclass
class TeamMetadata:
    """Comprehensive team metadata"""
    team_id: str
    canonical_name: str
    short_name: str
    abbreviation: str
    display_name: str
    aliases: List[str] = field(default_factory=list)
    founded_year: Optional[int] = None
    dissolved_year: Optional[int] = None
    sport_type: SportType = SportType.FOOTBALL
    team_type: TeamType = TeamType.CLUB
    competition_level: CompetitionLevel = CompetitionLevel.DOMESTIC_TOP
    
    # Location information
    country: str = ""
    country_code: str = ""
    region: str = ""
    city: str = ""
    postal_code: str = ""
    timezone: str = "UTC"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_m: Optional[float] = None
    
    # Stadium information
    stadium_name: str = ""
    stadium_type: StadiumType = StadiumType.OPEN_AIR
    stadium_capacity: Optional[int] = None
    stadium_built_year: Optional[int] = None
    stadium_pitch_type: str = "grass"
    stadium_roof_type: str = "open"
    stadium_lighting_type: str = "floodlights"
    
    # Organizational information
    club_colors: List[str] = field(default_factory=list)
    nicknames: List[str] = field(default_factory=list)
    motto: str = ""
    website: str = ""
    social_media: Dict[str, str] = field(default_factory=dict)
    
    # Financial information
    ownership_type: OwnershipType = OwnershipType.PRIVATE
    owner_name: str = ""
    ceo_name: str = ""
    annual_revenue_usd: Optional[float] = None
    market_value_usd: Optional[float] = None
    debt_usd: Optional[float] = None
    
    # Sporting information
    league_id: str = ""
    league_name: str = ""
    division: str = ""
    current_position: Optional[int] = None
    total_titles: int = 0
    domestic_titles: int = 0
    international_titles: int = 0
    historical_performance_rating: float = 0.0
    
    # Team characteristics
    playing_style: str = ""
    formation_preference: str = ""
    attack_rating: float = 0.0
    defense_rating: float = 0.0
    midfield_rating: float = 0.0
    
    # Squad information
    squad_size: int = 0
    avg_player_age: float = 0.0
    avg_player_value_usd: float = 0.0
    total_squad_value_usd: float = 0.0
    foreign_players_percentage: float = 0.0
    
    # Temporal information
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    valid_from: datetime = field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None
    
    # Quality metrics
    data_quality_score: float = 1.0
    completeness_score: float = 1.0
    freshness_days: int = 0
    source_count: int = 1
    
    # Tags and categorization
    tags: Set[str] = field(default_factory=set)
    categories: List[str] = field(default_factory=list)
    rivals: List[str] = field(default_factory=list)
    affiliate_teams: List[str] = field(default_factory=list)
    
    # System fields
    version: str = "1.0.0"
    source_system: str = "master_data"
    is_active: bool = True
    is_verified: bool = False
    needs_review: bool = False
    review_notes: str = ""
    
    def to_dict(self) -> Dict:
        """Convert metadata to dictionary"""
        return {
            "team_id": self.team_id,
            "canonical_name": self.canonical_name,
            "short_name": self.short_name,
            "abbreviation": self.abbreviation,
            "display_name": self.display_name,
            "aliases": self.aliases,
            "founded_year": self.founded_year,
            "dissolved_year": self.dissolved_year,
            "sport_type": self.sport_type.value,
            "team_type": self.team_type.value,
            "competition_level": self.competition_level.value,
            "country": self.country,
            "country_code": self.country_code,
            "region": self.region,
            "city": self.city,
            "postal_code": self.postal_code,
            "timezone": self.timezone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "elevation_m": self.elevation_m,
            "stadium_name": self.stadium_name,
            "stadium_type": self.stadium_type.value,
            "stadium_capacity": self.stadium_capacity,
            "stadium_built_year": self.stadium_built_year,
            "stadium_pitch_type": self.stadium_pitch_type,
            "stadium_roof_type": self.stadium_roof_type,
            "stadium_lighting_type": self.stadium_lighting_type,
            "club_colors": self.club_colors,
            "nicknames": self.nicknames,
            "motto": self.motto,
            "website": self.website,
            "social_media": self.social_media,
            "ownership_type": self.ownership_type.value,
            "owner_name": self.owner_name,
            "ceo_name": self.ceo_name,
            "annual_revenue_usd": self.annual_revenue_usd,
            "market_value_usd": self.market_value_usd,
            "debt_usd": self.debt_usd,
            "league_id": self.league_id,
            "league_name": self.league_name,
            "division": self.division,
            "current_position": self.current_position,
            "total_titles": self.total_titles,
            "domestic_titles": self.domestic_titles,
            "international_titles": self.international_titles,
            "historical_performance_rating": self.historical_performance_rating,
            "playing_style": self.playing_style,
            "formation_preference": self.formation_preference,
            "attack_rating": self.attack_rating,
            "defense_rating": self.defense_rating,
            "midfield_rating": self.midfield_rating,
            "squad_size": self.squad_size,
            "avg_player_age": self.avg_player_age,
            "avg_player_value_usd": self.avg_player_value_usd,
            "total_squad_value_usd": self.total_squad_value_usd,
            "foreign_players_percentage": self.foreign_players_percentage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "data_quality_score": self.data_quality_score,
            "completeness_score": self.completeness_score,
            "freshness_days": self.freshness_days,
            "source_count": self.source_count,
            "tags": list(self.tags),
            "categories": self.categories,
            "rivals": self.rivals,
            "affiliate_teams": self.affiliate_teams,
            "version": self.version,
            "source_system": self.source_system,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "needs_review": self.needs_review,
            "review_notes": self.review_notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TeamMetadata':
        """Create TeamMetadata from dictionary"""
        metadata = cls(
            team_id=data["team_id"],
            canonical_name=data["canonical_name"],
            short_name=data["short_name"],
            abbreviation=data["abbreviation"],
            display_name=data["display_name"],
            aliases=data.get("aliases", []),
            founded_year=data.get("founded_year"),
            dissolved_year=data.get("dissolved_year"),
            sport_type=SportType(data.get("sport_type", "football")),
            team_type=TeamType(data.get("team_type", "club")),
            competition_level=CompetitionLevel(data.get("competition_level", "domestic_top")),
            country=data.get("country", ""),
            country_code=data.get("country_code", ""),
            region=data.get("region", ""),
            city=data.get("city", ""),
            postal_code=data.get("postal_code", ""),
            timezone=data.get("timezone", "UTC"),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            elevation_m=data.get("elevation_m"),
            stadium_name=data.get("stadium_name", ""),
            stadium_type=StadiumType(data.get("stadium_type", "open_air")),
            stadium_capacity=data.get("stadium_capacity"),
            stadium_built_year=data.get("stadium_built_year"),
            stadium_pitch_type=data.get("stadium_pitch_type", "grass"),
            stadium_roof_type=data.get("stadium_roof_type", "open"),
            stadium_lighting_type=data.get("stadium_lighting_type", "floodlights"),
            club_colors=data.get("club_colors", []),
            nicknames=data.get("nicknames", []),
            motto=data.get("motto", ""),
            website=data.get("website", ""),
            social_media=data.get("social_media", {}),
            ownership_type=OwnershipType(data.get("ownership_type", "private")),
            owner_name=data.get("owner_name", ""),
            ceo_name=data.get("ceo_name", ""),
            annual_revenue_usd=data.get("annual_revenue_usd"),
            market_value_usd=data.get("market_value_usd"),
            debt_usd=data.get("debt_usd"),
            league_id=data.get("league_id", ""),
            league_name=data.get("league_name", ""),
            division=data.get("division", ""),
            current_position=data.get("current_position"),
            total_titles=data.get("total_titles", 0),
            domestic_titles=data.get("domestic_titles", 0),
            international_titles=data.get("international_titles", 0),
            historical_performance_rating=data.get("historical_performance_rating", 0.0),
            playing_style=data.get("playing_style", ""),
            formation_preference=data.get("formation_preference", ""),
            attack_rating=data.get("attack_rating", 0.0),
            defense_rating=data.get("defense_rating", 0.0),
            midfield_rating=data.get("midfield_rating", 0.0),
            squad_size=data.get("squad_size", 0),
            avg_player_age=data.get("avg_player_age", 0.0),
            avg_player_value_usd=data.get("avg_player_value_usd", 0.0),
            total_squad_value_usd=data.get("total_squad_value_usd", 0.0),
            foreign_players_percentage=data.get("foreign_players_percentage", 0.0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            valid_from=datetime.fromisoformat(data["valid_from"]) if data.get("valid_from") else datetime.utcnow(),
            valid_to=datetime.fromisoformat(data["valid_to"]) if data.get("valid_to") else None,
            data_quality_score=data.get("data_quality_score", 1.0),
            completeness_score=data.get("completeness_score", 1.0),
            freshness_days=data.get("freshness_days", 0),
            source_count=data.get("source_count", 1),
            tags=set(data.get("tags", [])),
            categories=data.get("categories", []),
            rivals=data.get("rivals", []),
            affiliate_teams=data.get("affiliate_teams", []),
            version=data.get("version", "1.0.0"),
            source_system=data.get("source_system", "master_data"),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            needs_review=data.get("needs_review", False),
            review_notes=data.get("review_notes", ""),
        )
        return metadata

# ============================================================================
# FEAST ENTITY DEFINITIONS
# ============================================================================

# Primary Team Entity (Main entity for team features)
team_entity = Entity(
    name="team",
    description="Primary team entity for all sports",
    join_keys=["team_id"],
    value_type=ValueType.STRING,
    
    # Entity metadata
    tags={
        "entity_type": "primary",
        "domain": "sports",
        "owner": "data_team",
        "version": "2.0.0",
        "freshness_requirement": "daily",
        "data_quality_tier": "tier_1",
        "pii_level": "low",
        "retention_days": "3650",  # 10 years
        "compliance": ["gdpr", "ccpa"],
    },
    
    # Entity schema (extended metadata fields)
    schema=[
        # Core identification fields
        Field(name="team_id", dtype=String, description="Unique team identifier"),
        Field(name="canonical_name", dtype=String, description="Official team name"),
        Field(name="short_name", dtype=String, description="Short team name"),
        Field(name="abbreviation", dtype=String, description="Team abbreviation (3-4 chars)"),
        Field(name="display_name", dtype=String, description="Display name for UI"),
        
        # Temporal fields
        Field(name="founded_year", dtype=Int32, description="Year team was founded"),
        Field(name="dissolved_year", dtype=Int32, description="Year team was dissolved (if applicable)"),
        Field(name="is_active", dtype=Bool, description="Whether team is currently active"),
        
        # Sport and type fields
        Field(name="sport_type", dtype=String, description="Type of sport (football, basketball, etc.)"),
        Field(name="team_type", dtype=String, description="Type of team (club, national, etc.)"),
        Field(name="competition_level", dtype=String, description="Competition level"),
        
        # Location fields
        Field(name="country", dtype=String, description="Country where team is based"),
        Field(name="country_code", dtype=String, description="ISO country code"),
        Field(name="region", dtype=String, description="Region/state/province"),
        Field(name="city", dtype=String, description="City where team is based"),
        Field(name="latitude", dtype=Float32, description="Geographic latitude"),
        Field(name="longitude", dtype=Float32, description="Geographic longitude"),
        Field(name="timezone", dtype=String, description="Time zone of team location"),
        Field(name="elevation_m", dtype=Float32, description="Elevation in meters"),
        
        # Stadium fields
        Field(name="stadium_name", dtype=String, description="Name of home stadium"),
        Field(name="stadium_type", dtype=String, description="Type of stadium"),
        Field(name="stadium_capacity", dtype=Int32, description="Maximum stadium capacity"),
        Field(name="stadium_built_year", dtype=Int32, description="Year stadium was built"),
        Field(name="stadium_pitch_type", dtype=String, description="Type of playing surface"),
        Field(name="stadium_roof_type", dtype=String, description="Type of stadium roof"),
        
        # Organizational fields
        Field(name="club_colors", dtype=Array(String), description="Team colors"),
        Field(name="nicknames", dtype=Array(String), description="Team nicknames"),
        Field(name="website", dtype=String, description="Official website URL"),
        
        # Financial fields
        Field(name="ownership_type", dtype=String, description="Type of ownership"),
        Field(name="owner_name", dtype=String, description="Name of owner(s)"),
        Field(name="annual_revenue_usd", dtype=Float64, description="Annual revenue in USD"),
        Field(name="market_value_usd", dtype=Float64, description="Estimated market value in USD"),
        
        # League/competition fields
        Field(name="league_id", dtype=String, description="ID of current league"),
        Field(name="league_name", dtype=String, description="Name of current league"),
        Field(name="division", dtype=String, description="Current division"),
        Field(name="current_position", dtype=Int32, description="Current league position"),
        
        # Historical performance fields
        Field(name="total_titles", dtype=Int32, description="Total titles won"),
        Field(name="domestic_titles", dtype=Int32, description="Domestic titles won"),
        Field(name="international_titles", dtype=Int32, description="International titles won"),
        Field(name="historical_performance_rating", dtype=Float32, description="Historical performance rating (0-100)"),
        
        # Team characteristics fields
        Field(name="playing_style", dtype=String, description="Preferred playing style"),
        Field(name="formation_preference", dtype=String, description="Preferred formation"),
        Field(name="attack_rating", dtype=Float32, description="Attack rating (0-100)"),
        Field(name="defense_rating", dtype=Float32, description="Defense rating (0-100)"),
        Field(name="midfield_rating", dtype=Float32, description="Midfield rating (0-100)"),
        
        # Squad information fields
        Field(name="squad_size", dtype=Int32, description="Number of players in squad"),
        Field(name="avg_player_age", dtype=Float32, description="Average player age"),
        Field(name="avg_player_value_usd", dtype=Float64, description="Average player value in USD"),
        Field(name="total_squad_value_usd", dtype=Float64, description="Total squad value in USD"),
        Field(name="foreign_players_percentage", dtype=Float32, description="Percentage of foreign players"),
        
        # System fields
        Field(name="created_at", dtype=UnixTimestamp, description="Timestamp when record was created"),
        Field(name="updated_at", dtype=UnixTimestamp, description="Timestamp when record was last updated"),
        Field(name="valid_from", dtype=UnixTimestamp, description="Timestamp when record became valid"),
        Field(name="valid_to", dtype=UnixTimestamp, description="Timestamp when record expires"),
        Field(name="data_quality_score", dtype=Float32, description="Data quality score (0-1)"),
        Field(name="completeness_score", dtype=Float32, description="Data completeness score (0-1)"),
        Field(name="freshness_days", dtype=Int32, description="Days since last update"),
        Field(name="source_count", dtype=Int32, description="Number of data sources"),
        Field(name="version", dtype=String, description="Entity version"),
        Field(name="source_system", dtype=String, description="Source system identifier"),
        Field(name="is_verified", dtype=Bool, description="Whether data has been verified"),
        Field(name="needs_review", dtype=Bool, description="Whether data needs review"),
    ],
    
    # Entity lineage and relationships
    lineage={
        "upstream_sources": [
            "sports_db.team_master",
            "api_football.teams",
            "transfermarkt.teams",
            "fifa_teams_db"
        ],
        "downstream_consumers": [
            "match_prediction_model",
            "player_performance_model",
            "team_form_analysis",
            "betting_models"
        ],
        "transformation_steps": [
            "data_validation",
            "entity_resolution",
            "quality_scoring",
            "enrichment"
        ]
    },
    
    # Entity constraints
    constraints={
        "unique_constraints": ["team_id"],
        "not_null_constraints": ["team_id", "canonical_name", "sport_type"],
        "foreign_key_constraints": {
            "league_id": "league.league_id"
        },
        "value_constraints": {
            "founded_year": {"min": 1800, "max": 2100},
            "dissolved_year": {"min": 1800, "max": 2100},
            "stadium_capacity": {"min": 0},
            "annual_revenue_usd": {"min": 0},
            "market_value_usd": {"min": 0},
            "current_position": {"min": 1},
            "historical_performance_rating": {"min": 0, "max": 100},
            "attack_rating": {"min": 0, "max": 100},
            "defense_rating": {"min": 0, "max": 100},
            "midfield_rating": {"min": 0, "max": 100},
            "squad_size": {"min": 0, "max": 100},
            "avg_player_age": {"min": 16, "max": 40},
            "avg_player_value_usd": {"min": 0},
            "total_squad_value_usd": {"min": 0},
            "foreign_players_percentage": {"min": 0, "max": 100},
            "data_quality_score": {"min": 0, "max": 1},
            "completeness_score": {"min": 0, "max": 1},
        }
    },
)

# League Entity (for league-level features)
league_entity = Entity(
    name="league",
    description="Sports league entity",
    join_keys=["league_id"],
    value_type=ValueType.STRING,
    tags={
        "entity_type": "reference",
        "domain": "sports",
        "owner": "data_team",
        "version": "1.0.0",
    },
)

# Sport-Specific Team Entities (for specialized features)

# Football Team Entity
football_team_entity = Entity(
    name="football_team",
    description="Football-specific team entity",
    join_keys=["team_id"],
    value_type=ValueType.STRING,
    tags={
        "sport": "football",
        "entity_type": "specialized",
        "version": "1.2.0",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="uefa_coefficient", dtype=Float32, description="UEFA club coefficient"),
        Field(name="fifa_club_world_ranking", dtype=Int32, description="FIFA club world ranking"),
        Field(name="domestic_cup_performance", dtype=Float32, description="Domestic cup performance rating"),
        Field(name="european_cup_performance", dtype=Float32, description="European cup performance rating"),
        Field(name="home_advantage_coefficient", dtype=Float32, description="Home advantage coefficient"),
        Field(name="style_of_play", dtype=String, description="Detailed style of play description"),
        Field(name="pressing_intensity", dtype=Float32, description="Pressing intensity rating (0-100)"),
        Field(name="build_up_speed", dtype=Float32, description="Build-up speed rating (0-100)"),
        Field(name="defensive_line_height", dtype=Float32, description="Defensive line height rating (0-100)"),
    ],
)

# Basketball Team Entity
basketball_team_entity = Entity(
    name="basketball_team",
    description="Basketball-specific team entity",
    join_keys=["team_id"],
    value_type=ValueType.STRING,
    tags={
        "sport": "basketball",
        "entity_type": "specialized",
        "version": "1.0.0",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="nba_championships", dtype=Int32, description="NBA championships won"),
        Field(name="conference_championships", dtype=Int32, description="Conference championships won"),
        Field(name="division_championships", dtype=Int32, description="Division championships won"),
        Field(name="playoff_appearances", dtype=Int32, description="Playoff appearances"),
        Field(name="offensive_rating", dtype=Float32, description="Offensive rating"),
        Field(name="defensive_rating", dtype=Float32, description="Defensive rating"),
        Field(name="net_rating", dtype=Float32, description="Net rating"),
        Field(name="pace", dtype=Float32, description="Pace (possessions per 48 minutes)"),
        Field(name="true_shooting_percentage", dtype=Float32, description="True shooting percentage"),
        Field(name="effective_field_goal_percentage", dtype=Float32, description="Effective field goal percentage"),
    ],
)

# Tennis Team Entity (for Davis Cup, etc.)
tennis_team_entity = Entity(
    name="tennis_team",
    description="Tennis team entity (national teams)",
    join_keys=["team_id"],
    value_type=ValueType.STRING,
    tags={
        "sport": "tennis",
        "entity_type": "specialized",
        "version": "1.0.0",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="davis_cup_titles", dtype=Int32, description="Davis Cup titles"),
        Field(name="fed_cup_titles", dtype=Int32, description="Fed Cup titles"),
        Field(name="atp_cup_titles", dtype=Int32, description="ATP Cup titles"),
        Field(name="billie_jean_king_cup_titles", dtype=Int32, description="Billie Jean King Cup titles"),
        Field(name="current_davis_cup_ranking", dtype=Int32, description="Current Davis Cup ranking"),
        Field(name="top_player_rankings", dtype=Array(Int32), description="Rankings of top players"),
        Field(name="team_surface_preference", dtype=String, description="Preferred surface (hard/clay/grass)"),
        Field(name="team_experience_years", dtype=Float32, description="Average years of team experience"),
    ],
)

# Esports Team Entity
esports_team_entity = Entity(
    name="esports_team",
    description="Esports team entity",
    join_keys=["team_id"],
    value_type=ValueType.STRING,
    tags={
        "sport": "esports",
        "entity_type": "specialized",
        "version": "1.0.0",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="game_type", dtype=String, description="Primary game (CS:GO, LoL, Dota2, etc.)"),
        Field(name="world_championships", dtype=Int32, description="World championships won"),
        Field(name="major_tournament_wins", dtype=Int32, description="Major tournament wins"),
        Field(name="total_prize_money_usd", dtype=Float64, description="Total prize money in USD"),
        Field(name="current_world_ranking", dtype=Int32, description="Current world ranking"),
        Field(name="team_organization", dtype=String, description="Esports organization name"),
        Field(name="roster_stability_months", dtype=Int32, description="Roster stability in months"),
        Field(name="coaching_staff_count", dtype=Int32, description="Number of coaching staff"),
        Field(name="analysts_count", dtype=Int32, description="Number of analysts"),
        Field(name="gaming_house", dtype=Bool, description="Whether team has gaming house"),
        Field(name="sponsorship_tier", dtype=String, description="Sponsorship tier (S/A/B/C)"),
    ],
)

# Historical Team Entity (for time-series analysis)
historical_team_entity = Entity(
    name="historical_team",
    description="Historical team entity with temporal dimension",
    join_keys=["team_id", "season_year"],
    value_type=ValueType.STRING,
    tags={
        "entity_type": "temporal",
        "domain": "sports",
        "owner": "analytics_team",
        "version": "1.0.0",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="season_year", dtype=Int32, description="Season year"),
        Field(name="league_position", dtype=Int32, description="Final league position"),
        Field(name="points", dtype=Int32, description="Total points"),
        Field(name="matches_played", dtype=Int32, description="Matches played"),
        Field(name="matches_won", dtype=Int32, description="Matches won"),
        Field(name="matches_drawn", dtype=Int32, description="Matches drawn"),
        Field(name="matches_lost", dtype=Int32, description="Matches lost"),
        Field(name="goals_for", dtype=Int32, description="Goals scored"),
        Field(name="goals_against", dtype=Int32, description="Goals conceded"),
        Field(name="goal_difference", dtype=Int32, description="Goal difference"),
        Field(name="home_record", dtype=String, description="Home record (W-D-L)"),
        Field(name="away_record", dtype=String, description="Away record (W-D-L)"),
        Field(name="cup_performance", dtype=String, description="Cup performance description"),
        Field(name="european_performance", dtype=String, description="European performance description"),
        Field(name="manager_name", dtype=String, description="Manager name for season"),
        Field(name="top_scorer", dtype=String, description="Top scorer name"),
        Field(name="top_scorer_goals", dtype=Int32, description="Top scorer goals"),
        Field(name="avg_attendance", dtype=Int32, description="Average attendance"),
        Field(name="transfer_spending_usd", dtype=Float64, description="Transfer spending in USD"),
        Field(name="transfer_income_usd", dtype=Float64, description="Transfer income in USD"),
        Field(name="net_transfer_spend_usd", dtype=Float64, description="Net transfer spend in USD"),
        Field(name="season_rating", dtype=Float32, description="Overall season rating (0-100)"),
    ],
)

# Team Performance Entity (for real-time updates)
team_performance_entity = Entity(
    name="team_performance",
    description="Real-time team performance entity",
    join_keys=["team_id", "match_id", "timestamp"],
    value_type=ValueType.STRING,
    tags={
        "entity_type": "realtime",
        "domain": "sports",
        "owner": "realtime_team",
        "version": "2.0.0",
        "freshness_requirement": "seconds",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="match_id", dtype=String),
        Field(name="timestamp", dtype=UnixTimestamp),
        Field(name="current_score", dtype=Int32, description="Current score in match"),
        Field(name="possession_percentage", dtype=Float32, description="Current possession percentage"),
        Field(name="shots_on_target", dtype=Int32, description="Shots on target"),
        Field(name="shots_off_target", dtype=Int32, description="Shots off target"),
        Field(name="total_shots", dtype=Int32, description="Total shots"),
        Field(name="corners", dtype=Int32, description="Corner kicks"),
        Field(name="fouls", dtype=Int32, description="Fouls committed"),
        Field(name="yellow_cards", dtype=Int32, description="Yellow cards"),
        Field(name="red_cards", dtype=Int32, description="Red cards"),
        Field(name="offsides", dtype=Int32, description="Offsides"),
        Field(name="saves", dtype=Int32, description="Goalkeeper saves"),
        Field(name="passes_completed", dtype=Int32, description="Passes completed"),
        Field(name="pass_accuracy", dtype=Float32, description="Pass accuracy percentage"),
        Field(name="aerial_duels_won", dtype=Int32, description="Aerial duels won"),
        Field(name="tackles_won", dtype=Int32, description="Tackles won"),
        Field(name="interceptions", dtype=Int32, description="Interceptions"),
        Field(name="clearances", dtype=Int32, description="Clearances"),
        Field(name="blocks", dtype=Int32, description="Blocks"),
        Field(name="expected_goals", dtype=Float32, description="Expected goals"),
        Field(name="expected_assists", dtype=Float32, description="Expected assists"),
        Field(name="expected_points", dtype=Float32, description="Expected points"),
        Field(name="momentum_score", dtype=Float32, description="Momentum score (0-100)"),
        Field(name="fatigue_index", dtype=Float32, description="Fatigue index (0-100)"),
        Field(name="pressure_index", dtype=Float32, description="Pressure index (0-100)"),
    ],
)

# Team Form Entity (for current form tracking)
team_form_entity = Entity(
    name="team_form",
    description="Team current form entity",
    join_keys=["team_id", "calculation_date"],
    value_type=ValueType.STRING,
    tags={
        "entity_type": "analytical",
        "domain": "sports",
        "owner": "analytics_team",
        "version": "1.5.0",
        "freshness_requirement": "daily",
    },
    schema=[
        Field(name="team_id", dtype=String),
        Field(name="calculation_date", dtype=UnixTimestamp),
        Field(name="form_points_last_5", dtype=Int32, description="Form points from last 5 matches"),
        Field(name="form_points_last_10", dtype=Int32, description="Form points from last 10 matches"),
        Field(name="win_streak", dtype=Int32, description="Current win streak"),
        Field(name="unbeaten_streak", dtype=Int32, description="Current unbeaten streak"),
        Field(name="losing_streak", dtype=Int32, description="Current losing streak"),
        Field(name="home_form_points", dtype=Int32, description="Form points at home"),
        Field(name="away_form_points", dtype=Int32, description="Form points away"),
        Field(name="form_rating", dtype=Float32, description="Overall form rating (0-100)"),
        Field(name="offensive_form_rating", dtype=Float32, description="Offensive form rating"),
        Field(name="defensive_form_rating", dtype=Float32, description="Defensive form rating"),
        Field(name="momentum_index", dtype=Float32, description="Momentum index (-100 to 100)"),
        Field(name="consistency_score", dtype=Float32, description="Performance consistency score"),
        Field(name="clutch_performance_score", dtype=Float32, description="Clutch performance score"),
        Field(name="recovery_score", dtype=Float32, description="Recovery from losing positions"),
        Field(name="big_game_performance", dtype=Float32, description="Performance in big games"),
    ],
)

# ============================================================================
# ENTITY REGISTRY AND MANAGEMENT
# ============================================================================

class TeamEntityRegistry:
    """Registry for managing all team entities"""
    
    def __init__(self):
        self._entities = {}
        self._initialize_registry()
    
    def _initialize_registry(self):
        """Initialize the entity registry"""
        self._entities = {
            "team": team_entity,
            "league": league_entity,
            "football_team": football_team_entity,
            "basketball_team": basketball_team_entity,
            "tennis_team": tennis_team_entity,
            "esports_team": esports_team_entity,
            "historical_team": historical_team_entity,
            "team_performance": team_performance_entity,
            "team_form": team_form_entity,
        }
        
        # Create entity relationships
        self._relationships = {
            "team": {
                "specialized_by": ["football_team", "basketball_team", "tennis_team", "esports_team"],
                "temporal_versions": ["historical_team"],
                "real_time_versions": ["team_performance"],
                "analytical_versions": ["team_form"],
                "references": ["league"],
            },
            "football_team": {
                "extends": ["team"],
                "related_to": ["historical_team", "team_performance", "team_form"],
            },
            "basketball_team": {
                "extends": ["team"],
                "related_to": ["historical_team", "team_performance", "team_form"],
            },
            "tennis_team": {
                "extends": ["team"],
                "related_to": ["historical_team", "team_performance", "team_form"],
            },
            "esports_team": {
                "extends": ["team"],
                "related_to": ["historical_team", "team_performance", "team_form"],
            },
        }
    
    def get_entity(self, entity_name: str) -> Optional[Entity]:
        """Get entity by name"""
        return self._entities.get(entity_name)
    
    def get_all_entities(self) -> List[Entity]:
        """Get all entities"""
        return list(self._entities.values())
    
    def get_entities_by_sport(self, sport: str) -> List[Entity]:
        """Get entities for a specific sport"""
        sport_entities = []
        for name, entity in self._entities.items():
            tags = entity.tags or {}
            if tags.get("sport") == sport:
                sport_entities.append(entity)
            elif sport == "all" and name != "team" and name != "league":
                sport_entities.append(entity)
        
        # Always include the base team entity
        if "team" in self._entities and sport != "all":
            sport_entities.append(self._entities["team"])
        
        return sport_entities
    
    def get_entity_relationships(self, entity_name: str) -> Dict:
        """Get relationships for an entity"""
        return self._relationships.get(entity_name, {})
    
    def get_join_keys(self, entity_name: str) -> List[str]:
        """Get join keys for an entity"""
        entity = self.get_entity(entity_name)
        if entity:
            return entity.join_keys
        return []
    
    def create_team_metadata_entity(self, metadata: TeamMetadata) -> Dict:
        """Create entity data from team metadata"""
        return {
            "team_id": metadata.team_id,
            "canonical_name": metadata.canonical_name,
            "short_name": metadata.short_name,
            "abbreviation": metadata.abbreviation,
            "display_name": metadata.display_name,
            "founded_year": metadata.founded_year,
            "dissolved_year": metadata.dissolved_year,
            "is_active": metadata.is_active,
            "sport_type": metadata.sport_type.value,
            "team_type": metadata.team_type.value,
            "competition_level": metadata.competition_level.value,
            "country": metadata.country,
            "country_code": metadata.country_code,
            "region": metadata.region,
            "city": metadata.city,
            "latitude": metadata.latitude,
            "longitude": metadata.longitude,
            "timezone": metadata.timezone,
            "elevation_m": metadata.elevation_m,
            "stadium_name": metadata.stadium_name,
            "stadium_type": metadata.stadium_type.value,
            "stadium_capacity": metadata.stadium_capacity,
            "stadium_built_year": metadata.stadium_built_year,
            "stadium_pitch_type": metadata.stadium_pitch_type,
            "stadium_roof_type": metadata.stadium_roof_type,
            "club_colors": metadata.club_colors,
            "nicknames": metadata.nicknames,
            "website": metadata.website,
            "ownership_type": metadata.ownership_type.value,
            "owner_name": metadata.owner_name,
            "annual_revenue_usd": metadata.annual_revenue_usd,
            "market_value_usd": metadata.market_value_usd,
            "league_id": metadata.league_id,
            "league_name": metadata.league_name,
            "division": metadata.division,
            "current_position": metadata.current_position,
            "total_titles": metadata.total_titles,
            "domestic_titles": metadata.domestic_titles,
            "international_titles": metadata.international_titles,
            "historical_performance_rating": metadata.historical_performance_rating,
            "playing_style": metadata.playing_style,
            "formation_preference": metadata.formation_preference,
            "attack_rating": metadata.attack_rating,
            "defense_rating": metadata.defense_rating,
            "midfield_rating": metadata.midfield_rating,
            "squad_size": metadata.squad_size,
            "avg_player_age": metadata.avg_player_age,
            "avg_player_value_usd": metadata.avg_player_value_usd,
            "total_squad_value_usd": metadata.total_squad_value_usd,
            "foreign_players_percentage": metadata.foreign_players_percentage,
            "created_at": int(metadata.created_at.timestamp()),
            "updated_at": int(metadata.updated_at.timestamp()),
            "valid_from": int(metadata.valid_from.timestamp()),
            "valid_to": int(metadata.valid_to.timestamp()) if metadata.valid_to else None,
            "data_quality_score": metadata.data_quality_score,
            "completeness_score": metadata.completeness_score,
            "freshness_days": metadata.freshness_days,
            "source_count": metadata.source_count,
            "version": metadata.version,
            "source_system": metadata.source_system,
            "is_verified": metadata.is_verified,
            "needs_review": metadata.needs_review,
        }

# ============================================================================
# ENTITY VALIDATION AND UTILITIES
# ============================================================================

class TeamEntityValidator:
    """Validator for team entities"""
    
    @staticmethod
    def validate_team_id(team_id: str) -> bool:
        """Validate team ID format"""
        if not team_id or not isinstance(team_id, str):
            return False
        
        # Basic validation: alphanumeric with underscores and hyphens
        import re
        pattern = r'^[a-zA-Z0-9_\-]+$'
        return bool(re.match(pattern, team_id))
    
    @staticmethod
    def validate_team_metadata(metadata: TeamMetadata) -> List[str]:
        """Validate team metadata and return list of errors"""
        errors = []
        
        # Required field validation
        if not metadata.team_id:
            errors.append("team_id is required")
        if not metadata.canonical_name:
            errors.append("canonical_name is required")
        if not metadata.sport_type:
            errors.append("sport_type is required")
        
        # Team ID format validation
        if not TeamEntityValidator.validate_team_id(metadata.team_id):
            errors.append(f"Invalid team_id format: {metadata.team_id}")
        
        # Year validation
        if metadata.founded_year and (metadata.founded_year < 1800 or metadata.founded_year > 2100):
            errors.append(f"Invalid founded_year: {metadata.founded_year}")
        
        if metadata.dissolved_year and (metadata.dissolved_year < 1800 or metadata.dissolved_year > 2100):
            errors.append(f"Invalid dissolved_year: {metadata.dissolved_year}")
        
        if metadata.founded_year and metadata.dissolved_year and metadata.dissolved_year < metadata.founded_year:
            errors.append(f"dissolved_year ({metadata.dissolved_year}) cannot be before founded_year ({metadata.founded_year})")
        
        # Stadium capacity validation
        if metadata.stadium_capacity and metadata.stadium_capacity < 0:
            errors.append(f"Invalid stadium_capacity: {metadata.stadium_capacity}")
        
        # Financial validation
        if metadata.annual_revenue_usd and metadata.annual_revenue_usd < 0:
            errors.append(f"Invalid annual_revenue_usd: {metadata.annual_revenue_usd}")
        
        if metadata.market_value_usd and metadata.market_value_usd < 0:
            errors.append(f"Invalid market_value_usd: {metadata.market_value_usd}")
        
        if metadata.debt_usd and metadata.debt_usd < 0:
            errors.append(f"Invalid debt_usd: {metadata.debt_usd}")
        
        # Rating validation (0-100)
        ratings_to_check = [
            ("historical_performance_rating", metadata.historical_performance_rating),
            ("attack_rating", metadata.attack_rating),
            ("defense_rating", metadata.defense_rating),
            ("midfield_rating", metadata.midfield_rating),
            ("data_quality_score", metadata.data_quality_score),
            ("completeness_score", metadata.completeness_score),
        ]
        
        for field_name, value in ratings_to_check:
            if value is not None and (value < 0 or value > 100):
                errors.append(f"Invalid {field_name}: {value}. Must be between 0 and 100")
        
        # Percentage validation
        if metadata.foreign_players_percentage and (metadata.foreign_players_percentage < 0 or metadata.foreign_players_percentage > 100):
            errors.append(f"Invalid foreign_players_percentage: {metadata.foreign_players_percentage}. Must be between 0 and 100")
        
        # Squad validation
        if metadata.squad_size and metadata.squad_size < 0:
            errors.append(f"Invalid squad_size: {metadata.squad_size}")
        
        if metadata.avg_player_age and (metadata.avg_player_age < 16 or metadata.avg_player_age > 40):
            errors.append(f"Invalid avg_player_age: {metadata.avg_player_age}. Must be between 16 and 40")
        
        # Temporal validation
        if metadata.valid_to and metadata.valid_from and metadata.valid_to < metadata.valid_from:
            errors.append(f"valid_to ({metadata.valid_to}) cannot be before valid_from ({metadata.valid_from})")
        
        return errors
    
    @staticmethod
    def generate_team_id(name: str, country_code: str = "", sport: str = "football") -> str:
        """Generate a standardized team ID"""
        import re
        
        # Clean the name
        cleaned_name = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        cleaned_name = cleaned_name.lower().strip()
        cleaned_name = re.sub(r'\s+', '_', cleaned_name)
        
        # Add sport prefix
        sport_prefix = sport[:3].lower()
        
        # Add country code if provided
        if country_code:
            country_part = country_code.lower()
            team_id = f"{sport_prefix}_{country_part}_{cleaned_name}"
        else:
            team_id = f"{sport_prefix}_{cleaned_name}"
        
        return team_id

# ============================================================================
# ENTITY FACTORY AND BUILDER
# ============================================================================

class TeamEntityFactory:
    """Factory for creating team entities"""
    
    @staticmethod
    def create_football_team(
        name: str,
        country: str,
        league: str,
        founded_year: Optional[int] = None,
        **kwargs
    ) -> TeamMetadata:
        """Create a football team metadata object"""
        team_id = TeamEntityValidator.generate_team_id(name, country_code=country[:2].upper() if country else "", sport="football")
        
        metadata = TeamMetadata(
            team_id=team_id,
            canonical_name=name,
            short_name=name[:15],
            abbreviation=name[:3].upper() if len(name) >= 3 else name.upper(),
            display_name=name,
            sport_type=SportType.FOOTBALL,
            team_type=TeamType.CLUB,
            country=country,
            league_name=league,
            founded_year=founded_year,
            **kwargs
        )
        
        return metadata
    
    @staticmethod
    def create_basketball_team(
        name: str,
        country: str,
        league: str,
        **kwargs
    ) -> TeamMetadata:
        """Create a basketball team metadata object"""
        team_id = TeamEntityValidator.generate_team_id(name, country_code=country[:2].upper() if country else "", sport="basketball")
        
        metadata = TeamMetadata(
            team_id=team_id,
            canonical_name=name,
            short_name=name[:15],
            abbreviation=name[:3].upper() if len(name) >= 3 else name.upper(),
            display_name=name,
            sport_type=SportType.BASKETBALL,
            team_type=TeamType.CLUB,
            country=country,
            league_name=league,
            **kwargs
        )
        
        return metadata
    
    @staticmethod
    def create_esports_team(
        name: str,
        game_type: str,
        organization: str,
        **kwargs
    ) -> TeamMetadata:
        """Create an esports team metadata object"""
        team_id = TeamEntityValidator.generate_team_id(name, sport="esports")
        
        metadata = TeamMetadata(
            team_id=team_id,
            canonical_name=name,
            short_name=name[:15],
            abbreviation=name[:3].upper() if len(name) >= 3 else name.upper(),
            display_name=name,
            sport_type=SportType.ESPORTS,
            team_type=TeamType.ESPORTS,
            country="",  # Esports teams can be international
            league_name=game_type,
            **kwargs
        )
        
        return metadata

# ============================================================================
# EXPORTS
# ============================================================================

# Main entities
__all__ = [
    # Core entities
    "team_entity",
    "league_entity",
    
    # Sport-specific entities
    "football_team_entity",
    "basketball_team_entity",
    "tennis_team_entity",
    "esports_team_entity",
    
    # Specialized entities
    "historical_team_entity",
    "team_performance_entity",
    "team_form_entity",
    
    # Enums
    "SportType",
    "TeamType",
    "CompetitionLevel",
    "OwnershipType",
    "StadiumType",
    
    # Dataclasses
    "TeamMetadata",
    
    # Registry and management
    "TeamEntityRegistry",
    
    # Validation
    "TeamEntityValidator",
    
    # Factory
    "TeamEntityFactory",
]

# ============================================================================
# DOCUMENTATION AND USAGE
# ============================================================================

"""
TEAM ENTITIES MODULE - Goat Prediction Ultimate

This module provides comprehensive entity definitions for sports teams across
all supported sports. Entities are the foundation of the feature store and
enable feature joining, aggregation, and retrieval.

KEY CONCEPTS:
1. Primary Entities: Core team data that rarely changes
2. Specialized Entities: Sport-specific team attributes
3. Temporal Entities: Historical team data for time-series analysis
4. Real-time Entities: Live match performance data
5. Analytical Entities: Calculated metrics and form data

USAGE EXAMPLES:

1. Registering entities with Feast:
```python
from feast import FeatureStore
from entities.teams import team_entity, football_team_entity

store = FeatureStore(repo_path=".")
store.apply([team_entity, football_team_entity])
