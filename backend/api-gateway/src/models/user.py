"""
GOAT PREDICTION ULTIMATE - User Models
Modèles de données pour les utilisateurs
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator, constr
import uuid


class UserRole(str, Enum):
    """Rôles utilisateur"""
    USER = "user"
    PREMIUM = "premium"
    VIP = "vip"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class UserStatus(str, Enum):
    """Statuts utilisateur"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BANNED = "banned"
    PENDING = "pending"


class SubscriptionTier(str, Enum):
    """Niveaux d'abonnement"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


class UserBase(BaseModel):
    """Modèle de base utilisateur"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    username: constr(min_length=3, max_length=50) = Field(
        ..., 
        description="Nom d'utilisateur (3-50 caractères)"
    )
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Valide que le username est alphanumérique"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (-, _ allowed)')
        return v.lower()


class UserCreate(UserBase):
    """Modèle pour créer un utilisateur"""
    password: constr(min_length=8, max_length=128) = Field(
        ..., 
        description="Mot de passe (minimum 8 caractères)"
    )
    confirm_password: str = Field(..., description="Confirmation du mot de passe")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Valide que les mots de passe correspondent"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        """Valide la force du mot de passe"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                'Password must contain uppercase, lowercase, and digits'
            )
        
        return v


class UserUpdate(BaseModel):
    """Modèle pour mettre à jour un utilisateur"""
    email: Optional[EmailStr] = None
    username: Optional[constr(min_length=3, max_length=50)] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    preferences: Optional[Dict[str, Any]] = None


class UserInDB(UserBase):
    """Modèle utilisateur en base de données"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hashed_password: str
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    
    # Informations additionnelles
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    # Préférences utilisateur
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    # Métriques
    total_predictions: int = 0
    correct_predictions: int = 0
    total_bets: int = 0
    total_profit: float = 0.0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Flags
    is_verified: bool = False
    is_active: bool = True
    is_superuser: bool = False
    
    # Subscription
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        use_enum_values = True


class User(UserBase):
    """Modèle utilisateur (réponse API)"""
    id: uuid.UUID
    role: UserRole
    status: UserStatus
    subscription_tier: SubscriptionTier
    
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    
    total_predictions: int = 0
    correct_predictions: int = 0
    total_bets: int = 0
    total_profit: float = 0.0
    
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    
    is_verified: bool
    is_active: bool
    
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    
    @property
    def accuracy(self) -> float:
        """Calcule le taux de précision"""
        if self.total_predictions == 0:
            return 0.0
        return (self.correct_predictions / self.total_predictions) * 100
    
    @property
    def roi(self) -> float:
        """Calcule le ROI"""
        if self.total_bets == 0:
            return 0.0
        return (self.total_profit / self.total_bets) * 100
    
    class Config:
        orm_mode = True
        use_enum_values = True


class UserPublic(BaseModel):
    """Modèle utilisateur public (profil visible)"""
    id: uuid.UUID
    username: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    subscription_tier: SubscriptionTier
    
    total_predictions: int = 0
    accuracy: float = 0.0
    
    created_at: datetime
    
    class Config:
        orm_mode = True


class UserStats(BaseModel):
    """Statistiques utilisateur"""
    user_id: uuid.UUID
    
    # Prédictions
    total_predictions: int
    correct_predictions: int
    accuracy: float
    
    # Betting
    total_bets: int
    winning_bets: int
    win_rate: float
    total_profit: float
    roi: float
    
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
    
    # Préférences de notification
    email_notifications: bool = True
    push_notifications: bool = True
    sms_notifications: bool = False
    
    # Préférences de sport
    favorite_sports: List[str] = Field(default_factory=list)
    favorite_leagues: List[str] = Field(default_factory=list)
    favorite_teams: List[str] = Field(default_factory=list)
    
    # Préférences de betting
    default_stake: float = 10.0
    max_stake: float = 100.0
    auto_bet: bool = False
    
    # Préférences d'affichage
    theme: str = "light"
    language: str = "en"
    timezone: str = "UTC"
    currency: str = "USD"
    
    # Préférences de confidentialité
    public_profile: bool = True
    show_stats: bool = True
    
    class Config:
        orm_mode = True


class UserLogin(BaseModel):
    """Modèle de connexion"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")
    password: str = Field(..., description="Mot de passe")
    remember_me: bool = Field(default=False, description="Se souvenir de moi")


class UserLoginResponse(BaseModel):
    """Réponse de connexion"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class PasswordChange(BaseModel):
    """Changement de mot de passe"""
    current_password: str = Field(..., description="Mot de passe actuel")
    new_password: constr(min_length=8, max_length=128) = Field(
        ..., 
        description="Nouveau mot de passe"
    )
    confirm_password: str = Field(..., description="Confirmation du nouveau mot de passe")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordReset(BaseModel):
    """Réinitialisation de mot de passe"""
    email: EmailStr = Field(..., description="Email de l'utilisateur")


class PasswordResetConfirm(BaseModel):
    """Confirmation de réinitialisation"""
    token: str = Field(..., description="Token de réinitialisation")
    new_password: constr(min_length=8, max_length=128) = Field(
        ..., 
        description="Nouveau mot de passe"
    )
    confirm_password: str = Field(..., description="Confirmation")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class EmailVerification(BaseModel):
    """Vérification d'email"""
    token: str = Field(..., description="Token de vérification")


class UserList(BaseModel):
    """Liste paginée d'utilisateurs"""
    users: List[User]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserActivity(BaseModel):
    """Activité utilisateur"""
    user_id: uuid.UUID
    activity_type: str
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
