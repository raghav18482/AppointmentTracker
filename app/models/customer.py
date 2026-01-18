from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Customer(BaseModel):
    """Customer model for booking system."""
    
    __tablename__ = "customers"
    
    firstname = Column(String, nullable=False, index=True)
    lastname = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=False, index=True)
    whatsapp_enabled = Column(Boolean, default=False, nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationships
    business = relationship("Business", back_populates="customers")
    queue_items = relationship("QueueItem", back_populates="customer", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="customer", cascade="all, delete-orphan")
