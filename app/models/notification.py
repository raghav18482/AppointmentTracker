from sqlalchemy import Column, String, ForeignKey, Integer, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import BaseModel


class NotificationStatus(str, enum.Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    READ = "read"


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


class Notification(BaseModel):
    """Notification model for tracking message delivery."""
    
    __tablename__ = "notifications"
    
    queue_item_id = Column(UUID(as_uuid=True), ForeignKey("queue_items.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    
    notification_type = Column(SQLEnum(NotificationType, native_enum=False), nullable=False, default=NotificationType.WHATSAPP, index=True)
    recipient_phone = Column(String, nullable=False, index=True)
    recipient_email = Column(String, nullable=True)
    
    message_template = Column(String, nullable=True)  # Template name if using templates
    message_body = Column(Text, nullable=False)
    
    status = Column(SQLEnum(NotificationStatus, native_enum=False), nullable=False, default=NotificationStatus.PENDING, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    external_id = Column(String, nullable=True, index=True)  # ID from Twilio/Gupshup
    error_message = Column(Text, nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    queue_item = relationship("QueueItem", back_populates="notifications")
    customer = relationship("Customer", back_populates="notifications")
    business = relationship("Business", back_populates="notifications")

