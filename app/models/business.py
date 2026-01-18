from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class BusinessType(str, enum.Enum):
    """Business type enumeration."""
    CLINIC = "clinic"
    HOSPITAL = "hospital"
    SALON = "salon"
    SPA = "spa"
    FITNESS = "fitness"
    OTHER = "other"


class UserRole(str, enum.Enum):
    """User role in a business."""
    OWNER = "owner"
    MANAGER = "manager"
    COUNTER = "counter"


class Business(BaseModel):
    """Business model for multi-tenant support."""
    
    __tablename__ = "businesses"
    
    name = Column(String, nullable=False, index=True)
    type = Column(SQLEnum(BusinessType, native_enum=False), nullable=False, default=BusinessType.OTHER)
    timezone = Column(String, nullable=False, default="UTC")
    
    # Relationships
    user_businesses = relationship("UserBusiness", back_populates="business", cascade="all, delete-orphan")
    counters = relationship("Counter", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business", cascade="all, delete-orphan")
    queue_items = relationship("QueueItem", back_populates="business", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="business", cascade="all, delete-orphan")


class UserBusiness(BaseModel):
    """User-Business mapping table with roles."""
    
    __tablename__ = "user_businesses"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(UserRole, native_enum=False), nullable=False, default=UserRole.COUNTER)
    
    # Relationships
    user = relationship("User", back_populates="user_businesses")
    business = relationship("Business", back_populates="user_businesses")
    
    # Unique constraint: a user can only have one role per business
    __table_args__ = (
        UniqueConstraint('user_id', 'business_id', name='uq_user_business'),
    )

