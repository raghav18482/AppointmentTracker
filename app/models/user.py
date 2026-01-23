from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user_businesses = relationship("UserBusiness", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def businesses(self):
        """Get all businesses associated with this user."""
        return [ub.business for ub in self.user_businesses]

