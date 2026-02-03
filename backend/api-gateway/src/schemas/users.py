"""
GOAT PREDICTION ULTIMATE - User Schemas
Schémas pour les utilisateurs
"""

from pydantic import BaseModel, Field, validator, EmailStr, constr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import re


# ============================================
# ENUMS
# ============================================

class UserRole(str, Enum):
    """Rôles utilisateur"""
    USER = "user"
    PREMIUM = "premium"
    VIP = "vip"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"
    MODERATOR = "moderator"


class UserStatus(str, Enum):
    """Statuts utilisateur"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"
    DELETED = "deleted"


class SubscriptionTier(str, Enum):
    """Niveaux d'abonnement"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


class NotificationChannel(str, Enum):
    """Canaux de notification"""
    EMAIL = "email"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"


# ============================================
# REQUEST SCHEMAS
# ============================================

class UserRegister(BaseModel):
    """Inscription utilisateur"""
    email: EmailStr = Field(..., description="Email valide")
    username: constr(min_length=3, max_length=50) = Field(
        ...,
        description="Nom d'utilisateur (3-50 caractères, alphanumérique)"
    )
    password: constr(min_length=8, max_length=128) = Field(
        ...,
        description="Mot de passe (min 8 caractères)"
    )
    confirm_password: str = Field(..., description="Confirmation du mot de passe")
    
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    # Acceptation des conditions
    accept_terms: bool = Field(..., description="Acceptation des CGU")
    accept_privacy: bool = Field(..., description="Acceptation de la politique de confidentialité")
    
    # Marketing
    marketing_consent: bool = Field(default=False, description="Consentement marketing")
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Valide que le username est alphanumérique"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username doit être alphanumérique (_, - autorisés)')
        return v.lower()
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Valide que les mots de passe correspondent"""
        if 'password' in values and v != values['password']:
            raise ValueError('Les mots de passe ne correspondent pas')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        """Valide la force du mot de passe"""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                'Le mot de passe doit contenir majuscules, minuscules et chiffres'
            )
        
        return v
    
    @validator('accept_terms')
    def terms_must_be_accepted(cls, v):
        """Les CGU doivent être acceptées"""
        if not v:
            raise ValueError('Vous devez accepter les conditions générales')
        return v
    
    @validator('accept_privacy')
    def privacy_must_be_accepted(cls, v):
        """La politique de confidentialité doit être acceptée"""
        if not v:
            raise ValueError('Vous devez accepter la politique de confidentialité')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123",
                "first_name": "John",
                "last_name": "Doe",
                "accept_terms": True,
                "accept_privacy": True,
                "marketing_consent": False
            }
        }


class UserLogin(BaseModel):
    """Connexion utilisateur"""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Mot de passe")
    remember_me: bool = Field(default=False, description="Se souvenir de moi")
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123",
                "remember_me": True
            }
        }


class UserUpdate(BaseModel):
    """Mise à jour du profil"""
    email: Optional[EmailStr] = None
    username: Optional[constr(min_length=3, max_length=50)] = None
    
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    phone: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = None
    
    # Social links
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    website: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+33612345678",
                "bio": "Passionné de paris sportifs et d'analyse de données",
                "twitter": "https://twitter.com/johndoe"
            }
        }


class PasswordChange(BaseModel):
    """Changement de mot de passe"""
    current_password: str = Field(..., description="Mot de passe actuel")
    new_password: constr(min_length=8, max_length=128) = Field(
        ...,
        description="Nouveau mot de passe"
    )
    confirm_password: str = Field(..., description="Confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Les mots de passe ne correspondent pas')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "OldPass123",
                "new_password": "NewSecurePass456",
                "confirm_password": "NewSecurePass456"
            }
        }


# ============================================
# RESPONSE SCHEMAS
# ============================================

class UserResponse(BaseModel):
    """Réponse utilisateur"""
    id: uuid.UUID
    email: EmailStr
    username: str
    
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    role: UserRole
    status: UserStatus
    subscription_tier: SubscriptionTier
    
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Stats
    total_predictions: int = 0
    correct_predictions: int = 0
    total_bets: int = 0
    total_profit: float = 0.0
    
    # Flags
    is_verified: bool = False
    is_active: bool = True
    
    # Dates
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    # Abonnement
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    
    @property
    def accuracy(self) -> float:
        """Calcule la précision"""
        if self.total_predictions == 0:
            return 0.0
        return round((self.correct_predictions / self.total_predictions) * 100, 2)
    
    @property
    def full_name(self) -> str:
        """Nom complet"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "role": "premium",
                "status": "active",
                "subscription_tier": "premium",
                "avatar_url": "https://example.com/avatars/johndoe.jpg",
                "total_predictions": 250,
                "correct_predictions": 175,
                "total_bets": 100,
                "total_profit": 1250.50,
                "is_verified": True,
                "is_active": True,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2026-02-03T10:00:00Z",
                "last_login": "2026-02-03T09:30:00Z"
            }
        }


class UserPublic(BaseModel):
    """Profil public"""
    id: uuid.UUID
    username: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    subscription_tier: SubscriptionTier
    
    # Stats publiques
    total_predictions: int = 0
    accuracy: float = 0.0
    
    created_at: datetime
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "johndoe",
                "subscription_tier": "premium",
                "total_predictions": 250,
                "accuracy": 70.0,
                "created_at": "2025-01-15T10:00:00Z"
            }
        }


class UserStats(BaseModel):
    """Statistiques utilisateur"""
    user_id: uuid.UUID
    
    # Prédictions
    total_predictions: int = 0
    correct_predictions: int = 0
    accuracy: float = 0.0
    
    # Betting
    total_bets: int = 0
    winning_bets: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    roi: float = 0.0
    
    # Par sport
    by_sport: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Par marché
    by_market: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Historique
    last_30_days: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        orm_mode = True


class UserPreferences(BaseModel):
    """Préférences utilisateur"""
    user_id: uuid.UUID
    
    # Notifications
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    
    notification_predictions: bool = True
    notification_bets: bool = True
    notification_marketing: bool = False
    
    # Sports favoris
    favorite_sports: List[str] = Field(default_factory=list)
    favorite_leagues: List[str] = Field(default_factory=list)
    favorite_teams: List[str] = Field(default_factory=list)
    
    # Betting
    default_stake: float = 10.0
    max_stake: float = 100.0
    auto_bet: bool = False
    
    # Affichage
    theme: str = Field(default="light", regex="^(light|dark|auto)$")
    language: str = Field(default="en", regex="^(en|fr|es|de|it)$")
    timezone: str = "UTC"
    currency: str = Field(default="USD", regex="^(USD|EUR|GBP|BTC|ETH)$")
    
    # Confidentialité
    public_profile: bool = True
    show_stats: bool = True
    
    class Config:
        orm_mode = True


class UserActivity(BaseModel):
    """Activité utilisateur"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    
    activity_type: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


# ============================================
# AUTHENTICATION SCHEMAS
# ============================================

class TokenPair(BaseModel):
    """Paire de tokens JWT"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class LoginResponse(BaseModel):
    """Réponse de connexion"""
    user: UserResponse
    tokens: TokenPair
    
    class Config:
        schema_extra = {
            "example": {
                "user": {},
                "tokens": {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    "token_type": "bearer",
                    "expires_in": 3600
                }
            }
        }


class RefreshTokenRequest(BaseModel):
    """Requête de refresh token"""
    refresh_token: str = Field(..., min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }
        }
