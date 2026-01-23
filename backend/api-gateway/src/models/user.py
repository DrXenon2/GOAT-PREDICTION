"""
User model for authentication and authorization.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User roles enumeration."""
    
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SYSTEM = "system"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Personal information
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    
    # Subscription
    subscription_tier = Column(String(50))
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Preferences
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    currency = Column(String(3), default="USD")
    
    # Limits
    daily_prediction_limit = Column(Integer, default=10)
    api_rate_limit = Column(Integer, default=100)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    # tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    # predictions = relationship("Prediction", back_populates="user")
    # bets = relationship("Bet", back_populates="user")
    
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return None
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    @property
    def is_system(self) -> bool:
        """Check if user is system user."""
        return self.role == UserRole.SYSTEM
    
    @property
    def is_subscription_active(self) -> bool:
        """Check if user's subscription is active."""
        if not self.subscription_expires_at:
            return False
        
        return self.subscription_expires_at > datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
