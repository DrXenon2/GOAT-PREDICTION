"""
GOAT PREDICTION ULTIMATE - Admin Models
Modèles de données pour les routes admin
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class AlertSeverity(str, Enum):
    """Niveaux de sévérité des alertes"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActivityType(str, Enum):
    """Types d'activité"""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    PREDICTION_CREATE = "prediction_create"
    BET_PLACED = "bet_placed"
    SUBSCRIPTION_CHANGE = "subscription_change"
    ADMIN_ACTION = "admin_action"
    SYSTEM_ERROR = "system_error"


class AdminStats(BaseModel):
    """Statistiques administrateur"""
    # Utilisateurs
    total_users: int = 0
    active_users: int = 0
    new_users_today: int = 0
    new_users_this_week: int = 0
    new_users_this_month: int = 0
    
    # Prédictions
    total_predictions: int = 0
    predictions_today: int = 0
    predictions_accuracy: float = 0.0
    
    # Betting
    total_bets: int = 0
    bets_today: int = 0
    total_wagered: float = 0.0
    total_profit: float = 0.0
    
    # Système
    system_uptime: float = 0.0  # en secondes
    api_requests_today: int = 0
    average_response_time: float = 0.0  # en ms
    error_rate: float = 0.0  # en pourcentage
    
    # Performance
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    
    # Base de données
    db_connections: int = 0
    db_size: float = 0.0  # en MB
    
    class Config:
        orm_mode = True


class SystemMetrics(BaseModel):
    """Métriques système en temps réel"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # API
    requests_per_second: float = 0.0
    active_connections: int = 0
    average_latency: float = 0.0
    
    # Utilisateurs
    active_users: int = 0
    online_users: int = 0
    
    # Ressources
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    
    # Base de données
    db_connections: int = 0
    db_queries_per_second: float = 0.0
    
    # Cache
    cache_hit_rate: float = 0.0
    cache_size: int = 0


class ActivityLog(BaseModel):
    """Log d'activité"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    
    activity_type: ActivityType
    description: str
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
        use_enum_values = True


class SystemAlert(BaseModel):
    """Alerte système"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    
    severity: AlertSeverity
    title: str
    message: str
    
    source: str  # Module/service source
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    is_active: bool = True
    is_acknowledged: bool = False
    acknowledged_by: Optional[uuid.UUID] = None
    acknowledged_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        use_enum_values = True


class AdminDashboard(BaseModel):
    """Dashboard administrateur"""
    stats: AdminStats
    recent_activity: List[ActivityLog] = Field(default_factory=list)
    alerts: List[SystemAlert] = Field(default_factory=list)
    realtime_metrics: SystemMetrics
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserManagement(BaseModel):
    """Gestion utilisateur par admin"""
    user_id: uuid.UUID
    action: str  # suspend, activate, ban, promote, demote
    reason: Optional[str] = None
    duration: Optional[int] = None  # en jours (pour suspension temporaire)
    
    class Config:
        orm_mode = True


class SystemConfig(BaseModel):
    """Configuration système"""
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    maintenance_mode: bool = False
    maintenance_message: Optional[str] = None


class BackupInfo(BaseModel):
    """Information de backup"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    backup_type: str  # full, incremental
    size: int  # en bytes
    status: str  # pending, completed, failed
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
